/**
 * FILE: frontend/src/components/SensorChart.jsx
 * Responsive Recharts line chart for plotting sensor time series.
 * Supports multi-line overlay (e.g. temperature + humidity on same axes).
 */

import React from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import { timeTickFormatter } from "../utils/helpers";

const COLORS = ["#2563EB", "#64748B", "#DC2626", "#D97706", "#7C3AED"];

/**
 * @param {Object[]} data         - Array of data points with timestamp + value keys
 * @param {Object[]} lines        - [{ key: "temperature_c", name: "Temp (°C)" }, ...]
 * @param {string}   title        - Chart title
 * @param {number}   height       - Chart height in px (default 260)
 * @param {Object}   thresholds   - { key: value } reference lines (optional)
 */
export default function SensorChart({
  data       = [],
  lines      = [],
  title      = "",
  height     = 260,
  thresholds = {},
}) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-gray-500 text-sm"
        style={{ height }}
      >
        No data available
      </div>
    );
  }

  return (
    <div>
      {title && (
        <h3 className="text-sm font-medium text-gray-400 mb-3">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={timeTickFormatter}
            tick={{ fill: "#6b7280", fontSize: 11 }}
            stroke="#374151"
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            stroke="#374151"
            width={40}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #D1D5DB",
              borderRadius: "4px",
              color: "#1F2937",
              fontSize: "12px",
            }}
            labelFormatter={timeTickFormatter}
          />
          {lines.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: "12px", color: "#9ca3af" }}
            />
          )}

          {/* Reference lines (thresholds) */}
          {Object.entries(thresholds).map(([label, value]) => (
            <ReferenceLine
              key={label}
              y={value}
              stroke="#ef4444"
              strokeDasharray="4 4"
              label={{ value: label, position: "right", fill: "#ef4444", fontSize: 10 }}
            />
          ))}

          {/* Data lines */}
          {lines.map(({ key, name }, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={name || key}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
              activeDot={{ r: 3, strokeWidth: 0 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
