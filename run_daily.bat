@echo off
REM Daily Forward Volatility Scanner - Windows Batch Runner
REM Double-click this file to run all daily scans

echo ========================================
echo  Daily Forward Volatility Scanner
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Run the Python script
python daily_run.py

echo.
echo ========================================
echo  Execution Complete
echo ========================================
echo.
pause
