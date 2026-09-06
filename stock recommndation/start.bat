@echo off
echo ============================================
echo  IndiaStocks AI - Starting Services
echo ============================================

echo.
echo [1/2] Starting FastAPI Backend on port 8000...
start "IndiaStocks-Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting React Frontend on port 3000...
start "IndiaStocks-Frontend" cmd /k "cd /d "%~dp0" && npm run dev"

echo.
echo ============================================
echo  Both services started!
echo  Frontend: http://localhost:3000
echo  Backend:  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo ============================================
pause
