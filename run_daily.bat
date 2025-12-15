@echo off
REM Daily Forward Volatility Scanner - Windows Batch Runner
REM Double-click this file to run all daily scans

echo ========================================
echo  Daily Forward Volatility Scanner
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Prefer venv Python if available
set VENV_PY=%~dp0.venv\Scripts\python.exe
if exist "%VENV_PY%" (
    "%VENV_PY%" daily_run.py
) else (
    python daily_run.py
)

echo.
echo ========================================
echo  Execution Complete
echo  Website will update in ~2 minutes
echo ========================================
echo.
pause
