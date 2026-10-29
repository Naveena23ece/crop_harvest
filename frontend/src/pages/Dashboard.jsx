/**
 * FILE: frontend/src/pages/Dashboard.jsx
 * GrainGuard AI Central Monitoring Console.
 * Features:
 *  - Storage Unit (Silo) Selector with real-time risk updates
 *  - Metric cards for Temperature, Humidity, Gas, Grain Moisture
 *  - Rolling temporal trend charts
 *  - Actionable DSS recommendations
 *  - Role-aware Alert table (Admin can acknowledge, Viewer is read-only)
 */

import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  FiThermometer,
  FiDroplet,
  FiWind,
  FiRefreshCw,
  FiCheck,
  FiAlertTriangle,
  FiLayers,
} from "react-icons/fi";
import { GiGrain } from "react-icons/gi";

import SensorCard from "../components/SensorCard";
import SensorChart from "../components/SensorChart";
import {
  getLatestRisk,
  getHistory,
  getAlerts,
  getStorageUnitsApi,
  acknowledgeAlertApi,
} from "../services/api";
import { formatSensor, formatTimestamp } from "../utils/helpers";
import toast from "react-hot-toast";

export default function Dashboard() {
  const { isAdmin } = useAuth();
  const [selectedUnit, setSelectedUnit] = useState("silo-1");
  const [units, setUnits] = useState([]);
  const [sensorData, setSensorData] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Load storage units
  useEffect(() => {
    getStorageUnitsApi()
      .then((data) => setUnits(data?.storage_units || []))
      .catch((err) => console.warn("Failed to load units:", err));
  }, []);

  // Fetch telemetry and prediction for the selected unit
  const refreshData = async () => {
    setLoading(true);
    try {
      const riskRes = await getLatestRisk(false, selectedUnit);
      if (riskRes?.sensor_data) setSensorData(riskRes.sensor_data);
      if (riskRes?.prediction) setPrediction(riskRes.prediction);

      const histRes = await getHistory("sensors", 50, selectedUnit);
      if (histRes?.records) setHistory(histRes.records);

      const alertRes = await getAlerts(10, selectedUnit);
      if (alertRes?.alerts) setAlerts(alertRes.alerts);

      setLastUpdated(new Date());
    } catch (err) {
      console.warn("Telemetry refresh error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
    const timer = setInterval(refreshData, 30000);
    return () => clearInterval(timer);
  }, [selectedUnit]);

  const handleAcknowledge = async (alertId) => {
    if (!isAdmin) {
      toast.error("Only Administrators can modify or acknowledge alerts.");
      return;
    }
    try {
      await acknowledgeAlertApi(alertId);
      toast.success(`Alert #${alertId} acknowledged.`);
      refreshData();
    } catch (err) {
      toast.error("Failed to acknowledge alert: " + err.message);
    }
  };

  const chartHistory = history.slice(-50);
  const risk = prediction?.risk_category || "Low";
  const recommendations = prediction?.recommendations || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            Storage Risk Monitoring Dashboard
          </h1>
          <p className="text-[var(--text-muted)] text-xs mt-1">
            Real-time multi-sensor telemetry, temporal trend analysis, and adaptive risk classification
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Silo Selector */}
          <div className="flex items-center gap-2 bg-[var(--bg-surface)] border border-[var(--border-color)] px-3 py-1.5 rounded-lg text-xs text-[var(--text-primary)]">
            <FiLayers className="text-emerald-600 dark:text-emerald-400" />
            <span className="font-semibold text-[var(--text-muted)]">Unit:</span>
            <select
              value={selectedUnit}
              onChange={(e) => setSelectedUnit(e.target.value)}
              className="bg-transparent border-none text-xs text-[var(--text-primary)] font-semibold focus:outline-none cursor-pointer"
            >
              {units.length > 0 ? (
                units.map((u) => (
                  <option key={u.unit_id} value={u.unit_id} className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                    {u.name} ({u.unit_id})
                  </option>
                ))
              ) : (
                <option value="silo-1" className="bg-[var(--bg-surface)] text-[var(--text-primary)]">Main Silo (silo-1)</option>
              )}
            </select>
          </div>

          <button
            onClick={refreshData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <FiRefreshCw className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {/* Sensor Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SensorCard
          title="Internal Temperature"
          value={formatSensor(sensorData?.temperature_c)}
          unit="°C"
          icon={<FiThermometer className="text-rose-500 dark:text-rose-400" />}
          loading={loading}
        />
        <SensorCard
          title="Relative Humidity"
          value={formatSensor(sensorData?.humidity_pct)}
          unit="%"
          icon={<FiDroplet className="text-blue-500 dark:text-blue-400" />}
          loading={loading}
        />
        <SensorCard
          title="CO2 / Gas Concentration"
          value={formatSensor(sensorData?.gas_concentration, "", 0)}
          unit="ppm"
          icon={<FiWind className="text-amber-500 dark:text-amber-400" />}
          loading={loading}
        />
        <SensorCard
          title="Grain Moisture"
          value={formatSensor(sensorData?.grain_moisture)}
          unit="%"
          icon={<GiGrain className="text-emerald-600 dark:text-emerald-400" />}
          loading={loading}
        />
      </div>

      {/* Real-time Trend Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm">
          <SensorChart
            title="Temperature Profile (°C)"
            data={chartHistory}
            lines={[{ key: "temperature_c", name: "Temperature (°C)" }]}
            height={220}
          />
        </div>
        <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm">
          <SensorChart
            title="Relative Humidity Profile (%)"
            data={chartHistory}
            lines={[{ key: "humidity_pct", name: "Humidity (%)" }]}
            height={220}
          />
        </div>
      </div>

      {/* Risk Assessment & DSS Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl p-5 space-y-3 shadow-sm">
          <h2 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
            Predicted Spoilage Risk
          </h2>
          <div className="flex items-center gap-3">
            <span
              className={`px-3 py-1.5 rounded-lg text-sm font-bold uppercase tracking-wider ${
                risk === "High"
                  ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                  : risk === "Moderate"
                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                  : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
              }`}
            >
              {risk} Risk
            </span>
            {prediction?.confidence != null && (
              <span className="text-xs text-[var(--text-muted)] font-mono">
                {(prediction.confidence * 100).toFixed(1)}% Confidence
              </span>
            )}
          </div>
          <p className="text-[11px] text-[var(--text-muted)] font-mono">
            Evaluated by AR-TCN Model (Temporal Receptive Field)
          </p>
        </div>

        <div className="lg:col-span-2 bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl p-5 space-y-2 shadow-sm">
          <h2 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
            Decision Support System (DSS) Recommended Actions
          </h2>
          {recommendations.length > 0 ? (
            <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
              {recommendations.slice(0, 4).map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-[var(--text-muted)]">Storage microclimate is stable. Continue routine monitoring.</p>
          )}
        </div>
      </div>

      {/* Storage Unit Incidents & Alert Records */}
      <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-[var(--border-color)] flex justify-between items-center">
          <div className="flex items-center gap-2">
            <FiAlertTriangle className="text-amber-500" />
            <span className="text-sm font-semibold text-[var(--text-primary)]">
              Storage Unit Alert Log ({selectedUnit})
            </span>
          </div>
          <span className="text-[11px] text-[var(--text-muted)] font-mono">
            Last Updated: {lastUpdated ? formatTimestamp(lastUpdated) : "—"}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[var(--text-secondary)]">
            <thead className="bg-[var(--bg-surface-elevated)] border-b border-[var(--border-color)] text-[var(--text-secondary)] uppercase tracking-wider text-[10px]">
              <tr>
                <th className="p-3">Timestamp</th>
                <th className="p-3">Risk Level</th>
                <th className="p-3">Alert Message</th>
                <th className="p-3">Status</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {alerts.length > 0 ? (
                alerts.slice(0, 5).map((a, idx) => (
                  <tr key={idx} className="hover:bg-[var(--bg-surface-elevated)]">
                    <td className="p-3 font-mono text-[var(--text-muted)]">
                      {a.timestamp ? formatTimestamp(a.timestamp) : "—"}
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30">
                        {a.level || a.risk_category || "HIGH"}
                      </span>
                    </td>
                    <td className="p-3 text-[var(--text-primary)]">{a.message || "High risk condition detected"}</td>
                    <td className="p-3">
                      <span className={`text-[11px] ${a.acknowledged ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                        {a.acknowledged ? `Acknowledged by ${a.acknowledged_by || "Admin"}` : "Unacknowledged"}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      {isAdmin ? (
                        <button
                          onClick={() => handleAcknowledge(a.id)}
                          disabled={a.acknowledged}
                          className="px-2 py-1 bg-[var(--bg-surface-elevated)] hover:bg-[var(--border-color)] disabled:opacity-40 rounded text-[11px] text-[var(--text-primary)] flex items-center gap-1 ml-auto cursor-pointer"
                        >
                          <FiCheck className="text-emerald-600 dark:text-emerald-400" /> {a.acknowledged ? "Acknowledged" : "Acknowledge"}
                        </button>
                      ) : (
                        <span className="text-[10px] text-[var(--text-muted)] italic">Read-Only</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="p-4 text-center text-[var(--text-muted)]">
                    No active high-risk alerts recorded for this silo.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
