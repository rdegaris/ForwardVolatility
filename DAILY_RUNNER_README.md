# Daily Forward Volatility Scanner

Automated daily workflow to run all scans and sync with Interactive Brokers.

## 🚀 Quick Start

### Option 1: Double-Click (Easiest)
- **`run_daily.bat`** - Runs everything (all scans + IB sync)
- **`run_scans_only.bat`** - Runs all scans without IB
- **`run_ib_sync.bat`** - Fetches IB positions only

### Option 2: Command Line

```bash
# Run everything (recommended daily use)
python daily_run.py

# Run specific scans
python daily_run.py --mag7           # MAG7 only
python daily_run.py --nasdaq100      # NASDAQ 100 only
python daily_run.py --midcap400      # MidCap 400 only

# Run all scans without IB sync
python daily_run.py --scans-only

# Fetch IB positions only
python daily_run.py --ib-only

# Run without uploading to web repo
python daily_run.py --no-upload
```

## 📋 What It Does

### 1. **Runs All Scanners**
- MAG7 Scanner (`run_mag7_scan.py`)
- NASDAQ 100 Scanner (`run_nasdaq100_scan.py`)
- MidCap 400 Scanner (`run_midcap400_scan.py`)

Each scanner:
- Fetches current market data
- Calculates forward volatility and forward factors
- Identifies calendar spread opportunities
- Saves results to JSON files

### 2. **Fetches IB Positions** (if IB is running)
- Connects to Interactive Brokers TWS/Gateway
- Retrieves open calendar spread positions
- Gets current prices and calculates P&L
- Exports to `trades.json`

### 3. **Uploads to Web**
- Copies scan results to web app's public data folder
- Makes results available on the website
- You can then commit and push the web repo

## 📊 Output Files

After running, you'll have:
- `scan_results_latest.json` - MAG7 results
- `nasdaq100_results_latest.json` - NASDAQ 100 results  
- `midcap400_results_latest.json` - MidCap 400 results
- `trades.json` - IB calendar spread positions (if IB sync ran)
- `logs/daily_run_YYYYMMDD_HHMMSS.log` - Execution log

## 📝 Logs

All executions are logged to the `logs/` folder with timestamps:
- What was run
- Success/failure status
- Any errors encountered
- Execution time

Example: `logs/daily_run_20251111_143000.log`

## ⚙️ Configuration

### Interactive Brokers Setup
Make sure TWS or IB Gateway is running:
- Paper Trading: Port 7497 (TWS) or 4002 (Gateway)
- Live Trading: Port 7496 (TWS) or 4001 (Gateway)

Edit `fetch_ib_positions.py` if you need to change the port.

### Web Upload Path
The script expects the web repo at:
```
forward-volatility-calculator/
forward-volatility-web/
```

If your folder structure is different, update the path in `daily_run.py`.

## 🔄 Daily Workflow

### Recommended Schedule

**Morning (Market Open):**
```bash
run_daily.bat
```
This runs all scans and fetches your current IB positions.

**Afternoon (Check for new opportunities):**
```bash
python daily_run.py --scans-only
```
Re-run scans to catch any new opportunities.

**Anytime (Quick IB sync):**
```bash
python daily_run.py --ib-only
```
Update your positions without re-running scans.

## 📈 Web Integration

After running the daily script:

1. **Results are automatically copied** to the web repo
2. **Go to the web repo:**
   ```bash
   cd ../forward-volatility-web
   ```
3. **Commit and push:**
   ```bash
   git add public/data/*.json
   git commit -m "Update scan results"
   git push
   ```
4. **Website updates automatically** (if hosted on GitHub Pages/Netlify/Vercel)

## 🛠️ Troubleshooting

### "Failed: IB positions fetch"
- Make sure TWS or IB Gateway is running
- Check that API connections are enabled
- Verify the port number (7497 for TWS paper)

### "Web repo path not found"
- Check that `forward-volatility-web` is in the parent directory
- Or update the path in `daily_run.py`

### "No option positions found"
- You don't have any open option positions
- Or the positions aren't calendar spreads

## 📅 Automation Options

### Windows Task Scheduler
Run automatically every day:

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Daily Forward Vol Scan"
4. Trigger: Daily at 9:35 AM (after market open)
5. Action: Start a program
6. Program: `C:\Path\To\run_daily.bat`

### Manual Execution
Just double-click `run_daily.bat` whenever you want fresh data!

## ✅ Example Output

```
======================================================================
     Daily Forward Volatility Scanner - 2025-11-11 14:30:00
======================================================================

▶ Running MAG7 Scanner
----------------------------------------------------------------------
ℹ Running: MAG7 scan
✓ Completed: MAG7 scan

▶ Running NASDAQ 100 Scanner
----------------------------------------------------------------------
ℹ Running: NASDAQ 100 scan
✓ Completed: NASDAQ 100 scan

▶ Running MidCap 400 Scanner
----------------------------------------------------------------------
ℹ Running: MidCap 400 scan
✓ Completed: MidCap 400 scan

▶ Fetching IB Positions
----------------------------------------------------------------------
ℹ Running: IB positions fetch
✓ Completed: IB positions fetch
✓ IB positions exported to trades.json
ℹ Found 2 calendar spread positions
  • 1x AMD $237.5 CALL - P&L: $35.00
  • 1x NVDA $145.0 CALL - P&L: -$12.50

▶ Uploading Results to Web Repositories
----------------------------------------------------------------------
✓ Copied scan_results_latest.json → mag7_results_latest.json
✓ Copied nasdaq100_results_latest.json → nasdaq100_results_latest.json
✓ Copied midcap400_results_latest.json → midcap400_results_latest.json
ℹ Copied 3 result files to web repo

======================================================================
                        Execution Summary
======================================================================
✓ MAG7 Scan: Success
✓ NASDAQ 100 Scan: Success
✓ MidCap 400 Scan: Success
✓ IB Positions Fetch: Success
✓ Web Upload: Success

✓ All 5 tasks completed successfully!

Finished at 2025-11-11 14:35:23
```

## 🎯 Tips

- Run in the morning for fresh opportunities
- Check the logs if something fails
- Use `--scans-only` during market hours for speed
- Use `--ib-only` to quickly update your positions
- The web upload is automatic, just commit and push afterward!
