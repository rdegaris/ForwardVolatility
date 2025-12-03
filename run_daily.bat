@echo off
REM Daily Forward Volatility Scanner - Windows Batch Runner
REM Double-click this file to run all daily scans

echo ========================================
echo  Daily Forward Volatility Scanner
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Run the Python script (handles scans + copying to web folder)
python daily_run.py

REM Ignore exit code from daily_run.py (IB disconnect can cause seg fault)
REM The scans and file copies have already completed by then

REM Copy any additional files that might have been missed
echo.
echo Ensuring all results are copied to web...
copy /Y *_results_latest.json "..\forward-volatility-web\public\data\" 2>nul
copy /Y *_iv_rankings_latest.json "..\forward-volatility-web\public\data\" 2>nul
copy /Y trades.json "..\forward-volatility-web\public\data\" 2>nul

REM Copy earnings crush from EarningsCrush folder
if exist "..\..\EarningsCrush\earnings-crush-calculator\earnings_crush_latest.json" (
    copy /Y "..\..\EarningsCrush\earnings-crush-calculator\earnings_crush_latest.json" "..\forward-volatility-web\public\data\" 2>nul
    copy /Y "..\..\EarningsCrush\earnings-crush-calculator\earnings_crush_latest.json" "..\forward-volatility-web\public\" 2>nul
    echo Copied earnings_crush_latest.json
)

REM Commit and push to deploy
echo.
echo Committing to Git...
cd ..\forward-volatility-web
git add -A
git commit -m "Daily scan update - %date%"
git push

REM Return to calculator directory
cd ..\forward-volatility-calculator

echo.
echo ========================================
echo  Execution Complete
echo  Website will update in ~2 minutes
echo ========================================
echo.
pause
