/**
 * FILE: frontend/src/pages/Settings.jsx
 * Application settings: Firebase config display, API URL, and training trigger.
 */

import React, { useState } from "react";
import { triggerTraining, healthCheck } from "../services/api";
import toast from "react-hot-toast";

export default function Settings() {
  const [apiUrl,    setApiUrl]    = useState(process.env.REACT_APP_API_URL || "http://localhost:8000");
  const [training,  setTraining]  = useState(false);
  const [healthRes, setHealthRes] = useState(null);

  const handlePing = async () => {
    try {
      const res = await healthCheck();
      setHealthRes(res);
      toast.success("Backend is online!");
    } catch {
      toast.error("Backend unreachable");
      setHealthRes(null);
    }
  };

  const handleTrain = async () => {
    setTraining(true);
    try {
      await triggerTraining({ model: "artcn" });
      toast.success("Training started! Check server logs.");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Configure system connections and model training</p>
      </div>

      {/* API Configuration */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-4">
        <h2 className="text-sm font-medium text-gray-300 uppercase tracking-wide">
          Backend API
        </h2>
        <div>
          <label className="text-xs text-gray-500 block mb-1">API URL</label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5
                       text-sm text-gray-200 font-mono focus:outline-none
                       focus:ring-2 focus:ring-green-600"
          />
        </div>
        <button
          onClick={handlePing}
          className="px-4 py-2 bg-blue-700/30 hover:bg-blue-700/50 border border-blue-600/50
                     text-blue-400 rounded-lg text-sm transition-colors"
        >
          🔌 Test Connection
        </button>
        {healthRes && (
          <div className="bg-green-900/20 border border-green-700/40 rounded-lg p-3 text-xs
                          text-green-400 font-mono">
            {JSON.stringify(healthRes, null, 2)}
          </div>
        )}
      </div>

      {/* Firebase */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-3">
        <h2 className="text-sm font-medium text-gray-300 uppercase tracking-wide">
          Firebase Configuration
        </h2>
        <p className="text-sm text-gray-500">
          Update Firebase credentials in{" "}
          <code className="text-green-400 bg-gray-800 px-1 rounded">
            frontend/src/services/firebase.js
          </code>{" "}
          and{" "}
          <code className="text-green-400 bg-gray-800 px-1 rounded">
            frontend/.env
          </code>
        </p>
        <div className="grid grid-cols-1 gap-2 text-xs font-mono">
          {[
            "REACT_APP_FIREBASE_API_KEY",
            "REACT_APP_FIREBASE_DATABASE_URL",
            "REACT_APP_FIREBASE_PROJECT_ID",
          ].map((key) => (
            <div key={key} className="flex items-center gap-2 bg-gray-800 px-3 py-2 rounded">
              <span className="text-gray-500">{key}</span>
              <span className="text-green-400 ml-auto">
                {process.env[key] ? "✓ Set" : "⚠ Not set"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Model Training */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-4">
        <h2 className="text-sm font-medium text-gray-300 uppercase tracking-wide">
          Model Training
        </h2>
        <p className="text-sm text-gray-500">
          Triggers the AR-TCN training pipeline on the backend server.
          Training will run in the background (10–60 mins depending on hardware).
        </p>
        <button
          onClick={handleTrain}
          disabled={training}
          className="flex items-center gap-2 px-4 py-2 bg-green-700/30 hover:bg-green-700/50
                     border border-green-600/50 text-green-400 rounded-lg text-sm
                     transition-colors disabled:opacity-50"
        >
          {training ? (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
          ) : "🚀"}
          {training ? "Starting..." : "Trigger Training"}
        </button>
      </div>
    </div>
  );
}
