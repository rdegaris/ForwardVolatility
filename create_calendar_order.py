"""
Create Calendar Spread Order in TWS

Usage:
    python create_calendar_order.py ADBE 340 20251212 20260109 10
    python create_calendar_order.py AVGO 400 20251212 20260109 5
    
Arguments:
    ticker       - Stock symbol (e.g., ADBE, AVGO)
    strike       - Strike price (e.g., 340)
    front_expiry - Front month expiration YYYYMMDD (e.g., 20251212)
    back_expiry  - Back month expiration YYYYMMDD (e.g., 20260109)
    quantity     - Number of spreads (e.g., 10)

The order is placed in TWS but NOT transmitted - review and transmit manually.
"""

import sys
from ib_insync import IB, Option, ComboLeg, Contract, LimitOrder


def create_calendar_order(ticker: str, strike: float, front_expiry: str, back_expiry: str, quantity: int = 10, transmit: bool = False):
    """Create a calendar spread order in TWS.
    
    Args:
        ticker: Stock symbol
        strike: Strike price
        front_expiry: Front month expiration (YYYYMMDD format)
        back_expiry: Back month expiration (YYYYMMDD format)
        quantity: Number of spreads (default 10)
        transmit: Whether to transmit immediately (default False)
    """
    
    print("=" * 60)
    print(f"CREATING CALENDAR SPREAD ORDER")
    print("=" * 60)
    print()
    print(f"Ticker: {ticker}")
    print(f"Strike: ${strike}")
    print(f"Front Expiry: {front_expiry}")
    print(f"Back Expiry: {back_expiry}")
    print(f"Quantity: {quantity}")
    print()
    
    # Connect to IB
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7498, clientId=100)
        print('[OK] Connected to IB')
    except Exception as e:
        print(f'[ERROR] Could not connect to IB: {e}')
        print('Make sure TWS is running with API enabled on port 7498')
        return None
    
    try:
        # Create option contracts
        front_call = Option(ticker, front_expiry, strike, 'C', 'SMART')
        back_call = Option(ticker, back_expiry, strike, 'C', 'SMART')
        
        # Qualify contracts
        ib.qualifyContracts(front_call, back_call)
        print(f'Front: {front_call.localSymbol}')
        print(f'Back: {back_call.localSymbol}')
        
        # Get current prices
        front_data = ib.reqMktData(front_call, '', False, False)
        back_data = ib.reqMktData(back_call, '', False, False)
        ib.sleep(2)
        
        front_bid = front_data.bid if front_data.bid and front_data.bid > 0 else None
        front_ask = front_data.ask if front_data.ask and front_data.ask > 0 else None
        back_bid = back_data.bid if back_data.bid and back_data.bid > 0 else None
        back_ask = back_data.ask if back_data.ask and back_data.ask > 0 else None
        
        if front_bid and front_ask:
            front_mid = (front_bid + front_ask) / 2
        else:
            print('[WARNING] No front month prices available')
            front_mid = None
            
        if back_bid and back_ask:
            back_mid = (back_bid + back_ask) / 2
        else:
            print('[WARNING] No back month prices available')
            back_mid = None
        
        if front_mid and back_mid:
            net_debit = back_mid - front_mid
        else:
            print('[ERROR] Cannot calculate net debit without prices')
            ib.cancelMktData(front_call)
            ib.cancelMktData(back_call)
            ib.disconnect()
            return None
        
        print()
        print("-" * 60)
        print("PRICING")
        print("-" * 60)
        print(f"Front {front_expiry} ${strike}C: Bid ${front_bid:.2f} / Ask ${front_ask:.2f} / Mid ${front_mid:.2f}")
        print(f"Back  {back_expiry} ${strike}C: Bid ${back_bid:.2f} / Ask ${back_ask:.2f} / Mid ${back_mid:.2f}")
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
        leg1.conId = front_call.conId
        leg1.ratio = 1
        leg1.action = 'SELL'
        leg1.exchange = 'SMART'
        
        # Leg 2: BUY back
        leg2 = ComboLeg()
        leg2.conId = back_call.conId
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
        print(f"{ticker} {front_expiry[:6]}/{back_expiry[:6]} {int(strike)} Calendar Call    {quantity}")
        print(f"    {ticker} {front_expiry} {int(strike)} CALL              -{quantity}")
        print(f"    {ticker} {back_expiry} {int(strike)} CALL               {quantity}")
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
        ib.cancelMktData(front_call)
        ib.cancelMktData(back_call)
        
        return {
            'ticker': ticker,
            'strike': strike,
            'front_expiry': front_expiry,
            'back_expiry': back_expiry,
            'quantity': quantity,
            'front_mid': front_mid,
            'back_mid': back_mid,
            'net_debit': net_debit,
            'total_cost': net_debit * quantity * 100,
            'order_id': trade.order.orderId,
            'status': trade.orderStatus.status
        }
        
    finally:
        ib.disconnect()
        print()
        print('[OK] Disconnected from IB')


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        print()
        print("Example: python create_calendar_order.py ADBE 340 20251212 20260109 10")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    strike = float(sys.argv[2])
    front_expiry = sys.argv[3]
    back_expiry = sys.argv[4]
    quantity = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    
    create_calendar_order(ticker, strike, front_expiry, back_expiry, quantity)


if __name__ == "__main__":
    main()
