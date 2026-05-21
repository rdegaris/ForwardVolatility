"""Simple Yahoo Finance Quote Server

A lightweight HTTP server that fetches quotes from Yahoo Finance via yfinance.
Run this alongside your web UI to get live price data without CORS issues.

Usage:
    cd forward-volatility-calculator
    .venv\\Scripts\\python.exe quote_server.py

Endpoints:
    GET /api/quotes?symbols=GOOGL,QCOM - Fetch quotes for comma-separated symbols
    GET /api/option-quotes             - Fetch option prices (POST JSON body)
    GET /api/health                    - Health check
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List
from urllib.parse import urlparse, parse_qs

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("WARNING: yfinance not installed. Run: pip install yfinance")


HOST = os.environ.get("QUOTE_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUOTE_SERVER_PORT", "8787"))


def fetch_yahoo_quotes(symbols: List[str]) -> Dict[str, Any]:
    """Fetch live/after-hours quotes from Yahoo Finance using yfinance library."""
    if not YFINANCE_AVAILABLE:
        return {"ok": False, "error": "yfinance not installed"}
    
    if not symbols:
        return {"ok": True, "quotes": {}}
    
    quotes = {}
    
    try:
        # yfinance can fetch multiple tickers at once
        tickers = yf.Tickers(" ".join(symbols))
        
        for symbol in symbols:
            try:
                ticker = tickers.tickers.get(symbol.upper())
                if not ticker:
                    continue
                
                # Try to get fast_info first
                try:
                    info = ticker.fast_info
                    regular_price = getattr(info, 'last_price', None) or getattr(info, 'previous_close', None)
                    previous_close = getattr(info, 'previous_close', None)
                except Exception:
                    regular_price = None
                    previous_close = None
                
                # Try to get extended hours data from history
                display_price = regular_price
                try:
                    hist = ticker.history(period="1d", interval="1m", prepost=True)
                    if not hist.empty:
                        # Latest price including pre/post market
                        display_price = float(hist['Close'].iloc[-1])
                        if regular_price is None:
                            regular_price = display_price
                except Exception as e:
                    print(f"  [WARN] Error getting history for {symbol}: {e}")
                
                if regular_price is None and display_price is None:
                    print(f"  [WARN] No price data for {symbol}")
                    continue
                
                # Calculate changes
                change = 0.0
                change_pct = 0.0
                if previous_close and display_price:
                    change = display_price - previous_close
                    change_pct = (change / previous_close) * 100.0
                
                quotes[symbol.upper()] = {
                    "symbol": symbol.upper(),
                    "regularMarketPrice": round(regular_price, 2) if regular_price else None,
                    "displayPrice": round(display_price, 2) if display_price else None,
                    "previousClose": round(previous_close, 2) if previous_close else None,
                    "change": round(change, 2),
                    "changePercent": round(change_pct, 2),
                    "marketState": "UNKNOWN",
                }
                print(f"  [OK] {symbol}: ${display_price:.2f}" if display_price else f"  [WARN] {symbol}: no price")
            except Exception as e:
                print(f"  [ERROR] Error fetching quote for {symbol}: {e}")
                continue
        
        return {
            "ok": True,
            "asof": datetime.now().isoformat(),
            "quotes": quotes,
        }
    
    except Exception as e:
        return {"ok": False, "error": str(e)}


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def fetch_option_quotes(requests: List[Dict]) -> Dict[str, Any]:
    """Fetch option last-trade prices from Yahoo Finance option chains.
    
    Each request: {"symbol": "GLD", "strike": 435, "expiration": "2026-03-23", "type": "CALL"}
    """
    if not YFINANCE_AVAILABLE:
        return {"ok": False, "error": "yfinance not installed"}
    
    results = {}
    
    for req in requests:
        sym = req.get("symbol", "").upper()
        strike = float(req.get("strike", 0))
        exp = req.get("expiration", "")  # "2026-03-23"
        opt_type = req.get("type", "CALL").upper()
        req_id = req.get("id", f"{sym}_{strike}_{opt_type}_{exp}")
        
        try:
            ticker = yf.Ticker(sym)
            # yfinance wants expiration as "YYYY-MM-DD"
            chain = ticker.option_chain(exp)
            df = chain.calls if opt_type == "CALL" else chain.puts
            
            # Find the row matching our strike
            row = df[df["strike"] == strike]
            if row.empty:
                # Try closest strike
                closest_idx = (df["strike"] - strike).abs().idxmin()
                row = df.loc[[closest_idx]]
            
            if not row.empty:
                r = row.iloc[0]
                results[req_id] = {
                    "id": req_id,
                    "symbol": sym,
                    "strike": float(r["strike"]),
                    "type": opt_type,
                    "expiration": exp,
                    "lastPrice": float(r["lastPrice"]),
                    "bid": float(r.get("bid", 0)),
                    "ask": float(r.get("ask", 0)),
                    "mid": round((float(r.get("bid", 0)) + float(r.get("ask", 0))) / 2, 2),
                    "volume": int(r.get("volume", 0)) if r.get("volume") and not (isinstance(r.get("volume"), float) and r["volume"] != r["volume"]) else 0,
                    "openInterest": int(r.get("openInterest", 0)) if r.get("openInterest") and not (isinstance(r.get("openInterest"), float) and r["openInterest"] != r["openInterest"]) else 0,
                    "impliedVolatility": round(float(r.get("impliedVolatility", 0)) * 100, 1),
                }
                print(f"  [OK] {sym} {strike} {opt_type} {exp}: last=${r['lastPrice']:.2f} bid=${r.get('bid', 0):.2f} ask=${r.get('ask', 0):.2f}")
            else:
                results[req_id] = {"id": req_id, "error": "Strike not found"}
                print(f"  [WARN] {sym} {strike} {opt_type} {exp}: strike not found")
        except Exception as e:
            results[req_id] = {"id": req_id, "error": str(e)}
            print(f"  [ERROR] {sym} {strike} {opt_type} {exp}: {e}")
    
    return {"ok": True, "asof": datetime.now().isoformat(), "options": results}


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        json_response(self, 200, {"ok": True})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/option-quotes":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                json_response(self, 400, {"ok": False, "error": "Invalid JSON"})
                return
            
            requests = data if isinstance(data, list) else data.get("options", [])
            if not requests:
                json_response(self, 400, {"ok": False, "error": "No option requests provided"})
                return
            
            if not YFINANCE_AVAILABLE:
                json_response(self, 503, {"ok": False, "error": "yfinance not installed"})
                return
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching {len(requests)} option quotes")
            payload = fetch_option_quotes(requests)
            json_response(self, 200 if payload.get("ok") else 500, payload)
            return

        json_response(self, 404, {"ok": False, "error": "Not found"})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            json_response(self, 200, {
                "ok": YFINANCE_AVAILABLE,
                "yfinance_available": YFINANCE_AVAILABLE,
                "asof": datetime.now().isoformat(),
            })
            return

        if path == "/api/quotes":
            query_params = parse_qs(parsed.query)
            symbols_param = query_params.get("symbols", [""])[0]
            
            if not symbols_param:
                json_response(self, 400, {"ok": False, "error": "Missing 'symbols' query parameter"})
                return
            
            symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()]
            if not symbols:
                json_response(self, 400, {"ok": False, "error": "No valid symbols provided"})
                return
            
            if not YFINANCE_AVAILABLE:
                json_response(self, 503, {"ok": False, "error": "yfinance not installed on server"})
                return
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching quotes for: {', '.join(symbols)}")
            payload = fetch_yahoo_quotes(symbols)
            json_response(self, 200 if payload.get("ok") else 500, payload)
            return

        json_response(self, 404, {"ok": False, "error": "Not found"})

    def log_message(self, format: str, *args) -> None:
        # Suppress default logging
        pass


def main() -> int:
    if not YFINANCE_AVAILABLE:
        print("ERROR: yfinance not installed")
        print("Install with: pip install yfinance")
        return 1

    print(f"Quote Server listening on http://{HOST}:{PORT}")
    print(f"Endpoints:")
    print(f"  GET  /api/health              - Health check")
    print(f"  GET  /api/quotes?symbols=...  - Fetch stock quotes (comma-separated)")
    print(f"  POST /api/option-quotes       - Fetch option prices (JSON body)")
    print()
    print("Example: http://127.0.0.1:8787/api/quotes?symbols=GOOGL,GLD")
    print()

    httpd = HTTPServer((HOST, PORT), Handler)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        httpd.server_close()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
