"""
=============================================================================
FILE: training/preprocess.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation DSS
DESCRIPTION:
    Complete data preprocessing pipeline for the grain storage IoT dataset.
    Handles:
      - Loading raw CSV
      - Missing value imputation (median + forward fill)
      - Outlier capping (IQR-based Winsorization)
      - Feature engineering (cyclic time encoding, interaction features,
        rolling statistics, lag features)
      - Normalization and StandardScaler fitting
      - Label encoding for the target
      - Time-series sequence generation for deep learning models
      - Saving preprocessed artefacts (scaler, label encoder, feature list)
=============================================================================
"""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
SEQUENCE_LENGTH   = 12    # 12 timesteps × 15 min = 3 hours of context (CPU-friendly)
PREDICTION_HORIZON= 1     # predict 1 step ahead
TEST_SPLIT_RATIO  = 0.15  # last 15% as test set
VAL_SPLIT_RATIO   = 0.10  # 10% of train as validation

MODELS_DIR        = os.path.join(os.path.dirname(__file__), "..", "models")
DATASET_DIR       = os.path.join(os.path.dirname(__file__), "..", "dataset")

SENSOR_COLS = [
    "temperature_c", "humidity_pct", "gas_concentration",
    "grain_moisture", "storage_duration", "ext_temperature_c",
    "ventilation_status", "battery_voltage", "sensor_health",
]

TARGET_COL = "risk_category"


# ─────────────────────────────────────────────
# STEP 1 – LOAD DATASET
# ─────────────────────────────────────────────
def load_dataset(csv_path = None) -> pd.DataFrame:
    """Load the raw CSV dataset and parse timestamps."""
    if csv_path is None:
        csv_path = os.path.join(DATASET_DIR, "grain_storage_dataset.csv")
    print(f"[PREPROCESS] Loading dataset from {csv_path} ...")
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"[PREPROCESS] Loaded {len(df):,} rows × {df.shape[1]} columns")
    return df


