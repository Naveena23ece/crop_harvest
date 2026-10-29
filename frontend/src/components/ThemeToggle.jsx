/**
 * FILE: frontend/src/components/ThemeToggle.jsx
 * Accessible, minimal Theme Toggle button for GrainGuard AI.
 * Displays clear Sun/Moon icons with subtle enterprise styling.
 */

import React from "react";
import { useTheme } from "../context/ThemeContext";
import { FiSun, FiMoon } from "react-icons/fi";

export default function ThemeToggle({ className = "", showLabel = false }) {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className={`inline-flex items-center justify-center gap-2 p-2 rounded-lg text-xs font-medium transition-colors border ${
        isDark
          ? "bg-slate-800/90 text-amber-400 border-slate-700 hover:bg-slate-700/80 hover:text-amber-300"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100 hover:text-slate-900 shadow-sm"
      } ${className}`}
    >
      {isDark ? (
        <FiSun className="text-sm flex-shrink-0" />
      ) : (
        <FiMoon className="text-sm flex-shrink-0 text-slate-600" />
      )}
      {showLabel && (
        <span className="font-medium tracking-tight">
          {isDark ? "Light Mode" : "Dark Mode"}
        </span>
      )}
    </button>
  );
}
