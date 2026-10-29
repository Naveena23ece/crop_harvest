/**
 * FILE: frontend/src/utils/helpers.js
 * Utility functions shared across the dashboard.
 */

import { format, parseISO, formatDistanceToNow } from "date-fns";

// ─── Risk styling ──────────────────────────────────────────
export const RISK_COLORS = {
  Low:      "#22c55e",
  Moderate: "#f59e0b",
  High:     "#ef4444",
};

export const RISK_BG = {
  Low:      "bg-green-100 text-green-800 border-green-300",
  Moderate: "bg-amber-100  text-amber-800  border-amber-300",
  High:     "bg-red-100   text-red-800   border-red-300",
};

export const RISK_ICONS = {
  Low:      "🟢",
  Moderate: "🟡",
  High:     "🔴",
};

// ─── Date formatting ──────────────────────────────────────
export const ensureUtc = (ts) => {
  if (!ts) return ts;
  if (typeof ts === "string") {
    // If it's an ISO timestamp from SQLite without timezone suffix, append 'Z' so browsers parse it as UTC
    const trimmed = ts.trim();
    if (trimmed.includes("T") && !trimmed.endsWith("Z") && !trimmed.includes("+") && !trimmed.slice(10).includes("-")) {
      return trimmed + "Z";
    }
  }
  return ts;
};

export const formatTimestamp = (ts) => {
  try {
    const safeTs = ensureUtc(ts);
    return format(typeof safeTs === "string" ? parseISO(safeTs) : safeTs, "MMM dd, HH:mm:ss");
  } catch {
    return ts || "—";
  }
};

export const timeAgo = (ts) => {
  try {
    const safeTs = ensureUtc(ts);
    return formatDistanceToNow(
      typeof safeTs === "string" ? parseISO(safeTs) : safeTs,
      { addSuffix: true }
    );
  } catch {
    return "—";
  }
};

// ─── Sensor value formatting ──────────────────────────────
export const formatSensor = (value, unit = "", decimals = 1) => {
  if (value === null || value === undefined || isNaN(value)) return "—";
  return `${Number(value).toFixed(decimals)}${unit}`;
};

// ─── Risk to numeric (for gauge) ──────────────────────────
export const riskToPercent = (risk) => {
  if (!risk) return 0;
  const map = { Low: 0.2, Moderate: 0.5, High: 0.85 };
  return map[risk] ?? 0;
};

// ─── Clamp a value to a range ─────────────────────────────
export const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

// ─── Generate chart tick formatter ────────────────────────
export const timeTickFormatter = (ts) => {
  try {
    return format(parseISO(ts), "HH:mm");
  } catch {
    return ts;
  }
};
