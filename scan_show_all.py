"""
IB Scanner that shows ALL forward factor results (not just > 0.4)
"""

import sys
sys.path.insert(0, '.')

from scanner_ib import IBScanner, calculate_dte, calculate_forward_vol, print_bordered_table
import pandas as pd
from datetime import datetime

def scan_show_all():
    """Scan and show all results, not just > 0.4."""
    print("=" * 80)
    print("IB SCANNER - SHOW ALL RESULTS")
    print("=" * 80)
    print("\nMake sure IB Gateway or TWS is running!\n")
    
    port = 7497
    scanner = IBScanner(port=port)
    
    if not scanner.connect():
        return
    
    try:
        ticker = input("Enter ticker (default: TSLA): ").strip().upper() or 'TSLA'
        threshold = float(input("Enter minimum FF threshold (default: 0.2): ").strip() or '0.2')
        
        print("\n" + "=" * 80)
        print(f"SCANNING {ticker}")
        print("=" * 80)
        
        opportunities = scanner.scan_ticker(ticker, threshold=threshold)
        
        if opportunities:
            df = pd.DataFrame(opportunities)
            df = df.sort_values('ff_ratio', ascending=False)
            
            print("\n" + "=" * 120)
            print(f"OPPORTUNITIES FOUND (FF > {threshold})".center(120))
            print("=" * 120)
            print()
            print_bordered_table(df)
            
            filename = f"forward_vol_IB_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"\nResults saved to {filename}")
            
            # Show best opportunity
            best = df.iloc[0]
            print("\n" + "=" * 80)
            print("BEST OPPORTUNITY")
            print("=" * 80)
            print(f"Ticker: {best['ticker']}")
            print(f"Price: ${best['price']:.2f}")
            print(f"Front Month: {best['expiry1']} (DTE={best['dte1']}, IV={best['iv1']}%)")
            print(f"Back Month: {best['expiry2']} (DTE={best['dte2']}, IV={best['iv2']}%)")
            print(f"Forward Vol: {best['fwd_vol_pct']:.2f}%")
            print(f"Forward Factor: {best['ff_ratio']:.3f} ({best['ff_pct']:.1f}%)")
            print("\nINTERPRETATION:")
            print(f"Front month IV is {best['ff_pct']:.1f}% higher than forward volatility")
            print("Consider: Sell front month, buy back month (calendar spread)")
            
        else:
            print(f"\nNo opportunities found with FF > {threshold}")
            print("Try lowering the threshold or scanning different tickers.")
    
    finally:
        scanner.disconnect()
        print("\nDisconnected from Interactive Brokers")

if __name__ == "__main__":
    scan_show_all()
