"""
Demo Scanner with Sample Data
Shows what the output looks like when Yahoo Finance API is working
"""

import pandas as pd
from datetime import datetime


def print_bordered_table(df):
    """Print a DataFrame with ASCII borders."""
    
    # Convert all columns to strings and get max widths
    col_widths = {}
    for col in df.columns:
        col_widths[col] = max(
            len(str(col)),
            df[col].astype(str).str.len().max()
        )
    
    # Create separator line
    sep_line = '+'
    for col in df.columns:
        sep_line += '-' * (col_widths[col] + 2) + '+'
    
    # Print top border
    print(sep_line)
    
    # Print header
    header = '|'
    for col in df.columns:
        header += f' {str(col).ljust(col_widths[col])} |'
    print(header)
    print(sep_line)
    
    # Print rows
    for _, row in df.iterrows():
        row_str = '|'
        for col in df.columns:
            value = str(row[col])
            row_str += f' {value.ljust(col_widths[col])} |'
        print(row_str)
    
    # Print bottom border
    print(sep_line)

# Sample opportunities (realistic data based on typical market conditions)
sample_data = [
    {
        'ticker': 'AAPL',
        'price': 178.25,
        'expiry1': '2025-11-15',
        'expiry2': '2025-12-20',
        'dte1': 31,
        'dte2': 66,
        'iv1': 25.3,
        'iv2': 18.2,
        'fwd_vol_pct': 12.5,
        'ff_ratio': 0.456,
        'ff_pct': 45.6
    },
    {
        'ticker': 'AAPL',
        'price': 178.25,
        'expiry1': '2025-12-20',
        'expiry2': '2026-01-17',
        'dte1': 66,
        'dte2': 94,
        'iv1': 23.1,
        'iv2': 17.8,
        'fwd_vol_pct': 14.2,
        'ff_ratio': 0.442,
        'ff_pct': 44.2
    },
    {
        'ticker': 'TSLA',
        'price': 242.50,
        'expiry1': '2025-11-08',
        'expiry2': '2025-11-29',
        'dte1': 24,
        'dte2': 45,
        'iv1': 58.7,
        'iv2': 42.3,
        'fwd_vol_pct': 28.4,
        'ff_ratio': 0.518,
        'ff_pct': 51.8
    },
    {
        'ticker': 'NVDA',
        'price': 485.30,
        'expiry1': '2025-11-15',
        'expiry2': '2025-12-20',
        'dte1': 31,
        'dte2': 66,
        'iv1': 48.2,
        'iv2': 35.8,
        'fwd_vol_pct': 24.9,
        'ff_ratio': 0.482,
        'ff_pct': 48.2
    },
    {
        'ticker': 'META',
        'price': 505.75,
        'expiry1': '2025-11-22',
        'expiry2': '2025-12-20',
        'dte1': 38,
        'dte2': 66,
        'iv1': 42.5,
        'iv2': 32.1,
        'fwd_vol_pct': 21.8,
        'ff_ratio': 0.425,
        'ff_pct': 42.5
    },
    {
        'ticker': 'AMD',
        'price': 143.80,
        'expiry1': '2025-11-15',
        'expiry2': '2025-12-20',
        'dte1': 31,
        'dte2': 66,
        'iv1': 52.3,
        'iv2': 39.7,
        'fwd_vol_pct': 28.5,
        'ff_ratio': 0.467,
        'ff_pct': 46.7
    }
]

def main():
    print("=" * 80)
    print("FORWARD VOLATILITY SCANNER - DEMO MODE")
    print("=" * 80)
    print("This is sample data showing what the scanner outputs when API is working")
    print("Scanning for opportunities where Forward Factor (FF) > 0.4")
    print()
    
    # Simulate scanning AAPL
    print("\n" + "=" * 80)
    print("SCANNING AAPL")
    print("=" * 80)
    print("\nScanning AAPL (Price: $178.25)...")
    
    aapl_opps = [opp for opp in sample_data if opp['ticker'] == 'AAPL']
    for opp in aapl_opps:
        print(f"  [FOUND] {opp['expiry1']} (DTE={opp['dte1']}, IV={opp['iv1']:.1f}%) -> "
              f"{opp['expiry2']} (DTE={opp['dte2']}, IV={opp['iv2']:.1f}%) | "
              f"FF={opp['ff_ratio']:.3f} ({opp['ff_pct']:.1f}%)")
    
    # Show AAPL opportunities table
    df_aapl = pd.DataFrame(aapl_opps)
    print("\n" + "=" * 80)
    print("AAPL OPPORTUNITIES")
    print("=" * 80)
    print(df_aapl[['ticker', 'price', 'expiry1', 'expiry2', 'dte1', 'dte2', 
                   'iv1', 'iv2', 'fwd_vol_pct', 'ff_ratio', 'ff_pct']].to_string(index=False))
    
    # Simulate scanning more tickers
    print("\n" + "=" * 80)
    print("SCANNING ADDITIONAL TICKERS (SAMPLE)")
    print("=" * 80)
    
    other_tickers = ['TSLA', 'NVDA', 'META', 'AMD']
    for ticker in other_tickers:
        ticker_opps = [opp for opp in sample_data if opp['ticker'] == ticker]
        if ticker_opps:
            opp = ticker_opps[0]
            print(f"\n[Sample] Scanning {ticker} (Price: ${opp['price']:.2f})...")
            print(f"  [FOUND] {opp['expiry1']} (DTE={opp['dte1']}, IV={opp['iv1']:.1f}%) -> "
                  f"{opp['expiry2']} (DTE={opp['dte2']}, IV={opp['iv2']:.1f}%) | "
                  f"FF={opp['ff_ratio']:.3f} ({opp['ff_pct']:.1f}%)")
    
    # Show all opportunities
    df_all = pd.DataFrame(sample_data)
    df_all = df_all.sort_values('ff_ratio', ascending=False)
    
    print("\n" + "=" * 140)
    print("ALL OPPORTUNITIES (FF > 0.4)".center(140))
    print("=" * 140)
    print()
    print_bordered_table(df_all[['ticker', 'price', 'expiry1', 'expiry2', 'dte1', 'dte2', 
                  'iv1', 'iv2', 'fwd_vol_pct', 'ff_ratio', 'ff_pct']])
    
    # Save to CSV
    filename = f"forward_vol_opportunities_DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_all.to_csv(filename, index=False)
    print(f"\nSample results saved to {filename}")
    
    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print("""
High Forward Factor (FF > 0.4) indicates:
- Front month IV is significantly elevated relative to forward volatility
- Potential calendar spread opportunity (sell front, buy back)
- Market pricing in near-term event/volatility that may be overdone
- Forward volatility suggests lower implied vol in the outer months

Top opportunity: TSLA with FF = 0.518 (51.8%)
- Front month (24 DTE) IV: 58.7%
- Back month (45 DTE) IV: 42.3%
- Forward vol implies only 28.4% for the period between
- Consider: Sell 24 DTE options, buy 45 DTE as hedge

NOTE: This is sample data for demonstration purposes.
      When Yahoo Finance API is available, scanner.py will fetch live data.
    """)


if __name__ == "__main__":
    main()
