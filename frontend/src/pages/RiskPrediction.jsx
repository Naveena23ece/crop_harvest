/**
 * FILE: frontend/src/pages/RiskPrediction.jsx
 * Manual risk prediction page.
 * User can input sensor values and get an immediate prediction from the backend.
 */

import React, { useState } from "react";
import { predictSingle } from "../services/api";
import RiskBadge         from "../components/RiskBadge";
import AlertCard         from "../components/AlertCard";
import toast             from "react-hot-toast";
import { RISK_COLORS }   from "../utils/helpers";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const DEFAULT_FORM = {
  temperature_c:      28.0,
  humidity_pct:       65.0,
  gas_concentration:  480.0,
  grain_moisture:     12.0,
  storage_duration:   45,
  ext_temperature_c:  30.0,
  ventilation_status: 1,
  battery_voltage:    3.9,
  sensor_health:      1,
};

const FIELDS = [
  { key: "temperature_c",      label: "Temperature (°C)",    min: 10,  max: 60,   step: 0.1 },
  { key: "humidity_pct",       label: "Humidity (%)",         min: 20,  max: 100,  step: 0.1 },
  { key: "gas_concentration",  label: "Gas Concentration (ppm)", min: 250, max: 2500, step: 1 },
  { key: "grain_moisture",     label: "Grain Moisture (%)",   min: 8,   max: 28,   step: 0.1 },
  { key: "storage_duration",   label: "Storage Duration (days)", min: 0, max: 180, step: 1 },
  { key: "ext_temperature_c",  label: "Ext. Temperature (°C)", min: 5, max: 55,   step: 0.1 },
];

const TOGGLES = [
  { key: "ventilation_status", label: "Ventilation Status",  on: "ON",  off: "OFF" },
  { key: "sensor_health",      label: "Sensor Health",        on: "Healthy", off: "Degraded" },
];

export default function RiskPrediction() {
  const [form,        setForm]        = useState(DEFAULT_FORM);
  const [unitId,      setUnitId]      = useState("silo-1");
  const [result,      setResult]      = useState(null);
  const [loading,     setLoading]     = useState(false);

  const handleChange = (key, value) =>
    setForm((prev) => ({ ...prev, [key]: parseFloat(value) }));

  const handleToggle = (key) =>
    setForm((prev) => ({ ...prev, [key]: prev[key] === 1 ? 0 : 1 }));

  const handlePreset = (preset) => {
    if (preset === "high")
      setForm({ temperature_c: 38, humidity_pct: 88, gas_concentration: 1600,
                grain_moisture: 19, storage_duration: 120, ext_temperature_c: 42,
                ventilation_status: 0, battery_voltage: 3.6, sensor_health: 1 });
    else if (preset === "low")
      setForm({ temperature_c: 18, humidity_pct: 45, gas_concentration: 320,
                grain_moisture: 10, storage_duration: 15, ext_temperature_c: 22,
                ventilation_status: 1, battery_voltage: 4.0, sensor_health: 1 });
    else setForm(DEFAULT_FORM);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await predictSingle(form, unitId);
      setResult(res);
      toast.success(`Prediction: ${res.risk_category} Risk for ${unitId}`);
    } catch (err) {
      toast.error(`Prediction failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Build bar chart data from probabilities
  const barData = result?.probabilities
    ? Object.entries(result.probabilities).map(([k, v]) => ({
        name: k, value: Math.round(v * 100), color: RISK_COLORS[k],
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Risk Prediction</h1>
        <p className="text-gray-500 text-sm mt-1">
          Manually enter sensor readings to get an instant AI risk prediction
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* ── Input form ─────────────────────────────── */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-medium text-gray-300 uppercase tracking-wide">
              Sensor Readings
            </h2>
            <div className="flex gap-2">
              {["low", "default", "high"].map((p) => (
                <button
                  key={p}
                  onClick={() => handlePreset(p)}
                  className="text-xs px-3 py-1 rounded-full bg-gray-800 hover:bg-gray-700
                             text-gray-400 hover:text-white border border-gray-700 transition-colors"
                >
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {FIELDS.map(({ key, label, min, max, step }) => (
              <div key={key}>
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <label htmlFor={key}>{label}</label>
                  <span className="font-mono text-white">{form[key]}</span>
                </div>
                <input
                  id={key}
                  type="range"
                  min={min} max={max} step={step}
                  value={form[key]}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-full accent-green-500 h-2 cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-700">
                  <span>{min}</span><span>{max}</span>
                </div>
              </div>
            ))}

            {/* Toggles */}
            <div className="grid grid-cols-2 gap-4 pt-2">
              {TOGGLES.map(({ key, label, on, off }) => (
                <div key={key}>
                  <p className="text-xs text-gray-400 mb-1">{label}</p>
                  <button
                    type="button"
                    onClick={() => handleToggle(key)}
                    className={`w-full py-2 rounded-lg text-sm font-medium border transition-colors
                                ${form[key] === 1
                                  ? "bg-green-700/30 border-green-600 text-green-400"
                                  : "bg-gray-800 border-gray-700 text-gray-400"
                                }`}
                  >
                    {form[key] === 1 ? on : off}
                  </button>
                </div>
              ))}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-900
                         text-white font-semibold rounded-lg transition-colors flex items-center
                         justify-center gap-2"
            >
              {loading ? (
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10"
                          stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
              ) : "🔮 Predict Risk"}
            </button>
          </form>
        </div>

        {/* ── Result panel ───────────────────────────── */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Main result */}
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-4">
                  Prediction Result
                </p>
                <RiskBadge
                  risk={result.risk_category}
                  confidence={result.confidence}
                  size="lg"
                />
                <p className="text-gray-500 text-sm mt-3">
                  Model: <span className="text-gray-300">{result.model_name}</span>
                </p>
              </div>

              {/* Probability bar chart */}
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
                <h3 className="text-sm text-gray-400 mb-3">Class Probabilities</h3>
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={barData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                    <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                    <YAxis domain={[0, 100]} tick={{ fill: "#9ca3af", fontSize: 11 }}
                           tickFormatter={(v) => `${v}%`} />
                    <Tooltip
                      formatter={(v) => [`${v}%`, "Probability"]}
                      contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151",
                                      borderRadius: "8px", color: "#e5e7eb" }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {barData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Alert with recommendations */}
              <AlertCard
                alert={{
                  risk_category:   result.risk_category,
                  message:         result.risk_category === "High"
                                     ? "⚠ High risk — take immediate action"
                                     : `${result.risk_category} risk conditions detected`,
                  recommendations: result.recommendations,
                  timestamp:       result.timestamp,
                }}
              />
            </>
          ) : (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-10
                            flex flex-col items-center justify-center text-center h-full">
              <div className="text-5xl mb-4">🔮</div>
              <p className="text-gray-500">
                Adjust the sensor sliders and click<br/>
                <span className="text-green-400">Predict Risk</span> to see the result
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
