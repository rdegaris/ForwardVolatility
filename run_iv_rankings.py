"""
Scan all tickers across all lists and rank by near-term IV
Uses the existing rank_tickers_by_iv functionality from scanner_ib
"""
import json
from datetime import datetime
from scanner_ib import IBScanner, rank_tickers_by_iv
from nasdaq100 import get_nasdaq_100_list
from midcap400 import get_midcap400_list, get_mag7
import time

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
    
    scanner = IBScanner(port=7497, check_earnings=False)
    
    if not scanner.connect():
        print("❌ Could not connect to Interactive Brokers")
        print("Make sure TWS or IB Gateway is running on port 7497")
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
        
        # Format results
        results = []
        for item in ranked:
            # Determine which universe this ticker belongs to
            ticker_universe = 'MAG7' if item['ticker'] in get_mag7() else \
                            'NASDAQ100' if item['ticker'] in get_nasdaq_100_list() else \
                            'MIDCAP400'
            
            result = {
                'ticker': item['ticker'],
                'price': item['price'],
                'iv': item['iv'],
                'expiry': item['expiry'],
                'dte': item['dte'],
                'ma_200': item.get('ma_200'),
                'above_ma_200': item.get('above_ma_200'),
                'universe': ticker_universe
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
        
        print(f"✅ Results saved to: {filename}")
        
        # Save latest file
        latest_filename = f"iv_rankings_{universe}_latest.json"
        with open(latest_filename, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        print(f"✅ Latest results saved to: {latest_filename}")
        
        # Print top 20
        print()
        print("=" * 80)
        print("TOP 20 BY IMPLIED VOLATILITY")
        print("=" * 80)
        print(f"{'Rank':<6} {'Ticker':<8} {'Price':<10} {'IV':<10} {'Universe':<12} {'Trend':<8}")
        print("-" * 80)
        
        for i, r in enumerate(results[:20], 1):
            trend = "↑ ABOVE" if r.get('above_ma_200') else "↓ BELOW" if r.get('above_ma_200') is not None else "-"
            print(f"{i:<6} {r['ticker']:<8} ${r['price']:<9.2f} {r['iv']:<9.1f}% {r['universe']:<12} {trend:<8}")
        
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
