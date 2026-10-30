/**
 * FILE: frontend/src/services/api.js
 * Axios-based API client for the GrainGuard AI FastAPI backend.
 * Provides complete authenticated methods for RBAC, Telemetry, Storage Units, Reports, and System Diagnostics.
 */

import axios from "axios";

const BASE_URL = (process.env.REACT_APP_API_URL || "https://grainguard-backend-ssva.onrender.com").replace(/\/$/, "");

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor: attach session token from sessionStorage ──
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("grainguard_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor ──
apiClient.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || "Unknown error occurred";
    return Promise.reject(new Error(msg));
  }
);

// ── Authentication Endpoints ──
export const loginApi = (username, password) =>
  apiClient.post("/auth/login", { username, password });

export const signupApi = (username, email, password) =>
  apiClient.post("/auth/signup", { username, email, password });

export const logoutApi = () =>
  apiClient.post("/auth/logout");

export const getMeApi = () =>
  apiClient.get("/auth/me");

// ── Admin User Management ──
export const listUsersApi = () =>
  apiClient.get("/admin/users");

export const createUserApi = (userData) =>
  apiClient.post("/admin/users", userData);

export const updateUserApi = (userId, updates) =>
  apiClient.patch(`/admin/users/${userId}`, updates);

export const getAuditLogsApi = (limit = 100, offset = 0) =>
  apiClient.get(`/admin/audit-logs?limit=${limit}&offset=${offset}`);

// ── Notifications Configuration & Logs ──
export const getNotificationConfigApi = () =>
  apiClient.get("/admin/notifications/config");

export const updateNotificationConfigApi = (config) =>
  apiClient.post("/admin/notifications/config", config);

export const testNotificationApi = (channel, target = null) =>
  apiClient.post("/admin/notifications/test", { channel, target });

export const getNotificationLogsApi = (limit = 50) =>
  apiClient.get(`/admin/notifications/logs?limit=${limit}`);

// ── Storage Units (Silos) ──
export const getStorageUnitsApi = () =>
  apiClient.get("/storage-units");

export const getStorageUnitDetailsApi = (unitId) =>
  apiClient.get(`/storage-units/${unitId}`);

export const createStorageUnitApi = (unitData) =>
  apiClient.post("/admin/storage-units", unitData);

export const updateStorageUnitApi = (unitId, updates) =>
  apiClient.patch(`/admin/storage-units/${unitId}`, updates);

// ── System Health & Model Performance ──
export const getSystemStatusApi = () =>
  apiClient.get("/system/status");

export const healthCheck = () =>
  apiClient.get("/health");

export const getModelInfo = () =>
  apiClient.get("/model-info");

// ── Predictions & Telemetry ──
export const predictSingle = (sensorData, unitId = "silo-1") =>
  apiClient.post(`/predict?unit_id=${unitId}`, sensorData);

export const predictSequence = (readings, unitId = "silo-1") =>
  apiClient.post(`/predict-sequence?unit_id=${unitId}`, { readings });

export const getLatestRisk = (useMock = false, unitId = "silo-1") =>
  apiClient.get(`/latest-risk?use_mock=${useMock}&unit_id=${unitId}`);

export const getHistory = (type = "predictions", limit = 50, unitId = null) => {
  let url = `/history?type=${type}&limit=${limit}`;
  if (unitId && unitId !== "all") url += `&unit_id=${unitId}`;
  return apiClient.get(url);
};

export const getAlerts = (limit = 20, unitId = null) => {
  let url = `/alerts?limit=${limit}`;
  if (unitId && unitId !== "all") url += `&unit_id=${unitId}`;
  return apiClient.get(url);
};

export const acknowledgeAlertApi = (alertId) =>
  apiClient.post(`/alerts/${alertId}/acknowledge`);

export const getRecommendations = (level) =>
  apiClient.get(`/recommendations/${level}`);

export const triggerTraining = (payload) =>
  apiClient.post("/train", payload);

// ── Direct Download URLs for CSV / PDF ──
export const getExportCsvUrl = (type = "predictions", unitId = "silo-1", limit = 1000) => {
  const token = sessionStorage.getItem("grainguard_token");
  return `${BASE_URL}/export/csv?type=${type}&unit_id=${unitId}&limit=${limit}&auth_token=${token || ""}`;
};

export const getExportPdfUrl = (unitId = "silo-1") => {
  const token = sessionStorage.getItem("grainguard_token");
  return `${BASE_URL}/export/pdf?unit_id=${unitId}&auth_token=${token || ""}`;
};

export default apiClient;
