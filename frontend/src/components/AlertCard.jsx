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

  const {
    risk_category   = "High",
    message         = "High risk detected",
    recommendations = [],
    timestamp,
  } = alert;

  const isHigh     = risk_category === "High";
  const isMod      = risk_category === "Moderate";

  const cardClass = isHigh
    ? "border-red-500/60 bg-red-950/40"
    : isMod
    ? "border-amber-500/60 bg-amber-950/30"
    : "border-green-500/60 bg-green-950/30";

  const iconClass = isHigh ? "text-red-400" : isMod ? "text-amber-400" : "text-green-400";

  return (
    <div className={`rounded-xl border p-4 ${cardClass} transition-all duration-300`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <FiAlertTriangle className={`text-xl flex-shrink-0 ${iconClass}`} />
          <div>
            <p className={`font-semibold ${iconClass}`}>{message}</p>
            {timestamp && (
              <p className="text-xs text-gray-500 mt-0.5">{timeAgo(timestamp)}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {recommendations.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-gray-400 hover:text-white text-sm flex items-center gap-1"
            >
              {expanded ? <FiChevronUp /> : <FiChevronDown />}
              {expanded ? "Less" : "Actions"}
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-gray-500 hover:text-white"
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
            <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
              <span className={`mt-0.5 flex-shrink-0 ${iconClass}`}>→</span>
              {rec}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
