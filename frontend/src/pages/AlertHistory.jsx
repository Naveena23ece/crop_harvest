/**
 * FILE: frontend/src/pages/AlertHistory.jsx
 * Displays the historical list of generated alerts from Firebase.
 */

import React, { useEffect, useState } from "react";
import { getAlerts }         from "../services/api";
import AlertCard             from "../components/AlertCard";
import { formatTimestamp }   from "../utils/helpers";

export default function AlertHistory() {
  const [alerts,  setAlerts]  = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAlerts(50)
      .then((res) => setAlerts(res?.alerts || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="pb-4 border-b border-[var(--border-color)]">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Alert Incident History</h1>
        <p className="text-[var(--text-muted)] text-xs mt-1">
          Historical high-risk events identified by AR-TCN causal inference and microclimate threshold monitors
        </p>
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
            <div key={i}>
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
