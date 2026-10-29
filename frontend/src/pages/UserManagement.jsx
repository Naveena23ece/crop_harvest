/**
 * FILE: frontend/src/pages/UserManagement.jsx
 * Dedicated Enterprise Admin Portal for User Account Provisioning and Role Management.
 * Accessible strictly to Admin users.
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { listUsersApi, createUserApi, updateUserApi } from "../services/api";
import toast from "react-hot-toast";
import {
  FiUsers,
  FiUserPlus,
  FiShield,
  FiUser,
  FiLock,
  FiCheckCircle,
  FiXCircle,
  FiKey,
  FiRefreshCw,
  FiSearch,
  FiEye,
  FiEyeOff,
  FiAlertTriangle,
} from "react-icons/fi";

export default function UserManagement() {
  const { user: currentUser, isAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");

  // Create User Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [newRole, setNewRole] = useState("viewer");
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState(null);

  // Password Reset Modal State
  const [resetUser, setResetUser] = useState(null);
  const [resetPasswordVal, setResetPasswordVal] = useState("");
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await listUsersApi();
      setUsers(data?.users || []);
    } catch (err) {
      toast.error(err.message || "Failed to load user accounts.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setModalError(null);

    if (newUsername.trim().length < 3) {
      setModalError("Username must be at least 3 characters.");
      return;
    }
    if (!newEmail.includes("@")) {
      setModalError("Please provide a valid email address.");
      return;
    }
    if (newPassword.length < 4) {
      setModalError("Password must be at least 4 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setModalError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await createUserApi({
        username: newUsername.trim(),
        email: newEmail.trim(),
        password: newPassword,
        role: newRole,
      });
      toast.success(`Account '${newUsername}' created successfully as ${newRole.toUpperCase()}.`);
      setShowCreateModal(false);
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      setConfirmPassword("");
      fetchUsers();
    } catch (err) {
      setModalError(err.message || "Failed to create user account.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStatus = async (targetUser) => {
    if (targetUser.id === currentUser?.id) {
      toast.error("You cannot deactivate your own active session.");
      return;
    }

    const action = targetUser.is_active ? "deactivate" : "activate";
    if (!window.confirm(`Are you sure you want to ${action} user '${targetUser.username}'?`)) {
      return;
    }

    try {
      await updateUserApi(targetUser.id, { is_active: !targetUser.is_active });
      toast.success(`User '${targetUser.username}' has been ${action}d.`);
      fetchUsers();
    } catch (err) {
      toast.error(err.message || `Failed to ${action} user.`);
    }
  };

  const handleToggleRole = async (targetUser) => {
    if (targetUser.id === currentUser?.id) {
      toast.error("You cannot modify your own administrative role.");
      return;
    }

    const nextRole = targetUser.role === "admin" ? "viewer" : "admin";
    if (
      !window.confirm(
        `Are you sure you want to change role for '${targetUser.username}' from ${targetUser.role.toUpperCase()} to ${nextRole.toUpperCase()}?`
      )
    ) {
      return;
    }

    try {
      await updateUserApi(targetUser.id, { role: nextRole });
      toast.success(`User '${targetUser.username}' role changed to ${nextRole.toUpperCase()}.`);
      fetchUsers();
    } catch (err) {
      toast.error(err.message || "Failed to update role.");
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!resetUser || resetPasswordVal.length < 4) {
      toast.error("Password must be at least 4 characters.");
      return;
    }

    setResetting(true);
    try {
      await updateUserApi(resetUser.id, { password: resetPasswordVal });
      toast.success(`Password for '${resetUser.username}' updated successfully.`);
      setResetUser(null);
      setResetPasswordVal("");
    } catch (err) {
      toast.error(err.message || "Failed to reset password.");
    } finally {
      setResetting(false);
    }
  };

  // Filtered accounts
  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      (u.email && u.email.toLowerCase().includes(search.toLowerCase()));
    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  if (!isAdmin) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-lg text-center">
        <FiLock className="text-4xl text-amber-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-[var(--text-primary)]">
          Access Restricted: Administrator Privileges Required
        </h2>
        <p className="text-xs text-[var(--text-muted)] mt-1.5 leading-relaxed">
          The User Management portal is restricted to system administrators. Viewer accounts are provisioned with read-only monitoring access.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <FiUsers className="text-emerald-600 dark:text-emerald-500 text-lg" />
            User Account Management
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Provision authorized facility operators, assign roles, and manage system access credentials
          </p>
        </div>

        <button
          onClick={() => {
            setModalError(null);
            setShowCreateModal(true);
          }}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-emerald-700 hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white rounded-md text-xs font-semibold shadow-sm transition-colors cursor-pointer"
        >
          <FiUserPlus className="text-sm" /> Provision New User
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-[var(--bg-surface)] p-3 rounded-lg border border-[var(--border-color)]">
        <div className="relative w-full sm:w-80">
          <FiSearch className="absolute left-3 top-2.5 text-xs text-[var(--text-muted)] pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by username or email..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs text-[var(--text-muted)] font-medium">Filter Role:</label>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md"
          >
            <option value="all">All Roles ({users.length})</option>
            <option value="admin">Administrators</option>
            <option value="viewer">Viewers</option>
          </select>
          <button
            onClick={fetchUsers}
            title="Refresh Users"
            className="p-2 text-xs border border-[var(--border-color)] rounded-md text-[var(--text-secondary)] hover:bg-[var(--bg-surface-elevated)]"
          >
            <FiRefreshCw className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[var(--text-primary)]">
            <thead className="bg-[var(--bg-surface-elevated)] border-b border-[var(--border-color)] text-[var(--text-secondary)] uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">User</th>
                <th className="py-3 px-4 font-semibold">Role</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Created Date</th>
                <th className="py-3 px-4 font-semibold">Last Login</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--text-muted)]">
                    Loading accounts...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--text-muted)]">
                    No user accounts match the selected criteria.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  return (
                    <tr key={u.id} className="hover:bg-[var(--bg-surface-subtle)] transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                          {u.username}
                          {isSelf && (
                            <span className="text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 px-1.5 py-0.2 rounded font-normal">
                              You
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-[var(--text-muted)] font-mono">{u.email}</div>
                      </td>

                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                            u.role === "admin"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800"
                              : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700"
                          }`}
                        >
                          {u.role === "admin" ? <FiShield className="text-[10px]" /> : <FiUser className="text-[10px]" />}
                          {u.role}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 text-[11px] font-medium ${
                            u.is_active ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"
                          }`}
                        >
                          {u.is_active ? <FiCheckCircle /> : <FiXCircle />}
                          {u.is_active ? "Active" : "Deactivated"}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-[11px] text-[var(--text-muted)] font-mono">
                        {u.created_at ? u.created_at.slice(0, 10) : "System"}
                      </td>

                      <td className="py-3 px-4 text-[11px] text-[var(--text-muted)] font-mono">
                        {u.last_login ? u.last_login.slice(0, 19).replace("T", " ") : "Never"}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => {
                              setResetUser(u);
                              setResetPasswordVal("");
                            }}
                            title="Reset Password"
                            className="p-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-elevated)] rounded border border-[var(--border-color)]"
                          >
                            <FiKey />
                          </button>

                          <button
                            onClick={() => handleToggleRole(u)}
                            disabled={isSelf}
                            title={isSelf ? "Cannot change own role" : `Switch to ${u.role === "admin" ? "Viewer" : "Admin"}`}
                            className="px-2 py-1 text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-elevated)] rounded border border-[var(--border-color)] disabled:opacity-40"
                          >
                            Role
                          </button>

                          <button
                            onClick={() => handleToggleStatus(u)}
                            disabled={isSelf}
                            title={isSelf ? "Cannot deactivate yourself" : u.is_active ? "Deactivate" : "Activate"}
                            className={`px-2 py-1 text-[11px] rounded font-medium disabled:opacity-40 border ${
                              u.is_active
                                ? "text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/50 hover:bg-rose-100"
                                : "text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/50 hover:bg-emerald-100"
                            }`}
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Modal: Provision New User Account ──────────────────────────────── */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-lg shadow-xl w-full max-w-md p-6 animate-in fade-in zoom-in-95 duration-100">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <FiUserPlus className="text-emerald-600 dark:text-emerald-500" />
                Provision User Account
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mb-4 p-2.5 rounded bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 text-rose-700 dark:text-rose-400 text-xs flex items-center gap-2">
                <FiAlertTriangle className="flex-shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Username
                </label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="e.g. operator_john"
                  className="w-full px-3 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="e.g. operator@grainstore.local"
                  className="w-full px-3 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Initial Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 4 characters"
                    className="w-full pl-3 pr-8 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-2 text-[var(--text-muted)]"
                  >
                    {showPassword ? <FiEyeOff size={13} /> : <FiEye size={13} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm password"
                  className="w-full px-3 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Authorized Role
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md"
                >
                  <option value="viewer">Viewer (Read-Only Monitoring)</option>
                  <option value="admin">Administrator (Full Control)</option>
                </select>
                <p className="text-[11px] text-[var(--text-muted)] mt-1">
                  Viewers have read-only monitoring access; Admins have full facility configuration privileges.
                </p>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 text-xs font-medium border border-[var(--border-color)] rounded-md text-[var(--text-secondary)] hover:bg-[var(--bg-surface-elevated)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 text-xs font-semibold bg-emerald-700 hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white rounded-md shadow-sm disabled:opacity-50"
                >
                  {submitting ? "Creating..." : "Create Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal: Reset Password ────────────────────────────────────────── */}
      {resetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-lg shadow-xl w-full max-w-sm p-6">
            <h3 className="text-sm font-bold text-[var(--text-primary)] mb-1">
              Reset Password for '{resetUser.username}'
            </h3>
            <p className="text-xs text-[var(--text-muted)] mb-4">
              Enter a new temporary password for this user.
            </p>

            <form onSubmit={handleResetPassword} className="space-y-3">
              <div className="relative">
                <input
                  type={showResetPassword ? "text" : "password"}
                  required
                  value={resetPasswordVal}
                  onChange={(e) => setResetPasswordVal(e.target.value)}
                  placeholder="Enter new password"
                  className="w-full pl-3 pr-8 py-1.5 text-xs bg-[var(--bg-app)] border border-[var(--border-color)] rounded-md"
                />
                <button
                  type="button"
                  onClick={() => setShowResetPassword(!showResetPassword)}
                  className="absolute right-2.5 top-2 text-[var(--text-muted)]"
                >
                  {showResetPassword ? <FiEyeOff size={13} /> : <FiEye size={13} />}
                </button>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setResetUser(null)}
                  className="px-3 py-1.5 text-xs font-medium border border-[var(--border-color)] rounded-md text-[var(--text-secondary)] hover:bg-[var(--bg-surface-elevated)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resetting}
                  className="px-4 py-1.5 text-xs font-semibold bg-emerald-700 hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white rounded-md shadow-sm disabled:opacity-50"
                >
                  {resetting ? "Updating..." : "Update Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
