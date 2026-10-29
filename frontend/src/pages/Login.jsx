/**
 * FILE: frontend/src/pages/Login.jsx
 * Professional Authentication Portal for GrainGuard AI.
 * Supports:
 *  - Secure Role-Based Sign In (Admin / Viewer accounts)
 *  - Public Self-Registration (Viewer role strictly enforced)
 *  - Clear Demo Prototype Exploration Mode
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";
import { FiLock, FiUser, FiMail, FiShield, FiEye, FiArrowRight } from "react-icons/fi";
import { GiWheat } from "react-icons/gi";

export default function Login() {
  const [isSignup, setIsSignup] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const { login, signup, enterDemo } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isSignup) {
        if (password.length < 8) {
          toast.error("Password must be at least 8 characters long.");
          setLoading(false);
          return;
        }
        await signup(username, email, password);
        toast.success("Account created successfully as Viewer! You can now log in.");
        setIsSignup(false);
      } else {
        const loggedUser = await login(username, password);
        toast.success(`Welcome, ${loggedUser.username}! (${loggedUser.role.toUpperCase()})`);
        navigate("/dashboard");
      }
    } catch (err) {
      toast.error(err.message || "Authentication failed. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = (role) => {
    enterDemo(role);
    toast.success(`Entered Demo Mode as ${role.toUpperCase()}`);
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md z-10">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white shadow-lg shadow-emerald-500/20 mb-3">
            <GiWheat className="text-3xl" />
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">GrainGuard AI</h1>
          <p className="text-slate-400 mt-1 text-sm font-medium">
            Post-Harvest Grain Storage Risk Monitoring & RBAC DSS
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-7 text-slate-100">
          {/* Tab Switcher */}
          <div className="flex border-b border-slate-800 mb-6 pb-2">
            <button
              onClick={() => setIsSignup(false)}
              className={`flex-1 pb-2 text-sm font-semibold transition-colors ${
                !isSignup
                  ? "text-emerald-400 border-b-2 border-emerald-500"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setIsSignup(true)}
              className={`flex-1 pb-2 text-sm font-semibold transition-colors ${
                isSignup
                  ? "text-emerald-400 border-b-2 border-emerald-500"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register (Viewer)
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Username
              </label>
              <div className="relative">
                <FiUser className="absolute left-3.5 top-3.5 text-slate-500" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl
                             focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent
                             text-white placeholder-slate-500 text-sm"
                  placeholder="e.g. admin or viewer"
                  required
                />
              </div>
            </div>

            {isSignup && (
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <FiMail className="absolute left-3.5 top-3.5 text-slate-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl
                               focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent
                               text-white placeholder-slate-500 text-sm"
                    placeholder="user@example.com"
                    required
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <FiLock className="absolute left-3.5 top-3.5 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl
                             focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent
                             text-white placeholder-slate-500 text-sm"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800
                         text-white font-semibold rounded-xl transition duration-150 shadow-lg
                         shadow-emerald-600/20 flex items-center justify-center gap-2 text-sm mt-2"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : isSignup ? (
                <>Create Viewer Account <FiArrowRight /></>
              ) : (
                <>Sign In Securely <FiArrowRight /></>
              )}
            </button>
          </form>

          {/* Quick Demo Access Buttons */}
          <div className="mt-6 pt-5 border-t border-slate-800">
            <p className="text-center text-xs font-medium text-slate-400 mb-3">
              Prototype Evaluation Shortcuts:
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleDemoLogin("admin")}
                className="py-2 px-3 border border-slate-700 bg-slate-800/60 hover:bg-slate-800
                           text-xs font-semibold text-slate-200 rounded-lg transition-colors flex items-center justify-center gap-1.5"
              >
                <FiShield className="text-emerald-400" /> Explore as Admin
              </button>
              <button
                type="button"
                onClick={() => handleDemoLogin("viewer")}
                className="py-2 px-3 border border-slate-700 bg-slate-800/60 hover:bg-slate-800
                           text-xs font-semibold text-slate-200 rounded-lg transition-colors flex items-center justify-center gap-1.5"
              >
                <FiEye className="text-blue-400" /> Explore as Viewer
              </button>
            </div>
            <p className="text-center text-slate-500 text-[11px] mt-3">
              🔒 NIST-compliant PBKDF2 password hashing & role-based backend authorization.
            </p>
          </div>
        </div>

        <p className="text-center text-slate-500 text-xs mt-5">
          GrainGuard AI · Final Year Engineering Project · Local Prototype Verification
        </p>
      </div>
    </div>
  );
}
