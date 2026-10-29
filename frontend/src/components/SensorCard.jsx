/**
 * FILE: frontend/src/components/SensorCard.jsx
 * Reusable metric card for displaying a single sensor value with
 * an icon, value, unit, and optional trend indicator.
 */

import React from "react";

export default function SensorCard({
  title,
  value,
  unit       = "",
  icon,
  color      = "text-blue-400",
  bgColor    = "bg-blue-500/10",
  borderColor= "border-blue-500/30",
  trend      = null,   // "up" | "down" | null
  status     = null,   // "ok" | "warning" | "critical"
  loading    = false,
}) {
  const statusColors = {
    ok:       "bg-green-500",
    warning:  "bg-amber-500",
    critical: "bg-red-500",
  };

  return (
    <div
      className="metric-card"
    >
      {/* Status dot */}
      {status && (
        <span
          className={`absolute top-3 right-3 w-2.5 h-2.5 rounded-full
                      ${statusColors[status] || "bg-gray-500"}`}
          title={`Status: ${status}`}
        />
      )}

      {/* Icon + Title */}
      <div className="flex items-center gap-3 mb-3">
        <div className={`text-2xl ${color}`}>{icon}</div>
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          {title}
        </span>
      </div>

      {/* Value */}
      {loading ? (
        <div className="h-8 w-24 bg-gray-700 animate-pulse rounded" />
      ) : (
        <div className={`text-3xl font-bold ${color}`}>
          {value ?? "—"}
          <span className="text-base font-normal text-gray-400 ml-1">{unit}</span>
        </div>
      )}

      {/* Trend */}
      {trend && (
        <div className={`mt-2 text-xs flex items-center gap-1
                         ${trend === "up" ? "text-red-400" : "text-green-400"}`}>
          {trend === "up" ? "▲" : "▼"} Trending {trend}
        </div>
      )}
    </div>
  );
}
