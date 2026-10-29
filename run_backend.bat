@echo off
title GrainGuard AI - FastAPI Backend (Port 8000)
echo =======================================================
echo  🌾 GrainGuard AI - AR-TCN Backend Server
echo =======================================================
echo [INFO] Working directory: %CD%
echo [INFO] Binding to: http://127.0.0.1:8000
echo [INFO] Interactive Swagger UI: http://127.0.0.1:8000/docs
echo.

set PYTHONPATH=%CD%;%CD%\.venv\Lib\site-packages
"C:\Users\Naveena\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Backend failed to start.
    pause
)
