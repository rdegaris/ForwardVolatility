"""
Daily Forward Volatility Scanner - Master Script

Runs all daily scans and syncs with IB positions:
- NASDAQ 100 scanner  
- MidCap 400 scanner
- IB positions fetcher
- Upload results to web repositories

Usage:
    python daily_run.py                    # Run everything
    python daily_run.py --scans-only       # Run scans only (no IB)
    python daily_run.py --ib-only          # Fetch IB positions only
    python daily_run.py --nasdaq100        # Run NASDAQ100 only
    python daily_run.py --midcap400        # Run MidCap400 only
    python daily_run.py --no-upload        # Don't upload to web repos
"""

import subprocess
import sys
import os
import time
from datetime import datetime
import argparse
import json
import logging
from pathlib import Path

# Delay between IB scans to let TWS recover from rate limits
IB_SCAN_DELAY_SECONDS = 10


def get_venv_python():
    """Get the venv Python executable, handling Task Scheduler context.
    
    When running from Task Scheduler, sys.executable may return the system Python
    even if the script was launched with the venv Python. This function explicitly
    looks for the venv Python in the script's directory.
    """
    script_dir = Path(__file__).parent.resolve()  # Use resolve() for absolute path
    venv_python = script_dir / '.venv' / 'Scripts' / 'python.exe'
    
    if venv_python.exists():
        result = str(venv_python)
        print(f"[DEBUG] Using venv Python: {result}")
        return result
    
    # Fallback to sys.executable if venv not found
    print(f"[DEBUG] Venv not found at {venv_python}, using sys.executable: {sys.executable}")
    return sys.executable


# Use venv Python for all subprocess calls
PYTHON_EXE = get_venv_python()


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(message):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")


