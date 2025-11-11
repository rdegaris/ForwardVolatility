"""
Batch Scanner - Scan multiple tickers from Nasdaq 100 and rank opportunities
"""

import sys
sys.path.insert(0, '.')

from scanner_ib import IBScanner, print_bordered_table, rank_tickers_by_iv
from nasdaq100 import get_nasdaq_100_list, get_tech_heavy_list, get_mag7
import pandas as pd
from datetime import datetime
import time

def batch_scan(tickers, threshold=0.2, max_tickers=None, rank_by_iv=True, top_n_iv=None):
    """
    Scan multiple tickers and return ranked opportunities.
    
    Args:
        tickers: List of ticker symbols
        threshold: Minimum FF to include (default 0.2)
        max_tickers: Maximum number of tickers to scan (None = all)
        rank_by_iv: Pre-rank tickers by near-term IV (default True)
        top_n_iv: If rank_by_iv=True, scan only top N by IV (None = scan all with ranking)
    
    Returns:
        DataFrame of all opportunities, sorted by FF
    """
    print("=" * 80)
    print(f"BATCH SCANNER - {len(tickers)} TICKERS")
    print("=" * 80)
    print()
    
    scanner = IBScanner(port=7497, check_earnings=True)
    
    if not scanner.connect():
        print("Could not connect to IB")
        return None
    
    all_opportunities = []
    tickers_scanned = 0
    tickers_with_opps = 0
    
    try:
        # Limit number of tickers if specified
        initial_list = tickers[:max_tickers] if max_tickers else tickers
        
        # Rank by IV if requested
        if rank_by_iv:
            print(f"\n🔍 Pre-ranking {len(initial_list)} tickers by near-term IV...")
            ranked = rank_tickers_by_iv(scanner, initial_list, top_n=top_n_iv)
            scan_list = [ticker for ticker, iv, price in ranked]
            print(f"\n✅ Will scan {len(scan_list)} tickers (sorted by IV)")
        else:
            scan_list = initial_list
        
        print()
        print(f"Scanning {len(scan_list)} tickers with FF threshold > {threshold}")
        print(f"Earnings filtering: ENABLED")
        print("-" * 80)
        print()
        
        for i, ticker in enumerate(scan_list, 1):
            print(f"[{i}/{len(scan_list)}] {ticker}...")
            
            try:
                opportunities = scanner.scan_ticker(ticker, threshold=threshold)
                tickers_scanned += 1
                
                if opportunities:
                    tickers_with_opps += 1
                    all_opportunities.extend(opportunities)
                    print(f"  ✅ Found {len(opportunities)} opportunity(ies)")
                else:
                    print(f"  ⚪ No opportunities")
                
                # Rate limit between tickers
                if i < len(scan_list):
                    time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n\nScan interrupted by user")
                break
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
        
        print()
        print("=" * 80)
        print("SCAN COMPLETE")
        print("=" * 80)
        print(f"Tickers scanned: {tickers_scanned}")
        print(f"Tickers with opportunities: {tickers_with_opps}")
        print(f"Total opportunities found: {len(all_opportunities)}")
        print()
        
        if all_opportunities:
            # Convert to DataFrame
            df = pd.DataFrame(all_opportunities)
            
            # Sort by best opportunities
            # Primary sort: ff_avg (blended), then ff_call, then ff_put
            df['best_ff'] = df[['ff_avg', 'ff_call', 'ff_put']].max(axis=1)
            df = df.sort_values('best_ff', ascending=False)
            
            # Add rank
            df.insert(0, 'rank', range(1, len(df) + 1))
            
            return df
        else:
            print("No opportunities found above threshold")
            return None
    
    finally:
        scanner.disconnect()


def print_top_opportunities(df, top_n=10):
    """Print top N opportunities in a formatted table."""
    if df is None or df.empty:
        return
    
    print("=" * 140)
    print(f"TOP {min(top_n, len(df))} OPPORTUNITIES (Sorted by Best FF)".center(140))
    print("=" * 140)
    print()
    
    # Select key columns for display
    display_df = df.head(top_n)[['rank', 'ticker', 'price', 'expiry1', 'expiry2', 
                                   'dte1', 'dte2', 'ff_call', 'ff_put', 'ff_avg', 'best_ff']]
    
    # Format for display
    display_df = display_df.copy()
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:.2f}")
    display_df['ff_call'] = display_df['ff_call'].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
    display_df['ff_put'] = display_df['ff_put'].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
    display_df['ff_avg'] = display_df['ff_avg'].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
    display_df['best_ff'] = display_df['best_ff'].apply(lambda x: f"{x:.3f}")
    
    print_bordered_table(display_df)
    print()


