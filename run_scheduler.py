"""
Python-based scheduler for daily scanner.
Alternative to Windows Task Scheduler - runs continuously and executes at specified time.

Usage:
    python run_scheduler.py

To run in background on Windows:
    pythonw run_scheduler.py
"""

import schedule
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_daily_scan():
    """Execute the daily scanner."""
    print(f"\n{'='*70}")
    print(f"Starting Daily Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    try:
        # Run the daily scanner
        result = subprocess.run(
            [sys.executable, "daily_run.py"],
            cwd=Path(__file__).parent,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\n✓ Daily scan completed successfully at {datetime.now().strftime('%H:%M:%S')}")
        else:
            print(f"\n✗ Daily scan failed with exit code {result.returncode}")
            
    except Exception as e:
        print(f"\n✗ Error running daily scan: {e}")


def main():
    """Main scheduler loop."""
    # Schedule the daily scan
    # Default: 9:30 AM PST (after market open)
    schedule.every().day.at("09:30").do(run_daily_scan)
    
    print("="*70)
    print("Forward Volatility Daily Scanner - Scheduler")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scheduled to run daily at: 09:30 PST")
    print("Press Ctrl+C to stop")
    print("="*70)
    print()
    
    # Optional: Run immediately on startup (uncomment if desired)
    # print("Running initial scan on startup...")
    # run_daily_scan()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")
        sys.exit(0)
