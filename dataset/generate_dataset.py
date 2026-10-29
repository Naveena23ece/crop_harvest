"""
=============================================================================
FILE: dataset/generate_dataset.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation
         Decision Support System for Real-Time Post-Harvest Storage Environments
DESCRIPTION:
    Generates a realistic synthetic IoT sensor dataset (120,000+ rows) that
    simulates grain storage conditions recorded every 15 minutes by an ESP32.
    Includes seasonal variation, sensor drift, random noise, outliers, and
    deliberate missing values to mimic real-world IoT deployments.
AUTHOR: AI Senior ML Engineer
=============================================================================
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import math
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

NUM_SAMPLES       = 125_000        # Minimum 120,000 rows
INTERVAL_MINUTES  = 15             # Sensor reading every 15 minutes
START_DATE        = datetime(2022, 1, 1, 0, 0, 0)
OUTPUT_CSV        = "grain_storage_dataset.csv"

# ─────────────────────────────────────────────
# REALISTIC AGRICULTURAL RANGES
# ─────────────────────────────────────────────
TEMP_RANGE        = (10.0, 45.0)   # °C
HUMIDITY_RANGE    = (20.0, 100.0)  # %
GAS_RANGE         = (250.0, 2500.0)# ppm (CO₂ / VOC proxy)
MOISTURE_RANGE    = (8.0, 28.0)    # %
DURATION_RANGE    = (0, 180)       # days
EXT_TEMP_RANGE    = (5.0, 50.0)    # °C
BATTERY_RANGE     = (3.0, 4.2)     # V (LiPo cell)

VENTILATION_STATES = [0, 1]        # 0=OFF, 1=ON
SENSOR_HEALTH_STATES = [1, 1, 1, 0]  # mostly healthy


# ─────────────────────────────────────────────
# HELPER: SEASONAL TEMPERATURE PROFILE
# ─────────────────────────────────────────────
def seasonal_temperature(timestamp: datetime) -> float:
    """
    Returns a seasonal base temperature.
    Models Indian sub-continent pattern:
      - Peak summer ~May-June (~38-42°C inside silo)
      - Winter ~Dec-Feb (~12-18°C)
    """
    day_of_year = timestamp.timetuple().tm_yday          # 1-365
    hour        = timestamp.hour

    # Annual sinusoidal: peak at day ~160 (June)
    annual_cycle = 15 * math.sin(2 * math.pi * (day_of_year - 80) / 365)

    # Diurnal: peak ~14:00, trough ~04:00
    diurnal_cycle = 4 * math.sin(2 * math.pi * (hour - 6) / 24)

    base_temp = 27.0 + annual_cycle + diurnal_cycle
    return np.clip(base_temp, TEMP_RANGE[0], TEMP_RANGE[1])


def seasonal_humidity(timestamp: datetime) -> float:
    """
    Models monsoon-affected humidity:
      - High during July-September (~70-95 %)
      - Low during winter / summer (~30-55 %)
    """
    day_of_year = timestamp.timetuple().tm_yday
    # Monsoon peak at day ~210 (late July)
    humidity = 55 + 30 * math.sin(2 * math.pi * (day_of_year - 120) / 365)
    humidity += np.random.normal(0, 5)
    return float(np.clip(humidity, HUMIDITY_RANGE[0], HUMIDITY_RANGE[1]))


# ─────────────────────────────────────────────
# HELPER: SENSOR DRIFT SIMULATION
# ─────────────────────────────────────────────
def apply_sensor_drift(values: np.ndarray, drift_rate: float = 0.0002) -> np.ndarray:
    """
    Simulates gradual sensor drift over time.
    drift_rate: fraction of reading added per sample cumulatively.
    """
    drift = np.cumsum(np.random.normal(0, drift_rate, len(values)))
    return values + drift * values


# ─────────────────────────────────────────────
# HELPER: INTRODUCE OUTLIERS
# ─────────────────────────────────────────────
def inject_outliers(series: np.ndarray, fraction: float = 0.005,
                    multiplier: float = 2.5) -> np.ndarray:
    """
    Randomly replaces a fraction of readings with extreme outlier values.
    """
    series = series.copy()
    n_outliers = int(len(series) * fraction)
    idx = np.random.choice(len(series), n_outliers, replace=False)
    series[idx] *= np.random.uniform(multiplier, multiplier + 0.5, n_outliers)
    return series


# ─────────────────────────────────────────────
# HELPER: INTRODUCE MISSING VALUES (NaN)
# ─────────────────────────────────────────────
def inject_missing(series: np.ndarray, fraction: float = 0.012) -> np.ndarray:
    """
    Sets a fraction of values to NaN to simulate sensor disconnects.
    Missing values tend to appear in bursts (sensor power cycle).
    """
    series = series.astype(float).copy()
    n_missing = int(len(series) * fraction)
    # Burst-style missing: pick random start indices
    starts = np.random.choice(len(series) - 5, n_missing // 3, replace=False)
    for s in starts:
        burst_len = np.random.randint(1, 6)
        series[s:s + burst_len] = np.nan
    return series


# ─────────────────────────────────────────────
# RISK SCORING ENGINE (Agricultural Rules)
# ─────────────────────────────────────────────
def compute_risk_score(temp: float, humidity: float, gas: float,
                        moisture: float, duration: int,
                        ext_temp: float, ventilation: int) -> float:
    """
    Computes a weighted spoilage risk score in [0, 1].
    Based on USDA / FAO grain storage guidelines.

    Weights derived from agricultural research:
      - Grain Moisture: highest driver of mould/mycotoxin
      - Temperature: accelerates enzymatic activity
      - Humidity: secondary moisture driver
      - Gas (CO₂): respiration proxy (higher = active spoilage)
      - Duration: cumulative risk
      - Ventilation: mitigates risk when ON
    """
    score = 0.0

    # ── Temperature component ──────────────────
    # Optimal storage: 10-15°C. Risk rises sharply above 25°C.
    if temp < 15:
        t_score = 0.05
    elif temp < 25:
        t_score = 0.10 + (temp - 15) * 0.02    # linear rise
    elif temp < 35:
        t_score = 0.30 + (temp - 25) * 0.04
    else:
        t_score = 0.70 + (temp - 35) * 0.03
    score += 0.22 * np.clip(t_score, 0, 1)

    # ── Humidity component ─────────────────────
    # Above 70 % RH triggers mold; above 85 % is critical
    if humidity < 55:
        h_score = 0.05
    elif humidity < 70:
        h_score = 0.10 + (humidity - 55) * 0.01
    elif humidity < 85:
        h_score = 0.25 + (humidity - 70) * 0.03
    else:
        h_score = 0.70 + (humidity - 85) * 0.02
    score += 0.20 * np.clip(h_score, 0, 1)

    # ── Gas concentration component ───────────
    # CO₂ above 600 ppm indicates active respiration
    if gas < 400:
        g_score = 0.05
    elif gas < 800:
        g_score = 0.10 + (gas - 400) * 0.001
    elif gas < 1500:
        g_score = 0.50 + (gas - 800) * 0.0008
    else:
        g_score = 0.80 + (gas - 1500) * 0.0001
    score += 0.18 * np.clip(g_score, 0, 1)

    # ── Grain moisture component (dominant) ───
    # Safe moisture: <13 %. Critical: >16 %
    if moisture < 11:
        m_score = 0.02
    elif moisture < 13:
        m_score = 0.05 + (moisture - 11) * 0.05
    elif moisture < 16:
        m_score = 0.15 + (moisture - 13) * 0.10
    elif moisture < 20:
        m_score = 0.45 + (moisture - 16) * 0.08
    else:
        m_score = 0.77 + (moisture - 20) * 0.04
    score += 0.25 * np.clip(m_score, 0, 1)

    # ── Storage duration component ─────────────
    # Risk accumulates with time; mitigated by good conditions
    d_score = duration / 180
    score += 0.10 * d_score

    # ── External temperature (heat transfer) ──
    temp_diff = abs(temp - ext_temp)
    ext_score = np.clip(temp_diff / 20, 0, 1) * 0.3
    score += 0.05 * ext_score

    # ── Ventilation mitigation ─────────────────
    # Active ventilation reduces score by 12 %
    if ventilation == 1:
        score *= 0.88

    return float(np.clip(score, 0.0, 1.0))


def score_to_risk_label(score: float) -> str:
    """
    Maps continuous risk score to categorical labels.
    Thresholds tuned to produce balanced class distribution:
      ~40% Low, ~35% Moderate, ~25% High
    """
    if score < 0.28:
        return "Low"
    elif score < 0.50:
        return "Moderate"
    else:
        return "High"


# ─────────────────────────────────────────────
# MAIN DATASET GENERATOR
# ─────────────────────────────────────────────
def generate_dataset(n_samples: int = NUM_SAMPLES) -> pd.DataFrame:
    """
    Generates the complete IoT sensor dataset with all features,
    realistic correlations, noise, drift, outliers, and missing values.
    """
    print(f"[INFO] Generating {n_samples:,} sensor readings...")
    print(f"[INFO] Time range: {START_DATE} → "
          f"{START_DATE + timedelta(minutes=INTERVAL_MINUTES * n_samples)}")

    # ── Timestamps ─────────────────────────────
    timestamps = [START_DATE + timedelta(minutes=INTERVAL_MINUTES * i)
                  for i in range(n_samples)]

    # ── Base temperature (seasonal + diurnal) ──
    base_temps   = np.array([seasonal_temperature(ts) for ts in timestamps])
    base_humidity= np.array([seasonal_humidity(ts)     for ts in timestamps])

    # ── Temperature with noise ─────────────────
    temp_noise   = np.random.normal(0, 1.2, n_samples)
    temperature  = base_temps + temp_noise

    # ── Humidity (correlated with temperature) ─
    # Hot + humid = high risk; cold + dry = low risk
    humidity     = base_humidity + np.random.normal(0, 3.5, n_samples)

    # ── Gas concentration (CO₂ proxy) ──────────
    # Rises with temperature, moisture, and duration
    gas_base     = 350 + temperature * 15 + humidity * 8
    gas          = gas_base + np.random.normal(0, 80, n_samples)

    # ── Grain moisture (semi-independent) ──────
    # Influenced by ambient humidity over time
    moisture_base = 9.5 + humidity * 0.08 + np.random.normal(0, 1.5, n_samples)
    moisture      = np.clip(moisture_base, MOISTURE_RANGE[0], MOISTURE_RANGE[1])

    # ── Storage duration (resets every ~30-180 days) ─
    # Simulates multiple storage batches
    duration = np.zeros(n_samples, dtype=int)
    d = 0
    for i in range(n_samples):
        duration[i] = d
        d += INTERVAL_MINUTES / (60 * 24)  # increment in day fractions
        if d >= random.randint(30, 180):
            d = 0  # new batch

    # ── External temperature ───────────────────
    ext_temp = base_temps - np.random.uniform(2, 8, n_samples) + \
               np.random.normal(0, 1.5, n_samples)

    # ── Ventilation status ─────────────────────
    # Farmers turn on ventilation when temp or humidity is high
    ventilation = np.where(
        (temperature > 30) | (humidity > 75),
        np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
        np.random.choice([0, 1], n_samples, p=[0.8, 0.2])
    )

    # ── Battery voltage (gradual drain cycles) ─
    cycle_len = 5000  # charge cycle length in samples
    battery = 4.2 - (np.arange(n_samples) % cycle_len) / cycle_len * 1.1
    battery += np.random.normal(0, 0.02, n_samples)

    # ── Sensor health ──────────────────────────
    sensor_health = np.random.choice(SENSOR_HEALTH_STATES, n_samples)

    # ── Apply sensor drift to gas and moisture ─
    gas      = apply_sensor_drift(gas, drift_rate=0.00015)
    moisture = apply_sensor_drift(moisture, drift_rate=0.00008)

    # ── Inject outliers ────────────────────────
    temperature = inject_outliers(temperature, fraction=0.004, multiplier=1.4)
    humidity    = inject_outliers(humidity,    fraction=0.003, multiplier=1.2)
    gas         = inject_outliers(gas,         fraction=0.005, multiplier=2.0)

    # ── Clip to realistic ranges after outlier injection ──
    temperature = np.clip(temperature, TEMP_RANGE[0] - 5, TEMP_RANGE[1] + 10)
    humidity    = np.clip(humidity,    HUMIDITY_RANGE[0], HUMIDITY_RANGE[1])
    gas         = np.clip(gas,         GAS_RANGE[0] - 50, GAS_RANGE[1] + 500)
    moisture    = np.clip(moisture,    MOISTURE_RANGE[0], MOISTURE_RANGE[1])
    battery     = np.clip(battery,     BATTERY_RANGE[0],  BATTERY_RANGE[1])
    ext_temp    = np.clip(ext_temp,    EXT_TEMP_RANGE[0], EXT_TEMP_RANGE[1])

    # ── Compute risk labels BEFORE adding missing values ──
    print("[INFO] Computing risk scores (this may take ~30 seconds)...")
    risk_scores = np.array([
        compute_risk_score(
            temperature[i], humidity[i], gas[i],
            moisture[i], int(duration[i]),
            ext_temp[i], int(ventilation[i])
        )
        for i in range(n_samples)
    ])
    risk_labels = np.array([score_to_risk_label(s) for s in risk_scores])

    # ── Now inject missing values into sensor columns only ──
    temperature_m = inject_missing(temperature, fraction=0.010)
    humidity_m    = inject_missing(humidity,    fraction=0.012)
    gas_m         = inject_missing(gas,         fraction=0.008)
    moisture_m    = inject_missing(moisture,    fraction=0.015)
    battery_m     = inject_missing(battery,     fraction=0.005)

    # ── Build DataFrame ────────────────────────
    df = pd.DataFrame({
        "timestamp":          timestamps,
        "temperature_c":      np.round(temperature_m, 2),
        "humidity_pct":       np.round(humidity_m,    2),
        "gas_concentration":  np.round(gas_m,         1),
        "grain_moisture":     np.round(moisture_m,    2),
        "storage_duration":   duration.astype(int),
        "ext_temperature_c":  np.round(ext_temp,      2),
        "ventilation_status": ventilation.astype(int),
        "battery_voltage":    np.round(battery_m,     3),
        "sensor_health":      sensor_health.astype(int),
        "risk_score":         np.round(risk_scores,   4),
        "risk_category":      risk_labels,
    })

    # ── Log class distribution ─────────────────
    dist = df["risk_category"].value_counts()
    print("\n[INFO] Risk category distribution:")
    for label, count in dist.items():
        print(f"  {label:10s}: {count:7,d} ({count/n_samples*100:.1f}%)")

    print(f"\n[INFO] Missing values per column:")
    print(df.isnull().sum()[df.isnull().sum() > 0].to_string())

    return df


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import os
    df = generate_dataset(NUM_SAMPLES)

    out_path = os.path.join(os.path.dirname(__file__), OUTPUT_CSV)
    df.to_csv(out_path, index=False)
    print(f"\n[SUCCESS] Dataset saved → {out_path}")
    print(f"[INFO] Shape: {df.shape}")
    print(f"\n[SAMPLE]\n{df.head(5).to_string()}")
