/**
 * FILE: frontend/src/index.js
 * React application entry point.
 */

import React        from "react";
import ReactDOM     from "react-dom/client";
import "./index.css";
import App          from "./App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register PWA service worker in production environments
if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js")
      .then((registration) => {
        console.log("GrainGuard PWA ServiceWorker registered: ", registration.scope);
      })
      .catch((err) => {
        console.log("GrainGuard PWA ServiceWorker registration error: ", err);
      });
  });
}
