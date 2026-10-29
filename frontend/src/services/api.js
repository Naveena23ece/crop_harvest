/**
 * FILE: frontend/src/services/api.js
 * Axios-based API client for the FastAPI backend.
 * All backend calls are centralised here.
 */

import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// â”€â”€ Request interceptor (attach auth token if present) â”€â”€â”€â”€â”€â”€
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) config.headers.Authorization = Bearer ;
  return config;
});

// â”€â”€ Response interceptor (uniform error handling) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
apiClient.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || "Unknown error";
    return Promise.reject(new Error(msg));
  }
);

// â”€â”€â”€ API Functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** POST /predict â€” single reading */
export const predictSingle = (sensorData) =>
  apiClient.post("/predict", sensorData);

/** POST /predict-sequence â€” 24-step sequence */
export const predictSequence = (readings) =>
  apiClient.post("/predict-sequence", { readings });

/** GET /latest-risk â€” fetch latest from Firebase + predict */
export const getLatestRisk = (useMock = false) =>
  apiClient.get(`/latest-risk?use_mock=${useMock}`);

/** GET /history */
export const getHistory = (type = "predictions", limit = 50) =>
  apiClient.get(`/history?type=${type}&limit=${limit}`);

/** GET /alerts */
export const getAlerts = (limit = 20) =>
  apiClient.get(`/alerts?limit=${limit}`);

/** GET /model-info */
export const getModelInfo = () =>
  apiClient.get("/model-info");

/** POST /train */
export const triggerTraining = (payload) =>
  apiClient.post("/train", payload);

/** GET /health */
export const healthCheck = () =>
  apiClient.get("/health");

/** GET /recommendations/:level */
export const getRecommendations = (level) =>
  apiClient.get(`/recommendations/${level}`);

export default apiClient;

