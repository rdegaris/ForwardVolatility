"""
Get real-time option prices from Interactive Brokers for TSLA calendar spread
"""

import sys
sys.path.insert(0, '.')

from ib_insync import IB, Stock, Option
import time

def get_current_prices():
    """Fetch current option prices for TSLA $435 Oct 24 / Oct 31 spread."""
    
    print("=" * 80)
    print("TSLA CALENDAR SPREAD - CURRENT MARKET PRICES")
    print("=" * 80)
    print("\nConnecting to Interactive Brokers...")
    
    ib = IB()
    
    try:
        ib.connect('127.0.0.1', 7497, clientId=2)
        print("Connected!\n")
        
        # Get current stock price
        stock = Stock('TSLA', 'SMART', 'USD')
        ib.qualifyContracts(stock)
        
        ticker_data = ib.reqMktData(stock, '', False, False)
        ib.sleep(2)
        
        current_price = ticker_data.marketPrice() or ticker_data.last
        print(f"TSLA Current Price: ${current_price:.2f}")
        print("=" * 80)
        print()
        
        # Define options
        strike = 435.0
        
        # Front month - Oct 24
        front_call = Option('TSLA', '20251024', strike, 'C', 'SMART')
        front_put = Option('TSLA', '20251024', strike, 'P', 'SMART')
        
        # Back month - Oct 31
        back_call = Option('TSLA', '20251031', strike, 'C', 'SMART')
        back_put = Option('TSLA', '20251031', strike, 'P', 'SMART')
        
        # Qualify contracts
        ib.qualifyContracts(front_call, front_put, back_call, back_put)
        
        # Request market data
        print("Fetching option prices...\n")
        
        fc_ticker = ib.reqMktData(front_call, '', False, False)
        fp_ticker = ib.reqMktData(front_put, '', False, False)
        bc_ticker = ib.reqMktData(back_call, '', False, False)
        bp_ticker = ib.reqMktData(back_put, '', False, False)
        
        ib.sleep(3)
        
        print("=" * 80)
        print("FRONT MONTH (Oct 24, 8 DTE) - $435 Strike")
        print("=" * 80)
        
        # Front call
        fc_bid = fc_ticker.bid if fc_ticker.bid > 0 else None
        fc_ask = fc_ticker.ask if fc_ticker.ask > 0 else None
        fc_last = fc_ticker.last if fc_ticker.last > 0 else None
        fc_mid = (fc_bid + fc_ask) / 2 if fc_bid and fc_ask else fc_last
        
        fc_bid_str = f"${fc_bid:.2f}" if fc_bid else "N/A"
        fc_ask_str = f"${fc_ask:.2f}" if fc_ask else "N/A"
        fc_last_str = f"${fc_last:.2f}" if fc_last else "N/A"
        fc_mid_str = f"${fc_mid:.2f}" if fc_mid else "N/A"
        print(f"Call:  Bid: {fc_bid_str:>8}  |  Ask: {fc_ask_str:>8}  |  Last: {fc_last_str:>8}  |  Mid: {fc_mid_str:>8}")
        
        # Front put
        fp_bid = fp_ticker.bid if fp_ticker.bid > 0 else None
        fp_ask = fp_ticker.ask if fp_ticker.ask > 0 else None
        fp_last = fp_ticker.last if fp_ticker.last > 0 else None
        fp_mid = (fp_bid + fp_ask) / 2 if fp_bid and fp_ask else fp_last
        
        fp_bid_str = f"${fp_bid:.2f}" if fp_bid else "N/A"
        fp_ask_str = f"${fp_ask:.2f}" if fp_ask else "N/A"
        fp_last_str = f"${fp_last:.2f}" if fp_last else "N/A"
        fp_mid_str = f"${fp_mid:.2f}" if fp_mid else "N/A"
        print(f"Put:   Bid: {fp_bid_str:>8}  |  Ask: {fp_ask_str:>8}  |  Last: {fp_last_str:>8}  |  Mid: {fp_mid_str:>8}")
        
        print()
        print("=" * 80)
        print("BACK MONTH (Oct 31, 15 DTE) - $435 Strike")
        print("=" * 80)
        
        # Back call
        bc_bid = bc_ticker.bid if bc_ticker.bid > 0 else None
        bc_ask = bc_ticker.ask if bc_ticker.ask > 0 else None
        bc_last = bc_ticker.last if bc_ticker.last > 0 else None
        bc_mid = (bc_bid + bc_ask) / 2 if bc_bid and bc_ask else bc_last
        
        bc_bid_str = f"${bc_bid:.2f}" if bc_bid else "N/A"
        bc_ask_str = f"${bc_ask:.2f}" if bc_ask else "N/A"
        bc_last_str = f"${bc_last:.2f}" if bc_last else "N/A"
        bc_mid_str = f"${bc_mid:.2f}" if bc_mid else "N/A"
        print(f"Call:  Bid: {bc_bid_str:>8}  |  Ask: {bc_ask_str:>8}  |  Last: {bc_last_str:>8}  |  Mid: {bc_mid_str:>8}")
        
        # Back put
        bp_bid = bp_ticker.bid if bp_ticker.bid > 0 else None
        bp_ask = bp_ticker.ask if bp_ticker.ask > 0 else None
        bp_last = bp_ticker.last if bp_ticker.last > 0 else None
        bp_mid = (bp_bid + bp_ask) / 2 if bp_bid and bp_ask else bp_last
        
        bp_bid_str = f"${bp_bid:.2f}" if bp_bid else "N/A"
        bp_ask_str = f"${bp_ask:.2f}" if bp_ask else "N/A"
        bp_last_str = f"${bp_last:.2f}" if bp_last else "N/A"
        bp_mid_str = f"${bp_mid:.2f}" if bp_mid else "N/A"
        print(f"Put:   Bid: {bp_bid_str:>8}  |  Ask: {bp_ask_str:>8}  |  Last: {bp_last_str:>8}  |  Mid: {bp_mid_str:>8}")
        
        print()
        print("=" * 80)
        print("CALENDAR SPREAD PRICING (1 Contract)")
        print("=" * 80)
        print()
        
        # Call calendar spread
        print("CALL CALENDAR SPREAD (Buy Oct 31 Call, Sell Oct 24 Call):")
        print("-" * 80)
        
        # Best case: Sell front at bid, buy back at ask
        call_worst_fill = bc_ask - fc_bid if bc_ask and fc_bid else None
        # Best case: Sell front at ask, buy back at bid
        call_best_fill = bc_bid - fc_ask if bc_bid and fc_ask else None
        # Typical: Both at mid
        call_mid_fill = bc_mid - fc_mid if bc_mid and fc_mid else None
        
        if call_worst_fill:
            print(f"  Buy:  Oct 31 Call @ ${bc_ask:.2f} (ask)")
            print(f"  Sell: Oct 24 Call @ ${fc_bid:.2f} (bid)")
            print(f"  Net Debit (worst):   ${call_worst_fill:.2f} × 100 = ${call_worst_fill * 100:.2f}")
            print()
        
        if call_mid_fill:
            print(f"  Buy:  Oct 31 Call @ ${bc_mid:.2f} (mid)")
            print(f"  Sell: Oct 24 Call @ ${fc_mid:.2f} (mid)")
            print(f"  Net Debit (typical): ${call_mid_fill:.2f} × 100 = ${call_mid_fill * 100:.2f}")
            print()
        
        if call_best_fill:
            print(f"  Buy:  Oct 31 Call @ ${bc_bid:.2f} (bid)")
            print(f"  Sell: Oct 24 Call @ ${fc_ask:.2f} (ask)")
            print(f"  Net Debit (best):    ${call_best_fill:.2f} × 100 = ${call_best_fill * 100:.2f}")
        
        print()
        print("PUT CALENDAR SPREAD (Buy Oct 31 Put, Sell Oct 24 Put):")
        print("-" * 80)
        
        # Put calendar spread
        put_worst_fill = bp_ask - fp_bid if bp_ask and fp_bid else None
        put_best_fill = bp_bid - fp_ask if bp_bid and fp_ask else None
        put_mid_fill = bp_mid - fp_mid if bp_mid and fp_mid else None
        
        if put_worst_fill:
            print(f"  Buy:  Oct 31 Put @ ${bp_ask:.2f} (ask)")
            print(f"  Sell: Oct 24 Put @ ${fp_bid:.2f} (bid)")
            print(f"  Net Debit (worst):   ${put_worst_fill:.2f} × 100 = ${put_worst_fill * 100:.2f}")
            print()
        
        if put_mid_fill:
            print(f"  Buy:  Oct 31 Put @ ${bp_mid:.2f} (mid)")
            print(f"  Sell: Oct 24 Put @ ${fp_mid:.2f} (mid)")
            print(f"  Net Debit (typical): ${put_mid_fill:.2f} × 100 = ${put_mid_fill * 100:.2f}")
            print()
        
        if put_best_fill:
            print(f"  Buy:  Oct 31 Put @ ${bp_bid:.2f} (bid)")
            print(f"  Sell: Oct 24 Put @ ${fp_ask:.2f} (ask)")
            print(f"  Net Debit (best):    ${put_best_fill:.2f} × 100 = ${put_best_fill * 100:.2f}")
        
        print()
        print("=" * 80)
        print("PROFIT/LOSS ESTIMATES (Based on Mid Price)")
        print("=" * 80)
        
        if call_mid_fill:
            print(f"\nCALL SPREAD (Initial Investment: ${call_mid_fill * 100:.2f}):")
            print(f"  • Best Case (stock near $435):     +${call_mid_fill * 100 * 0.4:.2f} (40% profit)")
            print(f"  • Typical (stock moves ±2%):       +${call_mid_fill * 100 * 0.2:.2f} (20% profit)")
            print(f"  • Worst Case (stock moves ±5%):    -${call_mid_fill * 100 * 0.3:.2f} (30% loss)")
            print(f"  • Max Loss:                        -${call_mid_fill * 100:.2f} (net debit)")
        
        if put_mid_fill:
            print(f"\nPUT SPREAD (Initial Investment: ${put_mid_fill * 100:.2f}):")
            print(f"  • Best Case (stock near $435):     +${put_mid_fill * 100 * 0.4:.2f} (40% profit)")
            print(f"  • Typical (stock moves ±2%):       +${put_mid_fill * 100 * 0.2:.2f} (20% profit)")
            print(f"  • Worst Case (stock moves ±5%):    -${put_mid_fill * 100 * 0.3:.2f} (30% loss)")
            print(f"  • Max Loss:                        -${put_mid_fill * 100:.2f} (net debit)")
        
        print()
        print("=" * 80)
        print("RECOMMENDATION:")
        print("=" * 80)
        print("• Use LIMIT orders at mid price or better")
        print("• Consider the call spread if bullish bias, put spread if bearish")
        print("• Plan to exit Oct 24 on expiration day (or day before)")
        print("• Monitor: If stock moves >3%, consider closing early")
        print("=" * 80)
        
        # Cancel market data
        ib.cancelMktData(front_call)
        ib.cancelMktData(front_put)
        ib.cancelMktData(back_call)
        ib.cancelMktData(back_put)
        ib.cancelMktData(stock)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        ib.disconnect()
        print("\nDisconnected from IB")


if __name__ == "__main__":
    get_current_prices()
