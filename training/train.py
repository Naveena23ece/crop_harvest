"""
=============================================================================
FILE: training/train.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation DSS
DESCRIPTION:
    Main training script for all models:
      - Baseline ML: Random Forest, XGBoost, LightGBM
      - Baseline DL: LSTM, GRU
      - Proposed:    TCN (baseline), AR-TCN (proposed)

    Training strategy:
      - Temporal train/val/test split (no data leakage)
      - Early stopping based on validation loss
      - ReduceLROnPlateau learning rate scheduler
      - ModelCheckpoint saves best weights
      - All metrics logged to JSON for evaluation

    Run:
        python training/train.py --all
        python training/train.py --model artcn
=============================================================================
"""

import os
import sys
import json
import time
import argparse
import numpy as np
import joblib
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import ReduceLROnPlateau

# ML baselines
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics  import accuracy_score
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[WARN] xgboost not installed — skipping XGBoost training")
try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    print("[WARN] lightgbm not installed — skipping LightGBM training")

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from training.preprocess   import run_preprocessing, SEQUENCE_LENGTH
from training.model_artcn  import build_artcn

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
MODELS_DIR  = os.path.join(os.path.dirname(__file__), "..", "models")
LOG_DIR     = os.path.join(os.path.dirname(__file__), "..", "models", "logs")
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BATCH_SIZE  = 256      # larger batch = fewer steps per epoch = faster on CPU
MAX_EPOCHS  = 50
LR          = 3e-3     # higher LR for faster convergence
PATIENCE    = 8        # stop earlier
SUBSAMPLE   = 0.4      # use 40% of training data per epoch (faster CPU training)

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(LOG_DIR,    exist_ok=True)


# ─────────────────────────────────────────────
# PYTORCH HELPERS
# ─────────────────────────────────────────────
class EarlyStopping:
    """Stops training if validation loss does not improve for `patience` epochs."""
    def __init__(self, patience: int = PATIENCE, delta: float = 1e-4):
        self.patience  = patience
        self.delta     = delta
        self.best_loss = float("inf")
        self.counter   = 0
        self.triggered = False

    def __call__(self, val_loss: float) -> bool:
        if val_loss < self.best_loss - self.delta:
            self.best_loss = val_loss
            self.counter   = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.triggered = True
        return self.triggered


def make_dataloader(X: np.ndarray, y: np.ndarray,
                    batch_size: int = BATCH_SIZE, shuffle: bool = True,
                    subsample: float = 1.0) -> DataLoader:
    """Wraps numpy arrays into a PyTorch DataLoader.
    subsample: fraction of data to use (speeds up CPU training).
    """
    if subsample < 1.0 and shuffle:
        n = int(len(X) * subsample)
        idx = np.random.choice(len(X), n, replace=False)
        X, y = X[idx], y[idx]
    X_t = torch.FloatTensor(X)
    y_t = torch.LongTensor(y)
    ds  = TensorDataset(X_t, y_t)
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle,
                      pin_memory=False, num_workers=0)


# ─────────────────────────────────────────────
# LSTM / GRU MODELS
# ─────────────────────────────────────────────
class LSTMClassifier(nn.Module):
    def __init__(self, n_features, n_classes=3, hidden=128, layers=2, dropout=0.3):
        super().__init__()
        self.rnn  = nn.LSTM(n_features, hidden, layers, batch_first=True,
                            dropout=dropout if layers > 1 else 0)
        self.head = nn.Sequential(
            nn.Linear(hidden, 64), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(64, n_classes)
        )

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.head(out[:, -1, :])


class GRUClassifier(nn.Module):
    def __init__(self, n_features, n_classes=3, hidden=128, layers=2, dropout=0.3):
        super().__init__()
        self.rnn  = nn.GRU(n_features, hidden, layers, batch_first=True,
                           dropout=dropout if layers > 1 else 0)
        self.head = nn.Sequential(
            nn.Linear(hidden, 64), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(64, n_classes)
        )

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.head(out[:, -1, :])


class TCNBaseline(nn.Module):
    """Minimal TCN baseline (no residual connections, no adaptive head)."""
    def __init__(self, n_features, n_classes=3, channels=64, dropout=0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(n_features, channels, 3, padding=1), nn.ReLU(),
            nn.Conv1d(channels,   channels, 3, padding=2, dilation=2), nn.ReLU(),
            nn.Conv1d(channels,   channels, 3, padding=4, dilation=4), nn.ReLU(),
        )
        self.gap  = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Linear(channels, 64), nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, n_classes)
        )

    def forward(self, x):
        x = x.permute(0, 2, 1)
        x = self.net(x)
        x = self.gap(x).squeeze(-1)
        return self.head(x)


