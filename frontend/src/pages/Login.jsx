/**
 * FILE: frontend/src/pages/Login.jsx
 * Professional Enterprise Authentication Interface for GrainGuard AI.
 * Design Direction:
 *  - Serious agricultural & industrial monitoring platform aesthetic
 *  - Strict server-authenticated sign-in (Naveena Admin / Viewer)
 *  - Global Light/Dark theme toggle with immediate persistence
 *  - Show/Hide password toggle, visible focus states, zero marketing fluff
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "../components/ThemeToggle";
import { FiLock, FiUser, FiEye, FiEyeOff, FiAlertCircle } from "react-icons/fi";
import { GiWheat } from "react-icons/gi";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Please enter both username and password.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login(username.trim(), password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Invalid credentials. Please verify username and password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-app)] flex flex-col justify-between p-4 sm:p-6 transition-colors duration-150">
      {/* Top Header with Theme Toggle */}
      <div className="w-full max-w-6xl mx-auto flex items-center justify-between py-2">
        <div className="flex items-center gap-2 text-sm font-semibold tracking-tight text-[var(--text-secondary)]">
          <GiWheat className="text-emerald-600 dark:text-emerald-500 text-lg" />
          <span>Agricultural Storage System</span>
        </div>
        <ThemeToggle showLabel={true} />
      </div>

      {/* Main Authentication Card */}
      <div className="w-full max-w-md mx-auto my-auto">
        <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-lg shadow-sm p-8 transition-colors duration-150">
          {/* Brand Header */}
          <div className="mb-6">
            <div className="inline-flex items-center justify-center w-11 h-11 rounded-lg bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/60 mb-3">
              <GiWheat className="text-2xl" />
            </div>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              GrainGuard AI
            </h1>
            <p className="text-xs text-[var(--text-muted)] mt-1 font-medium">
              Post-Harvest Grain Risk Monitoring
            </p>
          </div>

          {/* Authentication Error Alert */}
          {error && (
            <div
              role="alert"
              className="mb-5 p-3 rounded-md bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/60 text-rose-800 dark:text-rose-300 text-xs flex items-start gap-2.5"
            >
              <FiAlertCircle className="text-sm flex-shrink-0 mt-0.5 text-rose-600 dark:text-rose-400" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5"
              >
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--text-muted)]">
                  <FiUser className="text-sm" />
                </div>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="Enter username"
                  className="w-full pl-9 pr-3 py-2 text-sm bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-md focus:outline-none focus:ring-1 focus:ring-emerald-600 focus:border-emerald-600"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--text-muted)]">
                  <FiLock className="text-sm" />
                </div>
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-10 py-2 text-sm bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-md focus:outline-none focus:ring-1 focus:ring-emerald-600 focus:border-emerald-600"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                >
                  {showPassword ? <FiEyeOff className="text-sm" /> : <FiEye className="text-sm" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-emerald-700 hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs rounded-md shadow-sm transition-colors duration-150 flex items-center justify-center gap-2 cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:ring-offset-1"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  <span>Authenticating...</span>
                </>
              ) : (
                <span>Sign In</span>
              )}
            </button>
          </form>

          {/* Security & Access Notice */}
          <div className="mt-6 pt-5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] text-center leading-relaxed">
            Authorized personnel only. Contact facility administration to request account access.
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="w-full max-w-6xl mx-auto py-3 text-center text-xs text-[var(--text-muted)] font-mono">
        GrainGuard AI · Enterprise Agricultural Risk Engine v2.0
      </div>
    </div>
  );
}
