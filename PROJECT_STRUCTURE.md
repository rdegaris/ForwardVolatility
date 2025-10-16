# Forward Volatility Project - File Structure

## Core Application Files

### Calculators & Scanners
- **calculator.py** - GUI forward volatility calculator (tkinter)
- **scanner_ib.py** - Main IB scanner with earnings filtering
- **earnings_checker.py** - Earnings calendar checker module

### Test & Utility Scripts
- **quick_test_ib.py** - Quick single-ticker test (TSLA default)
- **scan_show_all.py** - Interactive scanner with custom threshold
- **test_call_put_ff.py** - Compare call vs put forward factors
- **test_earnings_filter.py** - Test earnings filtering functionality

### P&L Analysis
- **simple_pnl.py** - Simplified calendar spread P&L estimator
- **calendar_spread_pnl.py** - Full Black-Scholes P&L calculator (requires scipy)
- **get_prices.py** - Real-time option pricing from IB

### Trading Tools
- **TRADE_TICKET.md** - Complete trade execution checklist
- **QUICK_REFERENCE.txt** - One-page quick reference card

### Data & Configuration
- **nasdaq100.py** - Curated stock lists (Nasdaq 100, Tech-heavy, Mag 7)
- **requirements.txt** - Python dependencies

### Documentation
- **README.md** - Main project documentation
- **IB_SETUP.md** - Interactive Brokers setup guide
- **TROUBLESHOOTING.md** - Common issues and solutions
- **LICENSE** - Project license

## Workflow

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure IB Gateway/TWS (see IB_SETUP.md)
# Enable API connections on port 7497 (paper) or 7496 (live)
```

### 2. Scan for Opportunities
```bash
# Quick single ticker test
python quick_test_ib.py

# Interactive scan with custom threshold
python scan_show_all.py

# Full scanner with earnings filtering
python scanner_ib.py
```

### 3. Analyze Opportunity
```bash
# Compare call vs put spreads
python test_call_put_ff.py

# Get current market prices
python get_prices.py

# Calculate P&L scenarios
python simple_pnl.py
```

### 4. Execute Trade
- Use **TRADE_TICKET.md** for full execution checklist
- Use **QUICK_REFERENCE.txt** for at-a-glance order details

## Key Features

✅ **Earnings Filtering** - Automatically excludes tickers with earnings in window
✅ **Call/Put Analysis** - Separate FF calculations for calls and puts
✅ **Real-time IB Data** - No rate limits, reliable market data
✅ **P&L Calculators** - Estimate profits before entering trade
✅ **Trade Documentation** - Complete checklists and reference cards

## Removed Files (No Longer Needed)

These Yahoo Finance-based files were removed as they were rate-limited and unreliable:
- scanner.py (replaced by scanner_ib.py)
- test_api.py (Yahoo Finance diagnostics)
- test_tsla.py (Yahoo Finance test)
- test_alternative_providers.py (fallback providers)
- demo_scanner.py (sample data demo)
- view_table.py (CSV viewer)
