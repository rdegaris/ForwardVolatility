# Forward Volatility Calculator & Scanner

A comprehensive toolkit for analyzing forward implied volatility in options markets:
1. **GUI Calculator** - Manual calculation tool for forward volatility between two expiries
2. **Option Chain Scanner** - Automated scanner that analyzes real option chains from Yahoo Finance

## Overview

This toolkit implements the forward variance identity to compute forward volatility:

```
σ_fwd = sqrt( (σ₂²·T₂ − σ₁²·T₁) / (T₂ − T₁) )
```

Where:
- T = DTE / 365 (time in years)
- σ = IV / 100 (volatility in decimal form)

The application also calculates the Forward Factor (FF):
```
FF = (σ₁ − σ_fwd) / σ_fwd
```

A **positive FF** (especially FF > 0.4) indicates that front-month IV is significantly higher than the forward volatility, potentially signaling a volatility term structure opportunity.

## Features

### GUI Calculator (calculator.py)
- **User-friendly GUI** built with tkinter
- **Input validation** to ensure proper data entry
- **Real-time calculations** with detailed intermediate results
- **Forward Factor analysis** for volatility term structure insights
- **Error handling** for edge cases (negative variance, invalid inputs)

### Interactive Brokers Scanner (scanner_ib.py)
- **Real-time option data** from Interactive Brokers API
- **Earnings calendar filtering** - automatically excludes tickers with earnings in trading window
- **Separate call/put analysis** - calculates FF for calls, puts, and blended separately
- **Reliable data source** - no rate limits, always available during market hours
- **Advanced IV fetching** with generic tick 106 and debug mode
- **CSV export** of results with timestamps
- **Batch scanning** - scan multiple tickers from curated lists (Nasdaq 100, Tech-heavy, Mag 7)

## Requirements

- **calculator.py**: Python 3.7+ with tkinter (usually included)
- **scanner_ib.py**: 
  - ib_insync >= 0.9.86
  - pandas >= 2.0.0
  - numpy >= 1.20.0
  - yfinance >= 0.2.28 (for earnings calendar data)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/rdegaris/ForwardVolatility.git
cd ForwardVolatility
```

2. (Optional) Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### GUI Calculator (Manual Entry)

For manual calculations with known IV values:

```bash
python calculator.py
```

**Input Parameters:**
- **DTE₁ (days)**: Days to expiration for the near-term option
- **IV₁ (%)**: Implied volatility for the near-term option (as percentage, e.g., 24.5)
- **DTE₂ (days)**: Days to expiration for the far-term option
- **IV₂ (%)**: Implied volatility for the far-term option (as percentage, e.g., 26.8)

**Example:** For a front-month option with 30 DTE and 25% IV, and a back-month option with 60 DTE and 27% IV:
1. Enter: DTE₁=30, IV₁=25, DTE₂=60, IV₂=27
2. Click "Compute"
3. View the calculated forward volatility and Forward Factor

### Interactive Brokers Scanner (Live Data)

For automated scanning of real option chains via IB:

```bash
python scanner_ib.py
```

**What it does:**
1. Connects to IB Gateway or TWS
2. Prompts for tickers to scan
3. For each ticker, fetches option chains and current price
4. Compares consecutive expiration dates
5. Calculates forward volatility and forward factor for ATM options (calls, puts, and blended)
6. Filters out tickers with earnings in trading window
7. Reports all opportunities where FF meets threshold
8. Saves results to CSV file with timestamp

**Quick test scripts:**
- `python quick_test_ib.py` - Test single ticker (TSLA)
- `python scan_show_all.py` - Interactive scan with custom threshold
- `python test_call_put_ff.py` - Compare call vs put forward factors
- `python test_earnings_filter.py` - Test earnings filtering

### Using Stock Lists

The `nasdaq100.py` module provides curated stock lists:

```python
from nasdaq100 import get_nasdaq_100_list, get_tech_heavy_list, get_mag7

# Get full Nasdaq 100 (100 stocks)
all_stocks = get_nasdaq_100_list()

# Get high-volatility tech subset (28 stocks)
tech_stocks = get_tech_heavy_list()

# Get "Magnificent 7" mega-caps (7 stocks)
mag7 = get_mag7()
```

### Earnings Calendar Filtering

The IB scanner automatically filters out opportunities with earnings reports in the trading window:

```python
from scanner_ib import IBScanner

# Default: earnings filtering enabled
scanner = IBScanner(port=7497, check_earnings=True)

# Disable earnings filtering (not recommended)
scanner = IBScanner(port=7497, check_earnings=False)
```

**Why filter earnings?**
- Earnings reports cause IV spikes that distort forward volatility calculations
- Post-earnings IV crush can invalidate the opportunity
- Adds risk due to large potential price moves
- 2-day buffer before and after earnings date is applied by default

**How it works:**
1. Uses yfinance to fetch next earnings date for each ticker
2. Checks if earnings falls within the trading window (expiry1 to expiry2)
3. Applies 2-day buffer before and after earnings
4. Automatically excludes any opportunities with earnings conflicts
5. Reports excluded tickers with earnings dates

### Constraints

- DTE₂ > DTE₁ ≥ 0
- IV₁, IV₂ ≥ 0
- Forward variance must be positive for real-valued forward volatility
- Earnings should not fall within trading window (when using earnings filter)

## Output Interpretation

- **Forward Volatility**: The implied volatility for the period between the two expiries
- **Forward Factor**: Ratio indicating the relationship between front-month IV and forward volatility
  - Positive FF: Front-month IV > Forward volatility
  - Negative FF: Front-month IV < Forward volatility

## Applications

This tool is useful for:
- **Options traders** analyzing volatility term structure
- **Risk managers** calculating forward-looking volatility estimates
- **Quantitative analysts** studying volatility dynamics
- **Academic research** in options pricing and volatility modeling

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.