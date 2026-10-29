@echo off
title GrainGuard AI - React Dashboard (Port 3000)
echo =======================================================
echo  🌾 GrainGuard AI - Frontend React Dashboard
echo =======================================================
echo [INFO] Dashboard URL: http://localhost:3000
echo.

cd frontend
npm start

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Frontend failed to start.
    pause
)
