@echo off
REM IndiaStocks AI — Daily Report Wrapper (for Task Scheduler)
REM This file is in the backend folder with the engine.
REM To schedule: SCHTASKS /Create /TN "IndiaStocksAI" /TR "C:\Users\HP\Desktop\run_daily.bat" /SC DAILY /ST 16:00 /F
cd /d "%~dp0"
python daily_analysis_engine.py >> daily_run.log 2>&1
