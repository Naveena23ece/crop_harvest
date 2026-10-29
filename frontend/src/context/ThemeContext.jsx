/**
 * FILE: frontend/src/context/ThemeContext.jsx
 * Enterprise Light/Dark Theme Management for GrainGuard AI.
 * Handles:
 *  - Immediate zero-reload theme switching
 *  - Persistent storage in localStorage ('grainguard_theme')
 *  - OS/system preference fallback (prefers-color-scheme)
 *  - Class binding on <html> root element
 */

import React, { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    // 1. Check client-side persisted preference
    const saved = localStorage.getItem("grainguard_theme");
    if (saved === "light" || saved === "dark") {
      return saved;
    }
    // 2. Fall back to system preference
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return "light";
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.setAttribute("data-theme", "dark");
    } else {
      root.classList.remove("dark");
      root.setAttribute("data-theme", "light");
    }
    localStorage.setItem("grainguard_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const isDark = theme === "dark";

  return (
    <ThemeContext.Provider value={{ theme, isDark, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}
