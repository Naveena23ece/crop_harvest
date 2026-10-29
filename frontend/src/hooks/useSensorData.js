/**
 * FILE: frontend/src/hooks/useSensorData.js
 * Custom hook that manages live sensor data, predictions, and alerts.
 *
 * Behavior:
 *   - Subscribes to Firebase realtime listener for sensor updates
 *   - Polls /latest-risk every 60 seconds for updated predictions
 *   - Maintains a rolling history of readings for charts
 *   - Exposes loading / error states
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { subscribeToLatestSensor } from "../services/firebase";
import { getLatestRisk, getHistory } from "../services/api";

const HISTORY_MAX   = 100;   // keep last 100 readings for charts
const POLL_INTERVAL = 60_000; // 60 seconds

// ── Mock data generator (used when Firebase unavailable) ────
function generateMockReading() {
  const now = new Date();
  const h = now.getHours();
  const seasonal = Math.sin((2 * Math.PI * now.getDate()) / 30) * 5;
  return {
    timestamp:          now.toISOString(),
    temperature_c:      +(27 + seasonal + (Math.random() - 0.5) * 3).toFixed(2),
    humidity_pct:       +(62 + seasonal + (Math.random() - 0.5) * 6).toFixed(2),
    gas_concentration:  +(450 + (Math.random() - 0.5) * 100).toFixed(1),
    grain_moisture:     +(12 + (Math.random() - 0.5) * 2).toFixed(2),
    storage_duration:   45,
    ext_temperature_c:  +(30 + seasonal + (Math.random() - 0.5) * 2).toFixed(2),
    ventilation_status: Math.random() > 0.5 ? 1 : 0,
    battery_voltage:    +(3.85 + (Math.random() - 0.5) * 0.2).toFixed(3),
    sensor_health:      1,
  };
}

export default function useSensorData(useMock = false) {
  const [sensorData,  setSensorData]  = useState(null);
  const [prediction,  setPrediction]  = useState(null);
  const [history,     setHistory]     = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const historyRef = useRef([]);

  // ── Append to rolling history ──────────────────────────
  const appendHistory = useCallback((reading) => {
    historyRef.current = [...historyRef.current, reading].slice(-HISTORY_MAX);
    setHistory([...historyRef.current]);
  }, []);

  // ── Fetch latest risk prediction ───────────────────────
  const fetchLatestRisk = useCallback(async () => {
    try {
      const result = await getLatestRisk(useMock);
      if (result?.sensor_data)  setSensorData(result.sensor_data);
      if (result?.prediction)   setPrediction(result.prediction);
      if (result?.sensor_data)  appendHistory(result.sensor_data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      // Fall back to mock
      const mock = generateMockReading();
      setSensorData(mock);
      appendHistory(mock);
      setLastUpdated(new Date());
      if (!useMock) {
        setError(`Backend unreachable — showing mock data: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  }, [useMock, appendHistory]);

  // ── Initial load + polling ─────────────────────────────
  useEffect(() => {
    fetchLatestRisk();
    const interval = setInterval(fetchLatestRisk, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchLatestRisk]);

  // ── Firebase realtime listener ────────────────────────
  useEffect(() => {
    let unsubscribe;
    try {
      unsubscribe = subscribeToLatestSensor((data) => {
        setSensorData(data);
        appendHistory(data);
        setLastUpdated(new Date());
      });
    } catch {
      // Firebase not configured — polling only
    }
    return () => { if (unsubscribe) unsubscribe(); };
  }, [appendHistory]);

  // ── Load initial chart history from backend ────────────
  useEffect(() => {
    getHistory("sensors", 100)
      .then((res) => {
        if (res?.records?.length) {
          historyRef.current = res.records.slice(-HISTORY_MAX);
          setHistory([...historyRef.current]);
        }
      })
      .catch(() => {});
  }, []);

  return {
    sensorData,
    prediction,
    history,
    loading,
    error,
    lastUpdated,
    refresh: fetchLatestRisk,
  };
}
