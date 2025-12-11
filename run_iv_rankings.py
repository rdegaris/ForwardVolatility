"""
Scan all tickers across all lists and rank by near-term IV
Uses the existing rank_tickers_by_iv functionality from scanner_ib
"""
import json
from datetime import datetime, timedelta
from scanner_ib import IBScanner, rank_tickers_by_iv
from nasdaq100 import get_nasdaq_100_list
from midcap400 import get_midcap400_list, get_mag7
from earnings_checker import EarningsChecker
import time

# Days after earnings to exclude (IV already crushed)
DAYS_AFTER_EARNINGS_EXCLUDE = 3
# Days before earnings to exclude (IV elevated due to upcoming event)  
DAYS_BEFORE_EARNINGS_EXCLUDE = 7

def load_earnings_from_scans():
    """Load earnings dates from main scan result files."""
    earnings_map = {}
    
    for filename in ['nasdaq100_results_latest.json', 'midcap400_results_latest.json', 'mag7_results_latest.json']:
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                for opp in data.get('opportunities', []):
                    ticker = opp.get('ticker')
                    earnings = opp.get('next_earnings')
                    if ticker and earnings:
                        earnings_map[ticker] = earnings
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")
    
    return earnings_map

def scan_iv_rankings(universe='all', top_n=None):
    """Scan tickers and rank by near-term implied volatility.
    
    Args:
        universe: Which universe to scan - 'mag7', 'nasdaq100', 'midcap400', or 'all'
        top_n: Number of results to return (None = all)
    
    Returns:
        List of tickers with their IV rankings
    """
    
    print("=" * 80)
    print("IMPLIED VOLATILITY RANKING SCANNER")
    print("=" * 80)
    print()
    
    # Determine which tickers to scan
    if universe == 'mag7':
        tickers = get_mag7()
        universe_name = "MAG7"
    elif universe == 'nasdaq100':
        tickers = get_nasdaq_100_list()
        universe_name = "NASDAQ 100"
    elif universe == 'midcap400':
        tickers = get_midcap400_list()
        universe_name = "S&P MidCap 400"
    else:  # 'all'
        tickers = list(set(get_mag7() + get_nasdaq_100_list() + get_midcap400_list()))
        universe_name = "ALL (MAG7 + NASDAQ 100 + MidCap 400)"
    
    print(f"Universe: {universe_name}")
    print(f"Total tickers: {len(tickers)}")
    if top_n:
        print(f"Returning top: {top_n}")
    print()
    
    scanner = IBScanner(port=7498, check_earnings=False)
    
    if not scanner.connect():
        print("❌ Could not connect to Interactive Brokers")
        print("Make sure TWS or IB Gateway is running on port 7498")
        return None
    
    try:
        # Use the existing rank_tickers_by_iv function
        ranked = rank_tickers_by_iv(scanner, tickers, top_n=top_n)
        
        if not ranked:
            print("❌ No tickers could be ranked")
            return None
        
        print()
        print("=" * 80)
        print("SCAN COMPLETE")
        print("=" * 80)
        print(f"Successfully ranked: {len(ranked)} tickers")
        print()
        
        # Load earnings dates from main scan results (no extra API calls)
        print("Loading earnings dates from scan results...")
        earnings_map = load_earnings_from_scans()
        print(f"Found earnings for {len(earnings_map)} tickers")
        
        # Filter out tickers with recent or upcoming earnings
        print(f"Filtering out tickers with earnings within {DAYS_AFTER_EARNINGS_EXCLUDE} days ago or {DAYS_BEFORE_EARNINGS_EXCLUDE} days ahead...")
        earnings_checker = EarningsChecker()
        today = datetime.now().date()
        filtered_ranked = []
        removed_count = 0
        
        for ticker, iv, price in ranked:
            # Check earnings date
            earnings_date = earnings_checker.get_earnings_date(ticker)
            if earnings_date:
                days_diff = (earnings_date - today).days
                if -DAYS_AFTER_EARNINGS_EXCLUDE <= days_diff <= DAYS_BEFORE_EARNINGS_EXCLUDE:
                    print(f"    ⚠️ Removing {ticker}: Earnings on {earnings_date} ({days_diff} days)")
                    removed_count += 1
                    continue
            filtered_ranked.append((ticker, iv, price))
        
        print(f"Removed {removed_count} tickers with earnings in window")
        ranked = filtered_ranked
        
        # Get 200MA data from scanner
        mag7_list = get_mag7()
        nasdaq100_list = get_nasdaq_100_list()
        
        # Format results - ranked is list of (ticker, iv, price) tuples
        results = []
        for ticker, iv, price in ranked:
            # Determine which universe this ticker belongs to
            ticker_universe = 'MAG7' if ticker in mag7_list else \
                            'NASDAQ100' if ticker in nasdaq100_list else \
                            'MIDCAP400'
            
            # Get next earnings date from pre-loaded scan results
            next_earnings = earnings_map.get(ticker)
            
            # Get 200MA (we don't have it from rank_tickers_by_iv, so set to None)
            result = {
                'ticker': ticker,
                'price': price,
                'iv': iv,
                'ma_200': None,
                'above_ma_200': None,
                'universe': ticker_universe,
                'next_earnings': next_earnings
            }
            results.append(result)
        
        # Create result object
        result_data = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'universe': universe_name,
            'total_scanned': len(results),
            'rankings': results,
            'summary': {
                'highest_iv': results[0]['iv'] if results else 0,
                'lowest_iv': results[-1]['iv'] if results else 0,
                'average_iv': round(sum(r['iv'] for r in results) / len(results), 2) if results else 0,
                'median_iv': results[len(results)//2]['iv'] if results else 0
            }
        }
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"iv_rankings_{universe}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        print(f"[OK] Results saved to: {filename}")
        
        # Save latest file
        latest_filename = f"iv_rankings_{universe}_latest.json"
        with open(latest_filename, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        print(f"[OK] Latest results saved to: {latest_filename}")
        
        # Print top 20
        print()
        print("=" * 80)
        print("TOP 20 BY IMPLIED VOLATILITY")
        print("=" * 80)
        print(f"{'Rank':<6} {'Ticker':<8} {'Price':<10} {'IV':<10} {'Earnings':<12} {'Trend':<8}")
        print("-" * 80)
        
        for i, r in enumerate(results[:20], 1):
            trend = "↑ ABOVE" if r.get('above_ma_200') else "↓ BELOW" if r.get('above_ma_200') is not None else "-"
            earnings = r.get('next_earnings', '-') or '-'
            print(f"{i:<6} {r['ticker']:<8} ${r['price']:<9.2f} {r['iv']:<9.1f}% {earnings:<12} {trend:<8}")
        
        print("=" * 80)
        
        return result_data
        
    finally:
        scanner.disconnect()
    
    return None


if __name__ == "__main__":
    import sys
    
    # Allow command line arguments for universe and top_n
    universe = sys.argv[1] if len(sys.argv) > 1 else 'all'
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if universe not in ['mag7', 'nasdaq100', 'midcap400', 'all']:
        print(f"Invalid universe: {universe}")
        print("Valid options: mag7, nasdaq100, midcap400, all")
        print("Usage: python run_iv_rankings.py [universe] [top_n]")
        sys.exit(1)
    
    scan_iv_rankings(universe=universe, top_n=top_n)
