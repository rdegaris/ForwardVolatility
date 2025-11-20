# Daily Scanner Scheduling Guide

## Option 1: Windows Task Scheduler (Recommended)

### Setup Instructions:

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create a New Task**
   - Click "Create Task" (not "Create Basic Task")
   - Name: `Forward Volatility Daily Scan`
   - Description: `Run daily options scanner and upload results`
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"

3. **Triggers Tab**
   - Click "New..."
   - Begin the task: `On a schedule`
   - Settings: `Daily`
   - Start: Choose your preferred time (e.g., `9:00 AM` after market open)
   - Recur every: `1 days`
   - Enabled: Check this box
   - Click "OK"

4. **Actions Tab**
   - Click "New..."
   - Action: `Start a program`
   - Program/script: `C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\schedule_daily_scan.bat`
   - Click "OK"

5. **Conditions Tab**
   - Uncheck "Start the task only if the computer is on AC power"
   - Check "Wake the computer to run this task" (if you want it to wake from sleep)

6. **Settings Tab**
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
   - If the task fails, restart every: `10 minutes`, Attempt to restart up to: `3 times`

7. **Save the Task**
   - Click "OK"
   - Enter your Windows password if prompted

### Test the Task:
- Right-click the task in Task Scheduler
- Click "Run"
- Monitor the task to ensure it completes successfully

---

## Option 2: Python Scheduler Script

If you prefer a Python-based scheduler that runs continuously:

1. Install schedule package:
   ```bash
   pip install schedule
   ```

2. Create a scheduler script (already created as `run_scheduler.py`)

3. Run it in the background or set up as a Windows service

---

## Option 3: Desktop Shortcuts (Manual)

Use the existing desktop shortcuts created earlier:
- **Daily Scanner** - Runs full daily scan
- **Scans Only** - Runs just the scans (no IB sync)

Double-click to run manually each day.

---

## Recommended Schedule

**Best time to run:** 
- **9:30 AM - 10:00 AM PST** (after market open, when IB data is fresh)
- Alternatively: **4:00 PM - 5:00 PM PST** (after market close, for next-day prep)

**Important:**
- Ensure IB Gateway or TWS is running before the scheduled time
- Set IB Gateway to auto-start and auto-login
- The scanner takes 20-30 minutes to complete
- Results automatically deploy to AWS Amplify via Git push

---

## Monitoring

Check the log files in `logs/` directory:
- `daily_run_YYYYMMDD_HHMMSS.log` - Full execution logs
- Review for any errors or failed scans

---

## IB Gateway Auto-Start

To fully automate, set up IB Gateway to start automatically:

1. Create a batch file `start_ib_gateway.bat`:
   ```batch
   @echo off
   start "" "C:\Jts\ibgateway\1037\ibgateway.exe"
   ```

2. Add to Windows Startup folder:
   - Press `Win + R`, type `shell:startup`, press Enter
   - Create shortcut to `start_ib_gateway.bat`

3. Configure IB Gateway:
   - Settings > API > Settings
   - Enable "Read-Only API"
   - Socket port: 7497 (paper) or 7496 (live)
   - Auto-restart: 24:00
   - Check "Bypass Order Precautions for API Orders"

---

## Troubleshooting

**Scanner doesn't run:**
- Check Task Scheduler History tab
- Verify IB Gateway is running
- Check that Python virtual environment path is correct
- Review log files in `logs/` directory

**Results don't deploy:**
- Verify Git credentials are saved
- Check internet connection
- Manually run `git push` to test

**Partial scan completion:**
- Some tickers may fail due to IB data issues (normal)
- Scanner will continue with available data
- Check logs for specific errors
