/**
 * FILE: frontend/src/components/Layout.jsx
 * GrainGuard AI Application Layout: Sidebar Navigation + Topbar + Content Area.
 * Features:
 *  - Dynamic User Role Badges (ADMIN vs VIEWER)
 *  - Prototype Telemetry Status Banner (Simulated Prototype Replay)
 *  - Responsive navigation with active route highlights
 *  - Clean session sign out
 */

import React, { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";
import {
  FiHome,
  FiActivity,
  FiBarChart2,
  FiAlertTriangle,
  FiSettings,
  FiCpu,
  FiDatabase,
  FiLogOut,
  FiMenu,
  FiX,
  FiShield,
  FiUser,
  FiInfo,
} from "react-icons/fi";
import { GiWheat } from "react-icons/gi";

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [now, setNow] = useState(new Date());
  const { user, isAdmin, isViewer, demoMode, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(timer);
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      toast.success("Signed out successfully.");
      navigate("/login");
    } catch {
      toast.error("Logout failed.");
    }
  };

  const navItems = [
    { to: "/dashboard",   icon: FiHome,          label: "Dashboard" },
    { to: "/live",        icon: FiActivity,      label: "Live Monitoring" },
    { to: "/history",     icon: FiDatabase,      label: "Historical & Reports" },
    { to: "/prediction",  icon: FiCpu,           label: "Risk Prediction" },
    { to: "/performance", icon: FiBarChart2,     label: "Model Performance" },
    { to: "/alerts",      icon: FiAlertTriangle, label: "Alerts" },
    { to: "/settings",    icon: FiSettings,      label: isAdmin ? "Admin & Settings" : "System Settings" },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* ── Sidebar ───────────────────────────────── */}
      <aside
        className={`flex flex-col bg-slate-900 border-r border-slate-800 transition-all duration-200 z-20 ${
          sidebarOpen ? "w-64" : "w-20"
        }`}
      >
        {/* Brand Logo Header */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-800/80">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center text-white shadow-md shadow-emerald-600/20 flex-shrink-0">
            <GiWheat className="text-xl" />
          </div>
          {sidebarOpen && (
            <div className="overflow-hidden">
              <span className="font-bold text-white text-base tracking-tight block">
                GrainGuard AI
              </span>
              <span className="text-[10px] text-emerald-400 font-medium tracking-wide uppercase block">
                Storage Risk DSS
              </span>
            </div>
          )}
        </div>

        {/* User Role Profile Card */}
        {sidebarOpen && (
          <div className="mx-3 my-3 p-3 bg-slate-800/60 border border-slate-700/60 rounded-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="w-7 h-7 rounded-lg bg-slate-700 flex items-center justify-center text-slate-300 flex-shrink-0 text-xs">
                  {isAdmin ? <FiShield className="text-emerald-400" /> : <FiUser className="text-blue-400" />}
                </div>
                <div className="truncate">
                  <p className="text-xs font-semibold text-slate-200 truncate">
                    {user?.username || "Guest Operator"}
                  </p>
                  <p className="text-[10px] text-slate-400 truncate">
                    {user?.email || "Local Session"}
                  </p>
                </div>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                  isAdmin
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                }`}
              >
                {user?.role || "Viewer"}
              </span>
            </div>
          </div>
        )}

        {/* Navigation Items */}
        <nav className="flex-1 py-2 px-3 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold shadow-sm"
                    : "text-slate-400 hover:bg-slate-800/80 hover:text-slate-200"
                }`
              }
            >
              <Icon className="text-base flex-shrink-0" />
              {sidebarOpen && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Sign Out Action */}
        <div className="border-t border-slate-800 p-3">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-slate-400 hover:bg-rose-500/10 hover:text-rose-400 transition-colors text-xs font-medium"
          >
            <FiLogOut className="text-base flex-shrink-0" />
            {sidebarOpen && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* ── Main Workspace ─────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-950">
        {/* Prototype Evaluation Banner */}
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-6 py-1.5 flex items-center justify-between text-[11px] text-amber-300/90 font-medium">
          <div className="flex items-center gap-2">
            <FiInfo className="text-amber-400 flex-shrink-0" />
            <span>
              <b>Local Prototype Mode:</b> Telemetry is delivered via verified dataset replay. Physical ESP32 hardware and sensor probes will be connected in Phase 2.
            </span>
          </div>
          {demoMode && (
            <span className="bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">
              DEMO SESSION
            </span>
          )}
        </div>

        {/* Topbar */}
        <header className="flex items-center justify-between px-6 py-3.5 bg-slate-900/80 backdrop-blur border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <FiX className="text-lg" /> : <FiMenu className="text-lg" />}
            </button>
            <div className="hidden sm:block">
              <span className="text-sm font-semibold text-slate-200">
                GrainGuard AI Monitoring Console
              </span>
              <span className="text-xs text-slate-500 ml-2 font-mono">
                AR-TCN v2.0
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span className="font-mono hidden md:inline">
              {now.toUTCString().replace("GMT", "UTC")}
            </span>
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-[11px] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Backend Ready</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
