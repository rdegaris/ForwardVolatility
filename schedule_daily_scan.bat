@echo off
REM Daily Forward Volatility Scanner - Task Scheduler Wrapper
REM This script runs the daily scanner using the venv Python directly

cd /d "C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator"

REM Use FULL PATH to venv Python to prevent Windows py launcher interference
set PYTHON_EXE=C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\.venv\Scripts\python.exe

REM Disable Python launcher and ensure we use only venv Python
set PY_PYTHON=
set PYTHONHOME=
set PYTHONPATH=

REM Remove system Python from PATH for this session
set PATH=C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\.venv\Scripts;%SYSTEMROOT%\System32

REM Run the daily scanner (redirect output to log)
"%PYTHON_EXE%" daily_run.py >> logs\scheduled_run.log 2>&1

REM Exit cleanly
exit /b 0
