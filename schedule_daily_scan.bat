@echo on
REM Daily Forward Volatility Scanner - Task Scheduler Wrapper
REM This script runs the daily scanner using the venv Python directly

cd /d "C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator"

echo ======================================================================
echo Daily Forward Volatility Scanner - Task Scheduler
echo Started: %date% %time%
echo ======================================================================
echo.

REM Use FULL PATH to venv Python to prevent Windows py launcher interference
set PYTHON_EXE=C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\.venv\Scripts\python.exe

REM Disable Python launcher and ensure we use only venv Python
set PY_PYTHON=
set PYTHONHOME=
set PYTHONPATH=

REM Remove system Python from PATH for this session
set PATH=C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\.venv\Scripts;%SYSTEMROOT%\System32

echo Using Python: %PYTHON_EXE%
echo.

REM Run the daily scanner - output shows in window AND saves to log
"%PYTHON_EXE%" -u daily_run.py 2>&1 | powershell -Command "$input | Tee-Object -FilePath 'logs\scheduled_run.log' -Append"

echo.
echo ======================================================================
echo Scan completed: %date% %time%
echo ======================================================================
echo.
echo Window will close in 30 seconds...
timeout /t 30

exit /b 0