def print_trade_suggestions(df, top_n=3):
    """Print detailed trade suggestions for top opportunities."""
    if df is None or df.empty:
        return
    
    print("=" * 80)
    print(f"DETAILED TRADE SUGGESTIONS - TOP {min(top_n, len(df))}".center(80))
    print("=" * 80)
    print()
    
    for i, row in df.head(top_n).iterrows():
        print(f"#{row['rank']} - {row['ticker']} @ ${row['price']:.2f}")
        print("-" * 80)
        print(f"  Expiry Window: {row['expiry1']} ({row['dte1']}d) → {row['expiry2']} ({row['dte2']}d)")
        print()
        
        # Determine best spread type
        ff_call = row['ff_call'] if pd.notna(row['ff_call']) else 0
        ff_put = row['ff_put'] if pd.notna(row['ff_put']) else 0
        
        # Determine spread type based on trend alignment and forward factor
        stock_price = row['price']
        strike = round(stock_price / 2.5) * 2.5  # Round to nearest 2.50
        above_ma_200 = row.get('above_ma_200', True)  # Default to True if not available
        
        # If FF values are close (within 5%), prefer the side that aligns with trend
        ff_diff = abs(ff_call - ff_put)
        max_ff = max(ff_call, ff_put)
        
        if max_ff > 0 and ff_diff / max_ff < 0.05:
            # FF values are similar - use trend to decide
            if above_ma_200:
                spread_type = "CALL"  # Bullish trend -> CALL spread
                front_iv = row['call_iv1'] / 100
                back_iv = row['call_iv2'] / 100
                ff_display = ff_call
                front_mid = row.get('call1_mid')
                back_mid = row.get('call2_mid')
            else:
                spread_type = "PUT"  # Bearish trend -> PUT spread
                front_iv = row['put_iv1'] / 100 if pd.notna(row['put_iv1']) else row['avg_iv1'] / 100
                back_iv = row['put_iv2'] / 100 if pd.notna(row['put_iv2']) else row['avg_iv2'] / 100
                ff_display = ff_put
                front_mid = row.get('put1_mid')
                back_mid = row.get('put2_mid')
        elif ff_call > ff_put:
            # CALL has significantly better FF
            spread_type = "CALL"
            front_iv = row['call_iv1'] / 100
            back_iv = row['call_iv2'] / 100
            ff_display = ff_call
            # Use actual midpoint prices if available, otherwise estimate
            front_mid = row.get('call1_mid')
            back_mid = row.get('call2_mid')
        else:
            # PUT has significantly better FF
            spread_type = "PUT"
            front_iv = row['put_iv1'] / 100 if pd.notna(row['put_iv1']) else row['avg_iv1'] / 100
            back_iv = row['put_iv2'] / 100 if pd.notna(row['put_iv2']) else row['avg_iv2'] / 100
            ff_display = ff_put
            # Use actual midpoint prices if available, otherwise estimate
            front_mid = row.get('put1_mid')
            back_mid = row.get('put2_mid')
        
        # Calculate option prices - use midpoint if available, otherwise estimate
        front_dte = row['dte1']
        back_dte = row['dte2']
        
        if pd.notna(front_mid) and pd.notna(back_mid):
            # Use actual market midpoint prices
            front_price = front_mid
            back_price = back_mid
            price_source = "market midpoint"
        else:
            # Fallback to estimated prices using simplified ATM formula: 0.4 * S * IV * sqrt(T/365)
            front_price = 0.4 * stock_price * front_iv * (front_dte / 365) ** 0.5
            back_price = 0.4 * stock_price * back_iv * (back_dte / 365) ** 0.5
            price_source = "estimated"
        
        net_debit = back_price - front_price
        net_debit_total = net_debit * 100  # Per contract
        
        # Estimate P&L scenarios
        best_case = net_debit * 0.40  # 40% return
        typical_case = net_debit * 0.20  # 20% return
        adverse_case = -net_debit * 0.30  # 30% loss
        max_loss = -net_debit  # 100% loss
        
        print(f"  📊 RECOMMENDED: {spread_type} CALENDAR SPREAD")
        print(f"     Forward Factor: {ff_display:.3f} ({ff_display*100:.1f}%)")
        print(f"     Front IV: {front_iv*100:.2f}% | Back IV: {back_iv*100:.2f}%")
        print()
        print(f"  💰 PRICING ({price_source}, per contract):")
        print(f"     Front {spread_type}: ${front_price:.2f} (${front_price*100:.0f})")
        print(f"     Back {spread_type}:  ${back_price:.2f} (${back_price*100:.0f})")
        print(f"     Net Debit:      ${net_debit:.2f} (${net_debit_total:.0f})")
        print()
        print(f"  📈 POTENTIAL OUTCOMES (1 contract):")
        print(f"     🎯 Best Case (stock near ${strike:.0f}):  +${best_case*100:.0f} ({best_case/net_debit*100:.0f}%)")
        print(f"     ✅ Typical (±2% move):                  +${typical_case*100:.0f} ({typical_case/net_debit*100:.0f}%)")
        print(f"     🛑 Adverse (±5% move):                  ${adverse_case*100:.0f} ({adverse_case/net_debit*100:.0f}%)")
        print(f"     ⚠️  Max Loss (spread collapse):          ${max_loss*100:.0f} ({max_loss/net_debit*100:.0f}%)")
        
        print()
        print(f"  Alternative (Blended): FF = {row['ff_avg']:.3f}")
        print(f"     Front IV: {row['avg_iv1']:.2f}% | Back IV: {row['avg_iv2']:.2f}%")
        print()
        print(f"  💡 Trade Setup:")
        print(f"     • Sell: {row['expiry1']} ${strike:.0f} {spread_type}")
        print(f"     • Buy:  {row['expiry2']} ${strike:.0f} {spread_type}")
        print(f"     • Hold until: {row['expiry1']} (exit 15 min before close)")
        print()
        print("=" * 80)
        print()


