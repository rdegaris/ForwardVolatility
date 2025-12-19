"""
Setup Forward Volatility Trade from Scan Results

Reads the latest scan results and creates a calendar spread order in TWS.

Usage:
    python setup_forward_vol_trade.py RIVN
    python setup_forward_vol_trade.py RIVN 10
    python setup_forward_vol_trade.py RIVN 10 --transmit
    
Arguments:
    ticker    - Stock symbol from scan results
    quantity  - Number of spreads (default 10)
    --transmit - Transmit order immediately (default: don't transmit)

The script reads from nasdaq100_results_latest.json and midcap400_results_latest.json
"""

import sys
import json
import os
from ib_insync import IB, Option, ComboLeg, Contract, LimitOrder


IB_HOST = os.environ.get("IB_HOST", "127.0.0.1")
IB_PORT = int(os.environ.get("IB_PORT", "7498"))
IB_CLIENT_ID = int(os.environ.get("IB_CLIENT_ID", "101"))


def load_opportunity(ticker: str) -> dict:
    """Load opportunity details from scan results."""
    
    # Check both scan result files
    files = [
        'nasdaq100_results_latest.json',
        'midcap400_results_latest.json'
    ]
    
    for filename in files:
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            for opp in data.get('opportunities', []):
                if opp.get('ticker') == ticker:
                    return opp
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"[WARNING] Error reading {filename}: {e}")
            continue
    
    return None


