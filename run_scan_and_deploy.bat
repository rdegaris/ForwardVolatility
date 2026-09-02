@echo off
echo =======================================================
echo   OzCTA Futures & Paper Trading Scanner Suite
echo =======================================================
echo.

cd /d "%~dp0..\forward-volatility-web"

echo Running Daily Futures Strategy Scan and Paper Trades Update...
python scripts\daily_futures_scan.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Scanner script failed with error %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Syncing to GitHub repository...
git add public\data\*.json
git commit -m "Auto-update daily futures signals & paper trades [skip ci]"
git pull --rebase origin main
git push origin main

echo.
echo =======================================================
echo   Scan & Paper Trading Update Deployed Successfully!
echo =======================================================
pause
