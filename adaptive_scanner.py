"""
Adaptive Single-Pass Scanner

Instead of two passes (get all IVs, then scan top N), this scanner:
1. Gets IV for each stock in a single pass
2. Uses adaptive threshold - scans stocks in the top percentile of IVs seen so far
3. Immediately scans for FF opportunities when IV qualifies
4. Shows real-time progress

This is faster and more efficient than the two-pass approach.
"""

import time
import bisect
from typing import List, Dict, Optional, Tuple
from scanner_ib import IBScanner, calculate_dte
import pandas as pd


# Reconnect to IB every N tickers to avoid memory buildup
RECONNECT_INTERVAL = 100  # Reconnect every 100 tickers


class AdaptiveScanner:
    """Single-pass adaptive IV scanner."""
    
    def __init__(self, scanner: IBScanner, 
                 min_iv_threshold: float = 30.0,
                 adaptive_percentile: float = 0.20,
                 ff_threshold: float = 0.2,
                 reconnect_interval: int = RECONNECT_INTERVAL):
        """
        Initialize adaptive scanner.
        
        Args:
            scanner: IBScanner instance (already connected)
            min_iv_threshold: Minimum IV to even consider (default 30%)
            adaptive_percentile: Scan stocks in top X percentile (default 0.20 = top 20%)
            ff_threshold: Forward Factor threshold for opportunities (default 0.2)
            reconnect_interval: Reconnect to IB every N tickers to avoid memory buildup
        """
        self.scanner = scanner
        self.min_iv_threshold = min_iv_threshold
        self.adaptive_percentile = adaptive_percentile
        self.ff_threshold = ff_threshold
        self.reconnect_interval = reconnect_interval
        
        # Track IVs for adaptive threshold
        self.iv_list = []  # Sorted list of IVs seen
        self.iv_data = []  # All (ticker, iv, price) tuples
        
        # Results
        self.opportunities = []
        self.skipped_low_iv = []
        self.scanned_tickers = []
        
        # Counter for reconnection
        self.tickers_since_reconnect = 0
    
    def get_adaptive_threshold(self) -> float:
        """
        Get current adaptive IV threshold based on IVs seen so far.
        
        Returns the IV at the (1 - adaptive_percentile) percentile.
        E.g., with adaptive_percentile=0.20, returns IV at 80th percentile
        (meaning top 20% of stocks qualify).
        """
        if len(self.iv_list) < 5:
            # Not enough data yet, use minimum threshold
            return self.min_iv_threshold
        
        # Find the IV at the cutoff percentile
        cutoff_index = int(len(self.iv_list) * (1 - self.adaptive_percentile))
        cutoff_index = max(0, min(cutoff_index, len(self.iv_list) - 1))
        
        adaptive_threshold = self.iv_list[cutoff_index]
        
        # Never go below minimum threshold
        return max(adaptive_threshold, self.min_iv_threshold)
    
    def should_scan(self, iv: float) -> Tuple[bool, str]:
        """
        Determine if a stock with given IV should be scanned for FF opportunities.
        
        Returns:
            Tuple of (should_scan, reason)
        """
        if iv < self.min_iv_threshold:
            return False, f"IV {iv:.1f}% below minimum {self.min_iv_threshold:.0f}%"
        
        adaptive_thresh = self.get_adaptive_threshold()
        
        if iv >= adaptive_thresh:
            return True, f"IV {iv:.1f}% >= adaptive threshold {adaptive_thresh:.1f}%"
        else:
            return False, f"IV {iv:.1f}% below adaptive threshold {adaptive_thresh:.1f}%"
    
    def scan_single_pass(self, tickers: List[str], verbose: bool = True) -> pd.DataFrame:
        """
        Single-pass scan: get IV and scan for FF opportunities in one pass.
        
        Args:
            tickers: List of ticker symbols
            verbose: Print detailed progress
        
        Returns:
            DataFrame of opportunities
        """
        total = len(tickers)
        scanned_count = 0
        skipped_count = 0
        
        print("\n" + "=" * 80)
        print("ADAPTIVE SINGLE-PASS SCANNER")
        print("=" * 80)
        print(f"Total tickers: {total}")
        print(f"Minimum IV threshold: {self.min_iv_threshold:.0f}%")
        print(f"Adaptive percentile: top {self.adaptive_percentile * 100:.0f}%")
        print(f"FF threshold: {self.ff_threshold}")
        print("=" * 80 + "\n")
        
        start_time = time.time()
        
        for i, ticker in enumerate(tickers, 1):
            ticker_start = time.time()
            
            # Periodic reconnection to avoid memory buildup
            self.tickers_since_reconnect += 1
            if self.tickers_since_reconnect >= self.reconnect_interval:
                print(f"\n[INFO] Reconnecting to IB to free memory ({i}/{total})...")
                try:
                    self.scanner.disconnect()
                    time.sleep(2)  # Wait for clean disconnect
                    if not self.scanner.connect():
                        print("[ERROR] Failed to reconnect to IB")
                        break
                    self.tickers_since_reconnect = 0
                    print(f"[OK] Reconnected successfully\n")
                except Exception as e:
                    print(f"[ERROR] Reconnection failed: {e}")
                    break
            
            # Get price first
            print(f"[{i}/{total}] {ticker}...", end=" ", flush=True)
            
            try:
                price = self.scanner.get_stock_price(ticker)
                if not price:
                    print("[SKIP] No price data")
                    continue
                
                # Get near-term IV
                iv = self.scanner.get_near_term_iv(ticker, price)
                if not iv:
                    print(f"${price:.2f} [SKIP] No IV data")
                    continue
                
                # Track IV for adaptive threshold
                bisect.insort(self.iv_list, iv)
                self.iv_data.append((ticker, iv, price))
                
                # Check if should scan
                should_scan, reason = self.should_scan(iv)
                
                if should_scan:
                    print(f"${price:.2f} IV:{iv:.1f}% [SCANNING]", flush=True)
                    
                    # Scan for FF opportunities
                    opps = self.scanner.scan_ticker(ticker, threshold=self.ff_threshold)
                    
                    if opps:
                        self.opportunities.extend(opps)
                        print(f"    -> FOUND {len(opps)} opportunity(ies)!", flush=True)
                    else:
                        print(f"    -> No FF opportunities", flush=True)
                    
                    self.scanned_tickers.append((ticker, iv, price))
                    scanned_count += 1
                else:
                    elapsed = time.time() - ticker_start
                    print(f"${price:.2f} IV:{iv:.1f}% [SKIP] {reason} ({elapsed:.1f}s)")
                    self.skipped_low_iv.append((ticker, iv, price))
                    skipped_count += 1
                
                # Brief pause to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[ERROR] {e}")
                continue
        
        total_time = time.time() - start_time
        
        # Print summary
        print("\n" + "=" * 80)
        print("SCAN COMPLETE")
        print("=" * 80)
        print(f"Total time: {total_time:.1f}s ({total_time/total:.1f}s per ticker)")
        print(f"Tickers processed: {len(self.iv_data)}/{total}")
        print(f"Tickers scanned for FF: {scanned_count}")
        print(f"Tickers skipped (low IV): {skipped_count}")
        print(f"Opportunities found: {len(self.opportunities)}")
        
        if self.iv_list:
            print(f"\nIV Statistics:")
            print(f"  Min IV: {self.iv_list[0]:.1f}%")
            print(f"  Max IV: {self.iv_list[-1]:.1f}%")
            print(f"  Median IV: {self.iv_list[len(self.iv_list)//2]:.1f}%")
            print(f"  Final adaptive threshold: {self.get_adaptive_threshold():.1f}%")
        
        if self.opportunities:
            df = pd.DataFrame(self.opportunities)
            df['best_ff'] = df[['ff_avg', 'ff_call', 'ff_put']].max(axis=1)
            df = df.sort_values('best_ff', ascending=False)
            
            print(f"\nTop Opportunities:")
            for _, row in df.head(10).iterrows():
                print(f"  {row['ticker']:6s} FF={row['best_ff']:.3f} ({row['expiry1']} / {row['expiry2']})")
            
            return df
        
        return pd.DataFrame()
    
    def get_iv_rankings(self) -> List[Dict]:
        """Get IV rankings for all processed tickers."""
        rankings = []
        
        # Sort by IV descending
        sorted_data = sorted(self.iv_data, key=lambda x: x[1], reverse=True)
        
        for ticker, iv, price in sorted_data:
            ma_200 = self.scanner.ma_200_cache.get(ticker)
            above_ma_200 = price > ma_200 if ma_200 else None
            
            rankings.append({
                'ticker': ticker,
                'price': float(price),
                'iv': float(iv),
                'ma_200': float(ma_200) if ma_200 else None,
                'above_ma_200': bool(above_ma_200) if above_ma_200 is not None else None,
            })
        
        return rankings


