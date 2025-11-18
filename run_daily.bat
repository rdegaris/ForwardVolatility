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

REM Copy results to web public folder
echo.
echo Copying scan results to web...
copy /Y *_results_latest.json "..\forward-volatility-web\public\data\"
copy /Y *_iv_rankings_latest.json "..\forward-volatility-web\public\data\"
copy /Y trades.json "..\forward-volatility-web\public\data\"

REM Commit and push to deploy
echo.
echo Committing to Git...
cd ..\forward-volatility-web
git add public\data\*.json
git commit -m "Update scan results and IB positions - %date%"
git push
cd ..\forward-volatility-calculator

echo.
echo ========================================
echo  Execution Complete
echo  Website will update in ~2 minutes
echo ========================================
echo.
pause
