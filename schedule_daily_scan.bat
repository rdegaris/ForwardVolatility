@echo off
REM Daily Forward Volatility Scanner - Task Scheduler Wrapper
REM This script activates the virtual environment and runs the daily scanner

cd /d "C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Run the daily scanner (redirect output to log to prevent window issues)
python daily_run.py >> logs\scheduled_run.log 2>&1

REM Deactivate when done
deactivate

REM Exit cleanly
exit /b 0
