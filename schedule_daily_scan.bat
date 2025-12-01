@echo on
REM Daily Forward Volatility Scanner - Task Scheduler Wrapper
REM This script runs the daily scanner using the venv Python directly

echo ======================================================================
echo Daily Forward Volatility Scanner - Task Scheduler
echo Started: %date% %time%
echo ======================================================================
echo.

cd /d "C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator"
if errorlevel 1 (
    echo ERROR: Failed to change directory
    pause
    exit /b 1
)

echo Current directory: %CD%
echo.

REM Use FULL PATH to venv Python to prevent Windows py launcher interference
set PYTHON_EXE=C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\.venv\Scripts\python.exe

REM Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python not found at %PYTHON_EXE%
    pause
    exit /b 1
)

REM Disable Python launcher and ensure we use only venv Python
set PY_PYTHON=
set PYTHONHOME=
set PYTHONPATH=

REM Remove system Python from PATH for this session
set PATH=C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\.venv\Scripts;%SYSTEMROOT%\System32

echo Using Python: %PYTHON_EXE%
echo.

REM Run the daily scanner with unbuffered output
echo Starting daily_run.py...
echo.
"%PYTHON_EXE%" -u daily_run.py
set EXITCODE=%errorlevel%

echo.
echo ======================================================================
if %EXITCODE% == 0 (
    echo Scan completed successfully: %date% %time%
) else (
    echo Scan FAILED with exit code: %EXITCODE%
)
echo ======================================================================
echo.
echo Press any key to close this window...
pause
exit /b %EXITCODE%
