/**
 * FILE: frontend/src/pages/HistoricalCharts.jsx
 * Historical Sensor Data & Executive Reports Center.
 * Features:
 *  - Storage Unit (Silo) Filter Dropdown
 *  - Direct RFC-4180 CSV Export
 *  - Formatted ReportLab Executive PDF Risk Audit Download
 *  - Dynamic multi-sensor telemetry charts & Temp vs Humidity correlation scatter
 */

import React, { useEffect, useState } from "react";
import { getHistory, getStorageUnitsApi, getExportCsvUrl, getExportPdfUrl } from "../services/api";
import SensorChart from "../components/SensorChart";
import toast from "react-hot-toast";
import {
  FiDownload,
  FiFileText,
  FiLayers,
  FiFilter,
  FiRefreshCw,
  FiCalendar,
} from "react-icons/fi";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function HistoricalCharts() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(200);
  const [unitId, setUnitId] = useState("all");
  const [units, setUnits] = useState([]);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    getStorageUnitsApi()
      .then((data) => setUnits(data?.storage_units || []))
      .catch((err) => console.warn("Could not load units:", err));
  }, []);

  const fetchData = () => {
    setLoading(true);
    setError(null);
    getHistory("sensors", limit, unitId === "all" ? null : unitId)
      .then((res) => {
        setRecords(res?.records || []);
      })
      .catch((err) => {
        console.error("Historical data error:", err);
        setError(err.message || "Failed to load telemetry data");
        setRecords([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(fetchData, [limit, unitId]);

  // Handle direct file download with authentication
  const handleDownloadCsv = (type = "sensors") => {
    const url = getExportCsvUrl(type, unitId === "all" ? "silo-1" : unitId, limit);
    window.open(url, "_blank");
    toast.success(`Exporting ${type} CSV...`);
  };

  const handleDownloadPdf = () => {
    const url = getExportPdfUrl(unitId === "all" ? "silo-1" : unitId);
    window.open(url, "_blank");
    toast.success("Generating Executive PDF Risk Audit Report...");
  };

  // Build scatter data: temperature vs humidity, colour by moisture
  const scatterData = records
    .filter((r) => r.temperature_c != null && r.humidity_pct != null)
    .map((r) => ({
      x: parseFloat(r.temperature_c),
      y: parseFloat(r.humidity_pct),
      z: parseFloat(r.grain_moisture || 10) * 5,
      ts: r.timestamp,
    }))
    .filter((d) => !isNaN(d.x) && !isNaN(d.y) && isFinite(d.x) && isFinite(d.y));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header & Export Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            Historical Telemetry & Reports
          </h1>
          <p className="text-[var(--text-muted)] text-xs mt-1">
            Filter multi-silo telemetry trends · Export compliant CSV datasets · Download executive PDF audit reports
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Unit Selector */}
          <div className="flex items-center gap-1.5 bg-[var(--bg-surface)] border border-[var(--border-color)] px-3 py-1.5 rounded-lg text-xs text-[var(--text-primary)]">
            <FiLayers className="text-emerald-600 dark:text-emerald-400" />
            <select
              value={unitId}
              onChange={(e) => setUnitId(e.target.value)}
              className="bg-transparent border-none text-xs text-[var(--text-primary)] focus:outline-none cursor-pointer font-medium"
            >
              <option value="all" className="bg-[var(--bg-surface)] text-[var(--text-primary)]">All Silos (Composite)</option>
              {units.map((u) => (
                <option key={u.unit_id} value={u.unit_id} className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                  {u.name} ({u.unit_id})
                </option>
              ))}
            </select>
          </div>

          {/* Sample Size Limit */}
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="bg-[var(--bg-surface)] border border-[var(--border-color)] text-[var(--text-primary)] text-xs rounded-lg px-3 py-1.5 focus:outline-none cursor-pointer font-medium"
          >
            {[50, 100, 200, 500, 1000].map((v) => (
              <option key={v} value={v} className="bg-[var(--bg-surface)] text-[var(--text-primary)]">
                Last {v} records
              </option>
            ))}
          </select>

          {/* Export CSV */}
          <button
            onClick={() => handleDownloadCsv("sensors")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bg-surface-elevated)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-lg text-xs font-semibold transition cursor-pointer"
          >
            <FiDownload className="text-emerald-600 dark:text-emerald-400" /> Export CSV
          </button>

          {/* Download PDF Report */}
          <button
            onClick={handleDownloadPdf}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm transition cursor-pointer"
          >
            <FiFileText /> Executive PDF Report
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/40 border border-rose-700/50 rounded-xl p-4 text-xs text-rose-300 flex items-center justify-between">
          <span>Failed to load historical data: {error}</span>
          <button
            onClick={fetchData}
            className="px-3 py-1 bg-rose-900/60 hover:bg-rose-800 text-rose-200 rounded text-xs transition"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-64 bg-[var(--bg-surface-elevated)] rounded-xl animate-pulse border border-[var(--border-color)]" />
          ))}
        </div>
      ) : records.length === 0 ? (
        <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl p-12 text-center shadow-sm">
          <p className="text-[var(--text-primary)] font-semibold text-sm mb-1">No Telemetry Records Available</p>
          <p className="text-[var(--text-muted)] text-xs max-w-md mx-auto mb-4">
            The historical telemetry stream for this selection is awaiting additional readings.
          </p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
          >
            Refresh Telemetry
          </button>
        </div>
      ) : (
        <>
          {/* Multi-parameter Trend Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[
              { title: "Temperature (°C)", lines: [{ key: "temperature_c", name: "Temp (°C)" }] },
              { title: "Humidity (%)", lines: [{ key: "humidity_pct", name: "Humidity (%)" }] },
              { title: "Gas Concentration (ppm)", lines: [{ key: "gas_concentration", name: "CO2 / Gas (ppm)" }] },
              { title: "Grain Moisture (%)", lines: [{ key: "grain_moisture", name: "Moisture (%)" }] },
            ].map((p) => (
              <div key={p.title} className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm">
                <SensorChart data={records} title={p.title} lines={p.lines} height={220} />
              </div>
            ))}
          </div>

          {/* Scatter Chart: Temperature vs Humidity Correlation */}
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
                Micro-Climate Spoilage Vector (Temperature vs Humidity Correlation)
              </h3>
              <span className="text-[11px] text-[var(--text-muted)]">
                Bubble scale represents relative grain moisture content
              </span>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="Temperature"
                  unit="°C"
                  tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                  label={{ value: "Temperature (°C)", position: "insideBottom", offset: -5, fill: "var(--text-muted)", fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="Humidity"
                  unit="%"
                  tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                  label={{ value: "Relative Humidity (%)", angle: -90, position: "insideLeft", fill: "var(--text-muted)", fontSize: 11 }}
                />
                <ZAxis type="number" dataKey="z" range={[20, 200]} />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  contentStyle={{
                    backgroundColor: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    color: "var(--text-primary)",
                    fontSize: "12px",
                  }}
                  formatter={(val, name) => [
                    name === "Temperature" ? `${val}°C` : name === "Humidity" ? `${val}%` : val,
                    name,
                  ]}
                />
                <Scatter data={scatterData} fill="#16a34a" opacity={0.75} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
