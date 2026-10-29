/**
 * FILE: frontend/src/context/AuthContext.jsx
 * Provides NIST-compliant JWT Authentication and Role-Based Access Control context.
 * Manages active user claims, role enforcement (admin vs viewer), and session persistence.
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { loginApi, logoutApi, getMeApi, signupApi } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [demoMode, setDemoMode] = useState(false);

  useEffect(() => {
    // Check if an existing session token is stored in sessionStorage
    const initSession = async () => {
      const token = sessionStorage.getItem("grainguard_token");
      if (token) {
        try {
          const res = await getMeApi();
          if (res?.user) {
            setUser(res.user);
          }
        } catch (err) {
          console.warn("Session token expired or invalid:", err);
          sessionStorage.removeItem("grainguard_token");
          setUser(null);
        }
      }
      setLoading(false);
    };

    initSession();
  }, []);

  const login = async (username, password) => {
    const res = await loginApi(username, password);
    if (res?.access_token) {
      sessionStorage.setItem("grainguard_token", res.access_token);
      setUser(res.user);
      setDemoMode(false);
      return res.user;
    }
    throw new Error("No access token returned by authentication server.");
  };

  const signup = async (username, email, password) => {
    return await signupApi(username, email, password);
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch (e) {
      // Ignore network errors during logout
    } finally {
      sessionStorage.removeItem("grainguard_token");
      setUser(null);
      setDemoMode(false);
    }
  };

  // Safe client-side demo entry for prototype evaluation
  const enterDemo = (role = "viewer") => {
    const demoUser = {
      id: 999,
      username: role === "admin" ? "demo_admin" : "demo_viewer",
      email: `${role}@grainguard.demo`,
      role: role,
      is_active: true,
      is_demo: true,
    };
    setUser(demoUser);
    setDemoMode(true);
  };

  const isAdmin = user?.role === "admin";
  const isViewer = user?.role === "viewer";

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        demoMode,
        isAdmin,
        isViewer,
        login,
        signup,
        logout,
        enterDemo,
      }}
    >
      {!loading && children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
