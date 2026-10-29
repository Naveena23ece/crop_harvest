/**
 * FILE: frontend/src/components/RiskBadge.jsx
 * Animated risk level badge that changes color based on category.
 */

import React from "react";
import { RISK_COLORS, RISK_ICONS } from "../utils/helpers";

const PULSE_CLASS = {
  Low:      "",
  Moderate: "animate-pulse",
  High:     "animate-pulse",
};

const BG_CLASS = {
  Low:      "bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-400",
  Moderate: "bg-amber-500/10  border-amber-500/40  text-amber-700 dark:text-amber-400",
  High:     "bg-red-500/10    border-red-500/40    text-red-700 dark:text-red-400",
};

export default function RiskBadge({ risk, size = "md", confidence = null }) {
  if (!risk) return null;

  const sizeClass = {
    sm: "text-xs px-2 py-1",
    md: "text-sm px-3 py-1.5",
    lg: "text-xl px-6 py-3 font-bold",
  }[size] || "text-sm px-3 py-1.5";

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border font-semibold
                  ${BG_CLASS[risk] || "bg-gray-700 text-gray-300 border-gray-600"}
                  ${sizeClass} ${risk === "High" ? PULSE_CLASS["High"] : ""}`}
    >
      <span>{RISK_ICONS[risk] || "⚪"}</span>
      <span>{risk} Risk</span>
      {confidence !== null && (
        <span className="opacity-70 text-xs">
          ({(confidence * 100).toFixed(0)}%)
        </span>
      )}
    </div>
  );
}