# ─────────────────────────────────────────────
# STEP 2 – MISSING VALUE IMPUTATION
# ─────────────────────────────────────────────
def impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strategy:
      - Numeric sensor columns: forward fill (maintains temporal continuity),
        then back-fill for leading NaNs, finally median for any remainder.
      - Categorical / integer columns: mode fill.
    """
    print("[PREPROCESS] Imputing missing values ...")
    numeric_cols = [c for c in SENSOR_COLS if df[c].dtype in [np.float64, np.float32, float]]
    binary_cols  = ["ventilation_status", "sensor_health"]

    # Forward + backward fill for time series columns
    for col in numeric_cols:
        if df[col].isnull().any():
            df[col] = df[col].ffill().bfill()
            # If still NaN (entire window missing), fill with median
            df[col] = df[col].fillna(df[col].median())

    for col in binary_cols:
        df[col] = df[col].fillna(df[col].mode()[0])

    remaining = df[SENSOR_COLS].isnull().sum().sum()
    print(f"[PREPROCESS] Remaining NaN after imputation: {remaining}")
    return df


# ─────────────────────────────────────────────
# STEP 3 – OUTLIER REMOVAL (Winsorization)
# ─────────────────────────────────────────────
def winsorize_outliers(df: pd.DataFrame, factor: float = 2.5) -> pd.DataFrame:
    """
    Caps outliers at [Q1 - factor*IQR, Q3 + factor*IQR] for numeric columns.
    Preserves the row but clips the extreme value.
    """
    print("[PREPROCESS] Winsorizing outliers ...")
    continuous_cols = [
        "temperature_c", "humidity_pct", "gas_concentration",
        "grain_moisture", "ext_temperature_c", "battery_voltage"
    ]
    for col in continuous_cols:
        q1  = df[col].quantile(0.25)
        q3  = df[col].quantile(0.75)
        iqr = q3 - q1
        lo  = q1 - factor * iqr
        hi  = q3 + factor * iqr
        before = ((df[col] < lo) | (df[col] > hi)).sum()
        df[col] = df[col].clip(lo, hi)
        if before > 0:
            print(f"  {col}: clipped {before:,} values to [{lo:.2f}, {hi:.2f}]")
    return df


# ─────────────────────────────────────────────
# STEP 4 – FEATURE ENGINEERING
# ─────────────────────────────────────────────
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates derived features that improve model signal:
      - Cyclic time encoding (hour, day-of-year)
      - Interaction features (temperature × humidity, etc.)
      - Rolling statistics (mean, std over 4-window = 1 hour)
      - Lag features (previous 1, 2, 4 readings)
      - Absolute humidity (derived thermodynamic property)
      - Temperature-humidity index
    """
    print("[PREPROCESS] Engineering features ...")

    # ── Cyclic time encoding ───────────────────
    df["hour"]       = df["timestamp"].dt.hour
    df["day_of_year"]= df["timestamp"].dt.dayofyear
    df["month"]      = df["timestamp"].dt.month
    df["day_of_week"]= df["timestamp"].dt.dayofweek
    df["week_of_year"]= df["timestamp"].dt.isocalendar().week.astype(int)

    # Sin/cos encoding avoids 23→0 discontinuity
    df["hour_sin"]   = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"]   = np.cos(2 * np.pi * df["hour"] / 24)
    df["doy_sin"]    = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["doy_cos"]    = np.cos(2 * np.pi * df["day_of_year"] / 365)
    df["month_sin"]  = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"]  = np.cos(2 * np.pi * df["month"] / 12)

    # ── Interaction features ───────────────────
    df["temp_humidity_idx"]  = df["temperature_c"] * df["humidity_pct"] / 100
    df["temp_moisture_ratio"]= df["temperature_c"] / (df["grain_moisture"] + 1e-6)
    df["gas_per_humidity"]   = df["gas_concentration"] / (df["humidity_pct"] + 1)
    df["temp_ext_diff"]      = df["temperature_c"] - df["ext_temperature_c"]

    # ── Absolute humidity (Magnus formula approximation) ─
    # AH = 6.112 * e^(17.67T/(T+243.5)) * RH * 2.1674 / (273.15 + T)
    T = df["temperature_c"]
    RH= df["humidity_pct"]
    df["absolute_humidity"] = (
        6.112 * np.exp(17.67 * T / (T + 243.5)) * RH * 2.1674 / (273.15 + T)
    )

    # ── Heat Index (Rothfusz) ──────────────────
    df["heat_index"] = (
        -42.379
        + 2.04901523   * T
        + 10.14333127  * RH
        - 0.22475541   * T  * RH
        - 0.00683783   * T  * T
        - 0.05481717   * RH * RH
        + 0.00122874   * T  * T * RH
        + 0.00085282   * T  * RH * RH
        - 0.00000199   * T  * T  * RH * RH
    )

    # ── Rolling statistics (4-step = 1 hour) ──
    for col in ["temperature_c", "humidity_pct", "gas_concentration", "grain_moisture"]:
        df[f"{col}_roll_mean_4"] = df[col].rolling(4, min_periods=1).mean()
        df[f"{col}_roll_std_4"]  = df[col].rolling(4, min_periods=1).std().fillna(0)
        df[f"{col}_roll_mean_12"]= df[col].rolling(12, min_periods=1).mean()

    # ── Lag features ──────────────────────────
    for col in ["temperature_c", "humidity_pct", "gas_concentration", "grain_moisture"]:
        for lag in [1, 2, 4, 8]:
            df[f"{col}_lag{lag}"] = df[col].shift(lag).bfill()

    # ── Trend features (difference) ───────────
    for col in ["temperature_c", "humidity_pct", "gas_concentration"]:
        df[f"{col}_diff1"] = df[col].diff(1).fillna(0)
        df[f"{col}_diff4"] = df[col].diff(4).fillna(0)

    print(f"[PREPROCESS] Feature count after engineering: {df.shape[1]}")
    return df


# ─────────────────────────────────────────────
# STEP 5 – DEFINE FEATURE COLUMNS
# ─────────────────────────────────────────────
def get_feature_columns(df: pd.DataFrame) -> list:
    """Returns the list of feature columns (excludes timestamp, target, risk_score, and internal target label)."""
    exclude = {"timestamp", "risk_category", "risk_score", "_label"}
    return [c for c in df.columns if c not in exclude]


