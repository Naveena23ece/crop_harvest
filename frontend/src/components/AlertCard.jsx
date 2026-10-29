/**
 * FILE: frontend/src/components/AlertCard.jsx
 * Displays a high-risk alert with recommendations.
 * Shown as a dismissible banner when risk is "High".
 */

import React, { useState } from "react";
import { FiAlertTriangle, FiX, FiChevronDown, FiChevronUp } from "react-icons/fi";
import { timeAgo } from "../utils/helpers";

export default function AlertCard({ alert, onDismiss }) {
  const [expanded, setExpanded] = useState(false);

  if (!alert) return null;

  const risk_category = alert.risk_category || alert.details?.risk_category || (alert.level === "HIGH" ? "High" : alert.level === "WARNING" ? "Moderate" : "Low");
  const message = alert.message || (risk_category === "High" ? "Critical Spoilage Risk Condition" : "High risk detected");
  const recommendations = alert.recommendations || alert.details?.recommendations || [];
  const timestamp = alert.timestamp;

  const isHigh     = risk_category === "High";
  const isMod      = risk_category === "Moderate";

  const cardClass = isHigh
    ? "border-red-500/30 bg-red-500/10 dark:bg-red-950/40"
    : isMod
    ? "border-amber-500/30 bg-amber-500/10 dark:bg-amber-950/30"
    : "border-emerald-500/30 bg-emerald-500/10 dark:bg-emerald-950/30";

  const iconClass = isHigh
    ? "text-red-600 dark:text-red-400"
    : isMod
    ? "text-amber-600 dark:text-amber-400"
    : "text-emerald-600 dark:text-emerald-400";

  return (
    <div className={`rounded-xl border p-4 ${cardClass} shadow-sm transition-all duration-300`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <FiAlertTriangle className={`text-xl flex-shrink-0 ${iconClass}`} />
          <div>
            <p className={`font-semibold text-sm ${iconClass}`}>{message}</p>
            {timestamp && (
              <p className="text-xs text-[var(--text-muted)] mt-0.5">{timeAgo(timestamp)}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {recommendations.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs font-semibold flex items-center gap-1 cursor-pointer"
            >
              {expanded ? <FiChevronUp /> : <FiChevronDown />}
              {expanded ? "Less" : "Actions"}
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
              aria-label="Dismiss alert"
            >
              <FiX />
            </button>
          )}
        </div>
      </div>

      {/* Recommendations */}
      {expanded && recommendations.length > 0 && (
        <ul className="mt-3 space-y-1.5 pl-2">
          {recommendations.map((rec, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
              <span className={`mt-0.5 flex-shrink-0 ${iconClass}`}>→</span>
              {rec}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
