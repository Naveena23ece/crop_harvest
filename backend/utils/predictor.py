"""
=============================================================================
FILE: backend/utils/predictor.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation DSS
DESCRIPTION:
    Inference engine that loads the trained AR-TCN model (+ scaler + encoder)
    and exposes a clean prediction interface for the FastAPI backend.

    Supports:
      - Single-reading prediction (with internal mock history buffer)
      - Sequence-based prediction (full 24-step window)
      - Alert generation with actionable recommendations
      - Model hot-reload support
=============================================================================
"""

import os
import json
import logging
import numpy as np
import joblib
import torch
import torch.nn.functional as F
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("predictor")

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
ROOT_DIR    = os.path.join(os.path.dirname(__file__), "..", "..")
MODELS_DIR  = os.path.join(ROOT_DIR, "models")
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

SEQUENCE_LENGTH = 12
CLASS_NAMES     = ["Low", "Moderate", "High"]

# Alert recommendations per risk level
RECOMMENDATIONS = {
    "Low": [
        "Conditions are optimal. Continue regular monitoring.",
        "Maintain current ventilation schedule.",
        "Schedule routine inspection in 7 days.",
    ],
    "Moderate": [
        "Increase ventilation frequency.",
        "Monitor temperature and humidity closely.",
        "Check grain moisture levels manually.",
        "Inspect grain surface for early signs of clumping.",
    ],
    "High": [
        "IMMEDIATE ACTION REQUIRED: Activate emergency ventilation.",
        "Remove affected grain batches from storage.",
        "Reduce ambient humidity below 70%.",
        "Apply approved fungicide treatment if moisture > 16%.",
        "Contact agricultural officer for inspection.",
        "Do NOT continue storing new grain until conditions improve.",
    ],
}


# ─────────────────────────────────────────────
# FEATURE COLUMN ORDER (must match training)
# ─────────────────────────────────────────────
SENSOR_INPUT_COLS = [
    "temperature_c", "humidity_pct", "gas_concentration",
    "grain_moisture", "storage_duration", "ext_temperature_c",
    "ventilation_status", "battery_voltage", "sensor_health",
]


