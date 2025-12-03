"""
Fetch open calendar spread positions from Interactive Brokers.

This script connects to IB TWS/Gateway and retrieves open option positions,
identifies calendar spreads, and exports them in a format compatible with
the Forward Volatility Trade Tracker web app.

Requirements:
    pip install ib_insync

Usage:
    1. Start IB TWS or Gateway with API enabled (port 7497 for TWS, 4002 for Gateway)
    2. Run: python fetch_ib_positions.py
    3. Import the generated trades.json file into the Trade Tracker web app
"""

from ib_insync import IB, Stock, Option
import json
from datetime import datetime, date
from collections import defaultdict
import os


def connect_to_ib(host='127.0.0.1', port=7497, client_id=1):
    """
    Connect to Interactive Brokers TWS or Gateway.
    
    Args:
        host: IB host (default: localhost)
        port: 7497 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
        client_id: Unique client ID
    
    Returns:
        Connected IB instance
    """
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        print(f"[OK] Connected to IB on {host}:{port}")
        return ib
    except Exception as e:
        print(f"[ERROR] Failed to connect to IB: {e}")
        print("\nMake sure:")
        print("1. TWS or IB Gateway is running")
        print("2. API connections are enabled (File > Global Configuration > API > Settings)")
        print("3. Port number is correct (7497 for TWS paper, 4002 for Gateway paper)")
        raise


def get_option_positions(ib):
    """
    Fetch all option positions from IB.
    
    Returns:
        List of option positions
    """
    print("\n[INFO] Fetching positions from IB...")
    
    positions = ib.positions()
    
    option_positions = []
    for position in positions:
        contract = position.contract
        if isinstance(contract, Option):
            option_positions.append({
                'contract': contract,
                'position': position.position,  # Positive = long, negative = short
                'avgCost': position.avgCost,
            })
    
    print(f"Found {len(option_positions)} option positions")
    return option_positions


def identify_calendar_spreads(option_positions, ib):
    """
    Identify calendar spreads from option positions.
    
    Calendar spread criteria:
    - Same underlying symbol
    - Same strike price
    - Same option type (CALL or PUT)
    - Different expiration dates
    - One long position and one short position
    
    Returns:
        List of calendar spreads
    """
    print("\n[INFO] Identifying calendar spreads...")
    
    # Group positions by symbol, strike, and right (CALL/PUT)
    groups = defaultdict(list)
    
    for pos in option_positions:
        contract = pos['contract']
        key = (contract.symbol, contract.strike, contract.right)
        groups[key].append(pos)
    
    calendar_spreads = []
    
    for key, positions in groups.items():
        if len(positions) < 2:
            continue
        
        symbol, strike, right = key
        
        # Sort by expiration date
        positions_sorted = sorted(positions, key=lambda x: x['contract'].lastTradeDateOrContractMonth)
        
        # Look for pairs: short front month + long back month
        for i in range(len(positions_sorted) - 1):
            front = positions_sorted[i]
            back = positions_sorted[i + 1]
            
            # Calendar spread: short front, long back
            if front['position'] < 0 and back['position'] > 0:
                quantity = abs(front['position'])
                
                # Get current option prices
                front_contract = front['contract']
                back_contract = back['contract']
                
                # Request market data
                ib.qualifyContracts(front_contract, back_contract)
                
                front_ticker = ib.reqMktData(front_contract, '', False, False)
                back_ticker = ib.reqMktData(back_contract, '', False, False)
                ib.sleep(3)  # Wait longer for data
                
                # Get underlying price
                underlying = Stock(symbol, 'SMART', 'USD')
                ib.qualifyContracts(underlying)
                underlying_ticker = ib.reqMktData(underlying, '', False, False)
                ib.sleep(2)  # Wait for underlying data
                
                front_current = get_option_price(front_ticker)
                back_current = get_option_price(back_ticker)
                underlying_price = get_stock_price(underlying_ticker)
                
                # Skip if we couldn't get valid prices
                if front_current is None or back_current is None or underlying_price is None:
                    print(f"  [WARN] Skipping {symbol} ${strike} {right} - could not get valid market data")
                    continue
                
                # Calculate entry prices per share
                # IB avgCost is in cents PER CONTRACT (not total), so just divide by 100 to get dollars
                # Do NOT divide by position - avgCost is already per-contract
                front_entry_per_share = abs(front['avgCost']) / 100
                back_entry_per_share = abs(back['avgCost']) / 100
                
                # Calculate unrealized P&L
                # For short front: PnL = (entry - current) * contracts * 100
                # For long back: PnL = (current - entry) * contracts * 100
                front_pnl = (front_entry_per_share - front_current) * abs(front['position']) * 100
                back_pnl = (back_current - back_entry_per_share) * abs(back['position']) * 100
                
                calendar_spreads.append({
                    'symbol': symbol,
                    'strike': strike,
                    'right': right,
                    'quantity': quantity,
                    'front': {
                        'contract': front_contract,
                        'position': front['position'],
                        'avgCost': abs(front['avgCost']),
                        'currentPrice': front_current,
                        'unrealizedPnL': front_pnl,
                    },
                    'back': {
                        'contract': back_contract,
                        'position': back['position'],
                        'avgCost': abs(back['avgCost']),
                        'currentPrice': back_current,
                        'unrealizedPnL': back_pnl,
                    },
                    'underlying': {
                        'currentPrice': underlying_price,
                    }
                })
                
                print(f"  [+] Found: {quantity}x {symbol} ${strike} {right} calendar spread")
                print(f"    Front: {front_contract.lastTradeDateOrContractMonth} @ ${get_option_price(front_ticker):.2f}")
                print(f"    Back:  {back_contract.lastTradeDateOrContractMonth} @ ${get_option_price(back_ticker):.2f}")
    
    if not calendar_spreads:
        print("  [INFO] No calendar spreads found in current positions")
    
    return calendar_spreads


