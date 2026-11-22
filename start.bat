@echo off
echo ============================================
echo  IndiaStocks AI - Starting Services
echo ============================================

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    set "VENV_PY=python"
)

echo.
echo [1/2] Starting FastAPI Backend on port 8000...
start "IndiaStocks-Backend" /D "%~dp0stock recommndation\backend" cmd /k ""%VENV_PY%" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

ping -n 3 127.0.0.1 >nul

echo [2/2] Starting React Frontend on port 3000...
start "IndiaStocks-Frontend" /D "%~dp0stock recommndation" cmd /k "npm run dev"

echo.
echo ============================================
echo  Both services started!
echo  Frontend: http://localhost:3000
echo  Backend:  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo ============================================