# ─────────────────────────────────────────────
# GENERIC PYTORCH TRAINING LOOP
# ─────────────────────────────────────────────
def train_pytorch_model(model: nn.Module, name: str, data: dict) -> dict:
    """
    Trains a PyTorch model with early stopping, LR scheduling, and checkpointing.
    Returns a dict of training history.
    """
    model.to(DEVICE)
    print(f"\n{'='*60}")
    print(f"[TRAIN] {name.upper()} | device={DEVICE}")
    print(f"{'='*60}")

    train_loader = make_dataloader(data["X_train_seq"], data["y_train_seq"],
                                   subsample=SUBSAMPLE)
    val_loader   = make_dataloader(data["X_val_seq"],   data["y_val_seq"],   shuffle=False)

    criterion   = nn.CrossEntropyLoss()
    optimizer   = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler   = ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    stopper     = EarlyStopping(patience=PATIENCE)

    best_val_acc = 0.0
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    best_path = os.path.join(MODELS_DIR, f"{name}_best.pt")

    for epoch in range(1, MAX_EPOCHS + 1):
        t0 = time.time()

        # ── Training phase ──
        model.train()
        tr_loss, tr_correct, tr_total = 0.0, 0, 0
        for Xb, yb in train_loader:
            Xb, yb = Xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            logits = model(Xb)
            loss   = criterion(logits, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            tr_loss    += loss.item() * len(yb)
            tr_correct += (logits.argmax(1) == yb).sum().item()
            tr_total   += len(yb)

        # ── Validation phase ──
        model.eval()
        va_loss, va_correct, va_total = 0.0, 0, 0
        with torch.no_grad():
            for Xb, yb in val_loader:
                Xb, yb = Xb.to(DEVICE), yb.to(DEVICE)
                logits = model(Xb)
                loss   = criterion(logits, yb)
                va_loss    += loss.item() * len(yb)
                va_correct += (logits.argmax(1) == yb).sum().item()
                va_total   += len(yb)

        tr_loss /= tr_total; va_loss /= va_total
        tr_acc   = tr_correct / tr_total
        va_acc   = va_correct / va_total

        history["train_loss"].append(tr_loss)
        history["val_loss"].append(va_loss)
        history["train_acc"].append(tr_acc)
        history["val_acc"].append(va_acc)

        scheduler.step(va_loss)

        # Checkpoint
        if va_acc > best_val_acc:
            best_val_acc = va_acc
            torch.save(model.state_dict(), best_path)

        elapsed = time.time() - t0
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/{MAX_EPOCHS} | "
                  f"TrLoss={tr_loss:.4f} TrAcc={tr_acc:.4f} | "
                  f"VaLoss={va_loss:.4f} VaAcc={va_acc:.4f} | "
                  f"{elapsed:.1f}s")

        if stopper(va_loss):
            print(f"  [EARLY STOP] Epoch {epoch} — best val_acc={best_val_acc:.4f}")
            break

    # Load best weights
    model.load_state_dict(torch.load(best_path, map_location=DEVICE, weights_only=True))
    print(f"[TRAIN] {name} best val accuracy: {best_val_acc:.4f}")

    # Save full model
    torch.save(model, os.path.join(MODELS_DIR, f"{name}.pt"))

    # Log history
    with open(os.path.join(LOG_DIR, f"{name}_history.json"), "w") as f:
        json.dump(history, f, indent=2)

    return history


# ─────────────────────────────────────────────
# SKLEARN BASELINE TRAINERS
# ─────────────────────────────────────────────
def train_random_forest(data: dict) -> None:
    print(f"\n{'='*60}\n[TRAIN] RANDOM FOREST\n{'='*60}")
    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_leaf=5,
        n_jobs=-1,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(data["X_train_flat"], data["y_train"])
    val_acc = accuracy_score(data["y_val"], clf.predict(data["X_val_flat"]))
    print(f"  Val Accuracy: {val_acc:.4f}")
    joblib.dump(clf, os.path.join(MODELS_DIR, "random_forest.pkl"))
    print(f"  Saved → models/random_forest.pkl")


