# Forward Volatility Calculator

A Python GUI application for calculating forward (implied) volatility between two option expiries using their Days to Expiration (DTE) and Implied Volatilities (IV).

## Overview

This calculator implements the forward variance identity to compute forward volatility:

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

## Features

- **User-friendly GUI** built with tkinter
- **Input validation** to ensure proper data entry
- **Real-time calculations** with detailed intermediate results
- **Forward Factor analysis** for volatility term structure insights
- **Error handling** for edge cases (negative variance, invalid inputs)

## Requirements

- Python 3.7+
- tkinter (usually included with Python)
- No additional dependencies required

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/forward-volatility-calculator.git
cd forward-volatility-calculator
```

2. (Optional) Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies (if any):
```bash
pip install -r requirements.txt
```

## Usage

Run the calculator:
```bash
python calculator.py
```

### Input Parameters

- **DTE₁ (days)**: Days to expiration for the near-term option
- **IV₁ (%)**: Implied volatility for the near-term option (as percentage, e.g., 24.5)
- **DTE₂ (days)**: Days to expiration for the far-term option
- **IV₂ (%)**: Implied volatility for the far-term option (as percentage, e.g., 26.8)

### Constraints

- DTE₂ > DTE₁ ≥ 0
- IV₁, IV₂ ≥ 0
- Forward variance must be positive for real-valued forward volatility

### Example

For a front-month option with 30 DTE and 25% IV, and a back-month option with 60 DTE and 27% IV:

1. Enter: DTE₁=30, IV₁=25, DTE₂=60, IV₂=27
2. Click "Compute"
3. View the calculated forward volatility and Forward Factor

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