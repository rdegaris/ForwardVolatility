"""
Run NASDAQ 100 scan and save for web display
"""
import json
from datetime import datetime
from batch_scan import batch_scan
from nasdaq100 import get_nasdaq_100_list
from scanner_ib import IBScanner, rank_tickers_by_iv
import pandas as pd

def run_nasdaq100_scan(threshold=0.2, rank_by_iv=True, top_n_iv=50):
    """Run scan on NASDAQ 100 stocks and save formatted results.
    
    Args:
        threshold: FF threshold (default 0.2)
        rank_by_iv: Pre-rank by near-term IV (default True)
        top_n_iv: If ranking, scan top N tickers (default 50, None = scan all)
    """
    
    scan_log = []
    
    def log(msg):
        print(msg)
        scan_log.append(msg)
    
    log("=" * 80)
    log("NASDAQ 100 FORWARD VOLATILITY SCANNER")
    log("=" * 80)
    log("")
    
    tickers = get_nasdaq_100_list()
    log(f"Scanning: {len(tickers)} NASDAQ 100 stocks")
    log(f"Threshold: {threshold}")
    if rank_by_iv:
        log(f"Strategy: Scan top {top_n_iv if top_n_iv else 'all'} by near-term IV")
    log("")
    
    # Get IV rankings first (for IV Rankings page)
    iv_rankings_data = None
    if rank_by_iv:
        log("Ranking all tickers by near-term IV...")
        scanner = IBScanner(check_earnings=False)
        scanner.connect()
        try:
            ranked = rank_tickers_by_iv(scanner, tickers, top_n=None)  # Rank all
            iv_rankings_data = []
            for ticker, iv, price, expiry, dte, ma_200, above_ma_200 in ranked:
                iv_rankings_data.append({
                    'ticker': ticker,
                    'price': float(price) if price else None,
                    'iv': float(iv) if iv else None,
                    'expiry': str(expiry) if expiry else None,
                    'dte': int(dte) if dte else None,
                    'ma_200': float(ma_200) if pd.notna(ma_200) else None,
                    'above_ma_200': bool(above_ma_200) if pd.notna(above_ma_200) else None,
                    'universe': 'NASDAQ 100'
                })
            log(f"Ranked {len(iv_rankings_data)} tickers by IV")
            log("")
        finally:
            scanner.disconnect()
    
    # Run batch scan with IV ranking
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
        
        # Sort by ticker
        opportunities.sort(key=lambda x: x['ticker'])
        
        # Create result structure
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
    
    # Save to JSON
    output_file = 'nasdaq100_results_latest.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    log("")
    log(f"✅ Results saved to {output_file}")
    log(f"📊 Total opportunities: {result['summary']['total_opportunities']}")
    
    # Save IV rankings separately for IV Rankings page
    if iv_rankings_data:
        iv_rankings_file = 'nasdaq100_iv_rankings_latest.json'
        iv_rankings_result = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'universe': 'NASDAQ 100',
            'total_tickers': len(iv_rankings_data),
            'rankings': iv_rankings_data
        }
        with open(iv_rankings_file, 'w') as f:
            json.dump(iv_rankings_result, f, indent=2)
        log(f"✅ IV Rankings saved to {iv_rankings_file}")
    
    return result

if __name__ == "__main__":
    import sys
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2
    run_nasdaq100_scan(threshold=threshold)
