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

REM ALWAYS copy files to web folder (even if scans had errors)
echo.
echo ========================================
echo  Copying results to web folder...
echo ========================================

REM Copy scan results from calculator folder
copy /Y nasdaq100_results_latest.json "..\forward-volatility-web\public\data\" 2>nul && echo   Copied nasdaq100_results_latest.json
copy /Y midcap400_results_latest.json "..\forward-volatility-web\public\data\" 2>nul && echo   Copied midcap400_results_latest.json
copy /Y nasdaq100_iv_rankings_latest.json "..\forward-volatility-web\public\data\" 2>nul && echo   Copied nasdaq100_iv_rankings_latest.json
copy /Y midcap400_iv_rankings_latest.json "..\forward-volatility-web\public\data\" 2>nul && echo   Copied midcap400_iv_rankings_latest.json
copy /Y mag7_iv_rankings_latest.json "..\forward-volatility-web\public\data\" 2>nul && echo   Copied mag7_iv_rankings_latest.json
copy /Y trades.json "..\forward-volatility-web\public\data\" 2>nul && echo   Copied trades.json

REM Copy earnings crush from EarningsCrush folder (NOT from calculator folder)
if exist "..\..\EarningsCrush\earnings-crush-calculator\earnings_crush_latest.json" (
    copy /Y "..\..\EarningsCrush\earnings-crush-calculator\earnings_crush_latest.json" "..\forward-volatility-web\public\data\" 2>nul
    copy /Y "..\..\EarningsCrush\earnings-crush-calculator\earnings_crush_latest.json" "..\forward-volatility-web\public\" 2>nul
    echo   Copied earnings_crush_latest.json
)

REM ALWAYS commit and push to deploy (even if some scans failed)
echo.
echo ========================================
echo  Committing and pushing to Git...
echo ========================================
cd ..\forward-volatility-web
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Daily scan update - %date%"
    git push
    echo   Pushed to GitHub - Vercel will deploy
) else (
    echo   No changes to commit
)

REM Return to calculator directory
cd ..\forward-volatility-calculator

echo.
echo ========================================
echo  Execution Complete
echo  Website will update in ~2 minutes
echo ========================================
echo.
pause
