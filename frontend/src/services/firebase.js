/**
 * FILE: frontend/src/services/firebase.js
 * Firebase SDK initialisation and realtime database helpers.
 * Provides:
 *   - Realtime listener for latest sensor readings
 *   - Reads from /predictions and /alerts
 *   - Auth helpers (email/password)
 *
 * Replace the firebaseConfig values with your own from the Firebase console.
 */

import { initializeApp }           from "firebase/app";
import { getAuth }                 from "firebase/auth";
import {
  getDatabase, ref, onValue, off,
  query, orderByKey, limitToLast,
  get,
}                                  from "firebase/database";

// ─── Firebase Configuration ──────────────────────────────
// Replace these values with your project's Firebase config
const firebaseConfig = {
  apiKey:            process.env.REACT_APP_FIREBASE_API_KEY            || "YOUR_API_KEY",
  authDomain:        process.env.REACT_APP_FIREBASE_AUTH_DOMAIN        || "grain-storage-monitor.firebaseapp.com",
  databaseURL:       process.env.REACT_APP_FIREBASE_DATABASE_URL       || "https://grain-storage-monitor-default-rtdb.firebaseio.com",
  projectId:         process.env.REACT_APP_FIREBASE_PROJECT_ID         || "grain-storage-monitor",
  storageBucket:     process.env.REACT_APP_FIREBASE_STORAGE_BUCKET     || "grain-storage-monitor.appspot.com",
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID|| "123456789",
  appId:             process.env.REACT_APP_FIREBASE_APP_ID             || "1:123456789:web:abcdef",
};

// Initialise Firebase
const app  = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const database = getDatabase(app);

// ─── Realtime Listener: Latest Sensor Reading ─────────────
/**
 * Registers a listener that fires whenever the ESP32 writes a new reading.
 * @param {Function} callback - (data: Object) => void
 * @returns {Function} unsubscribe function
 */
export function subscribeToLatestSensor(callback) {
  const sensorRef = ref(database, "/sensor_data/latest");
  onValue(sensorRef, (snapshot) => {
    if (snapshot.exists()) {
      callback(snapshot.val());
    }
  });
  // Return cleanup function
  return () => off(sensorRef);
}

// ─── Realtime Listener: Latest Prediction ─────────────────
export function subscribeToLatestPrediction(callback) {
  const predRef = query(
    ref(database, "/predictions"),
    orderByKey(),
    limitToLast(1)
  );
  onValue(predRef, (snapshot) => {
    if (snapshot.exists()) {
      const vals = Object.values(snapshot.val());
      callback(vals[vals.length - 1]);
    }
  });
  return () => off(predRef);
}

// ─── Fetch: Prediction History ────────────────────────────
export async function fetchPredictionHistory(limit = 50) {
  const predRef = query(
    ref(database, "/predictions"),
    orderByKey(),
    limitToLast(limit)
  );
  const snapshot = await get(predRef);
  if (!snapshot.exists()) return [];
  return Object.values(snapshot.val()).sort(
    (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
  );
}

// ─── Fetch: Alert History ─────────────────────────────────
export async function fetchAlertHistory(limit = 30) {
  const alertRef = query(
    ref(database, "/alerts"),
    orderByKey(),
    limitToLast(limit)
  );
  const snapshot = await get(alertRef);
  if (!snapshot.exists()) return [];
  return Object.values(snapshot.val()).sort(
    (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
  );
}

// ─── Fetch: Sensor History ────────────────────────────────
export async function fetchSensorHistory(limit = 100) {
  const sensorRef = query(
    ref(database, "/sensor_data"),
    orderByKey(),
    limitToLast(limit + 1)
  );
  const snapshot = await get(sensorRef);
  if (!snapshot.exists()) return [];
  const all = snapshot.val();
  // Exclude the 'latest' sub-key
  return Object.entries(all)
    .filter(([k]) => k !== "latest")
    .map(([, v]) => v)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    .slice(-limit);
}

export default app;
