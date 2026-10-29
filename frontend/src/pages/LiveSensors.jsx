/**
 * FILE: frontend/src/pages/LiveSensors.jsx
 * Real-time sensor monitoring page.
 * Shows live updating charts for all 4 primary sensors.
 */

import React from "react";
import useSensorData from "../hooks/useSensorData";
import SensorChart   from "../components/SensorChart";
import RiskBadge     from "../components/RiskBadge";
import { formatSensor, formatTimestamp } from "../utils/helpers";

const SENSOR_PANELS = [
  {
    title: "Temperature (°C)",
    lines: [{ key: "temperature_c", name: "Temperature" }],
    thresholds: { "Safe limit 30°C": 30, "Critical 38°C": 38 },
    safeRange: "10 – 30°C",
  },
  {
    title: "Relative Humidity (%)",
    lines: [{ key: "humidity_pct", name: "Humidity" }],
    thresholds: { "70% threshold": 70, "85% critical": 85 },
    safeRange: "20 – 70%",
  },
  {
    title: "Gas Concentration (ppm)",
    lines: [{ key: "gas_concentration", name: "Gas (CO₂)" }],
    thresholds: { "600 ppm alert": 600, "1500 ppm danger": 1500 },
    safeRange: "250 – 600 ppm",
  },
  {
    title: "Grain Moisture Content (%)",
    lines: [{ key: "grain_moisture", name: "Moisture" }],
    thresholds: { "13% safe limit": 13, "16% critical": 16 },
    safeRange: "8 – 13%",
  },
];

export default function LiveSensors() {
  const { sensorData, prediction, history, loading, lastUpdated } = useSensorData();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Sensor Data</h1>
          <p className="text-gray-500 text-sm mt-1">
            Updates every 15 minutes from ESP32 IoT module
            {lastUpdated && ` · Last: ${formatTimestamp(lastUpdated)}`}
          </p>
        </div>
        {prediction && (
          <RiskBadge
            risk={prediction.risk_category}
            confidence={prediction.confidence}
            size="md"
          />
        )}
      </div>

      {/* Live value strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Temperature", value: formatSensor(sensorData?.temperature_c, " °C") },
          { label: "Humidity",    value: formatSensor(sensorData?.humidity_pct,  " %") },
          { label: "Gas",         value: formatSensor(sensorData?.gas_concentration, " ppm", 0) },
          { label: "Moisture",    value: formatSensor(sensorData?.grain_moisture, " %") },
        ].map(({ label, value }) => (
          <div key={label}
               className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
            <p className={`text-2xl font-bold ${loading ? "text-gray-600" : "text-white"}`}>
              {loading ? "..." : value}
            </p>
          </div>
        ))}
      </div>

      {/* Individual sensor charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {SENSOR_PANELS.map((panel) => (
          <div key={panel.title}
               className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-medium text-gray-300">{panel.title}</h3>
              <span className="text-xs text-gray-600">
                Safe range: {panel.safeRange}
              </span>
            </div>
            <SensorChart
              data={history.slice(-96)}    // last 24 hours at 15-min intervals
              lines={panel.lines}
              thresholds={panel.thresholds}
              height={220}
            />
          </div>
        ))}
      </div>

      {/* Correlation chart */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Multi-Sensor Overlay (last 48 readings)
        </h3>
        <SensorChart
          data={history.slice(-48)}
          lines={[
            { key: "temperature_c",  name: "Temp (°C)"   },
            { key: "humidity_pct",   name: "Humidity (%)" },
            { key: "grain_moisture", name: "Moisture (%)" },
          ]}
          height={300}
        />
      </div>
    </div>
  );
}
