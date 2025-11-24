# Task Scheduler Fix - Prevent Window Closing

## Problem
The scheduled task window closes immediately, sending KeyboardInterrupt to Python and killing the scan.

## Solution

### Update Task Scheduler Settings:

1. Open **Task Scheduler**
2. Find your "Daily Forward Volatility Scanner" task
3. Right-click → **Properties**

4. **General Tab:**
   - ✅ Check "Run whether user is logged on or not"
   - ✅ Check "Run with highest privileges"
   - ✅ Check "Hidden" (prevents window from showing)

5. **Actions Tab:**
   - Program/script: `cmd.exe`
   - Add arguments: `/c "C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator\schedule_daily_scan.bat"`
   - Start in: `C:\Ryan\CTA Business\Forward Volatility\forward-volatility-calculator`

6. **Settings Tab:**
   - ✅ UNcheck "Stop the task if it runs longer than: 3 days"
   - ✅ Check "If the task is already running, then the following rule applies: Do not start a new instance"

7. Click **OK** and enter your Windows password when prompted

## Why This Works
- "Hidden" prevents the console window from appearing (no window = no CTRL+C)
- Output redirects to `logs\scheduled_run.log` instead of console
- Task runs in background without user interaction
- No timeout limit (scans take 1-1.5 hours)

## Testing
Run manually: Right-click task → **Run**
Check logs: `logs\scheduled_run.log` and `logs\daily_run_*.log`
