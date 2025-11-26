@echo off
REM Daily Forward Volatility Scanner - Task Scheduler Wrapper
REM This script runs the daily scanner using the venv Python directly

cd /d "C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator"

REM Use venv Python directly (more reliable than activating in Task Scheduler)
set PYTHON_EXE=.venv\Scripts\python.exe

REM Run the daily scanner (redirect output to log)
%PYTHON_EXE% daily_run.py >> logs\scheduled_run.log 2>&1

REM Exit cleanly
exit /b 0