# ─────────────────────────────────────────────
# STEP 6 – SCALE FEATURES
# ─────────────────────────────────────────────
def scale_features(df_train: pd.DataFrame, df_val: pd.DataFrame,
                   df_test: pd.DataFrame, feature_cols: list):
    """
    Fits a StandardScaler on the training set only.
    Transforms train, val, and test sets.
    Returns scaled arrays and the fitted scaler.
    """
    print("[PREPROCESS] Fitting StandardScaler on training data ...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(df_train[feature_cols].values)
    X_val   = scaler.transform(df_val[feature_cols].values)
    X_test  = scaler.transform(df_test[feature_cols].values)
    return X_train, X_val, X_test, scaler


# ─────────────────────────────────────────────
# STEP 7 – ENCODE LABELS
# ─────────────────────────────────────────────
def encode_labels(df: pd.DataFrame) -> tuple:
    """
    Encodes risk_category → integer.
    Returns encoded array and the fitted LabelEncoder.
    Ordering: Low=0, Moderate=1, High=2
    """
    le = LabelEncoder()
    le.classes_ = np.array(["Low", "Moderate", "High"])
    y = le.transform(df[TARGET_COL].values)
    return y, le


# ─────────────────────────────────────────────
# STEP 8 – SEQUENCE GENERATOR (for TCN / LSTM)
# ─────────────────────────────────────────────
def create_sequences(X: np.ndarray, y: np.ndarray,
                     seq_len: int = SEQUENCE_LENGTH,
                     horizon: int = PREDICTION_HORIZON) -> tuple:
    """
    Converts a flat feature matrix into (N, seq_len, n_features) sequences.
    Each sequence X[i] predicts label y[i + horizon - 1].
    """
    Xs, ys = [], []
    for i in range(len(X) - seq_len - horizon + 1):
        Xs.append(X[i : i + seq_len])
        ys.append(y[i + seq_len + horizon - 1])
    return np.array(Xs, dtype=np.float32), np.array(ys, dtype=np.int64)


# ─────────────────────────────────────────────
# STEP 9 – TRAIN / VAL / TEST SPLIT
# ─────────────────────────────────────────────
def temporal_split(df: pd.DataFrame):
    """
    Splits the DataFrame temporally (no data leakage).
    Returns train_df, val_df, test_df.
    """
    n = len(df)
    test_start = int(n * (1 - TEST_SPLIT_RATIO))
    val_start  = int(test_start * (1 - VAL_SPLIT_RATIO))

    train_df = df.iloc[:val_start].copy()
    val_df   = df.iloc[val_start:test_start].copy()
    test_df  = df.iloc[test_start:].copy()

    print(f"[PREPROCESS] Split → Train: {len(train_df):,} | "
          f"Val: {len(val_df):,} | Test: {len(test_df):,}")
    return train_df, val_df, test_df


# ─────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────
def run_preprocessing(csv_path = None, save_artifacts: bool = True):
    """
    Runs the complete preprocessing pipeline and returns all processed arrays.

    Returns:
        dict with keys:
          X_train_flat, X_val_flat, X_test_flat      (2D arrays for sklearn)
          X_train_seq, X_val_seq, X_test_seq          (3D sequences for DL)
          y_train, y_val, y_test                      (integer labels)
          y_train_seq, y_val_seq, y_test_seq          (labels for sequences)
          scaler, label_encoder, feature_cols
    """
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Pipeline stages
    df = load_dataset(csv_path)
    df = impute_missing(df)
    df = winsorize_outliers(df)
    df = engineer_features(df)

    # Encode labels before split (encoder uses known classes)
    y_all, le = encode_labels(df)
    df["_label"] = y_all

    # Temporal split
    train_df, val_df, test_df = temporal_split(df)
    feature_cols = get_feature_columns(train_df)

    # Scale
    X_train, X_val, X_test, scaler = scale_features(
        train_df, val_df, test_df, feature_cols
    )

    y_train = train_df["_label"].values
    y_val   = val_df["_label"].values
    y_test  = test_df["_label"].values

    # Sequence generation for deep learning
    print("[PREPROCESS] Generating sequences for deep learning ...")
    X_tr_seq, y_tr_seq = create_sequences(X_train, y_train)
    X_va_seq, y_va_seq = create_sequences(X_val,   y_val)
    X_te_seq, y_te_seq = create_sequences(X_test,  y_test)

    print(f"[PREPROCESS] Sequence shapes: "
          f"train={X_tr_seq.shape}, val={X_va_seq.shape}, test={X_te_seq.shape}")

    # Save artifacts
    if save_artifacts:
        joblib.dump(scaler,       os.path.join(MODELS_DIR, "scaler.pkl"))
        joblib.dump(le,           os.path.join(MODELS_DIR, "label_encoder.pkl"))
        joblib.dump(feature_cols, os.path.join(MODELS_DIR, "feature_cols.pkl"))
        print(f"[PREPROCESS] Artifacts saved to {MODELS_DIR}/")

    return {
        "X_train_flat": X_train,      "X_val_flat": X_val,      "X_test_flat": X_test,
        "X_train_seq":  X_tr_seq,     "X_val_seq":  X_va_seq,   "X_test_seq":  X_te_seq,
        "y_train":      y_train,      "y_val":      y_val,      "y_test":      y_test,
        "y_train_seq":  y_tr_seq,     "y_val_seq":  y_va_seq,   "y_test_seq":  y_te_seq,
        "scaler":       scaler,
        "label_encoder":le,
        "feature_cols": feature_cols,
        "n_features":   len(feature_cols),
        "n_classes":    3,
    }


if __name__ == "__main__":
    data = run_preprocessing()
    print("\n[PREPROCESS] Done.")
    print(f"  n_features : {data['n_features']}")
    print(f"  X_train    : {data['X_train_flat'].shape}")
    print(f"  X_train_seq: {data['X_train_seq'].shape}")
    print(f"  Classes    : {data['label_encoder'].classes_}")
