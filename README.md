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

### Option Chain Scanner (scanner.py)
- **Live option data** fetched from Yahoo Finance via yfinance
- **Automated ATM IV calculation** for each expiration date
- **Batch scanning** of Nasdaq 100 stocks
- **Opportunity detection** flags trades where FF > 0.4
- **CSV export** of results with timestamps
- **Curated stock lists** (Full Nasdaq 100, Tech-heavy subset, Magnificent 7)

## Requirements

- **calculator.py**: Python 3.7+ with tkinter (usually included)
- **scanner.py**: 
  - yfinance >= 0.2.28
  - pandas >= 2.0.0
  - numpy >= 1.20.0

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

### Option Chain Scanner (Live Data)

For automated scanning of real option chains:

```bash
python scanner.py
```

**What it does:**
1. Scans AAPL option chain first as an example
2. Asks if you want to scan all Nasdaq 100 stocks
3. For each stock, compares consecutive expiration dates
4. Calculates forward volatility and forward factor for ATM options
5. Reports all opportunities where FF > 0.4
6. Saves results to CSV file with timestamp

**Example output:**
```
================================================================================
SCANNING AAPL
================================================================================

Scanning AAPL (Price: $178.25)...
  ✓ FOUND: 2025-11-15 (DTE=31, IV=25.3%) → 2025-12-20 (DTE=66, IV=18.2%) | FF=0.456 (45.6%)
  ✓ FOUND: 2025-12-20 (DTE=66, IV=23.1%) → 2026-01-17 (DTE=94, IV=17.8%) | FF=0.442 (44.2%)
```

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

### Constraints

- DTE₂ > DTE₁ ≥ 0
- IV₁, IV₂ ≥ 0
- Forward variance must be positive for real-valued forward volatility

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