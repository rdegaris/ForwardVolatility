"""
Run S&P MidCap 400 scan and save for web display
"""
import json
from datetime import datetime
from batch_scan import batch_scan
from midcap400 import get_midcap400_list
from scanner_ib import IBScanner, rank_tickers_by_iv
import pandas as pd

def run_midcap400_scan(threshold=0.2, rank_by_iv=True, top_n_iv=100):
    """Run scan on S&P MidCap 400 stocks and save formatted results.
    
    Args:
        threshold: FF threshold (default 0.2)
        rank_by_iv: Pre-rank by near-term IV (default True)
        top_n_iv: If ranking, scan top N tickers (default 100, None = scan all)
    """
    
    scan_log = []
    
    scan_log.append("=" * 80)
    scan_log.append("S&P MIDCAP 400 FORWARD VOLATILITY SCANNER")
    scan_log.append("=" * 80)
    scan_log.append("")
    
    tickers = get_midcap400_list()
    scan_log.append(f"Scanning: {len(tickers)} S&P MidCap 400 stocks")
    scan_log.append(f"Threshold: {threshold}")
    
    if rank_by_iv and top_n_iv:
        scan_log.append(f"Strategy: Scan top {top_n_iv} by near-term IV")
    elif rank_by_iv:
        scan_log.append("Strategy: Scan all, ranked by near-term IV")
    else:
        scan_log.append("Strategy: Scan all stocks")
    
    scan_log.append("")
    
    # Print to console
    for line in scan_log:
        print(line)
    
    # Get IV rankings first (for IV Rankings page)
    iv_rankings_data = None
    if rank_by_iv:
        print("Ranking all tickers by near-term IV...")
        scanner = IBScanner(check_earnings=False)
        scanner.connect()
        try:
            ranked = rank_tickers_by_iv(scanner, tickers, top_n=None)  # Rank all
            iv_rankings_data = []
            for ticker, iv, price in ranked:
                # Get 200-day MA
                ma_200 = scanner.get_200day_ma(ticker)
                above_ma_200 = price > ma_200 if ma_200 else None
                
                # Get near-term expiry
                expiry = scanner.get_near_term_expiry(ticker)
                dte = (expiry - datetime.now().date()).days if expiry else None
                
                iv_rankings_data.append({
                    'ticker': ticker,
                    'price': float(price) if price else None,
                    'iv': float(iv) if iv else None,
                    'expiry': str(expiry) if expiry else None,
                    'dte': int(dte) if dte else None,
                    'ma_200': float(ma_200) if pd.notna(ma_200) else None,
                    'above_ma_200': bool(above_ma_200) if pd.notna(above_ma_200) else None,
                    'universe': 'S&P MidCap 400'
                })
            print(f"Ranked {len(iv_rankings_data)} tickers by IV")
            print()
        finally:
            scanner.disconnect()
    
    # Run the batch scan
    df = batch_scan(tickers, threshold=threshold, rank_by_iv=rank_by_iv, top_n_iv=top_n_iv)
    
    if df is None or df.empty:
        result = {
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
    else:
        # Convert DataFrame to list of dicts for JSON
        opportunities = []
        for _, row in df.iterrows():
            opp = {
                'ticker': row['ticker'],
                'price': float(row['price']),
                'ma_200': float(row['ma_200']) if pd.notna(row.get('ma_200')) else None,
                'above_ma_200': bool(row['above_ma_200']) if pd.notna(row.get('above_ma_200')) else None,
                'expiry1': str(row['expiry1']),
                'expiry2': str(row['expiry2']),
                'dte1': int(row['dte1']),
                'dte2': int(row['dte2']),
                'ff_call': float(row['ff_call']) if pd.notna(row['ff_call']) else None,
                'ff_put': float(row['ff_put']) if pd.notna(row['ff_put']) else None,
                'ff_avg': float(row['ff_avg']) if pd.notna(row['ff_avg']) else None,
                'best_ff': float(row['best_ff']),
                'next_earnings': row.get('next_earnings', None),
                'call_iv1': float(row['call_iv1']) if pd.notna(row['call_iv1']) else None,
                'call_iv2': float(row['call_iv2']) if pd.notna(row['call_iv2']) else None,
                'put_iv1': float(row['put_iv1']) if pd.notna(row['put_iv1']) else None,
                'put_iv2': float(row['put_iv2']) if pd.notna(row['put_iv2']) else None,
                'avg_iv1': float(row['avg_iv1']) if pd.notna(row['avg_iv1']) else None,
                'avg_iv2': float(row['avg_iv2']) if pd.notna(row['avg_iv2']) else None,
                'fwd_var_call': float(row['fwd_var_call']) if pd.notna(row.get('fwd_var_call')) else None,
                'fwd_var_put': float(row['fwd_var_put']) if pd.notna(row.get('fwd_var_put')) else None,
                'fwd_var_avg': float(row['fwd_var_avg']) if pd.notna(row.get('fwd_var_avg')) else None,
                'fwd_vol_call': float(row['fwd_vol_call']) if pd.notna(row.get('fwd_vol_call')) else None,
                'fwd_vol_put': float(row['fwd_vol_put']) if pd.notna(row.get('fwd_vol_put')) else None,
                'fwd_vol_avg': float(row['fwd_vol_avg']) if pd.notna(row.get('fwd_vol_avg')) else None,
            }
            
            # Calculate trade details
            stock_price = opp['price']
            
            # Use the actual ATM strike from the scan if available, otherwise calculate
            if pd.notna(row.get('strike1')) and pd.notna(row.get('strike2')):
                # Use the strike from the front expiry (they should be the same or very close)
                strike = float(row['strike1'])
            else:
                # Fallback: Use appropriate strike interval based on stock price
                # IB uses: $0.50 for stocks <$25, $1 for $25-$200, $5 for $200-$500, $10 for >$500
                if stock_price < 25:
                    strike_interval = 0.5
                elif stock_price < 200:
                    strike_interval = 1.0
                elif stock_price < 500:
                    strike_interval = 5.0
                else:
                    strike_interval = 10.0
                
                strike = round(stock_price / strike_interval) * strike_interval
            
            ff_call = opp['ff_call'] if opp['ff_call'] is not None else 0
            ff_put = opp['ff_put'] if opp['ff_put'] is not None else 0
            
            if ff_call > ff_put:
                spread_type = "CALL"
                front_iv = opp['call_iv1'] / 100 if opp['call_iv1'] else opp['avg_iv1'] / 100
                back_iv = opp['call_iv2'] / 100 if opp['call_iv2'] else opp['avg_iv2'] / 100
                ff_display = ff_call
            else:
                spread_type = "PUT"
                front_iv = opp['put_iv1'] / 100 if opp['put_iv1'] else opp['avg_iv1'] / 100
                back_iv = opp['put_iv2'] / 100 if opp['put_iv2'] else opp['avg_iv2'] / 100
                ff_display = ff_put
            
            front_dte = opp['dte1']
            back_dte = opp['dte2']
            front_price = 0.4 * stock_price * front_iv * (front_dte / 365) ** 0.5
            back_price = 0.4 * stock_price * back_iv * (back_dte / 365) ** 0.5
            net_debit = back_price - front_price
            net_debit_total = net_debit * 100
            
            best_case = net_debit * 0.40
            typical_case = net_debit * 0.20
            adverse_case = -net_debit * 0.30
            max_loss = -net_debit
            
            opp['trade_details'] = {
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
            
            opportunities.append(opp)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'scan_log': scan_log,
            'opportunities': opportunities,
            'summary': {
                'total_opportunities': len(opportunities),
                'tickers_scanned': len(tickers),
                'best_ff': float(df['best_ff'].max()),
                'avg_ff': float(df['best_ff'].mean())
            }
        }
    
    # Save timestamped file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"midcap400_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Results saved to: {filename}")
    
    # Save latest file
    with open("midcap400_results_latest.json", 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Latest results saved to: midcap400_results_latest.json")
    
    # Save IV rankings separately for IV Rankings page
    if iv_rankings_data:
        iv_rankings_file = 'midcap400_iv_rankings_latest.json'
        iv_rankings_result = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'universe': 'S&P MidCap 400',
            'total_tickers': len(iv_rankings_data),
            'rankings': iv_rankings_data
        }
        with open(iv_rankings_file, 'w') as f:
            json.dump(iv_rankings_result, f, indent=2)
        print(f"✅ IV Rankings saved to {iv_rankings_file}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Opportunities found: {result['summary']['total_opportunities']}")
    if result['summary']['total_opportunities'] > 0:
        print(f"Best FF: {result['summary']['best_ff']:.3f}")
        print(f"Average FF: {result['summary']['avg_ff']:.3f}")
    print("=" * 80)
    
    return result


if __name__ == "__main__":
    # Configuration
    threshold = 0.2  # 20% forward factor threshold
    rank_by_iv = True  # Pre-rank by IV
    top_n_iv = 100  # Scan top 100 by IV (from 594 total)
    
    run_midcap400_scan(threshold=threshold, rank_by_iv=rank_by_iv, top_n_iv=top_n_iv)