def setup_trade(ticker: str, quantity: int = 10, transmit: bool = False):
    """Setup forward vol calendar spread trade from scan results."""
    
    print("=" * 60)
    print(f"FORWARD VOLATILITY TRADE SETUP")
    print("=" * 60)
    print()
    
    # Load opportunity from scan results
    opp = load_opportunity(ticker)
    
    if not opp:
        print(f"[ERROR] {ticker} not found in scan results")
        print("Run a scan first or check the ticker symbol")
        return None
    
    # Extract trade details
    price = opp['price']
    strike = opp.get('trade_details', {}).get('strike') or round(price)
    front_expiry = opp['expiry1']
    back_expiry = opp['expiry2']
    spread_type = opp.get('trade_details', {}).get('spread_type', 'CALL')
    ff = opp.get('best_ff', opp.get('ff_avg', 0))
    front_iv = opp.get('avg_iv1', 0)
    back_iv = opp.get('avg_iv2', 0)
    above_ma = opp.get('above_ma_200')
    ma_200 = opp.get('ma_200')
    dte1 = opp.get('dte1', 0)
    dte2 = opp.get('dte2', 0)
    
    print(f"Ticker: {ticker}")
    print(f"Price: ${price:.2f}")
    if ma_200:
        trend = "ABOVE" if above_ma else "BELOW"
        print(f"200-day MA: ${ma_200:.2f} ({trend})")
    print()
    print(f"Forward Factor: {ff:.3f}")
    print(f"Front IV: {front_iv:.1f}% ({dte1} DTE)")
    print(f"Back IV: {back_iv:.1f}% ({dte2} DTE)")
    print(f"IV Slope: {((front_iv/back_iv - 1) * 100):.1f}%")
    print()
    print(f"Trade: {spread_type} Calendar Spread")
    print(f"Strike: ${strike}")
    print(f"Front: {front_expiry}")
    print(f"Back: {back_expiry}")
    print(f"Quantity: {quantity}")
    print()
    
    # Connect to IB
    ib = IB()
    try:
        ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID)
        print('[OK] Connected to IB')
    except Exception as e:
        print(f'[ERROR] Could not connect to IB: {e}')
        return None
    
    try:
        # Create option contracts
        right = 'C' if spread_type == 'CALL' else 'P'
        front_opt = Option(ticker, front_expiry, strike, right, 'SMART')
        back_opt = Option(ticker, back_expiry, strike, right, 'SMART')
        
        # Qualify contracts
        ib.qualifyContracts(front_opt, back_opt)
        print(f'Front: {front_opt.localSymbol}')
        print(f'Back: {back_opt.localSymbol}')
        
        # Get current prices
        front_data = ib.reqMktData(front_opt, '', False, False)
        back_data = ib.reqMktData(back_opt, '', False, False)
        ib.sleep(2)
        
        front_bid = front_data.bid if front_data.bid and front_data.bid > 0 else None
        front_ask = front_data.ask if front_data.ask and front_data.ask > 0 else None
        back_bid = back_data.bid if back_data.bid and back_data.bid > 0 else None
        back_ask = back_data.ask if back_data.ask and back_data.ask > 0 else None
        
        if front_bid and front_ask:
            front_mid = (front_bid + front_ask) / 2
        else:
            print('[ERROR] No front month prices')
            return None
            
        if back_bid and back_ask:
            back_mid = (back_bid + back_ask) / 2
        else:
            print('[ERROR] No back month prices')
            return None
        
        net_debit = back_mid - front_mid
        
        print()
        print("-" * 60)
        print("LIVE PRICING")
        print("-" * 60)
        print(f"Front {front_expiry} ${strike}{right}: Bid ${front_bid:.2f} / Ask ${front_ask:.2f} / Mid ${front_mid:.2f}")
        print(f"Back  {back_expiry} ${strike}{right}: Bid ${back_bid:.2f} / Ask ${back_ask:.2f} / Mid ${back_mid:.2f}")
        print()
        print(f"Net Debit: ${net_debit:.2f} per spread")
        print(f"Total Cost: ${net_debit * quantity * 100:.0f} for {quantity} spreads")
        print()
        
        # Create calendar spread combo
        calendar = Contract()
        calendar.symbol = ticker
        calendar.secType = 'BAG'
        calendar.currency = 'USD'
        calendar.exchange = 'SMART'
        
        # Leg 1: SELL front
        leg1 = ComboLeg()
        leg1.conId = front_opt.conId
        leg1.ratio = 1
        leg1.action = 'SELL'
        leg1.exchange = 'SMART'
        
        # Leg 2: BUY back
        leg2 = ComboLeg()
        leg2.conId = back_opt.conId
        leg2.ratio = 1
        leg2.action = 'BUY'
        leg2.exchange = 'SMART'
        
        calendar.comboLegs = [leg1, leg2]
        
        # Create limit order
        order = LimitOrder('BUY', quantity, round(net_debit, 2))
        order.transmit = transmit
        order.tif = 'DAY'
        
        # Place order
        trade = ib.placeOrder(calendar, order)
        ib.sleep(1)
        
        print("=" * 60)
        print("ORDER PLACED" + (" AND TRANSMITTED" if transmit else " (NOT TRANSMITTED)"))
        print("=" * 60)
        print()
        print(f"{ticker} {front_expiry[:6]}/{back_expiry[:6]} {int(strike)} Calendar {spread_type}    {quantity}")
        print(f"    {ticker} {front_expiry} {int(strike)} {spread_type}              -{quantity}")
        print(f"    {ticker} {back_expiry} {int(strike)} {spread_type}               {quantity}")
        print()
        print(f"Limit: ${net_debit:.2f} debit")
        print(f"Total: ${net_debit * quantity * 100:.0f}")
        print()
        print(f"Order ID: {trade.order.orderId}")
        print(f"Status: {trade.orderStatus.status}")
        print()
        
        if not transmit:
            print("[!] Review in TWS and transmit when ready!")
        
        # Cleanup
        ib.cancelMktData(front_opt)
        ib.cancelMktData(back_opt)
        
        return {
            'ticker': ticker,
            'strike': strike,
            'spread_type': spread_type,
            'front_expiry': front_expiry,
            'back_expiry': back_expiry,
            'quantity': quantity,
            'ff': ff,
            'front_mid': front_mid,
            'back_mid': back_mid,
            'net_debit': net_debit,
            'total_cost': net_debit * quantity * 100,
            'order_id': trade.order.orderId
        }
        
    finally:
        ib.disconnect()
        print()
        print('[OK] Disconnected from IB')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print()
        print("Example: python setup_forward_vol_trade.py RIVN 10")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    quantity = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != '--transmit' else 10
    transmit = '--transmit' in sys.argv
    
    setup_trade(ticker, quantity, transmit)


if __name__ == "__main__":
    main()
