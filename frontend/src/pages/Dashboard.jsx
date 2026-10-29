import React, { useEffect, useState } from "react";
import { FiThermometer, FiDroplet, FiWind, FiRefreshCw } from "react-icons/fi";
import { GiGrain } from "react-icons/gi";

import useSensorData from "../hooks/useSensorData";
import SensorCard from "../components/SensorCard";
import SensorChart from "../components/SensorChart";
import { getAlerts } from "../services/api";
import { formatSensor, formatTimestamp } from "../utils/helpers";

export default function Dashboard() {
  const { sensorData, prediction, history, loading, error, lastUpdated, refresh } = useSensorData();
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    getAlerts(10).then((res) => setAlerts(res?.alerts || [])).catch(() => setAlerts([]));
  }, []);

  const chartHistory = history.slice(-60);
  const risk = prediction?.risk_category || "—";
  const recommendations = prediction?.recommendations || [];

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Post-harvest storage monitoring</p>
        </div>
        <button onClick={refresh} className="btn-primary" disabled={loading}>
          <FiRefreshCw size={14} /> Refresh
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <div className="metric-grid">
        <SensorCard title="Temperature" value={formatSensor(sensorData?.temperature_c)} unit="°C" icon={<FiThermometer />} loading={loading} />
        <SensorCard title="Humidity" value={formatSensor(sensorData?.humidity_pct)} unit="%" icon={<FiDroplet />} loading={loading} />
        <SensorCard title="Gas Level" value={formatSensor(sensorData?.gas_concentration, "", 0)} unit="ppm" icon={<FiWind />} loading={loading} />
        <SensorCard title="Grain Moisture" value={formatSensor(sensorData?.grain_moisture)} unit="%" icon={<GiGrain />} loading={loading} />
      </div>

      <div className="chart-grid">
        <div className="panel-card">
          <SensorChart title="Temperature Trend" data={chartHistory} lines={[{ key: "temperature_c", name: "Temperature (°C)" }]} height={230} />
        </div>
        <div className="panel-card">
          <SensorChart title="Humidity Trend" data={chartHistory} lines={[{ key: "humidity_pct", name: "Humidity (%)" }]} height={230} />
        </div>
      </div>

      <div className="info-grid">
        <div className="panel-card">
          <h2>Risk Prediction</h2>
          <div className="risk-summary">
            <span className={`risk-label risk-${String(risk).toLowerCase()}`}>{risk}</span>
            {prediction?.confidence != null && (
              <span className="confidence">Confidence: {Math.round(prediction.confidence * 100)}%</span>
            )}
          </div>
          <p className="muted-text">Model: {prediction?.model_name || "Not available"}</p>
        </div>

        <div className="panel-card">
          <h2>Recommended Actions</h2>
          {recommendations.length ? (
            <ul className="action-list">
              {recommendations.slice(0, 5).map((item, index) => <li key={index}>{item}</li>)}
            </ul>
          ) : (
            <p className="muted-text">No recommendations available.</p>
          )}
        </div>
      </div>

      <div className="panel-card alerts-card">
        <div className="panel-header">
          <h2>Recent Alerts</h2>
          <span className="muted-text">Last updated: {lastUpdated ? formatTimestamp(lastUpdated) : "—"}</span>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Date / Time</th><th>Severity</th><th>Message</th><th>Status</th></tr>
            </thead>
            <tbody>
              {alerts.length ? alerts.slice(0, 6).map((alert, index) => (
                <tr key={index}>
                  <td>{alert.timestamp ? formatTimestamp(alert.timestamp) : "—"}</td>
                  <td>{alert.risk_category || "High"}</td>
                  <td>{alert.message || "Storage risk detected"}</td>
                  <td>Recorded</td>
                </tr>
              )) : (
                <tr><td colSpan="4" className="empty-row">No recent alerts recorded</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