def get_option_price(ticker):
    """Get current option price from ticker, prefer last price, fall back to mid."""
    import math
    
    # Debug: print what we're getting
    print(f"      Debug - last:{ticker.last}, bid:{ticker.bid}, ask:{ticker.ask}, close:{ticker.close}")
    
    if ticker.last and not math.isnan(ticker.last) and ticker.last > 0:
        return ticker.last
    elif ticker.bid and ticker.ask and not math.isnan(ticker.bid) and not math.isnan(ticker.ask):
        mid = (ticker.bid + ticker.ask) / 2
        if mid > 0:
            return mid
    elif ticker.close and not math.isnan(ticker.close) and ticker.close > 0:
        return ticker.close
    elif ticker.modelGreeks and ticker.modelGreeks.optPrice:
        # Try model price as last resort
        return ticker.modelGreeks.optPrice
    return None


def get_stock_price(ticker):
    """Get current stock price from ticker."""
    import math
    if ticker.last and not math.isnan(ticker.last) and ticker.last > 0:
        return ticker.last
    elif ticker.bid and ticker.ask and not math.isnan(ticker.bid) and not math.isnan(ticker.ask):
        return (ticker.bid + ticker.ask) / 2
    elif ticker.close and not math.isnan(ticker.close) and ticker.close > 0:
        return ticker.close
    return None


def format_date(ib_date_str):
    """Convert IB date format (YYYYMMDD) to ISO format (YYYY-MM-DD)."""
    try:
        dt = datetime.strptime(ib_date_str, '%Y%m%d')
        return dt.strftime('%Y-%m-%d')
    except:
        return ib_date_str


