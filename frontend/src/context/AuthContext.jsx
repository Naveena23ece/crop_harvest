/**
 * FILE: frontend/src/context/AuthContext.jsx
 * Provides NIST-compliant JWT Authentication and Role-Based Access Control context.
 * Manages active user claims, server token sessions, and role enforcement.
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { loginApi, logoutApi, getMeApi } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

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
      return res.user;
    }
    throw new Error("No access token returned by authentication server.");
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch (e) {
      // Ignore network errors during logout
    } finally {
      sessionStorage.removeItem("grainguard_token");
      setUser(null);
    }
  };

  const isAdmin = user?.role === "admin";
  const isViewer = user?.role === "viewer";

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAdmin,
        isViewer,
        login,
        logout,
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