def train_xgboost(data: dict) -> None:
    if not HAS_XGB:
        print("  [SKIP] xgboost not available"); return
    print(f"\n{'='*60}\n[TRAIN] XGBOOST\n{'='*60}")
    clf = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(
        data["X_train_flat"], data["y_train"],
        eval_set=[(data["X_val_flat"], data["y_val"])],
        verbose=False,
        early_stopping_rounds=20,
    )
    val_acc = accuracy_score(data["y_val"], clf.predict(data["X_val_flat"]))
    print(f"  Val Accuracy: {val_acc:.4f}")
    joblib.dump(clf, os.path.join(MODELS_DIR, "xgboost.pkl"))
    print(f"  Saved → models/xgboost.pkl")


def train_lightgbm(data: dict) -> None:
    if not HAS_LGB:
        print("  [SKIP] lightgbm not available"); return
    print(f"\n{'='*60}\n[TRAIN] LIGHTGBM\n{'='*60}")
    clf = lgb.LGBMClassifier(
        n_estimators=500,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    clf.fit(
        data["X_train_flat"], data["y_train"],
        eval_set=[(data["X_val_flat"], data["y_val"])],
        callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(period=0)],
    )
    val_acc = accuracy_score(data["y_val"], clf.predict(data["X_val_flat"]))
    print(f"  Val Accuracy: {val_acc:.4f}")
    joblib.dump(clf, os.path.join(MODELS_DIR, "lightgbm.pkl"))
    print(f"  Saved → models/lightgbm.pkl")


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Train grain storage risk models")
    parser.add_argument("--model",    type=str,  default="all",
                        choices=["all", "rf", "xgb", "lgb", "lstm", "gru", "tcn", "artcn"])
    parser.add_argument("--dataset",  type=str,  default=None,
                        help="Path to CSV dataset")
    args = parser.parse_args()

    # ── Preprocess ────────────────────────────
    print("\n[MAIN] Starting preprocessing pipeline ...")
    data = run_preprocessing(csv_path=args.dataset, save_artifacts=True)
    n_features = data["n_features"]
    n_classes  = data["n_classes"]

    print(f"\n[MAIN] n_features={n_features}, n_classes={n_classes}")
    print(f"[MAIN] Training on device: {DEVICE}")

    # ── Train selected models ─────────────────
    if args.model in ("all", "rf"):
        train_random_forest(data)

    if args.model in ("all", "xgb"):
        train_xgboost(data)

    if args.model in ("all", "lgb"):
        train_lightgbm(data)

    if args.model in ("all", "lstm"):
        lstm = LSTMClassifier(n_features, n_classes, hidden=64, layers=1)
        train_pytorch_model(lstm, "lstm", data)

    if args.model in ("all", "gru"):
        gru = GRUClassifier(n_features, n_classes, hidden=64, layers=1)
        train_pytorch_model(gru, "gru", data)

    if args.model in ("all", "tcn"):
        tcn = TCNBaseline(n_features, n_classes, channels=32)
        train_pytorch_model(tcn, "tcn", data)

    if args.model in ("all", "artcn"):
        artcn = build_artcn(n_features, n_classes,
                            seq_len=SEQUENCE_LENGTH,
                            base_channels=32,          # reduced from 64
                            dilations=[1, 2, 4, 8],    # 4 blocks instead of 5
                            dropout=0.2)
        train_pytorch_model(artcn, "artcn", data)

        # Export ONNX (optional — skip gracefully if onnxscript not installed)
        print("\n[EXPORT] Exporting AR-TCN to ONNX ...")
        artcn.eval()
        dummy = torch.randn(1, SEQUENCE_LENGTH, n_features).to(DEVICE)
        onnx_path = os.path.join(MODELS_DIR, "model.onnx")
        try:
            torch.onnx.export(
                artcn, dummy, onnx_path,
                input_names=["input"], output_names=["logits"],
                dynamic_axes={"input": {0: "batch_size"}, "logits": {0: "batch_size"}},
                opset_version=13,
            )
            print(f"[EXPORT] Saved → {onnx_path}")
        except Exception as e:
            print(f"[EXPORT] ONNX export skipped: {e}")
            print("[EXPORT] Install 'onnxscript' to enable ONNX export: pip install onnxscript")

    print("\n[MAIN] Training complete. All models saved to /models/")


if __name__ == "__main__":
    main()
