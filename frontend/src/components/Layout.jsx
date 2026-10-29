/**
 * FILE: frontend/src/components/Layout.jsx
 * Enterprise Agricultural Monitoring Application Layout.
 * Features:
 *  - Professional industrial styling (neutral surfaces, restrained green accents)
 *  - Accessible Theme Toggle in Topbar
 *  - Role-gated navigation: Admin User Management visible only to Administrators
 *  - Active storage unit indicator & prototype simulated telemetry transparency
 *  - Responsive sidebar with clean collapsible mobile drawer
 */

import React, { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "./ThemeToggle";
import toast from "react-hot-toast";
import {
  FiHome,
  FiActivity,
  FiBarChart2,
  FiAlertTriangle,
  FiSettings,
  FiCpu,
  FiDatabase,
  FiUsers,
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [now, setNow] = useState(new Date());
  const { user, isAdmin, logout } = useAuth();
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

  // Base navigation items available to all authorized users
  const baseNavItems = [
    { to: "/dashboard", icon: FiHome, label: "Dashboard" },
    { to: "/live", icon: FiActivity, label: "Live Monitoring" },
    { to: "/history", icon: FiDatabase, label: "Historical Telemetry" },
    { to: "/prediction", icon: FiCpu, label: "Risk Prediction" },
    { to: "/performance", icon: FiBarChart2, label: "Model Evaluation" },
    { to: "/alerts", icon: FiAlertTriangle, label: "Alert History" },
  ];

  // Admin-only management navigation items
  const adminNavItems = [
    { to: "/users", icon: FiUsers, label: "User Management" },
    { to: "/settings", icon: FiSettings, label: "System Settings" },
  ];

  const currentNav = isAdmin ? [...baseNavItems, ...adminNavItems] : baseNavItems;

  return (
    <div className="flex h-screen bg-[var(--bg-app)] text-[var(--text-primary)] overflow-hidden font-sans">
      {/* ── Sidebar (Desktop) ─────────────────────────────────── */}
      <aside
        className={`hidden md:flex flex-col bg-[var(--bg-surface)] border-r border-[var(--border-color)] transition-all duration-200 z-20 ${
          sidebarOpen ? "w-60" : "w-16"
        }`}
      >
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-[var(--border-color)]">
          <div className="w-8 h-8 rounded bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center flex-shrink-0">
            <GiWheat className="text-lg" />
          </div>
          {sidebarOpen && (
            <div className="overflow-hidden leading-tight">
              <span className="font-bold text-sm tracking-tight text-[var(--text-primary)] block">
                GrainGuard AI
              </span>
              <span className="text-[10px] text-[var(--text-muted)] font-medium tracking-wide block uppercase">
                Post-Harvest Risk DSS
              </span>
            </div>
          )}
        </div>

        {/* User Role Card */}
        {sidebarOpen && (
          <div className="mx-3 my-3 p-2.5 bg-[var(--bg-surface-elevated)] border border-[var(--border-color)] rounded-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="w-6 h-6 rounded bg-[var(--bg-surface)] flex items-center justify-center text-[var(--text-secondary)] text-xs border border-[var(--border-color)] flex-shrink-0">
                  {isAdmin ? <FiShield className="text-emerald-600 dark:text-emerald-400 text-xs" /> : <FiUser className="text-slate-600 dark:text-slate-400 text-xs" />}
                </div>
                <div className="truncate">
                  <span className="text-xs font-semibold text-[var(--text-primary)] block truncate">
                    {user?.username || "Operator"}
                  </span>
                </div>
              </div>
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                  isAdmin
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800"
                    : "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700"
                }`}
              >
                {user?.role || "Viewer"}
              </span>
            </div>
          </div>
        )}

        {/* Navigation List */}
        <nav className="flex-1 py-2 px-2.5 space-y-1 overflow-y-auto">
          {currentNav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-400 font-semibold border border-emerald-200 dark:border-emerald-800/60"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-elevated)] hover:text-[var(--text-primary)]"
                }`
              }
            >
              <Icon className="text-sm flex-shrink-0" />
              {sidebarOpen && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Sidebar Footer / Sign Out */}
        <div className="border-t border-[var(--border-color)] p-2.5">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2.5 w-full px-3 py-2 rounded-md text-xs font-medium text-[var(--text-muted)] hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
          >
            <FiLogOut className="text-sm flex-shrink-0" />
            {sidebarOpen && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* ── Main Application Workspace ──────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[var(--bg-app)]">
        {/* Topbar Header */}
        <header className="flex items-center justify-between px-4 sm:px-6 py-2.5 bg-[var(--bg-surface)] border-b border-[var(--border-color)] flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="hidden md:inline-flex p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded hover:bg-[var(--bg-surface-elevated)]"
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <FiX size={16} /> : <FiMenu size={16} />}
            </button>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded"
              aria-label="Toggle mobile menu"
            >
              <FiMenu size={18} />
            </button>

            <div>
              <span className="text-xs font-semibold text-[var(--text-primary)]">
                Storage Risk Monitoring Console
              </span>
              <span className="hidden lg:inline text-[11px] text-[var(--text-muted)] font-mono ml-2">
                AR-TCN v2.0
              </span>
            </div>
          </div>

          {/* Right Header Utilities: ThemeToggle, Timestamp, Sign Out */}
          <div className="flex items-center gap-3 text-xs">
            <div className="hidden sm:flex items-center gap-1.5 font-mono text-[11px] text-[var(--text-muted)]">
              <span>{now.toUTCString().replace("GMT", "UTC")}</span>
            </div>

            {/* Global Theme Toggle */}
            <ThemeToggle showLabel={false} />

            {/* User Badge / Sign Out */}
            <div className="flex items-center gap-2 pl-2 border-l border-[var(--border-color)]">
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                  isAdmin
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-400"
                    : "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {user?.role || "Viewer"}
              </span>
              <button
                onClick={handleLogout}
                title="Sign out"
                className="p-1.5 text-[var(--text-muted)] hover:text-rose-600 rounded"
              >
                <FiLogOut size={14} />
              </button>
            </div>
          </div>
        </header>

        {/* ── Mobile Navigation Drawer ────────────────────────── */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[var(--bg-surface)] border-b border-[var(--border-color)] p-3 space-y-1 z-30">
            {currentNav.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded text-xs font-medium ${
                    isActive
                      ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-400 font-semibold"
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-elevated)]"
                  }`
                }
              >
                <Icon className="text-sm" />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        )}

        {/* ── Content Viewport ─────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[var(--bg-app)]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