def print_section(message):
    """Print formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}> {message}{Colors.END}")
    print(f"{Colors.BLUE}{'-' * 70}{Colors.END}")


def print_success(message):
    """Print success message."""
    print(f"{Colors.GREEN}[OK] {message}{Colors.END}")


def print_error(message):
    """Print error message."""
    print(f"{Colors.RED}[FAILED] {message}{Colors.END}")


def print_warning(message):
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARNING] {message}{Colors.END}")


def print_info(message):
    """Print info message."""
    print(f"{Colors.CYAN}[INFO] {message}{Colors.END}")


def run_command(command, description):
    """
    Run a shell command and return success status.
    Streams output in real-time for visibility.
    
    Args:
        command: Command to run (string or list)
        description: Description of what's being run
    
    Returns:
        True if successful, False otherwise
    """
    print_info(f"Running: {description}")
    sys.stdout.flush()
    
    try:
        # Use Popen to stream output in real-time
        if isinstance(command, str):
            process = subprocess.Popen(
                command, 
                shell=True, 
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                bufsize=1,  # Line buffered
            )
        else:
            process = subprocess.Popen(
                command, 
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                bufsize=1,  # Line buffered
            )
        
        # Stream output line by line in real-time
        output_lines = []
        for line in process.stdout:
            print(line, end='', flush=True)  # Print immediately
            output_lines.append(line)
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code == 0:
            print_success(f"Completed: {description}")
            return True
        else:
            print_error(f"Failed: {description} (exit code: {return_code})")
            return False
    
    except KeyboardInterrupt:
        print_warning(f"Interrupted: {description}")
        return False
    except Exception as e:
        print_error(f"Exception running {description}: {e}")
        import traceback
        traceback.print_exc()
        return False


def wait_for_ib_recovery(seconds=None):
    """Wait between scans to let IB recover from rate limits."""
    delay = seconds or IB_SCAN_DELAY_SECONDS
    print_info(f"Waiting {delay}s for IB to recover...")
    time.sleep(delay)


def run_mag7_scan():
    """Run MAG7 scanner."""
    print_section("Running MAG7 Scanner")
    return run_command(
        [PYTHON_EXE, "-u", "run_mag7_scan.py"],
        "MAG7 scan"
    )


def run_nasdaq100_scan():
    """Run NASDAQ 100 scanner."""
    print_section("Running NASDAQ 100 Scanner")
    return run_command(
        [PYTHON_EXE, "-u", "run_nasdaq100_scan.py"],
        "NASDAQ 100 scan"
    )


def run_midcap400_scan():
    """Run MidCap 400 scanner."""
    print_section("Running MidCap 400 Scanner")
    return run_command(
        [PYTHON_EXE, "-u", "run_midcap400_scan.py"],
        "MidCap 400 scan"
    )


def run_iv_rankings_scan():
    """Run IV Rankings scanner for all universes."""
    print_section("Running IV Rankings Scanner")
    
    # Run for each universe - results go into separate files
    success_count = 0
    
    for i, universe in enumerate(['nasdaq100', 'midcap400']):
        if i > 0:
            # Add delay between universes to let IB recover
            wait_for_ib_recovery(5)
        
        print_info(f"Scanning {universe} for IV rankings...")
        result = run_command(
            [PYTHON_EXE, "-u", "run_iv_rankings.py", universe],
            f"IV Rankings scan ({universe})"
        )
        if result:
            success_count += 1
    
    # Return True if at least one succeeded
    return success_count > 0


def run_earnings_crush_scan():
    """Run Earnings Crush scanner using IB."""
    print_section("Running Earnings Crush Scanner")
    
    # Path to earnings crush calculator
    earnings_crush_path = Path(__file__).parent.parent.parent / 'EarningsCrush' / 'earnings-crush-calculator'
    
    if not earnings_crush_path.exists():
        print_warning("Earnings crush calculator not found, skipping")
        return False
    
    # Use IB-based scanner (uses Finnhub for earnings, IB for all pricing)
    scan_script = earnings_crush_path / 'run_earnings_scan_ib.py'
    
    if not scan_script.exists():
        print_warning(f"run_earnings_scan_ib.py not found in {earnings_crush_path}, skipping")
        return False
    
    # Run the earnings crush scan
    success = run_command(
        [PYTHON_EXE, "-u", str(scan_script)],
        "Earnings Crush scan (Finnhub + IB)"
    )
    
    return success


def fetch_ib_positions():
    """Fetch IB positions and export to JSON."""
    print_section("Fetching IB Positions")
    
    # Check if IB connection scripts exist
    if not os.path.exists("fetch_ib_positions.py"):
        print_warning("fetch_ib_positions.py not found, skipping IB sync")
        return False
    
    success = run_command(
        [PYTHON_EXE, "-u", "fetch_ib_positions.py"],
        "IB positions fetch"
    )
    
    if success and os.path.exists("trades.json"):
        print_success(f"IB positions exported to trades.json")
        
        # Show summary
        try:
            with open("trades.json", 'r') as f:
                trades = json.load(f)
            print_info(f"Found {len(trades)} calendar spread positions")
            for trade in trades:
                pnl = ((trade['backCurrentPrice'] - trade['backEntryPrice']) - 
                       (trade['frontCurrentPrice'] - trade['frontEntryPrice'])) * trade['quantity'] * 100
                print(f"  • {trade['quantity']}x {trade['symbol']} ${trade['strike']} {trade['callOrPut']} - P&L: ${pnl:.2f}")
        except:
            pass
    
    return success


def upload_to_web_repos():
    """Upload scan results to web repositories."""
    print_section("Uploading Results to Web Repositories")
    
    # Check if web repo exists
    web_path = os.path.join("..", "forward-volatility-web", "public", "data")
    
    if not os.path.exists(web_path):
        print_warning(f"Web repo path not found: {web_path}")
        print_info("Skipping upload - make sure forward-volatility-web is in parent directory")
        return False
    
    # Copy latest scan results (copy whatever exists, even if some scans failed)
    files_to_copy = [
        ("nasdaq100_results_latest.json", "nasdaq100_results_latest.json"),
        ("midcap400_results_latest.json", "midcap400_results_latest.json"),
        ("nasdaq100_iv_rankings_latest.json", "nasdaq100_iv_rankings_latest.json"),
        ("midcap400_iv_rankings_latest.json", "midcap400_iv_rankings_latest.json"),
        ("mag7_iv_rankings_latest.json", "mag7_iv_rankings_latest.json"),
        ("trades.json", "trades.json"),
    ]
    
    # Also copy earnings crush results if they exist
    earnings_crush_path = Path(__file__).parent.parent.parent / 'EarningsCrush' / 'earnings-crush-calculator'
    if earnings_crush_path.exists():
        earnings_results = earnings_crush_path / 'earnings_crush_latest.json'
        if earnings_results.exists():
            # Copy to both locations: /data/ for Home page and root for EarningsCrush page
            files_to_copy.append((str(earnings_results), "earnings_crush_latest.json"))
    
    copied = 0
    for src, dst in files_to_copy:
        if os.path.exists(src):
            try:
                import shutil
                # Copy to /data/ directory
                dst_path = os.path.join(web_path, dst)
                shutil.copy2(src, dst_path)
                print_success(f"Copied {src} -> data/{dst}")
                copied += 1
                
                # Also copy earnings_crush_latest.json to root public folder for EarningsCrush page
                if dst == "earnings_crush_latest.json":
                    root_dst = os.path.join(web_path, "..", dst)
                    shutil.copy2(src, root_dst)
                    print_success(f"Copied {src} -> {dst} (root)")
                    
            except Exception as e:
                print_error(f"Failed to copy {src}: {e}")
    
    if copied > 0:
        print_info(f"Copied {copied} result files to web repo")
        
        # Git commit and push automatically
        try:
            import subprocess
            web_repo = os.path.join("..", "forward-volatility-web")
            
            # Stage all changes
            subprocess.run(["git", "add", "-A"], cwd=web_repo, check=True, capture_output=True)
            
            # Check if there are changes to commit
            result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=web_repo, capture_output=True)
            
            if result.returncode != 0:  # There are staged changes
                # Commit
                commit_msg = f"Daily scan update - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=web_repo, check=True, capture_output=True)
                print_success(f"Committed: {commit_msg}")
                
                # Push
                subprocess.run(["git", "push"], cwd=web_repo, check=True, capture_output=True)
                print_success("Pushed to GitHub - Vercel will deploy")
            else:
                print_info("No changes to commit")
        except Exception as e:
            print_warning(f"Git commit/push failed: {e}")
            print_info("Files were copied but not committed - commit manually if needed")
        
        return True
    else:
        print_warning("No scan result files found to copy")
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Daily Forward Volatility Scanner - Run all scans and IB sync"
    )
    parser.add_argument('--scans-only', action='store_true', help='Run scans only (skip IB)')
    parser.add_argument('--ib-only', action='store_true', help='Fetch IB positions only (skip scans)')
    parser.add_argument('--nasdaq100', action='store_true', help='Run NASDAQ100 scanner only')
    parser.add_argument('--midcap400', action='store_true', help='Run MidCap400 scanner only')
    parser.add_argument('--earnings-crush', action='store_true', help='Run Earnings Crush scanner only')
    parser.add_argument('--no-upload', action='store_true', help='Skip uploading to web repos')
    
    args = parser.parse_args()
    
    # Setup logging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"daily_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info("="*70)
    logging.info(f"Daily Forward Volatility Scanner Started")
    logging.info(f"Log file: {log_file}")
    logging.info("="*70)
    
    # Print header
    print_header(f"Daily Forward Volatility Scanner - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'mag7': None,
        'nasdaq100': None,
        'midcap400': None,
        'iv_rankings': None,
        'earnings_crush': None,
        'ib_positions': None,
        'upload': None
    }
    
    # Determine what to run
    run_all = not any([args.scans_only, args.ib_only, args.nasdaq100, args.midcap400, args.earnings_crush])
    
    # Run scans in priority order:
    # 1. Portfolio (IB positions) - most important, fast
    # 2. Earnings Crush - time-sensitive
    # 3. IV Rankings - useful for analysis
    # 4. NASDAQ 100 - main scanner
    # 5. MidCap 400 - largest, most likely to fail
    
    if args.ib_only:
        results['ib_positions'] = fetch_ib_positions()
    elif args.nasdaq100:
        results['nasdaq100'] = run_nasdaq100_scan()
    elif args.midcap400:
        results['midcap400'] = run_midcap400_scan()
    elif args.earnings_crush:
        results['earnings_crush'] = run_earnings_crush_scan()
    elif args.scans_only or run_all:
        # Run in priority order - portfolio first, midcap last
        # Add delays between IB scans to prevent rate limiting
        
        results['ib_positions'] = fetch_ib_positions()
        wait_for_ib_recovery(5)  # Short delay after positions
        
        results['earnings_crush'] = run_earnings_crush_scan()
        wait_for_ib_recovery()  # Full delay after earnings crush
        
        results['iv_rankings'] = run_iv_rankings_scan()
        wait_for_ib_recovery()  # Full delay after IV rankings
        
        results['nasdaq100'] = run_nasdaq100_scan()
        wait_for_ib_recovery()  # Full delay after NASDAQ100
        
        results['midcap400'] = run_midcap400_scan()
        # No delay needed after last scan
    
    # ALWAYS upload to web repos (even if some scans failed)
    if not args.no_upload and not args.ib_only:
        results['upload'] = upload_to_web_repos()
    
    # Print summary
    print_header("Execution Summary")
    
    summary_items = []
    if results['ib_positions'] is not None:
        summary_items.append(('IB Positions Fetch', results['ib_positions']))
    if results['earnings_crush'] is not None:
        summary_items.append(('Earnings Crush Scan', results['earnings_crush']))
    if results['iv_rankings'] is not None:
        summary_items.append(('IV Rankings Scan', results['iv_rankings']))
    if results['nasdaq100'] is not None:
        summary_items.append(('NASDAQ 100 Scan', results['nasdaq100']))
    if results['midcap400'] is not None:
        summary_items.append(('MidCap 400 Scan', results['midcap400']))
    if results['upload'] is not None:
        summary_items.append(('Web Upload', results['upload']))
    
    for name, success in summary_items:
        if success:
            print_success(f"{name}: Success")
        elif success is False:
            print_error(f"{name}: Failed")
        else:
            print_info(f"{name}: Skipped")
    
    # Overall status
    failures = sum(1 for _, success in summary_items if success is False)
    successes = sum(1 for _, success in summary_items if success is True)
    
    print()
    if failures == 0 and successes > 0:
        print_success(f"All {successes} tasks completed successfully!")
    elif failures > 0:
        print_warning(f"{successes} succeeded, {failures} failed")
    else:
        print_info("No tasks were executed")
    
    print(f"\n{Colors.BOLD}Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")
    
    logging.info("="*70)
    logging.info(f"Daily run completed - {successes} succeeded, {failures} failed")
    logging.info(f"Log saved to: {log_file}")
    logging.info("="*70)
    
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
