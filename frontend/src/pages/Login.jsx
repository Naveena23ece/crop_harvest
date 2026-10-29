/**
 * FILE: frontend/src/pages/Login.jsx
 * Login page with email/password Firebase authentication.
 * Shows the project title and a clean form.
 */

import React, { useState } from "react";
import { useNavigate }     from "react-router-dom";
import { useAuth }         from "../context/AuthContext";
import toast               from "react-hot-toast";

export default function Login() {
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const { login } = useAuth();
  const navigate  = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  // Demo: bypass auth for development
  const handleDemo = () => navigate("/dashboard");

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-emerald-900
                    flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo / Title */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🌾</div>
          <h1 className="text-3xl font-bold text-white">GrainGuard AI</h1>
          <p className="text-green-300 mt-2 text-sm">
            Post-Harvest Storage Risk Prediction System
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-6">Sign in to Dashboard</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent
                           text-gray-900 bg-gray-50"
                placeholder="admin@grainstorage.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent
                           text-gray-900 bg-gray-50"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-400
                         text-white font-semibold rounded-lg transition-colors duration-200
                         flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                            stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor"
                          d="M4 12a8 8 0 018-8v8z"/>
                  </svg>
                  Signing in...
                </>
              ) : "Sign In"}
            </button>
          </form>

          <div className="mt-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200"/>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">or</span>
              </div>
            </div>

            <button
              onClick={handleDemo}
              className="mt-4 w-full py-3 border-2 border-green-600 text-green-700
                         hover:bg-green-50 font-semibold rounded-lg transition-colors duration-200"
            >
              🚀 Enter Demo Mode (Software Prototype)
            </button>
            <p className="text-center text-gray-400 text-xs mt-2">
              Software-Phase Prototype · Cloud auth and physical ESP32 streaming scheduled for Phase 2
            </p>
          </div>
        </div>

        <p className="text-center text-green-400 text-xs mt-6">
          BE Final Year Project · AI-Integrated Predictive Modeling DSS
        </p>
      </div>
    </div>
  );
}
