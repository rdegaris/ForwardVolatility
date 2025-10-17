"""
Run MAG7 scan with full trade recommendations and save for web display
"""
import sys
import json
from datetime import datetime
from scanner_ib import IBScanner
from nasdaq100 import get_mag7
import pandas as pd
import time

def calculate_trade_details(row):
    """Calculate trade recommendations and P&L estimates"""
    stock_price = row['price']
    strike = round(stock_price / 2.5) * 2.5
    
    ff_call = row['ff_call'] if pd.notna(row['ff_call']) else 0
    ff_put = row['ff_put'] if pd.notna(row['ff_put']) else 0
    
    if ff_call > ff_put:
        spread_type = "CALL"
        front_iv = row['call_iv1'] / 100 if pd.notna(row['call_iv1']) else row['avg_iv1'] / 100
        back_iv = row['call_iv2'] / 100 if pd.notna(row['call_iv2']) else row['avg_iv2'] / 100
        ff_display = ff_call
    else:
        spread_type = "PUT"
        front_iv = row['put_iv1'] / 100 if pd.notna(row['put_iv1']) else row['avg_iv1'] / 100
        back_iv = row['put_iv2'] / 100 if pd.notna(row['put_iv2']) else row['avg_iv2'] / 100
        ff_display = ff_put
    
    front_dte = row['dte1']
    back_dte = row['dte2']
    front_price = 0.4 * stock_price * front_iv * (front_dte / 365) ** 0.5
    back_price = 0.4 * stock_price * back_iv * (back_dte / 365) ** 0.5
    net_debit = back_price - front_price
    net_debit_total = net_debit * 100
    
    best_case = net_debit * 0.40
    typical_case = net_debit * 0.20
    adverse_case = -net_debit * 0.30
    max_loss = -net_debit
    
    return {
        'spread_type': spread_type,
        'strike': strike,
        'front_iv': front_iv * 100,
        'back_iv': back_iv * 100,
        'ff_display': ff_display,
        'front_price': front_price,
        'back_price': back_price,
        'net_debit': net_debit,
        'net_debit_total': net_debit_total,
        'best_case': best_case * 100,
        'typical_case': typical_case * 100,
        'adverse_case': adverse_case * 100,
        'max_loss': max_loss * 100,
        'best_case_pct': (best_case / net_debit * 100) if net_debit > 0 else 0,
        'typical_case_pct': (typical_case / net_debit * 100) if net_debit > 0 else 0,
        'adverse_case_pct': (adverse_case / net_debit * 100) if net_debit > 0 else 0,
        'max_loss_pct': (max_loss / net_debit * 100) if net_debit > 0 else 0
    }

