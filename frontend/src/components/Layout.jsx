/**
 * FILE: frontend/src/components/Layout.jsx
 * Main application layout: sidebar navigation + topbar + content area.
 */

import React, { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast       from "react-hot-toast";
import {
  FiHome, FiActivity, FiBarChart2, FiAlertTriangle,
  FiSettings, FiCpu, FiDatabase, FiLogOut, FiMenu, FiX,
} from "react-icons/fi";
import { GiWheat } from "react-icons/gi";

const NAV_ITEMS = [
  { to: "/dashboard",  icon: FiHome,          label: "Dashboard"       },
  { to: "/live",       icon: FiActivity,      label: "Live Monitoring" },
  { to: "/history",    icon: FiDatabase,      label: "Historical Data" },
  { to: "/prediction", icon: FiCpu,           label: "Risk Prediction" },
  { to: "/alerts",     icon: FiAlertTriangle, label: "Alerts"          },
  { to: "/settings",   icon: FiSettings,      label: "Settings"        },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [now, setNow] = useState(new Date());
  const { user, logout } = useAuth();

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);
  const navigate = useNavigate();

  const handleLogout = async () => {
    try { await logout(); navigate("/login"); }
    catch { toast.error("Logout failed"); }
  };

  return (
    <div className="flex h-screen bg-gray-100 text-gray-800 overflow-hidden">
      {/* ── Sidebar ───────────────────────────────── */}
      <aside
        className={`flex flex-col bg-white border-r border-gray-200
                    transition-all duration-150 ${sidebarOpen ? "w-60" : "w-16"}`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-800">
          <GiWheat className="text-blue-600 text-xl flex-shrink-0" />
          {sidebarOpen && (
            <span className="font-semibold text-gray-900 text-base whitespace-nowrap">
              GrainGuard AI
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                 transition-colors duration-150
                 ${isActive
                   ? "bg-blue-50 text-blue-700 border border-blue-100"
                   : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                 }`
              }
            >
              <Icon className="text-lg flex-shrink-0" />
              {sidebarOpen && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User / Logout */}
        <div className="border-t border-gray-800 p-3">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg
                       text-gray-400 hover:bg-gray-800 hover:text-red-400 transition-colors text-sm"
          >
            <FiLogOut className="flex-shrink-0" />
            {sidebarOpen && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* ── Main area ─────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex items-center justify-between px-6 py-3
                           bg-white border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-500 hover:text-gray-800"
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <FiX className="text-lg" /> : <FiMenu className="text-lg" />}
            </button>
            <span className="text-base font-semibold text-gray-900">Grain Storage Monitoring</span>
          </div>

          <div className="flex items-center gap-5 text-sm text-gray-600">
            <span>{now.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })} · {now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</span>
            <span className="flex items-center gap-2"><span className="connection-dot"></span>Connected</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6 bg-gray-100">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