def adaptive_batch_scan(tickers: List[str], 
                        min_iv_threshold: float = 30.0,
                        adaptive_percentile: float = 0.20,
                        ff_threshold: float = 0.2,
                        port: int = 7498) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Run adaptive single-pass scan on a list of tickers.
    
    Args:
        tickers: List of ticker symbols
        min_iv_threshold: Minimum IV to consider (default 30%)
        adaptive_percentile: Scan stocks in top X percentile (default 0.20)
        ff_threshold: FF threshold for opportunities (default 0.2)
        port: IB port (default 7498)
    
    Returns:
        Tuple of (opportunities DataFrame, IV rankings list)
    """
    scanner = IBScanner(port=port, check_earnings=True)
    
    if not scanner.connect():
        print("Could not connect to Interactive Brokers")
        return pd.DataFrame(), []
    
    try:
        # Pre-fetch earnings dates
        if scanner.earnings_checker:
            print("Pre-fetching earnings dates from Interactive Brokers...")
            for ticker in tickers[:20]:  # Just first 20 to save time
                scanner.earnings_checker.get_earnings_date(ticker)
            print()
        
        # Run adaptive scan
        adaptive = AdaptiveScanner(
            scanner=scanner,
            min_iv_threshold=min_iv_threshold,
            adaptive_percentile=adaptive_percentile,
            ff_threshold=ff_threshold
        )
        
        df = adaptive.scan_single_pass(tickers)
        iv_rankings = adaptive.get_iv_rankings()
        
        return df, iv_rankings
        
    finally:
        scanner.disconnect()


if __name__ == "__main__":
    # Test with a few tickers
    test_tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'META', 'GOOGL', 'AMZN']
    
    df, rankings = adaptive_batch_scan(
        test_tickers,
        min_iv_threshold=25.0,
        adaptive_percentile=0.30,  # Scan top 30%
        ff_threshold=0.2
    )
    
    if not df.empty:
        print("\n\nFinal Results:")
        print(df[['ticker', 'best_ff', 'expiry1', 'expiry2', 'avg_iv1', 'avg_iv2']].to_string())
