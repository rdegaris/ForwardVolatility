"""
Batch scan module for scanning multiple tickers with IV ranking support.
"""
import pandas as pd
import time
from scanner_ib import IBScanner, rank_tickers_by_iv


def batch_scan(tickers, threshold=0.2, rank_by_iv=True, top_n_iv=None):
    """
    Scan a list of tickers for forward volatility opportunities.
    
    Args:
        tickers: List of ticker symbols to scan
        threshold: FF threshold (default 0.2)
        rank_by_iv: Pre-rank by near-term IV (default True)
        top_n_iv: If ranking, scan top N tickers (default None = scan all)
    
    Returns:
        DataFrame with opportunities, or None if no opportunities found
    """
    
    scanner = IBScanner(port=7498, check_earnings=True)
    
    if not scanner.connect():
        print("Could not connect to Interactive Brokers")
        print("Make sure TWS or IB Gateway is running on port 7498")
        return None
    
    try:
        # Pre-fetch earnings dates for all tickers from IB
        if scanner.earnings_checker:
            print("Pre-fetching earnings dates from Interactive Brokers...")
            for ticker in tickers:
                scanner.earnings_checker.get_earnings_date(ticker)
            print()
        
        # If ranking by IV, get top N tickers
        tickers_to_scan = tickers
        if rank_by_iv:
            print(f"Ranking {len(tickers)} tickers by near-term IV...")
            ranked = rank_tickers_by_iv(scanner, tickers, top_n=top_n_iv)
            if ranked:
                tickers_to_scan = [ticker for ticker, iv, price in ranked]
                if top_n_iv:
                    print(f"Scanning top {len(tickers_to_scan)} by IV (from {len(tickers)} total)")
                else:
                    print(f"Scanning all {len(tickers_to_scan)} tickers (sorted by IV)")
            print()
        
        all_opportunities = []
        
        for i, ticker in enumerate(tickers_to_scan, 1):
            start_time = time.time()
            print(f"[{i}/{len(tickers_to_scan)}] {ticker}...")
            
            try:
                opportunities = scanner.scan_ticker(ticker, threshold=threshold)
                
                elapsed = time.time() - start_time
                if opportunities:
                    all_opportunities.extend(opportunities)
                    print(f"  Found {len(opportunities)} opportunity(ies) ({elapsed:.1f}s)")
                else:
                    print(f"  No opportunities ({elapsed:.1f}s)")
                
                # Rate limiting between tickers
                if i < len(tickers_to_scan):
                    time.sleep(1)
                    
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        print()
        print("=" * 80)
        print("SCAN COMPLETE")
        print("=" * 80)
        print(f"Total opportunities: {len(all_opportunities)}")
        
        if all_opportunities:
            df = pd.DataFrame(all_opportunities)
            
            # Calculate best FF (max of call, put, or avg)
            df['best_ff'] = df[['ff_avg', 'ff_call', 'ff_put']].max(axis=1)
            
            # Sort by best FF descending
            df = df.sort_values('best_ff', ascending=False)
            
            print(f"Best FF: {df['best_ff'].max():.3f}")
            print(f"Average FF: {df['best_ff'].mean():.3f}")
            print("=" * 80)
            
            return df
        else:
            return None
            
    finally:
        scanner.disconnect()
