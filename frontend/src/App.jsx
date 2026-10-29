/**
 * FILE: frontend/src/App.jsx
 * Root Application Router with ThemeProvider, AuthProvider, and Role-Gated Protected Routes.
 */

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import { ThemeProvider, useTheme } from "./context/ThemeContext";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import LiveSensors from "./pages/LiveSensors";
import HistoricalCharts from "./pages/HistoricalCharts";
import RiskPrediction from "./pages/RiskPrediction";
import AlertHistory from "./pages/AlertHistory";
import ModelPerformance from "./pages/ModelPerformance";
import Settings from "./pages/Settings";
import UserManagement from "./pages/UserManagement";

// ── Authenticated Route Wrapper ──────────────────────────────
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-app)] flex items-center justify-center text-[var(--text-muted)]">
        <div className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping"></span>
          <span>Initializing GrainGuard AI...</span>
        </div>
      </div>
    );
  }
  return user ? children : <Navigate to="/login" replace />;
}

// ── Admin-Only Route Wrapper ─────────────────────────────────
function AdminRoute({ children }) {
  const { isAdmin, loading } = useAuth();
  if (loading) return null;
  return isAdmin ? children : <Navigate to="/dashboard" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public Authentication Route */}
      <Route path="/login" element={<Login />} />

      {/* Protected Enterprise Monitoring Suite */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="live" element={<LiveSensors />} />
        <Route path="history" element={<HistoricalCharts />} />
        <Route path="prediction" element={<RiskPrediction />} />
        <Route path="alerts" element={<AlertHistory />} />
        <Route path="performance" element={<ModelPerformance />} />

        {/* Admin-Only Management Routes */}
        <Route
          path="users"
          element={
            <AdminRoute>
              <UserManagement />
            </AdminRoute>
          }
        />
        <Route
          path="settings"
          element={
            <AdminRoute>
              <Settings />
            </AdminRoute>
          }
        />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function ThemedToaster() {
  const { isDark } = useTheme();
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        style: {
          background: isDark ? "#111827" : "#ffffff",
          color: isDark ? "#f8fafc" : "#0f172a",
          border: isDark ? "1px solid #1e293b" : "1px solid #e2e8f0",
          borderRadius: "6px",
          fontSize: "13px",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        },
        success: {
          iconTheme: {
            primary: isDark ? "#22c55e" : "#15803d",
            secondary: isDark ? "#111827" : "#ffffff",
          },
        },
        error: {
          iconTheme: {
            primary: isDark ? "#f87171" : "#dc2626",
            secondary: isDark ? "#111827" : "#ffffff",
          },
        },
      }}
    />
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <ThemedToaster />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
