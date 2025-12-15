"""
Place Calendar Spread Orders in TWS (without transmitting)
Requires: ib_insync library and IB Gateway/TWS running

This script creates calendar spread orders from scan results but does NOT transmit them.
Orders will appear in TWS ready for review before execution.
"""

import json
import sys
import argparse
import os
from datetime import datetime, timedelta
import time

try:
    from ib_insync import IB, Stock, Option, ComboLeg, Contract, LimitOrder
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    print("ERROR: ib_insync not installed")
    print("Install with: pip install ib_insync")
    sys.exit(1)


class CalendarOrderPlacer:
    """Places calendar spread orders in TWS without transmitting."""
    
    def __init__(self, host=None, port=None, client_id=None):
        """
        Initialize IB connection.
        
        Args:
            host: IB Gateway/TWS host (default: localhost)
            port: 7498 for TWS (matching scanner default)
            client_id: Unique client ID (use different from scanner)
        """
        if host is None:
            host = os.environ.get('IB_HOST', '127.0.0.1')
        if port is None:
            port = int(os.environ.get('IB_PORT', '7498'))
        if client_id is None:
            client_id = int(os.environ.get('IB_CLIENT_ID', '10'))
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
    
    def connect(self, max_retries=3):
        """Connect to IB Gateway or TWS with retry logic."""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt
                    print(f"  Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                
                print(f"Connecting to Interactive Brokers at {self.host}:{self.port}...")
                self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10)
                self.connected = True
                print("  Connected successfully!")
                return True
            except Exception as e:
                print(f"  Connection failed: {e}")
                if attempt == max_retries - 1:
                    print("\nMake sure TWS is running and API connections are enabled")
                    return False
        return False
    
    def disconnect(self):
        """Disconnect from IB."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            print("Disconnected from IB")
    
    def create_calendar_spread(self, ticker: str, strike: float, expiry_front: str, 
                                expiry_back: str, option_type: str = 'C') -> Contract:
        """
        Create a calendar spread combo contract.
        
        Args:
            ticker: Stock symbol
            strike: Strike price
            expiry_front: Front month expiry (YYYYMMDD format)
            expiry_back: Back month expiry (YYYYMMDD format)
            option_type: 'C' for call, 'P' for put
        
        Returns:
            Combo contract for the calendar spread
        """
        # Create option contracts
        front_option = Option(ticker, expiry_front, strike, option_type, 'SMART')
        back_option = Option(ticker, expiry_back, strike, option_type, 'SMART')
        
        # Qualify contracts to get conIds
        self.ib.qualifyContracts(front_option, back_option)
        
        print(f"  Front leg: {front_option.localSymbol} (conId: {front_option.conId})")
        print(f"  Back leg:  {back_option.localSymbol} (conId: {back_option.conId})")
        
        # Create combo legs
        # Sell front month (action=SELL, ratio=1)
        front_leg = ComboLeg(
            conId=front_option.conId,
            ratio=1,
            action='SELL',
            exchange='SMART'
        )
        
        # Buy back month (action=BUY, ratio=1)
        back_leg = ComboLeg(
            conId=back_option.conId,
            ratio=1,
            action='BUY',
            exchange='SMART'
        )
        
        # Create the combo contract
        combo = Contract()
        combo.symbol = ticker
        combo.secType = 'BAG'
        combo.currency = 'USD'
        combo.exchange = 'SMART'
        combo.comboLegs = [front_leg, back_leg]
        
        return combo
    
    def place_calendar_order(self, ticker: str, strike: float, expiry_front: str,
                              expiry_back: str, option_type: str = 'C',
                              quantity: int = 1, limit_price: float = None,
                              transmit: bool = False):
        """
        Place a calendar spread order in TWS as a single combo order.
        
        Args:
            ticker: Stock symbol
            strike: Strike price
            expiry_front: Front month expiry (YYYYMMDD format)
            expiry_back: Back month expiry (YYYYMMDD format)
            option_type: 'C' for call, 'P' for put
            quantity: Number of spreads (default: 1)
            limit_price: Limit price for the spread (net debit, positive value)
            transmit: If False, order appears in TWS but isn't sent (default: False)
        
        Returns:
            Trade object or None on error
        """
        try:
            print(f"\nCreating {option_type} calendar spread for {ticker}:")
            print(f"  Strike: ${strike}")
            print(f"  Front: {expiry_front} (SELL)")
            print(f"  Back:  {expiry_back} (BUY)")
            print(f"  Qty:   {quantity}")
            
            # Create option contracts
            front_option = Option(ticker, expiry_front, strike, option_type, 'SMART')
            back_option = Option(ticker, expiry_back, strike, option_type, 'SMART')
            
            # Qualify contracts to get conIds
            print(f"  Qualifying contracts...")
            self.ib.qualifyContracts(front_option, back_option)
            self.ib.sleep(0.5)
            
            print(f"  Front: {front_option.localSymbol} (conId: {front_option.conId})")
            print(f"  Back:  {back_option.localSymbol} (conId: {back_option.conId})")
            
            # Get current prices for the spread
            print(f"  Getting option prices...")
            front_ticker = self.ib.reqMktData(front_option, '', False, False)
            back_ticker = self.ib.reqMktData(back_option, '', False, False)
            self.ib.sleep(2)
            
            # Get mid prices
            front_bid = front_ticker.bid if front_ticker.bid and front_ticker.bid > 0 else 0
            front_ask = front_ticker.ask if front_ticker.ask and front_ticker.ask > 0 else 0
            front_mid = (front_bid + front_ask) / 2 if front_bid and front_ask else front_ticker.last or 0
            
            back_bid = back_ticker.bid if back_ticker.bid and back_ticker.bid > 0 else 0
            back_ask = back_ticker.ask if back_ticker.ask and back_ticker.ask > 0 else 0
            back_mid = (back_bid + back_ask) / 2 if back_bid and back_ask else back_ticker.last or 0
            
            # Cancel market data
            self.ib.cancelMktData(front_option)
            self.ib.cancelMktData(back_option)
            
            current_debit = back_mid - front_mid
            print(f"  Front mid: ${front_mid:.2f}")
            print(f"  Back mid:  ${back_mid:.2f}")
            print(f"  Current spread: ${current_debit:.2f}")
            
            # Create combo legs
            # Sell front month (action=SELL, ratio=1)
            front_leg = ComboLeg(
                conId=front_option.conId,
                ratio=1,
                action='SELL',
                exchange='SMART'
            )
            
            # Buy back month (action=BUY, ratio=1)
            back_leg = ComboLeg(
                conId=back_option.conId,
                ratio=1,
                action='BUY',
                exchange='SMART'
            )
            
            # Create the combo contract
            combo = Contract()
            combo.symbol = ticker
            combo.secType = 'BAG'
            combo.currency = 'USD'
            combo.exchange = 'SMART'
            combo.comboLegs = [front_leg, back_leg]
            
            # Determine limit price
            # Use provided limit_price, or current spread, or minimal
            if limit_price is not None:
                spread_limit = limit_price
            elif current_debit > 0:
                spread_limit = round(current_debit, 2)
            else:
                spread_limit = 0.05
            
            # Create limit order for the combo
            # For calendar spread debit: positive limit price = max we'll pay
            order = LimitOrder(
                action='BUY',  # BUY the spread = buy back, sell front
                totalQuantity=quantity,
                lmtPrice=spread_limit,
                transmit=transmit,
                tif='DAY'
            )
            order.orderRef = f'Cal-{ticker}-{expiry_front[:6]}'
            
            print(f"\n  Placing COMBO order...")
            print(f"  Spread: SELL {front_option.localSymbol} / BUY {back_option.localSymbol}")
            print(f"  Limit:  ${spread_limit:.2f} debit")
            print(f"  Transmit: {transmit}")
            
            # Place the combo order
            trade = self.ib.placeOrder(combo, order)
            self.ib.sleep(1)
            
            print(f"\n  ✅ Calendar spread staged in TWS!")
            print(f"  Order ID: {trade.order.orderId}")
            print(f"  Status: {trade.orderStatus.status}")
            
            return trade
            
        except Exception as e:
            print(f"\n  ❌ Error placing order: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def place_orders_from_json(self, json_file: str, tickers: list = None,
                                quantity: int = 1, transmit: bool = False):
        """
        Place orders for opportunities in a scan results JSON file.
        
        Args:
            json_file: Path to scan results JSON
            tickers: List of tickers to include (None = all)
            quantity: Contracts per trade (default: 1)
            transmit: If True, actually send orders (default: False)
        """
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        opportunities = data.get('opportunities', [])
        
        if not opportunities:
            print("No opportunities found in JSON file")
            return
        
        # Filter by tickers if specified
        if tickers:
            tickers = [t.upper() for t in tickers]
            opportunities = [o for o in opportunities if o['ticker'] in tickers]
        
        print(f"\n{'=' * 60}")
        print(f"STAGING {len(opportunities)} CALENDAR SPREAD ORDER(S)")
        print(f"{'=' * 60}")
        print(f"Transmit: {transmit}")
        print()
        
        placed = []
        failed = []
        
        for opp in opportunities:
            ticker = opp['ticker']
            trade_details = opp.get('trade_details', {})
            
            # Get trade parameters
            strike = trade_details.get('strike')
            spread_type = trade_details.get('spread_type', 'CALL')
            option_type = 'C' if spread_type.upper() == 'CALL' else 'P'
            net_debit = trade_details.get('net_debit')
            
            expiry_front = opp.get('expiry1')
            expiry_back = opp.get('expiry2')
            
            if not all([strike, expiry_front, expiry_back]):
                print(f"\n⚠️ Skipping {ticker}: Missing trade details")
                failed.append(ticker)
                continue
            
            # Place the order
            trades = self.place_calendar_order(
                ticker=ticker,
                strike=strike,
                expiry_front=expiry_front,
                expiry_back=expiry_back,
                option_type=option_type,
                quantity=quantity,
                limit_price=net_debit,
                transmit=transmit
            )
            
            if trades:
                placed.append({
                    'ticker': ticker,
                    'strike': strike,
                    'type': spread_type,
                    'front': expiry_front,
                    'back': expiry_back,
                    'price': net_debit,
                    'order_id': trades.order.orderId
                })
            else:
                failed.append(ticker)
        
        # Summary
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        print(f"✅ Orders staged: {len(placed)}")
        print(f"❌ Failed: {len(failed)}")
        
        if placed:
            print("\nStaged Orders:")
            for p in placed:
                print(f"  • {p['ticker']} {p['type']} ${p['strike']} "
                      f"{p['front']}/{p['back']} @ ${p['price']:.2f} "
                      f"(Order #{p['order_id']})")
        
        if failed:
            print(f"\nFailed: {', '.join(failed)}")
        
        print("\n⚠️ Orders are STAGED in TWS but NOT transmitted.")
        print("   Review in TWS and manually transmit when ready.")
        
        return placed


def main():
    parser = argparse.ArgumentParser(description='Place calendar spread orders in TWS')
    parser.add_argument('--file', '-f', type=str, default='nasdaq100_results_latest.json',
                        help='Scan results JSON file (default: nasdaq100_results_latest.json)')
    parser.add_argument('--tickers', '-t', type=str, nargs='+',
                        help='Specific tickers to place orders for (default: all)')
    parser.add_argument('--quantity', '-q', type=int, default=1,
                        help='Number of contracts per spread (default: 1)')
    parser.add_argument('--port', '-p', type=int, default=7498,
                        help='TWS port (default: 7498 to match scanner)')
    parser.add_argument('--transmit', action='store_true',
                        help='Actually transmit orders (default: False, just stage)')
    parser.add_argument('--single', '-s', type=str, nargs=5,
                        metavar=('TICKER', 'STRIKE', 'FRONT_EXPIRY', 'BACK_EXPIRY', 'PRICE'),
                        help='Place a single order: TICKER STRIKE FRONT_EXP BACK_EXP PRICE')
    
    args = parser.parse_args()
    
    placer = CalendarOrderPlacer(port=args.port)
    
    if not placer.connect():
        sys.exit(1)
    
    try:
        if args.single:
            # Single order mode
            ticker, strike, front, back, price = args.single
            placer.place_calendar_order(
                ticker=ticker,
                strike=float(strike),
                expiry_front=front,
                expiry_back=back,
                option_type='C',  # Default to calls
                quantity=args.quantity,
                limit_price=float(price),
                transmit=args.transmit
            )
        else:
            # Batch mode from JSON
            placer.place_orders_from_json(
                json_file=args.file,
                tickers=args.tickers,
                quantity=args.quantity,
                transmit=args.transmit
            )
    
    finally:
        placer.disconnect()


if __name__ == '__main__':
    main()
