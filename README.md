# 🌾 AI-Integrated Predictive Modeling and Adaptive Risk Evaluation Decision Support System
## Real-Time Post-Harvest Storage Environments

> **BE Final Year Project** — AI + IoT + Full Stack
> 
> Predicts grain spoilage risk (Low / Moderate / High) using real-time ESP32 sensor data and a custom Adaptive Risk-Aware Temporal Convolution Network (AR-TCN).

---

## 📌 Project Overview

| Component | Technology |
|-----------|-----------|
| IoT Sensor | ESP32 (Temperature, Humidity, Gas, Moisture) |
| ML Model | AR-TCN (PyTorch) + RF / XGBoost / LightGBM / LSTM / GRU baselines |
| Backend API | FastAPI (Python) |
| Database | Firebase Realtime Database |
| Dashboard | React + Recharts + Tailwind CSS |
| Deployment | Docker + Docker Compose |

---

## 🏗 Project Structure

```
├── dataset/
│   ├── generate_dataset.py       # Synthetic IoT dataset generator (125,000 rows)
│   └── grain_storage_dataset.csv # Generated dataset (after running generator)
│
├── training/
│   ├── preprocess.py             # Full preprocessing pipeline
│   ├── model_artcn.py            # AR-TCN architecture (PyTorch)
│   ├── train.py                  # Training script (all models)
│   └── evaluate.py               # Evaluation + plots + SHAP
│
├── models/
│   ├── artcn.pt                  # Trained AR-TCN (PyTorch)
│   ├── artcn_best.pt             # Best checkpoint
│   ├── model.onnx                # ONNX export
│   ├── random_forest.pkl         # Trained RF
│   ├── xgboost.pkl               # Trained XGBoost
│   ├── lightgbm.pkl              # Trained LightGBM
│   ├── lstm.pt / gru.pt / tcn.pt # DL baselines
│   ├── scaler.pkl                # StandardScaler
│   ├── label_encoder.pkl         # LabelEncoder
│   ├── feature_cols.pkl          # Feature column list
│   ├── metrics.json              # All model evaluation metrics
│   └── plots/                    # Confusion matrices, ROC, SHAP plots
│
├── backend/
│   ├── api/
│   │   └── main.py               # FastAPI application + all endpoints
│   ├── firebase/
│   │   ├── firebase_client.py    # Firebase Admin SDK client
│   │   └── serviceAccountKey.json # ← Add your Firebase key here
│   └── utils/
│       └── predictor.py          # AR-TCN inference engine
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Router + AuthProvider
│   │   ├── index.js / index.css  # Entry point
│   │   ├── context/
│   │   │   └── AuthContext.jsx   # Firebase Auth context
│   │   ├── hooks/
│   │   │   └── useSensorData.js  # Live data hook (Firebase + polling)
│   │   ├── services/
│   │   │   ├── firebase.js       # Firebase SDK helpers
│   │   │   └── api.js            # FastAPI client (Axios)
│   │   ├── utils/
│   │   │   └── helpers.js        # Formatting + risk colors
│   │   ├── components/
│   │   │   ├── Layout.jsx        # Sidebar + topbar
│   │   │   ├── SensorCard.jsx    # Metric KPI card
│   │   │   ├── SensorChart.jsx   # Recharts line chart
│   │   │   ├── RiskBadge.jsx     # Animated risk level badge
│   │   │   └── AlertCard.jsx     # Alert banner with recommendations
│   │   └── pages/
│   │       ├── Login.jsx         # Auth page
│   │       ├── Dashboard.jsx     # Main overview
│   │       ├── LiveSensors.jsx   # Real-time sensor charts
│   │       ├── HistoricalCharts.jsx # Historical trends + scatter
│   │       ├── RiskPrediction.jsx   # Manual prediction form
│   │       ├── AlertHistory.jsx     # Alert log
│   │       ├── ModelPerformance.jsx # Metrics + radar chart
│   │       └── Settings.jsx         # Config + training trigger
│   └── package.json
│
├── deployment/
│   ├── Dockerfile.backend        # Backend container
│   ├── Dockerfile.frontend       # Frontend container (Nginx)
│   ├── docker-compose.yml        # Full stack orchestration
│   ├── nginx.conf                # Nginx SPA config
│   ├── run_pipeline.ps1          # Windows one-click runner
│   └── run_pipeline.sh           # Linux/macOS one-click runner
│
├── requirements.txt              # Python dependencies
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or 3.11
- Node.js 18+
- (Optional) CUDA GPU for faster training
- (Optional) Firebase project

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Generate the synthetic dataset
```bash
python dataset/generate_dataset.py
# Output: dataset/grain_storage_dataset.csv (125,000 rows)
```

### Step 3 — Train all models
```bash
# Train only the AR-TCN (fastest)
python training/train.py --model artcn

