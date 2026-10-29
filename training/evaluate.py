"""
=============================================================================
FILE: training/evaluate.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation DSS
DESCRIPTION:
    Comprehensive evaluation suite for all trained models.
    Generates:
      - Accuracy, Precision, Recall, F1 (weighted + per-class)
      - ROC AUC (one-vs-rest, macro)
      - Confusion matrices (normalised and raw)
      - ROC curves
      - Training / validation curves
      - Feature importance (RF, XGB, LGB)
      - SHAP analysis (for tree models + deep model)
      - Classification reports
    Saves all plots to models/plots/ and metrics to models/metrics.json

    Usage:
        python training/evaluate.py
=============================================================================
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")           # non-interactive backend (safe for servers)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import joblib
import torch
import torch.nn.functional as F
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
    classification_report, roc_curve
)

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from training.preprocess import run_preprocessing, SEQUENCE_LENGTH

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
PLOTS_DIR  = os.path.join(MODELS_DIR, "plots")
LOG_DIR    = os.path.join(MODELS_DIR, "logs")
os.makedirs(PLOTS_DIR, exist_ok=True)
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CLASS_NAMES= ["Low", "Moderate", "High"]
PALETTE    = ["#2ecc71", "#f39c12", "#e74c3c"]


# ─────────────────────────────────────────────
# PREDICTION HELPERS
# ─────────────────────────────────────────────
def predict_sklearn(model, X: np.ndarray):
    y_pred  = model.predict(X)
    y_proba = model.predict_proba(X)
    return y_pred, y_proba


def predict_pytorch(model, X_seq: np.ndarray) -> tuple:
    model.eval().to(DEVICE)
    all_logits = []
    bs = 512
    with torch.no_grad():
        for i in range(0, len(X_seq), bs):
            Xb = torch.FloatTensor(X_seq[i:i+bs]).to(DEVICE)
            all_logits.append(model(Xb).cpu())
    logits = torch.cat(all_logits, dim=0)
    proba  = F.softmax(logits, dim=-1).numpy()
    preds  = np.argmax(proba, axis=1)
    return preds, proba


# ─────────────────────────────────────────────
# CORE METRICS
# ─────────────────────────────────────────────
def compute_metrics(name: str, y_true: np.ndarray,
                    y_pred: np.ndarray, y_proba: np.ndarray) -> dict:
    acc  = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average="weighted", zero_division=0)
    rec  = recall_score(y_true, y_pred, average="weighted",    zero_division=0)
    f1   = f1_score(y_true, y_pred, average="weighted",        zero_division=0)
    try:
        auc = roc_auc_score(y_true, y_proba, multi_class="ovr", average="macro")
    except Exception:
        auc = None

    metrics = {
        "model": name, "accuracy": round(acc, 4),
        "precision": round(prec, 4), "recall": round(rec, 4),
        "f1_score": round(f1, 4), "roc_auc": round(auc, 4) if auc else None,
    }
    print(f"\n── {name} ──────────────────────────")
    for k, v in metrics.items():
        if k != "model":
            print(f"  {k:12s}: {v}")
    print(classification_report(y_true, y_pred,
                                 target_names=CLASS_NAMES, zero_division=0))
    return metrics


# ─────────────────────────────────────────────
# CONFUSION MATRIX PLOT
# ─────────────────────────────────────────────
def plot_confusion_matrix(name: str, y_true: np.ndarray, y_pred: np.ndarray):
    cm      = confusion_matrix(y_true, y_pred)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"Confusion Matrix — {name}", fontsize=14, fontweight="bold")

    for ax, mat, title in zip(axes, [cm, cm_norm], ["Counts", "Normalised"]):
        sns.heatmap(mat, annot=True, fmt=".2f" if title == "Normalised" else "d",
                    xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES,
                    cmap="RdYlGn_r" if title == "Normalised" else "Blues",
                    ax=ax, linewidths=0.5)
        ax.set_title(title)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")

    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f"{name}_confusion_matrix.png"), dpi=150)
    plt.close()


# ─────────────────────────────────────────────
# ROC CURVE PLOT
# ─────────────────────────────────────────────
def plot_roc_curves(name: str, y_true: np.ndarray, y_proba: np.ndarray):
    from sklearn.preprocessing import label_binarize
    y_bin = label_binarize(y_true, classes=[0, 1, 2])

    fig, ax = plt.subplots(figsize=(7, 6))
    for i, (cls, color) in enumerate(zip(CLASS_NAMES, PALETTE)):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
        auc_val     = roc_auc_score(y_bin[:, i], y_proba[:, i])
        ax.plot(fpr, tpr, color=color, lw=2,
                label=f"{cls} (AUC={auc_val:.3f})")

    ax.plot([0, 1], [0, 1], "k--", lw=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"ROC Curves — {name}")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f"{name}_roc_curves.png"), dpi=150)
    plt.close()


# ─────────────────────────────────────────────
# TRAINING HISTORY CURVES
# ─────────────────────────────────────────────
def plot_training_curves(name: str):
    hist_path = os.path.join(LOG_DIR, f"{name}_history.json")
    if not os.path.exists(hist_path):
        return
    with open(hist_path) as f:
        history = json.load(f)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"Training Curves — {name}", fontsize=14, fontweight="bold")

    axes[0].plot(history["train_loss"], label="Train", color="#3498db")
    axes[0].plot(history["val_loss"],   label="Val",   color="#e74c3c")
    axes[0].set_title("Loss"); axes[0].set_xlabel("Epoch")
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

    axes[1].plot(history["train_acc"],  label="Train", color="#3498db")
    axes[1].plot(history["val_acc"],    label="Val",   color="#e74c3c")
    axes[1].set_title("Accuracy"); axes[1].set_xlabel("Epoch")
    axes[1].legend(); axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f"{name}_training_curves.png"), dpi=150)
    plt.close()


# ─────────────────────────────────────────────
# FEATURE IMPORTANCE (tree models)
# ─────────────────────────────────────────────
def plot_feature_importance(name: str, model, feature_cols: list, top_n: int = 25):
    try:
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        else:
            return

        idx = np.argsort(importances)[-top_n:]
        fig, ax = plt.subplots(figsize=(10, 8))
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(idx)))
        ax.barh([feature_cols[i] for i in idx], importances[idx], color=colors)
        ax.set_title(f"Feature Importance — {name} (Top {top_n})")
        ax.set_xlabel("Importance Score")
        ax.grid(True, axis="x", alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, f"{name}_feature_importance.png"), dpi=150)
        plt.close()
        print(f"  Feature importance plot saved for {name}")
    except Exception as e:
        print(f"  [WARN] Feature importance failed for {name}: {e}")


# ─────────────────────────────────────────────
# SHAP ANALYSIS
# ─────────────────────────────────────────────
def run_shap_analysis(name: str, model, X_test: np.ndarray, feature_cols: list):
    """SHAP summary plot for tree-based models."""
    try:
        import shap
        print(f"  Running SHAP analysis for {name} ...")
        X_sample = X_test[:500]   # use subset for speed

        if "random_forest" in name:
            explainer  = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_sample)
            # shap_values is a list of arrays for multiclass
            shap_arr   = np.abs(np.array(shap_values)).mean(axis=0)
        elif "xgboost" in name or "lightgbm" in name:
            explainer   = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_sample)
            shap_arr    = np.abs(np.array(shap_values)).mean(axis=0) if isinstance(shap_values, list) else np.abs(shap_values)
        else:
            return

        fig, ax = plt.subplots(figsize=(10, 8))
        mean_abs = shap_arr.mean(axis=0) if shap_arr.ndim == 2 else shap_arr
        idx = np.argsort(mean_abs)[-20:]
        ax.barh([feature_cols[i] for i in idx], mean_abs[idx], color="#8e44ad")
        ax.set_title(f"SHAP Feature Importance — {name}")
        ax.set_xlabel("Mean |SHAP Value|")
        ax.grid(True, axis="x", alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, f"{name}_shap.png"), dpi=150)
        plt.close()
        print(f"  SHAP plot saved for {name}")
    except Exception as e:
        print(f"  [WARN] SHAP analysis failed for {name}: {e}")


# ─────────────────────────────────────────────
# COMPARISON TABLE
# ─────────────────────────────────────────────
def plot_model_comparison(all_metrics: list):
    df = pd.DataFrame(all_metrics)
    df.sort_values("f1_score", ascending=False, inplace=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    x  = np.arange(len(df))
    w  = 0.18
    metrics = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    colors  = ["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"]

    for i, (m, c) in enumerate(zip(metrics, colors)):
        vals = [v if v is not None else 0 for v in df[m].tolist()]
        ax.bar(x + i * w, vals, w, label=m.replace("_", " ").title(), color=c)

    ax.set_xticks(x + w * 2)
    ax.set_xticklabels(df["model"].tolist(), rotation=20)
    ax.set_ylim(0.5, 1.02)
    ax.set_ylabel("Score")
    ax.set_title("Model Performance Comparison", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "model_comparison.png"), dpi=150)
    plt.close()
    print(f"\n[EVAL] Model comparison chart saved")
    print(df[["model", "accuracy", "f1_score", "roc_auc"]].to_string(index=False))


# ─────────────────────────────────────────────
# MAIN EVALUATION RUNNER
# ─────────────────────────────────────────────
def main():
    print("\n[EVAL] Loading preprocessed data ...")
    data = run_preprocessing(save_artifacts=False)
    feature_cols = data["feature_cols"]

    all_metrics = []

    # ── Sklearn models ─────────────────────────
    sklearn_models = {
        "random_forest": (data["X_test_flat"], data["y_test"]),
        "xgboost":       (data["X_test_flat"], data["y_test"]),
        "lightgbm":      (data["X_test_flat"], data["y_test"]),
    }

    for name, (X, y_true) in sklearn_models.items():
        path = os.path.join(MODELS_DIR, f"{name}.pkl")
        if not os.path.exists(path):
            print(f"  [SKIP] {name}.pkl not found")
            continue
        model = joblib.load(path)
        y_pred, y_proba = predict_sklearn(model, X)
        m = compute_metrics(name, y_true, y_pred, y_proba)
        all_metrics.append(m)
        plot_confusion_matrix(name, y_true, y_pred)
        plot_roc_curves(name, y_true, y_proba)
        plot_feature_importance(name, model, feature_cols)
        run_shap_analysis(name, model, X, feature_cols)

    # ── PyTorch models ─────────────────────────
    dl_models = ["lstm", "gru", "tcn", "artcn"]
    for name in dl_models:
        path = os.path.join(MODELS_DIR, f"{name}.pt")
        if not os.path.exists(path):
            print(f"  [SKIP] {name}.pt not found")
            continue
        # PyTorch 2.6+: need weights_only=False for full model objects we saved ourselves
        try:
            from training.model_artcn import ARTCN
            import torch.serialization as _ts
            _ts.add_safe_globals([ARTCN])
        except Exception:
            pass
        model = torch.load(path, map_location=DEVICE, weights_only=False)
        y_pred, y_proba = predict_pytorch(model, data["X_test_seq"])
        y_true = data["y_test_seq"]
        m = compute_metrics(name, y_true, y_pred, y_proba)
        all_metrics.append(m)
        plot_confusion_matrix(name, y_true, y_pred)
        plot_roc_curves(name, y_true, y_proba)
        plot_training_curves(name)

    # ── Comparison chart + save metrics ────────
    if all_metrics:
        plot_model_comparison(all_metrics)
        out_path = os.path.join(MODELS_DIR, "metrics.json")
        with open(out_path, "w") as f:
            json.dump(all_metrics, f, indent=2)
        print(f"\n[EVAL] All metrics saved → {out_path}")
        print(f"[EVAL] All plots saved  → {PLOTS_DIR}/")

    print("\n[EVAL] Evaluation complete.")


if __name__ == "__main__":
    main()
