/**
 * FILE: frontend/src/App.jsx
 * Root application component.
 * Sets up React Router, AuthProvider, and Toaster.
 */

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout            from "./components/Layout";
import Login             from "./pages/Login";
import Dashboard         from "./pages/Dashboard";
import LiveSensors       from "./pages/LiveSensors";
import HistoricalCharts  from "./pages/HistoricalCharts";
import RiskPrediction    from "./pages/RiskPrediction";
import AlertHistory      from "./pages/AlertHistory";
import ModelPerformance  from "./pages/ModelPerformance";
import Settings          from "./pages/Settings";

// ── Protected Route wrapper ─────────────────────────────────
function ProtectedRoute({ children }) {
  const { user } = useAuth();
  // Allow demo access without auth (remove this check to enforce login)
  return children;
  // Uncomment to enforce auth:
  // return user ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />

      {/* Protected */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"   element={<Dashboard />} />
        <Route path="live"        element={<LiveSensors />} />
        <Route path="history"     element={<HistoricalCharts />} />
        <Route path="prediction"  element={<RiskPrediction />} />
        <Route path="alerts"      element={<AlertHistory />} />
        <Route path="performance" element={<ModelPerformance />} />
        <Route path="settings"    element={<Settings />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#111827",
              color: "#e5e7eb",
              border: "1px solid #374151",
              borderRadius: "8px",
              fontSize: "14px",
            },
            success: { iconTheme: { primary: "#22c55e", secondary: "#111827" } },
            error:   { iconTheme: { primary: "#ef4444", secondary: "#111827" } },
          }}
        />
      </AuthProvider>
    </BrowserRouter>
  );
}
