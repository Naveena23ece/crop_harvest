/**
 * FILE: frontend/src/pages/AlertHistory.jsx
 * Displays the historical list of generated alerts with real-time refresh.
 */

import React, { useEffect, useState, useCallback } from "react";
import { getAlerts, getExportPdfUrl } from "../services/api";
import AlertCard from "../components/AlertCard";
import { formatTimestamp } from "../utils/helpers";
import { FiRefreshCw, FiDownload } from "react-icons/fi";

export default function AlertHistory() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAlerts = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const res = await getAlerts(50);
      setAlerts(res?.alerts || []);
    } catch (err) {
      console.error("Failed to load alerts:", err);
    } finally {
      setLoading(false);
      if (isManual) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(() => {
      fetchAlerts(false);
    }, 8000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="pb-4 border-b border-[var(--border-color)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Alert Incident History</h1>
          <p className="text-[var(--text-muted)] text-xs mt-1">
            Historical high-risk events identified by AR-TCN causal inference and microclimate threshold monitors
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchAlerts(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs font-semibold cursor-pointer transition-colors"
            title="Refresh alerts"
          >
            <FiRefreshCw className={refreshing ? "animate-spin text-emerald-600" : ""} />
            <span>Refresh</span>
          </button>
          <a
            href={getExportPdfUrl("silo-1")}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer shadow-sm transition-colors"
          >
            <FiDownload />
            <span>Export Audit PDF</span>
          </a>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-[var(--bg-surface-elevated)] rounded-xl animate-pulse border border-[var(--border-color)]" />
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-20 bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl shadow-sm">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center font-bold text-lg mb-3">
            ✓
          </div>
          <p className="text-xs text-[var(--text-primary)] font-semibold">No Critical Incidents Recorded</p>
          <p className="text-[11px] text-[var(--text-muted)] mt-1">All monitored storage facilities are within designated microclimate safety thresholds.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert, i) => (
            <div key={alert.id || i}>
              <AlertCard alert={alert} />
              <p className="text-[11px] font-mono text-[var(--text-muted)] mt-1 pl-2">
                Recorded: {formatTimestamp(alert.timestamp)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
