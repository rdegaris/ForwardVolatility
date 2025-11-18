@echo off
REM Run scans only (no IB positions)
python daily_run.py --scans-only

REM Copy results to web public folder
echo.
echo Copying scan results to web...
copy /Y *_results_latest.json "..\forward-volatility-web\public\data\"
copy /Y *_iv_rankings_latest.json "..\forward-volatility-web\public\data\"

REM Commit and push to deploy
echo.
echo Committing to Git...
cd ..\forward-volatility-web
git add public\data\*.json
git commit -m "Update scan results - %date%"
git push
cd ..\forward-volatility-calculator

echo.
echo Done! Website will update in ~2 minutes.
pause