def export_to_json(calendar_spreads, filename='trades.json'):
    """
    Export calendar spreads to JSON format compatible with Trade Tracker.
    
    Trade Tracker format:
    {
      id: string,
      symbol: string,
      strike: number,
      callOrPut: 'CALL' | 'PUT',
      quantity: number,
      frontExpiration: string (YYYY-MM-DD),
      frontEntryPrice: number,
      frontCurrentPrice: number,
      backExpiration: string (YYYY-MM-DD),
      backEntryPrice: number,
      backCurrentPrice: number,
      underlyingEntryPrice: number,
      underlyingCurrentPrice: number,
      entryDate: string (YYYY-MM-DD)
    }
    """
    print(f"\n[INFO] Exporting {len(calendar_spreads)} calendar spreads to {filename}...")
    
    trades = []
    
    for i, spread in enumerate(calendar_spreads):
        # Calculate entry prices per share
        # IB avgCost is in cents PER CONTRACT, so just divide by 100 to get dollars
        front_entry = abs(spread['front']['avgCost']) / 100
        back_entry = abs(spread['back']['avgCost']) / 100
        
        # Calculate total unrealized P&L for the spread
        # Calendar spread: long back - short front, so back PnL - front PnL
        front_pnl = spread['front']['unrealizedPnL']
        back_pnl = spread['back']['unrealizedPnL']
        total_unrealized_pnl = back_pnl - front_pnl
        
        trade = {
            'id': f"ib_{int(datetime.now().timestamp())}_{i}",
            'symbol': spread['symbol'],
            'strike': float(spread['strike']),
            'callOrPut': 'CALL' if spread['right'] == 'C' else 'PUT',
            'quantity': int(spread['quantity']),
            'frontExpiration': format_date(spread['front']['contract'].lastTradeDateOrContractMonth),
            'frontEntryPrice': round(front_entry, 2),
            'frontCurrentPrice': round(spread['front']['currentPrice'], 2),
            'frontUnrealizedPnL': round(front_pnl, 2),
            'backExpiration': format_date(spread['back']['contract'].lastTradeDateOrContractMonth),
            'backEntryPrice': round(back_entry, 2),
            'backCurrentPrice': round(spread['back']['currentPrice'], 2),
            'backUnrealizedPnL': round(back_pnl, 2),
            'underlyingEntryPrice': round(spread['underlying']['currentPrice'], 2),  # Using current as we don't have historical
            'underlyingCurrentPrice': round(spread['underlying']['currentPrice'], 2),
            'entryDate': date.today().strftime('%Y-%m-%d'),
            'unrealizedPnL': round(total_unrealized_pnl, 2),
            'status': 'open',
        }
        
        trades.append(trade)
        
        # Calculate P&L
        pnl = ((trade['backCurrentPrice'] - trade['backEntryPrice']) - 
               (trade['frontCurrentPrice'] - trade['frontEntryPrice'])) * trade['quantity'] * 100
        
        print(f"  {trade['quantity']}x {trade['symbol']} ${trade['strike']} {trade['callOrPut']}")
        print(f"    Front: {trade['frontExpiration']} | Entry: ${trade['frontEntryPrice']:.2f} | Current: ${trade['frontCurrentPrice']:.2f}")
        print(f"    Back:  {trade['backExpiration']} | Entry: ${trade['backEntryPrice']:.2f} | Current: ${trade['backCurrentPrice']:.2f}")
        print(f"    P&L: ${pnl:.2f}")
    
    # Write to JSON file
    with open(filename, 'w') as f:
        json.dump(trades, f, indent=2)
    
    print(f"\n[OK] Exported to {filename}")
    print(f"\n[INSTRUCTIONS] To import into Trade Tracker:")
    print(f"   1. Copy {filename} content")
    print(f"   2. Go to Trade Tracker page")
    print(f"   3. Click 'Import from JSON' button")
    print(f"   4. Paste and import")
    
    return filename


def main():
    """Main function to fetch and export IB positions."""
    print("=" * 60)
    print("Interactive Brokers Calendar Spread Position Fetcher")
    print("=" * 60)
    
    # Configuration
    HOST = '127.0.0.1'
    PORT = 7498  # 7498 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
    CLIENT_ID = 1
    
    ib = None
    try:
        # Connect to IB
        ib = connect_to_ib(HOST, PORT, CLIENT_ID)
        
        # Get option positions
        option_positions = get_option_positions(ib)
        
        if not option_positions:
            print("\n[WARNING] No option positions found")
            return
        
        # Identify calendar spreads
        calendar_spreads = identify_calendar_spreads(option_positions, ib)
        
        if not calendar_spreads:
            print("\n[WARNING] No calendar spreads found in positions")
            return
        
        # Export to JSON
        filename = export_to_json(calendar_spreads)
        
        print(f"\n[OK] Complete! Found {len(calendar_spreads)} calendar spreads")
        print(f"   JSON file: {os.path.abspath(filename)}")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if ib and ib.isConnected():
            ib.disconnect()
            print("\n[INFO] Disconnected from IB")


if __name__ == '__main__':
    main()