# Train all baseline models + AR-TCN
python training/train.py --model all
```

### Step 4 — Evaluate models
```bash
python training/evaluate.py
# Saves plots to models/plots/ and metrics to models/metrics.json
```

### Step 5 — Start the FastAPI backend
```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
# Swagger UI: http://localhost:8000/docs
```

### Step 6 — Start the React dashboard
```bash
cd frontend
npm install
cp .env.example .env        # Fill in Firebase values
npm start
# Dashboard: http://localhost:3000
```

### One-click (Windows)
```powershell
.\deployment\run_pipeline.ps1
```

---

## 🐳 Docker Deployment

```bash
cd deployment
docker-compose up --build
```
- Dashboard: http://localhost:3000
- API:       http://localhost:8000
- Swagger:   http://localhost:8000/docs

---

## 🤖 AR-TCN Architecture

```
Input (batch=B, seq=24, features=F)
    ↓
Input Projection: CausalConv1d → BN → ReLU
    ↓
ResidualBlock (dilation=1):  CausalConv → BN → ReLU → Dropout × 2  + skip
ResidualBlock (dilation=2):  CausalConv → BN → ReLU → Dropout × 2  + skip
ResidualBlock (dilation=4):  CausalConv → BN → ReLU → Dropout × 2  + skip
ResidualBlock (dilation=8):  CausalConv → BN → ReLU → Dropout × 2  + skip
ResidualBlock (dilation=16): CausalConv → BN → ReLU → Dropout × 2  + skip
    ↓
Global Average Pooling (temporal dim)
    ↓
Dense(128) → BN → ReLU → Dropout
Dense(64)  → BN → ReLU → Dropout
Dense(3)   → Softmax
    ↓
Output: [P(Low), P(Moderate), P(High)]
```

**Key features:**
- Dilated convolutions → exponentially growing receptive field
- Causal padding → zero data leakage from the future
- Residual connections → no vanishing gradients
- ~250K trainable parameters

---

## 📊 Dataset Features

| Feature | Range | Unit | Description |
|---------|-------|------|-------------|
| temperature_c | 10–45 | °C | Storage temperature |
| humidity_pct | 20–100 | % | Relative humidity |
| gas_concentration | 250–2500 | ppm | CO₂/VOC proxy |
| grain_moisture | 8–28 | % | Grain moisture content |
| storage_duration | 0–180 | days | Days since batch stored |
| ext_temperature_c | 5–50 | °C | External ambient temp |
| ventilation_status | 0/1 | — | Fan ON/OFF |
| battery_voltage | 3.0–4.2 | V | ESP32 battery level |
| sensor_health | 0/1 | — | Sensor operational status |

**Engineered features (60+ total):**
- Cyclic time encoding (hour, day-of-year, month)
- Interaction terms (temp×humidity, gas/humidity)
- Rolling stats (4-step, 12-step windows)
- Lag features (1, 2, 4, 8 steps)
- Absolute humidity, heat index

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/predict` | Single reading prediction |
| POST | `/predict-sequence` | 24-step sequence prediction |
| GET | `/latest-risk` | Latest from Firebase + predict |
| GET | `/history` | Prediction/sensor/alert history |
| GET | `/alerts` | Recent high-risk alerts |
| GET | `/model-info` | Model metadata + metrics |
| POST | `/train` | Trigger training (async) |
| POST | `/retrain` | Retrain with new data |
| GET | `/docs` | Swagger UI |

---

## 🔥 Firebase Structure

```
/sensor_data/
  latest/          ← ESP32 writes here every 15 min
  {pushId}/        ← Historical readings
/predictions/
  {pushId}/        ← ML backend writes predictions here
/alerts/
  {pushId}/        ← High-risk alerts
/model_info/       ← Current model metadata
```

---

## 📈 Risk Label Logic

Risk is computed using a **weighted agricultural scoring model**:

| Factor | Weight | Safe Threshold | Critical Threshold |
|--------|--------|---------------|-------------------|
| Grain Moisture | 25% | < 13% | > 16% |
| Temperature | 22% | < 25°C | > 35°C |
| Humidity | 20% | < 70% | > 85% |
| Gas (CO₂) | 18% | < 600 ppm | > 1500 ppm |
| Storage Duration | 10% | < 60 days | > 150 days |
| Ext. Temp diff | 5% | < 10°C diff | — |
| Ventilation (ON) | -12% | mitigation factor | — |

Score → Label: `< 0.35` = Low, `0.35–0.65` = Moderate, `> 0.65` = High

---

## 🔧 ESP32 Firebase Integration

Your ESP32 firmware should write to `/sensor_data/latest` in this format:

```json
{
  "timestamp":          "2024-01-15T10:30:00Z",
  "temperature_c":      27.5,
  "humidity_pct":       65.2,
  "gas_concentration":  420.0,
  "grain_moisture":     12.3,
  "storage_duration":   45,
  "ext_temperature_c":  30.0,
  "ventilation_status": 1,
  "battery_voltage":    3.95,
  "sensor_health":      1
}
```

Use the Firebase ESP32 Arduino library with your project credentials.

---

## 👨‍💻 Authors

BE Final Year Students — AI/IoT Integration Project  
Department of Computer Science & Engineering

---

*Built with PyTorch · FastAPI · React · Firebase · Docker*
