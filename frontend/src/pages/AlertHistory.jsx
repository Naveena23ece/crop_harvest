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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Alert History</h1>
        <p className="text-gray-500 text-sm mt-1">
          High-risk events detected by the AR-TCN model (Live session memory & software-phase baseline)
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-900 rounded-xl animate-pulse border border-gray-800" />
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <div className="text-5xl mb-4">✅</div>
          <p>No alerts recorded — storage conditions are healthy!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert, i) => (
            <div key={i}>
              <AlertCard alert={alert} />
              <p className="text-xs text-gray-700 mt-1 pl-2">
                {formatTimestamp(alert.timestamp)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
