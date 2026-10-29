/**
 * FILE: frontend/src/components/SensorChart.jsx
 * Theme-aware Recharts time-series chart for GrainGuard AI telemetry.
 * Dynamically switches grid lines, axes, legends, and tooltip surfaces for Light and Dark themes.
 */

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import { useTheme } from "../context/ThemeContext";
import { timeTickFormatter } from "../utils/helpers";

const COLORS = ["#16a34a", "#2563eb", "#d97706", "#9333ea", "#e11d48"];

export default function SensorChart({
  data = [],
  lines = [],
  title = "",
  height = 240,
  thresholds = {},
}) {
  const { isDark } = useTheme();

  const gridColor = isDark ? "#1e293b" : "#e2e8f0";
  const axisColor = isDark ? "#64748b" : "#94a3b8";
  const tooltipBg = isDark ? "#111827" : "#ffffff";
  const tooltipBorder = isDark ? "#334155" : "#e2e8f0";
  const tooltipText = isDark ? "#f8fafc" : "#0f172a";

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-[var(--text-muted)] text-xs font-mono"
        style={{ height }}
      >
        No telemetry records available
      </div>
    );
  }

  return (
    <div>
      {title && (
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-3">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={timeTickFormatter}
            tick={{ fill: axisColor, fontSize: 10 }}
            stroke={gridColor}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: axisColor, fontSize: 10 }}
            stroke={gridColor}
            width={38}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: tooltipBg,
              border: `1px solid ${tooltipBorder}`,
              borderRadius: "6px",
              color: tooltipText,
              fontSize: "11px",
              boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
            }}
            labelFormatter={timeTickFormatter}
          />
          {lines.length > 1 && (
            <Legend wrapperStyle={{ fontSize: "11px", color: axisColor }} />
          )}

          {/* Reference lines (thresholds) */}
          {Object.entries(thresholds).map(([label, value]) => (
            <ReferenceLine
              key={label}
              y={value}
              stroke="#ef4444"
              strokeDasharray="4 4"
              label={{ value: label, position: "right", fill: "#ef4444", fontSize: 9 }}
            />
          ))}

          {/* Telemetry data lines */}
          {lines.map(({ key, name }, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={name || key}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={1.75}
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