def run_mag7_scan(threshold=0.2):
    """Run scan on MAG7 stocks and return formatted results."""
    
    print("=" * 80)
    print("MAG7 FORWARD VOLATILITY SCANNER")
    print("=" * 80)
    print()
    
    tickers = get_mag7()
    print(f"Scanning: {', '.join(tickers)}")
    print(f"Threshold: {threshold}")
    print()
    
    scanner = IBScanner(port=7497, check_earnings=True)
    
    if not scanner.connect():
        print("Could not connect to Interactive Brokers")
        print("Make sure TWS or IB Gateway is running on port 7497")
        return None
    
    # Pre-fetch earnings dates for all tickers
    if scanner.earnings_checker:
        print("Pre-fetching earnings dates...")
        for ticker in tickers:
            scanner.earnings_checker.get_earnings_date_yfinance(ticker)
        print()
    
    all_opportunities = []
    scan_log = []
    
    try:
        for i, ticker in enumerate(tickers, 1):
            log_entry = f"[{i}/{len(tickers)}] {ticker}..."
            print(log_entry)
            scan_log.append(log_entry)
            
            try:
                opportunities = scanner.scan_ticker(ticker, threshold=threshold)
                
                if opportunities:
                    all_opportunities.extend(opportunities)
                    msg = f"  Found {len(opportunities)} opportunity(ies)"
                    print(msg)
                    scan_log.append(msg)
                else:
                    msg = f"  No opportunities"
                    print(msg)
                    scan_log.append(msg)
                
                if i < len(tickers):
                    time.sleep(1)
                    
            except Exception as e:
                msg = f"  Error: {e}"
                print(msg)
                scan_log.append(msg)
                continue
        
        print()
        print("=" * 80)
        print("SCAN COMPLETE")
        print("=" * 80)
        print(f"Total opportunities: {len(all_opportunities)}")
        print()
        
        if all_opportunities:
            df = pd.DataFrame(all_opportunities)
            df['best_ff'] = df[['ff_avg', 'ff_call', 'ff_put']].max(axis=1)
            df = df.sort_values('best_ff', ascending=False)
            
            results = []
            for _, row in df.iterrows():
                trade_details = calculate_trade_details(row)
                
                result = {
                    'ticker': row['ticker'],
                    'price': float(row['price']),
                    'expiry1': str(row['expiry1']),
                    'expiry2': str(row['expiry2']),
                    'dte1': int(row['dte1']),
                    'dte2': int(row['dte2']),
                    'ff_call': float(row['ff_call']) if pd.notna(row['ff_call']) else None,
                    'ff_put': float(row['ff_put']) if pd.notna(row['ff_put']) else None,
                    'ff_avg': float(row['ff_avg']) if pd.notna(row['ff_avg']) else None,
                    'best_ff': float(row['best_ff']),
                    'next_earnings': row.get('next_earnings', None),
                    'trade': trade_details
                }
                results.append(result)
            
            # Print detailed recommendations
            print()
            print("=" * 80)
            print(f"TOP {min(3, len(results))} TRADE RECOMMENDATIONS")
            print("=" * 80)
            print()
            
            for i, result in enumerate(results[:3], 1):
                trade = result['trade']
                print(f"#{i} - {result['ticker']} @ ${result['price']:.2f}")
                print("-" * 80)
                print(f"  Expiry Window: {result['expiry1']} ({result['dte1']}d) → {result['expiry2']} ({result['dte2']}d)")
                print()
                print(f"  RECOMMENDED: {trade['spread_type']} CALENDAR SPREAD")
                print(f"     Forward Factor: {trade['ff_display']:.3f} ({trade['ff_display']*100:.1f}%)")
                print(f"     Front IV: {trade['front_iv']:.2f}% | Back IV: {trade['back_iv']:.2f}%")
                print()
                print(f"  ESTIMATED PRICING (per contract):")
                print(f"     Front {trade['spread_type']}: ~${trade['front_price']:.2f} (${trade['front_price']*100:.0f})")
                print(f"     Back {trade['spread_type']}:  ~${trade['back_price']:.2f} (${trade['back_price']*100:.0f})")
                print(f"     Net Debit:      ~${trade['net_debit']:.2f} (${trade['net_debit_total']:.0f})")
                print()
                print(f"  POTENTIAL OUTCOMES (1 contract):")
                print(f"     Best Case:   +${trade['best_case']:.0f} ({trade['best_case_pct']:.0f}%)")
                print(f"     Typical:     +${trade['typical_case']:.0f} ({trade['typical_case_pct']:.0f}%)")
                print(f"     Adverse:     ${trade['adverse_case']:.0f} ({trade['adverse_case_pct']:.0f}%)")
                print(f"     Max Loss:    ${trade['max_loss']:.0f} ({trade['max_loss_pct']:.0f}%)")
                print()
                print(f"  Trade Setup:")
                print(f"     • Sell: {result['expiry1']} ${trade['strike']:.0f} {trade['spread_type']}")
                print(f"     • Buy:  {result['expiry2']} ${trade['strike']:.0f} {trade['spread_type']}")
                print(f"     • Hold until: {result['expiry1']}")
                print()
                print("=" * 80)
                print()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'scan_log': scan_log,
                'opportunities': results,
                'summary': {
                    'total_opportunities': len(results),
                    'tickers_scanned': len(tickers),
                    'best_ff': float(df['best_ff'].max()),
                    'avg_ff': float(df['best_ff'].mean())
                }
            }
        else:
            return {
                'timestamp': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'scan_log': scan_log,
                'opportunities': [],
                'summary': {
                    'total_opportunities': 0,
                    'tickers_scanned': len(tickers),
                    'best_ff': 0,
                    'avg_ff': 0
                }
            }
            
    finally:
        scanner.disconnect()


if __name__ == "__main__":
    results = run_mag7_scan(threshold=0.2)
    
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"scan_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {filename}")
        
        with open("scan_results_latest.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Latest results saved to: scan_results_latest.json")
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Opportunities found: {results['summary']['total_opportunities']}")
        print(f"Best FF: {results['summary']['best_ff']:.3f}")
        print(f"Average FF: {results['summary']['avg_ff']:.3f}")
        print("=" * 80)
