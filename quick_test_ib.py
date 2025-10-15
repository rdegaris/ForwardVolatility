"""
Quick test of IB scanner with single ticker
"""

import sys
sys.path.insert(0, '.')

from scanner_ib import IBScanner, calculate_dte, calculate_forward_vol, print_bordered_table
import pandas as pd
from datetime import datetime

def quick_test():
    """Quick test with TSLA."""
    print("=" * 80)
    print("INTERACTIVE BROKERS SCANNER - QUICK TEST")
    print("=" * 80)
    print("\nMake sure IB Gateway or TWS is running!")
    print("\nDefault port: 7497 (TWS Paper)")
    print("Press Ctrl+C to cancel\n")
    
    port = 7497  # Default TWS paper port
    
    scanner = IBScanner(port=port)
    
    if not scanner.connect():
        print("\nTroubleshooting:")
        print("1. Is IB Gateway/TWS running and logged in?")
        print("2. Is API enabled? (File → Global Configuration → API → Settings)")
        print("3. Try port 4002 for Gateway Paper, 7496 for TWS Live")
        return
    
    try:
        print("\n" + "=" * 80)
        print("SCANNING TSLA")
        print("=" * 80)
        
        opportunities = scanner.scan_ticker('TSLA', threshold=0.4)
        
        if opportunities:
            df = pd.DataFrame(opportunities)
            print("\n" + "=" * 120)
            print("OPPORTUNITIES FOUND (FF > 0.4)".center(120))
            print("=" * 120)
            print()
            print_bordered_table(df)
            
            filename = f"forward_vol_IB_TSLA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"\nResults saved to {filename}")
        else:
            print("\nNo opportunities found with FF > 0.4")
            print("This is normal if volatility term structure is flat.")
        
    finally:
        scanner.disconnect()
        print("\nDisconnected from Interactive Brokers")

if __name__ == "__main__":
    quick_test()
