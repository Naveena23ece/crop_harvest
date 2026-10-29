/**
 * FILE: frontend/src/pages/Settings.jsx
 * Comprehensive System Administration, RBAC User Management, Notifications, and Diagnostics Console.
 * Strictly enforces Admin permissions on sensitive operations while providing Viewers with read-only system telemetry.
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import {
  getSystemStatusApi,
  listUsersApi,
  createUserApi,
  updateUserApi,
  getNotificationConfigApi,
  updateNotificationConfigApi,
  testNotificationApi,
  getNotificationLogsApi,
  getAuditLogsApi,
  getStorageUnitsApi,
  createStorageUnitApi,
  updateStorageUnitApi,
  triggerTraining,
} from "../services/api";
import toast from "react-hot-toast";
import {
  FiShield,
  FiUsers,
  FiBell,
  FiActivity,
  FiServer,
  FiCheckCircle,
  FiXCircle,
  FiLock,
  FiPlus,
  FiSend,
  FiRefreshCw,
  FiLayers,
} from "react-icons/fi";

export default function Settings() {
  const { user, isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState("system");

  // System Diagnostics State
  const [sysStatus, setSysStatus] = useState(null);
  const [loadingSys, setLoadingSys] = useState(false);

  // Users State
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("viewer");

  // Notifications State
  const [notifConfig, setNotifConfig] = useState({
    email_enabled: false,
    email_recipients: "",
    smtp_host: "smtp.gmail.com",
    smtp_port: 587,
    smtp_user: "",
    smtp_password: "",
    telegram_enabled: false,
    telegram_bot_token: "",
    telegram_chat_id: "",
    min_risk_level: "High",
    cooldown_minutes: 15,
  });
  const [testingChannel, setTestingChannel] = useState(null);
  const [notifLogs, setNotifLogs] = useState([]);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  // Storage Units State
  const [storageUnits, setStorageUnits] = useState([]);
  const [newUnitId, setNewUnitId] = useState("");
  const [newUnitName, setNewUnitName] = useState("");
  const [newCropType, setNewCropType] = useState("Wheat");
  const [newCapacity, setNewCapacity] = useState(500);

  // Fetch initial data
  useEffect(() => {
    fetchSystemStatus();
    if (isAdmin) {
      fetchUsers();
      fetchNotificationConfig();
      fetchNotificationLogs();
      fetchAuditLogs();
      fetchStorageUnits();
    }
  }, [isAdmin]);

  const fetchSystemStatus = async () => {
    setLoadingSys(true);
    try {
      const data = await getSystemStatusApi();
      setSysStatus(data);
    } catch (err) {
      toast.error("Could not load system status: " + err.message);
    } finally {
      setLoadingSys(false);
    }
  };

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const data = await listUsersApi();
      setUsers(data.users || []);
    } catch (err) {
      toast.error("Failed to load users: " + err.message);
    } finally {
      setLoadingUsers(false);
    }
  };

  const fetchNotificationConfig = async () => {
    try {
      const data = await getNotificationConfigApi();
      if (data?.config) {
        setNotifConfig((prev) => ({ ...prev, ...data.config }));
      }
    } catch (err) {
      console.warn("Could not load notification config:", err);
    }
  };

  const fetchNotificationLogs = async () => {
    try {
      const data = await getNotificationLogsApi();
      setNotifLogs(data.logs || []);
    } catch (err) {
      console.warn("Could not load notification logs:", err);
    }
  };

  const fetchAuditLogs = async () => {
    setLoadingAudit(true);
    try {
      const data = await getAuditLogsApi(50);
      setAuditLogs(data.logs || []);
    } catch (err) {
      console.warn("Could not load audit logs:", err);
    } finally {
      setLoadingAudit(false);
    }
  };

  const fetchStorageUnits = async () => {
    try {
      const data = await getStorageUnitsApi();
      setStorageUnits(data.storage_units || []);
    } catch (err) {
      console.warn("Could not load storage units:", err);
    }
  };

  // User Management Actions
  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters long.");
      return;
    }
    try {
      await createUserApi({
        username: newUsername,
        email: newEmail,
        password: newPassword,
        role: newRole,
      });
      toast.success(`User '${newUsername}' created as ${newRole.toUpperCase()}!`);
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      fetchUsers();
    } catch (err) {
      toast.error(err.message || "User creation failed");
    }
  };

  const handleToggleUserStatus = async (targetUser) => {
    try {
      await updateUserApi(targetUser.id, { is_active: !targetUser.is_active });
      toast.success(`User '${targetUser.username}' status updated.`);
      fetchUsers();
    } catch (err) {
      toast.error(err.message || "Failed to update user");
    }
  };

  const handleToggleUserRole = async (targetUser) => {
    const updatedRole = targetUser.role === "admin" ? "viewer" : "admin";
    try {
      await updateUserApi(targetUser.id, { role: updatedRole });
      toast.success(`User '${targetUser.username}' role changed to ${updatedRole.toUpperCase()}.`);
      fetchUsers();
    } catch (err) {
      toast.error(err.message || "Failed to change user role");
    }
  };

  // Notification Actions
  const handleSaveNotifications = async (e) => {
    e.preventDefault();
    try {
      await updateNotificationConfigApi(notifConfig);
      toast.success("Notification configuration saved to database!");
      fetchNotificationConfig();
    } catch (err) {
      toast.error(err.message || "Failed to save configuration");
    }
  };

  const handleTestNotification = async (channel) => {
    setTestingChannel(channel);
    try {
      const res = await testNotificationApi(channel);
      if (res.success) {
        toast.success(`Test alert sent successfully via ${channel.toUpperCase()}!`);
      } else {
        toast.error(`Test failed: ${res.error || "Integration not responding"}`);
      }
      fetchNotificationLogs();
    } catch (err) {
      toast.error("Notification test failed: " + err.message);
    } finally {
      setTestingChannel(null);
    }
  };

  // Storage Unit Actions
  const handleCreateUnit = async (e) => {
    e.preventDefault();
    try {
      await createStorageUnitApi({
        unit_id: newUnitId,
        name: newUnitName,
        grain_type: newCropType,
        capacity_tons: parseFloat(newCapacity),
        current_fill_tons: parseFloat(newCapacity) * 0.6,
        location: "Warehouse Sector 1",
        status: "Operational",
      });
      toast.success(`Storage unit '${newUnitName}' created!`);
      setNewUnitId("");
      setNewUnitName("");
      fetchStorageUnits();
    } catch (err) {
      toast.error(err.message || "Failed to create storage unit");
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FiServer className="text-emerald-400" />
            {isAdmin ? "Administration & System Settings" : "System Diagnostics & Settings"}
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            Role-Based Access Control · Storage Unit Management · Notification Dispatchers · Audit Logs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider ${
              isAdmin
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                : "bg-blue-500/10 text-blue-400 border border-blue-500/30"
            }`}
          >
            Signed in as: {user?.role || "Viewer"}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-1 overflow-x-auto pb-1">
        <button
          onClick={() => setActiveTab("system")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors whitespace-nowrap ${
            activeTab === "system"
              ? "bg-slate-800 text-emerald-400 border-b-2 border-emerald-500"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <FiActivity /> System Diagnostics
        </button>
        <button
          onClick={() => setActiveTab("users")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors whitespace-nowrap ${
            activeTab === "users"
              ? "bg-slate-800 text-emerald-400 border-b-2 border-emerald-500"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <FiUsers /> User Management {!isAdmin && <FiLock className="text-amber-400" />}
        </button>
        <button
          onClick={() => setActiveTab("notifications")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors whitespace-nowrap ${
            activeTab === "notifications"
              ? "bg-slate-800 text-emerald-400 border-b-2 border-emerald-500"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <FiBell /> External Notifications {!isAdmin && <FiLock className="text-amber-400" />}
        </button>
        <button
          onClick={() => setActiveTab("silos")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors whitespace-nowrap ${
            activeTab === "silos"
              ? "bg-slate-800 text-emerald-400 border-b-2 border-emerald-500"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <FiLayers /> Storage Units (Silos) {!isAdmin && <FiLock className="text-amber-400" />}
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors whitespace-nowrap ${
            activeTab === "audit"
              ? "bg-slate-800 text-emerald-400 border-b-2 border-emerald-500"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <FiShield /> Audit Trail {!isAdmin && <FiLock className="text-amber-400" />}
        </button>
      </div>

      {/* ── Tab 1: System Diagnostics ── */}
      {activeTab === "system" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <span className="text-xs text-slate-400 font-medium uppercase tracking-wider block mb-1">
                Database Engine
              </span>
              <p className="text-lg font-bold text-slate-100">
                {sysStatus?.database?.engine || "SQLite / SQLAlchemy"}
              </p>
              <p className="text-xs text-slate-500 font-mono mt-1">
                {sysStatus?.database?.file || "backend/data/grainguard.db"}
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <span className="text-xs text-slate-400 font-medium uppercase tracking-wider block mb-1">
                Active AI Architecture
              </span>
              <p className="text-lg font-bold text-emerald-400">
                {sysStatus?.model?.name || "AR-TCN Checkpoint"}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                61-feature projection · Temporal Receptive Field
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <span className="text-xs text-slate-400 font-medium uppercase tracking-wider block mb-1">
                Hardware Integration Status
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 text-xs font-semibold">
                Simulated Telemetry Replay
              </span>
              <p className="text-[11px] text-slate-400 mt-2">
                Physical ESP32 hardware and sensor probes will be connected in Phase 2.
              </p>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-sm font-semibold text-slate-200 mb-4 flex items-center justify-between">
              <span>Database Persistence Summary</span>
              <button
                onClick={fetchSystemStatus}
                className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
              >
                <FiRefreshCw /> Refresh Diagnostics
              </button>
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700/60">
                <span className="text-2xl font-bold text-slate-100">{sysStatus?.database?.users_count ?? 2}</span>
                <span className="text-xs text-slate-400 block mt-1">Registered Users</span>
              </div>
              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700/60">
                <span className="text-2xl font-bold text-slate-100">{sysStatus?.database?.storage_units_count ?? 3}</span>
                <span className="text-xs text-slate-400 block mt-1">Storage Units</span>
              </div>
              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700/60">
                <span className="text-2xl font-bold text-slate-100">{sysStatus?.database?.predictions_count ?? 0}</span>
                <span className="text-xs text-slate-400 block mt-1">Predictions Logged</span>
              </div>
              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700/60">
                <span className="text-2xl font-bold text-rose-400">{sysStatus?.database?.alerts_count ?? 0}</span>
                <span className="text-xs text-slate-400 block mt-1">High-Risk Alerts</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 2: User Management (Admin Only) ── */}
      {activeTab === "users" && (
        <>
          {!isAdmin ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
              <FiLock className="text-4xl text-amber-400 mx-auto mb-3" />
              <h3 className="text-lg font-bold text-slate-200">Administrative Privileges Required</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                User account creation, deactivation, and role assignment are restricted to authorized Admin accounts. Viewer accounts hold read-only permissions.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Add User Form */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h2 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <FiPlus className="text-emerald-400" /> Create New User Account
                </h2>
                <form onSubmit={handleCreateUser} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  <input
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="Username"
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                    required
                  />
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="Email address"
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                    required
                  />
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Password (min 8 chars)"
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                    required
                  />
                  <div className="flex gap-2">
                    <select
                      value={newRole}
                      onChange={(e) => setNewRole(e.target.value)}
                      className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white flex-1"
                    >
                      <option value="viewer">Viewer (Read-Only)</option>
                      <option value="admin">Admin (Full Control)</option>
                    </select>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs transition"
                    >
                      Create
                    </button>
                  </div>
                </form>
              </div>

              {/* Users Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex justify-between items-center">
                  <span className="text-sm font-semibold text-slate-200">Registered Accounts ({users.length})</span>
                  <button onClick={fetchUsers} className="text-xs text-slate-400 hover:text-white flex items-center gap-1">
                    <FiRefreshCw /> Refresh
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider text-[10px]">
                      <tr>
                        <th className="p-3">ID</th>
                        <th className="p-3">Username</th>
                        <th className="p-3">Email</th>
                        <th className="p-3">Role</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Last Login</th>
                        <th className="p-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-slate-800/40">
                          <td className="p-3 font-mono">{u.id}</td>
                          <td className="p-3 font-semibold text-white">{u.username}</td>
                          <td className="p-3 text-slate-400">{u.email}</td>
                          <td className="p-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                u.role === "admin"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                  : "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                              }`}
                            >
                              {u.role}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className={`inline-flex items-center gap-1 text-[11px] ${u.is_active ? "text-emerald-400" : "text-rose-400"}`}>
                              {u.is_active ? <FiCheckCircle /> : <FiXCircle />}
                              {u.is_active ? "Active" : "Deactivated"}
                            </span>
                          </td>
                          <td className="p-3 font-mono text-[11px] text-slate-500">
                            {u.last_login ? u.last_login.slice(0, 19).replace("T", " ") : "Never"}
                          </td>
                          <td className="p-3 text-right space-x-2">
                            <button
                              onClick={() => handleToggleUserRole(u)}
                              disabled={u.username === user?.username}
                              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-[11px] text-slate-300 disabled:opacity-30"
                            >
                              Toggle Role
                            </button>
                            <button
                              onClick={() => handleToggleUserStatus(u)}
                              disabled={u.username === user?.username}
                              className={`px-2 py-1 rounded text-[11px] font-medium disabled:opacity-30 ${
                                u.is_active
                                  ? "bg-rose-500/10 text-rose-400 hover:bg-rose-500/20"
                                  : "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                              }`}
                            >
                              {u.is_active ? "Deactivate" : "Activate"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Tab 3: Notifications (Admin Only) ── */}
      {activeTab === "notifications" && (
        <>
          {!isAdmin ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
              <FiLock className="text-4xl text-amber-400 mx-auto mb-3" />
              <h3 className="text-lg font-bold text-slate-200">Administrative Privileges Required</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                Configuring automated external alerts via Telegram or Email is reserved for system administrators.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h2 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <FiBell className="text-emerald-400" /> Automated External Alerting Dispatcher
                </h2>
                <form onSubmit={handleSaveNotifications} className="space-y-4">
                  {/* Telegram Bot */}
                  <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/60 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
                        📱 Telegram Bot Integration
                      </span>
                      <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                        <input
                          type="checkbox"
                          checked={notifConfig.telegram_enabled}
                          onChange={(e) => setNotifConfig({ ...notifConfig, telegram_enabled: e.target.checked })}
                          className="rounded text-emerald-600 focus:ring-0"
                        />
                        Enable Telegram Alerts
                      </label>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[11px] text-slate-400 block mb-1">Bot Token</label>
                        <input
                          type="password"
                          placeholder="e.g. 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
                          value={notifConfig.telegram_bot_token || ""}
                          onChange={(e) => setNotifConfig({ ...notifConfig, telegram_bot_token: e.target.value })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                        />
                      </div>
                      <div>
                        <label className="text-[11px] text-slate-400 block mb-1">Target Chat ID</label>
                        <input
                          type="text"
                          placeholder="e.g. -100123456789 or @channel"
                          value={notifConfig.telegram_chat_id || ""}
                          onChange={(e) => setNotifConfig({ ...notifConfig, telegram_chat_id: e.target.value })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                        />
                      </div>
                    </div>
                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={() => handleTestNotification("telegram")}
                        disabled={testingChannel === "telegram"}
                        className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-200 flex items-center gap-1.5"
                      >
                        <FiSend /> {testingChannel === "telegram" ? "Sending..." : "Test Telegram Alert"}
                      </button>
                    </div>
                  </div>

                  {/* SMTP Email */}
                  <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/60 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
                        ✉️ SMTP Email Dispatcher
                      </span>
                      <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                        <input
                          type="checkbox"
                          checked={notifConfig.email_enabled}
                          onChange={(e) => setNotifConfig({ ...notifConfig, email_enabled: e.target.checked })}
                          className="rounded text-emerald-600 focus:ring-0"
                        />
                        Enable Email Alerts
                      </label>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="text-[11px] text-slate-400 block mb-1">SMTP Server</label>
                        <input
                          type="text"
                          value={notifConfig.smtp_host}
                          onChange={(e) => setNotifConfig({ ...notifConfig, smtp_host: e.target.value })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                        />
                      </div>
                      <div>
                        <label className="text-[11px] text-slate-400 block mb-1">Port</label>
                        <input
                          type="number"
                          value={notifConfig.smtp_port}
                          onChange={(e) => setNotifConfig({ ...notifConfig, smtp_port: parseInt(e.target.value) || 587 })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                        />
                      </div>
                      <div>
                        <label className="text-[11px] text-slate-400 block mb-1">SMTP Username</label>
                        <input
                          type="text"
                          value={notifConfig.smtp_user}
                          onChange={(e) => setNotifConfig({ ...notifConfig, smtp_user: e.target.value })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Recipients (comma-separated)</label>
                      <input
                        type="text"
                        placeholder="operator@company.com, manager@grainstore.org"
                        value={notifConfig.email_recipients}
                        onChange={(e) => setNotifConfig({ ...notifConfig, email_recipients: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                      />
                    </div>
                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={() => handleTestNotification("email")}
                        disabled={testingChannel === "email"}
                        className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-200 flex items-center gap-1.5"
                      >
                        <FiSend /> {testingChannel === "email" ? "Sending..." : "Test Email Alert"}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs transition"
                  >
                    Save Notification Settings
                  </button>
                </form>
              </div>

              {/* Delivery History Logs */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800">
                  <span className="text-sm font-semibold text-slate-200">Recent Notification Delivery Attempts</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider text-[10px]">
                      <tr>
                        <th className="p-3">Timestamp</th>
                        <th className="p-3">Channel</th>
                        <th className="p-3">Recipient</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Message / Error</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {notifLogs.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="p-4 text-center text-slate-500">
                            No notifications dispatched yet.
                          </td>
                        </tr>
                      ) : (
                        notifLogs.slice(0, 10).map((log) => (
                          <tr key={log.id} className="hover:bg-slate-800/40">
                            <td className="p-3 font-mono text-slate-400">{log.timestamp?.slice(0, 19).replace("T", " ")}</td>
                            <td className="p-3 uppercase font-semibold">{log.channel}</td>
                            <td className="p-3 text-slate-400">{log.recipient}</td>
                            <td className="p-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                  log.status === "sent"
                                    ? "bg-emerald-500/10 text-emerald-400"
                                    : "bg-rose-500/10 text-rose-400"
                                }`}
                              >
                                {log.status}
                              </span>
                            </td>
                            <td className="p-3 text-slate-400 truncate max-w-xs">{log.error_message || log.subject}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Tab 4: Storage Units (Silos) ── */}
      {activeTab === "silos" && (
        <div className="space-y-6">
          {isAdmin && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <FiPlus className="text-emerald-400" /> Register Storage Unit / Silo
              </h2>
              <form onSubmit={handleCreateUnit} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <input
                  type="text"
                  placeholder="Unit ID (e.g. silo-4)"
                  value={newUnitId}
                  onChange={(e) => setNewUnitId(e.target.value)}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                  required
                />
                <input
                  type="text"
                  placeholder="Unit Name (e.g. Silo Delta)"
                  value={newUnitName}
                  onChange={(e) => setNewUnitName(e.target.value)}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                  required
                />
                <input
                  type="number"
                  placeholder="Capacity (Tons)"
                  value={newCapacity}
                  onChange={(e) => setNewCapacity(e.target.value)}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                  required
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs transition"
                >
                  Register Silo
                </button>
              </form>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {storageUnits.map((u) => (
              <div key={u.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
                <div className="flex justify-between items-start">
                  <h3 className="font-bold text-white text-sm">{u.name}</h3>
                  <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                    {u.unit_id}
                  </span>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <p>Grain Type: <b className="text-slate-200">{u.grain_type}</b></p>
                  <p>Capacity: <b className="text-slate-200">{u.capacity_tons} Tons</b></p>
                  <p>Fill: <b className="text-slate-200">{u.current_fill_tons} Tons ({((u.current_fill_tons/u.capacity_tons)*100).toFixed(0)}%)</b></p>
                  <p>Current Risk: <b className={u.current_risk === "High" ? "text-rose-400" : "text-emerald-400"}>{u.current_risk}</b></p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tab 5: Audit Trail (Admin Only) ── */}
      {activeTab === "audit" && (
        <>
          {!isAdmin ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
              <FiLock className="text-4xl text-amber-400 mx-auto mb-3" />
              <h3 className="text-lg font-bold text-slate-200">Administrative Privileges Required</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                Security audit logs track all sensitive operations, login events, and configuration modifications.
              </p>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex justify-between items-center">
                <span className="text-sm font-semibold text-slate-200">Security & Operational Audit Trail</span>
                <button onClick={fetchAuditLogs} className="text-xs text-slate-400 hover:text-white flex items-center gap-1">
                  <FiRefreshCw /> Refresh Trail
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="p-3">Timestamp</th>
                      <th className="p-3">User</th>
                      <th className="p-3">Action</th>
                      <th className="p-3">Resource</th>
                      <th className="p-3">IP Address</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {auditLogs.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="p-4 text-center text-slate-500">No audit records found.</td>
                      </tr>
                    ) : (
                      auditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-800/40">
                          <td className="p-3 font-mono text-slate-400">{log.timestamp?.slice(0, 19).replace("T", " ")}</td>
                          <td className="p-3 font-semibold text-white">{log.username}</td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-emerald-400 border border-slate-700">
                              {log.action}
                            </span>
                          </td>
                          <td className="p-3 text-slate-400">{log.resource || "system"}</td>
                          <td className="p-3 font-mono text-slate-500">{log.ip_address || "127.0.0.1"}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
