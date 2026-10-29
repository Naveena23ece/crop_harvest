/**
 * FILE: frontend/src/components/SensorCard.jsx
 * Professional Industrial Sensor Metric Card for GrainGuard AI.
 * Adapts to Light and Dark themes with clean typography and precise unit indicators.
 */

import React from "react";

export default function SensorCard({
  title,
  value,
  unit = "",
  icon,
  status = null,
  loading = false,
}) {
  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-lg p-4 shadow-sm transition-colors duration-150">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-[var(--text-muted)] tracking-tight uppercase">
          {title}
        </span>
        <div className="text-base text-emerald-600 dark:text-emerald-500">{icon}</div>
      </div>

      {loading ? (
        <div className="h-7 w-24 bg-[var(--bg-surface-elevated)] animate-pulse rounded my-1" />
      ) : (
        <div className="flex items-baseline gap-1 mt-1">
          <span className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">
            {value ?? "—"}
          </span>
          {unit && (
            <span className="text-xs font-medium text-[var(--text-muted)]">
              {unit}
            </span>
          )}
        </div>
      )}

      {status && (
        <div className="mt-2 text-[11px] text-[var(--text-secondary)] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          <span>{status}</span>
        </div>
      )}
    </div>
  );
}