# ─────────────────────────────────────────────
# PREDICTOR CLASS
# ─────────────────────────────────────────────
class GrainRiskPredictor:
    """
    Loads trained models and performs risk inference.
    Maintains an internal sliding window buffer for sequence prediction.
    """

    def __init__(self):
        self.model: Optional[torch.nn.Module] = None
        self.scaler         = None
        self.label_encoder  = None
        self.feature_cols   = None
        self._telemetry_buffer: deque = deque(maxlen=SEQUENCE_LENGTH)
        self._loaded        = False
        self._model_info    = {}

    @property
    def _history_buffer(self) -> deque:
        """Alias for backward compatibility."""
        return self._telemetry_buffer

    def load(self, models_dir: str = MODELS_DIR) -> bool:
        """Loads all model artifacts from disk. Returns True on success."""
        try:
            scaler_path  = os.path.join(models_dir, "scaler.pkl")
            le_path      = os.path.join(models_dir, "label_encoder.pkl")
            fc_path      = os.path.join(models_dir, "feature_cols.pkl")
            model_path   = os.path.join(models_dir, "artcn.pt")

            if not all(os.path.exists(p) for p in [scaler_path, le_path, model_path]):
                logger.warning("Model artifacts not found. Using demo mode.")
                self._loaded = False
                return False

            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Trying to unpickle estimator.*")
                self.scaler        = joblib.load(scaler_path)
                self.label_encoder = joblib.load(le_path)
            self.feature_cols  = joblib.load(fc_path) if os.path.exists(fc_path) else None

            # PyTorch 2.6+ requires weights_only=False to load full model objects
            # (safe here since we saved this model ourselves)
            import torch.serialization as _ts
            try:
                from training.model_artcn import ARTCN
                _ts.add_safe_globals([ARTCN])
            except Exception:
                pass
            self.model = torch.load(model_path, map_location=DEVICE, weights_only=False)
            self.model.eval()
            self._loaded = True

            self._model_info = {
                "name":        "AR-TCN",
                "version":     "1.0.0",
                "loaded_at":   _utcnow(),
                "device":      str(DEVICE),
                "n_features":  len(self.feature_cols) if self.feature_cols else "unknown",
                "seq_length":  SEQUENCE_LENGTH,
                "classes":     CLASS_NAMES,
            }
            logger.info(f"Model loaded successfully on {DEVICE}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._loaded = False
            return False

    def _engineer_single(
        self,
        sensor_data: Dict,
        history_buffer: Optional[List[List[float]]] = None,
        ref_time: Optional[datetime] = None,
    ) -> np.ndarray:
        """
        Applies feature engineering to a single sensor reading dict.
        Returns a 1D numpy array of engineered features.

        - If `ref_time` is provided, it is used for cyclic temporal encoding.
        - If `ref_time` is None, checks sensor_data for "timestamp"; if missing,
          uses a fixed nominal reference time (NOMINAL_REFERENCE_DATETIME) to ensure
          100% deterministic manual inference across different times of day.
        - If `history_buffer` is None, computes rolling and lag features under steady-state
          assumptions (isolated single-point evaluation: std=0, diff=0, lags=current value).
        """
        import math

        # ── Deterministic timestamp resolution ────────────────────────────
        nominal_ref = datetime(2025, 6, 15, 12, 0, 0)
        if ref_time is not None:
            now = ref_time
        elif sensor_data.get("timestamp"):
            ts_val = sensor_data["timestamp"]
            if isinstance(ts_val, datetime):
                now = ts_val
            else:
                try:
                    now = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
                except Exception:
                    now = nominal_ref
        else:
            now = nominal_ref

        doy = now.timetuple().tm_yday
        hr  = now.hour
        mo  = now.month

        T  = float(sensor_data.get("temperature_c",    27.0))
        RH = float(sensor_data.get("humidity_pct",     60.0))
        G  = float(sensor_data.get("gas_concentration",450.0))
        M  = float(sensor_data.get("grain_moisture",   12.0))
        D  = float(sensor_data.get("storage_duration", 30.0))
        ET = float(sensor_data.get("ext_temperature_c",28.0))
        V  = float(sensor_data.get("ventilation_status", 1))
        B  = float(sensor_data.get("battery_voltage",   3.9))
        SH = float(sensor_data.get("sensor_health",      1))

        # Core sensor features
        row = [T, RH, G, M, D, ET, V, B, SH]

        # Temporal cyclic (matches training/preprocess.py order: hour, doy, mo, dow, woy, sin/cos)
        woy = int(now.isocalendar().week)
        row += [
            hr, doy, mo, now.weekday(), woy,
            math.sin(2*math.pi*hr/24), math.cos(2*math.pi*hr/24),
            math.sin(2*math.pi*doy/365), math.cos(2*math.pi*doy/365),
            math.sin(2*math.pi*mo/12),  math.cos(2*math.pi*mo/12),
        ]

        # Interactions (matches training/preprocess.py: temp_hum, temp_moist, gas_hum, temp_ext, abs_hum, heat_idx)
        abs_hum = 6.112 * math.exp(17.67*T/(T+243.5)) * RH * 2.1674 / (273.15 + T)
        heat_idx = (
            -42.379
            + 2.04901523 * T
            + 10.14333127 * RH
            - 0.22475541 * T * RH
            - 0.00683783 * T * T
            - 0.05481717 * RH * RH
            + 0.00122874 * T * T * RH
            + 0.00085282 * T * RH * RH
            - 0.00000199 * T * T * RH * RH
        )
        row += [
            T * RH / 100,        # temp_humidity_idx
            T / (M + 1e-6),      # temp_moisture_ratio
            G / (RH + 1),        # gas_per_humidity
            T - ET,              # temp_ext_diff
            abs_hum,             # absolute_humidity
            heat_idx,            # heat_index (Rothfusz equation matching preprocess.py)
        ]

        # ── Rolling, Lag, and Diff features ──────────────────────────────
        if history_buffer is None:
            # Steady-state assumption for isolated single-reading evaluation:
            # The silo is evaluated at steady state under the given conditions.
            for col_idx in range(4):  # temp, humidity, gas, moisture
                row += [
                    row[col_idx],     # roll_mean_4
                    0.0,              # roll_std_4
                    row[col_idx],     # roll_mean_12
                ]
            for col_idx in range(4):  # temp, humidity, gas, moisture
                for _ in [1, 2, 4, 8]:
                    row.append(row[col_idx])
            for col_idx in range(3):  # temp, humidity, gas
                row += [0.0, 0.0]     # diff1, diff4
        else:
            buf = history_buffer
            for col_idx in range(4):  # temp, humidity, gas, moisture
                vals_4  = [b[col_idx] for b in buf[-4:]]  if buf else [row[col_idx]]
                vals_12 = [b[col_idx] for b in buf[-12:]] if buf else [row[col_idx]]
                row += [
                    float(np.mean(vals_4)),
                    float(np.std(vals_4)) if len(vals_4) > 1 else 0.0,
                    float(np.mean(vals_12)),
                ]

            for col_idx in range(4):  # temp, humidity, gas, moisture
                for lag in [1, 2, 4, 8]:
                    if len(buf) >= lag:
                        row.append(buf[-lag][col_idx])
                    else:
                        row.append(row[col_idx])

            for col_idx in range(3):  # temp, humidity, gas
                prev1 = buf[-1][col_idx]  if buf else row[col_idx]
                prev4 = buf[-4][col_idx]  if len(buf) >= 4 else row[col_idx]
                row += [row[col_idx] - prev1, row[col_idx] - prev4]

        # Column 60: placeholder for '_label' (maintains 61-feature AR-TCN compatibility)
        if self.feature_cols and len(row) < len(self.feature_cols):
            row.append(0.0)

        return np.array(row, dtype=np.float32)

    def _update_telemetry_buffer(self, sensor_data: Dict) -> None:
        """Appends core sensor values to the live telemetry sliding window buffer."""
        core = [
            float(sensor_data.get("temperature_c",    27.0)),
            float(sensor_data.get("humidity_pct",     60.0)),
            float(sensor_data.get("gas_concentration",450.0)),
            float(sensor_data.get("grain_moisture",   12.0)),
        ]
        self._telemetry_buffer.append(core)

    def predict_single(self, sensor_data: Dict, is_telemetry: bool = False) -> Dict:
        """
        Makes a prediction from a single sensor reading.
        
        Args:
            sensor_data: Dictionary of sensor readings.
            is_telemetry: If True, updates the live telemetry buffer and computes
                          rolling/lag features from continuous telemetry.
                          If False (default for manual predictions), computes
                          stateless steady-state features with a fixed reference time,
                          guaranteeing 100% deterministic repeatability.
        """
        if is_telemetry:
            self._update_telemetry_buffer(sensor_data)
            feature_vec = self._engineer_single(
                sensor_data,
                history_buffer=list(self._telemetry_buffer),
                ref_time=None,
            )
        else:
            feature_vec = self._engineer_single(
                sensor_data,
                history_buffer=None,
                ref_time=datetime(2025, 6, 15, 12, 0, 0),
            )

        if self._loaded:
            return self._predict_with_model([feature_vec] * SEQUENCE_LENGTH, sensor_data)
        else:
            return self._rule_based_fallback(sensor_data)

    def predict_sequence(self, sequence: List[Dict]) -> Dict:
        """
        Makes a prediction from a full sequence of sensor readings.
        `sequence` should have up to SEQUENCE_LENGTH readings.
        Maintains an isolated sequence context to prevent buffer contamination.
        """
        if len(sequence) < SEQUENCE_LENGTH:
            # Pad with repeats of the first reading
            padding = [sequence[0]] * (SEQUENCE_LENGTH - len(sequence))
            sequence = padding + list(sequence)
        elif len(sequence) > SEQUENCE_LENGTH:
            sequence = sequence[-SEQUENCE_LENGTH:]

        feature_vecs = []
        seq_buf = []
        for s in sequence:
            core = [
                float(s.get("temperature_c",    27.0)),
                float(s.get("humidity_pct",     60.0)),
                float(s.get("gas_concentration",450.0)),
                float(s.get("grain_moisture",   12.0)),
            ]
            seq_buf.append(core)
            feat = self._engineer_single(s, history_buffer=seq_buf, ref_time=None)
            feature_vecs.append(feat)

        if self._loaded:
            return self._predict_with_model(feature_vecs, sequence[-1])
        else:
            return self._rule_based_fallback(sequence[-1])

    def _predict_with_model(self, feature_vecs: List[np.ndarray],
                             latest_reading: Dict) -> Dict:
        """Runs the AR-TCN model on a sequence of feature vectors."""
        try:
            seq = np.array(feature_vecs, dtype=np.float32)   # (24, n_raw)

            # Truncate / pad to match feature_cols length
            if self.feature_cols:
                n_feat = len(self.feature_cols)
                if seq.shape[1] < n_feat:
                    pad = np.zeros((seq.shape[0], n_feat - seq.shape[1]), dtype=np.float32)
                    seq = np.concatenate([seq, pad], axis=1)
                elif seq.shape[1] > n_feat:
                    seq = seq[:, :n_feat]

            # Scale
            seq_2d    = seq.reshape(-1, seq.shape[-1])
            seq_scaled= self.scaler.transform(seq_2d).reshape(1, SEQUENCE_LENGTH, -1)

            # Inference
            tensor     = torch.FloatTensor(seq_scaled).to(DEVICE)
            with torch.no_grad():
                logits     = self.model(tensor)
                proba      = F.softmax(logits, dim=-1).cpu().numpy()[0]

            pred_idx   = int(np.argmax(proba))
            pred_label = CLASS_NAMES[pred_idx]
            confidence = float(proba[pred_idx])

            return self._build_response(
                pred_label, confidence,
                {c: round(float(p), 4) for c, p in zip(CLASS_NAMES, proba)},
                latest_reading,
                model_name="artcn",
            )
        except Exception as e:
            logger.error(f"Model inference failed: {e}, falling back to rule-based")
            return self._rule_based_fallback(latest_reading)

    def _rule_based_fallback(self, sensor_data: Dict) -> Dict:
        """
        Simple rule-based fallback when the model is not loaded.
        Used in demo / development mode.
        """
        T  = float(sensor_data.get("temperature_c",    27.0))
        RH = float(sensor_data.get("humidity_pct",     60.0))
        M  = float(sensor_data.get("grain_moisture",   12.0))
        G  = float(sensor_data.get("gas_concentration",450.0))

        score = 0
        if T > 30: score += 2
        if T > 38: score += 2
        if RH > 70: score += 2
        if RH > 85: score += 2
        if M > 13: score += 3
        if M > 16: score += 3
        if G > 800: score += 2
        if G > 1500: score += 2

        if score <= 4:
            label, proba = "Low", [0.75, 0.20, 0.05]
        elif score <= 9:
            label, proba = "Moderate", [0.20, 0.60, 0.20]
        else:
            label, proba = "High", [0.05, 0.15, 0.80]

        confidence = max(proba)
        proba_dict = {c: round(p, 4) for c, p in zip(CLASS_NAMES, proba)}
        return self._build_response(label, confidence, proba_dict, sensor_data,
                                     model_name="rule_based_fallback")

    def _build_response(self, label: str, confidence: float,
                         probabilities: Dict, sensor_data: Dict,
                         model_name: str = "artcn") -> Dict:
        """Builds the standard prediction response dict."""
        response = {
            "timestamp":       _utcnow(),
            "risk_category":   label,
            "confidence":      round(confidence, 4),
            "probabilities":   probabilities,
            "model_name":      model_name,
            "recommendations": RECOMMENDATIONS[label],
            "alert":           label == "High",
            "sensor_snapshot": sensor_data,
        }
        return response

    def get_model_info(self) -> Dict:
        return self._model_info if self._loaded else {
            "name": "rule_based_fallback",
            "status": "Model not loaded — demo mode",
        }


# ─────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────
_predictor_instance: Optional[GrainRiskPredictor] = None


def get_predictor() -> GrainRiskPredictor:
    """Returns the global singleton predictor instance."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = GrainRiskPredictor()
        _predictor_instance.load()
    return _predictor_instance


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    predictor = get_predictor()

    # Test with a sample reading
    sample = {
        "temperature_c": 32.5,
        "humidity_pct":  78.0,
        "gas_concentration": 650.0,
        "grain_moisture": 14.5,
        "storage_duration": 60,
        "ext_temperature_c": 35.0,
        "ventilation_status": 0,
        "battery_voltage": 3.85,
        "sensor_health": 1,
    }
    result = predictor.predict_single(sample)
    print(json.dumps(result, indent=2))
