/**
 * FILE: frontend/src/pages/HistoricalCharts.jsx
 * Historical sensor data charts with date filtering and heatmap.
 */

import React, { useEffect, useState } from "react";
import { getHistory }    from "../services/api";
import SensorChart       from "../components/SensorChart";
import { formatTimestamp } from "../utils/helpers";
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis,
  Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

export default function HistoricalCharts() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [limit,   setLimit]   = useState(200);

  const fetchData = () => {
    setLoading(true);
    setError(null);
    getHistory("sensors", limit)
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

  useEffect(fetchData, [limit]);

  // Build scatter data: temperature vs humidity, colour by moisture
  const scatterData = records
    .filter((r) => r.temperature_c != null && r.humidity_pct != null)
    .map((r) => ({
      x:    parseFloat(r.temperature_c),
      y:    parseFloat(r.humidity_pct),
      z:    parseFloat(r.grain_moisture || 10) * 5,
      ts:   r.timestamp,
    }))
    .filter((d) => !isNaN(d.x) && !isNaN(d.y) && isFinite(d.x) && isFinite(d.y));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Historical Charts</h1>
          <p className="text-gray-500 text-sm mt-1">
            Sensor trends and correlations · Replayed storage telemetry (Phase 1 Software Prototype)
          </p>
        </div>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="bg-gray-900 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
        >
          {[100, 200, 500, 1000].map((v) => (
            <option key={v} value={v}>Last {v} readings</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-950/40 border border-red-700/50 rounded-xl p-4 text-sm text-red-300 flex items-center justify-between">
          <span>Failed to load historical data: {error}</span>
          <button
            onClick={fetchData}
            className="px-3 py-1 bg-red-900/60 hover:bg-red-800 text-red-200 rounded text-xs transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-64 bg-gray-900 rounded-xl animate-pulse border border-gray-800" />
          ))}
        </div>
      ) : records.length === 0 ? (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-12 text-center">
          <p className="text-gray-400 font-medium text-base mb-1">No Telemetry Records Available</p>
          <p className="text-gray-600 text-xs max-w-md mx-auto mb-4">
            The historical telemetry buffer is currently empty or awaiting sensor ingest.
          </p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Refresh Telemetry
          </button>
        </div>
      ) : (
        <>
          {/* Line charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[
              { title: "Temperature (°C)", lines: [{ key: "temperature_c", name: "Temp" }] },
              { title: "Humidity (%)",     lines: [{ key: "humidity_pct",   name: "Humidity" }] },
              { title: "Gas Concentration (ppm)", lines: [{ key: "gas_concentration", name: "Gas" }] },
              { title: "Grain Moisture (%)", lines: [{ key: "grain_moisture", name: "Moisture" }] },
            ].map((p) => (
              <div key={p.title} className="bg-gray-900 rounded-xl border border-gray-800 p-5">
                <SensorChart data={records} title={p.title} lines={p.lines} height={220} />
              </div>
            ))}
          </div>

          {/* Scatter: Temp vs Humidity */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <h3 className="text-sm font-medium text-gray-400 mb-3">
              Temperature vs Humidity Scatter (bubble size = grain moisture)
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  type="number" dataKey="x" name="Temperature"
                  unit="°C" tick={{ fill: "#6b7280", fontSize: 11 }}
                  label={{ value: "Temperature (°C)", position: "insideBottom",
                           offset: -5, fill: "#6b7280", fontSize: 11 }}
                />
                <YAxis
                  type="number" dataKey="y" name="Humidity"
                  unit="%" tick={{ fill: "#6b7280", fontSize: 11 }}
                  label={{ value: "Humidity (%)", angle: -90, position: "insideLeft",
                           fill: "#6b7280", fontSize: 11 }}
                />
                <ZAxis type="number" dataKey="z" range={[20, 200]} />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151",
                                  borderRadius: "8px", color: "#e5e7eb", fontSize: "12px" }}
                  formatter={(val, name) => [
                    name === "Temperature" ? `${val}°C` :
                    name === "Humidity"    ? `${val}%`  : val,
                    name,
                  ]}
                />
                <Scatter data={scatterData} fill="#22c55e" opacity={0.6} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