def main():
    print("=" * 80)
    print("NASDAQ 100 BATCH SCANNER")
    print("=" * 80)
    print()
    
    print("Select stock list:")
    print("  1. Magnificent 7 (7 tickers) - Quick test")
    print("  2. Tech Heavy (28 tickers) - Medium scan")
    print("  3. Full Nasdaq 100 (100 tickers) - Complete scan")
    print("  4. Custom list")
    print()
    
    choice = input("Enter choice (1-4) [default: 1]: ").strip() or "1"
    
    if choice == "1":
        tickers = get_mag7()
        print(f"\n📊 Scanning Magnificent 7: {', '.join(tickers)}")
    elif choice == "2":
        tickers = get_tech_heavy_list()
        print(f"\n📊 Scanning {len(tickers)} Tech-Heavy stocks")
    elif choice == "3":
        tickers = get_nasdaq_100_list()
        print(f"\n📊 Scanning all {len(tickers)} Nasdaq 100 stocks")
    elif choice == "4":
        tickers_input = input("Enter tickers (comma-separated): ")
        tickers = [t.strip().upper() for t in tickers_input.split(',')]
        print(f"\n📊 Scanning custom list: {', '.join(tickers)}")
    else:
        print("Invalid choice, using Magnificent 7")
        tickers = get_mag7()
    
    print()
    threshold_input = input("Enter FF threshold (default: 0.2): ").strip()
    threshold = float(threshold_input) if threshold_input else 0.2
    
    print()
    print("Starting scan...")
    print()
    
    # Run batch scan
    df = batch_scan(tickers, threshold=threshold)
    
    if df is not None and not df.empty:
        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_scan_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Results saved to: {filename}")
        print()
        
        # Display results
        print_top_opportunities(df, top_n=10)
        
        # Print detailed trade suggestions
        print_trade_suggestions(df, top_n=3)
        
        # Summary stats
        print("=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        print(f"  Best FF:          {df['best_ff'].max():.3f}")
        print(f"  Average FF:       {df['best_ff'].mean():.3f}")
        print(f"  Median FF:        {df['best_ff'].median():.3f}")
        print(f"  Opportunities:    {len(df)}")
        print(f"  Unique Tickers:   {df['ticker'].nunique()}")
        print("=" * 80)
    else:
        print("No opportunities found. Try:")
        print("  • Lower threshold (e.g., 0.15)")
        print("  • Different stock list")
        print("  • Scan during market hours for better data")


if __name__ == "__main__":
    main()
