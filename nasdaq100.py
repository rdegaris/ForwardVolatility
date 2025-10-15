"""
Nasdaq 100 stock list
Complete list as of 2025
"""

NASDAQ_100 = [
    # Top Technology & Communication Services
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'NFLX',
    'AMD', 'ADBE', 'CSCO', 'CRM', 'INTC', 'QCOM', 'TXN', 'INTU', 'AMAT', 'ADI',
    'SNPS', 'CDNS', 'LRCX', 'KLAC', 'MRVL', 'NXPI', 'MCHP', 'FTNT', 'PANW', 'CRWD',
    'WDAY', 'ADSK', 'DDOG', 'TEAM', 'ZS', 'ABNB', 'MDB', 'ANSS', 'PLTR', 'ARM',
    
    # Communication & Media
    'TMUS', 'CMCSA', 'CHTR', 'WBD', 'EA', 'TTWO', 'NTES', 'ZM',
    
    # Consumer
    'COST', 'SBUX', 'BKNG', 'MAR', 'ORLY', 'LULU', 'ROST', 'CTAS', 'ODFL', 'FAST',
    'DASH', 'MELI', 'CPRT', 'PCAR', 'CSX', 'VRSK', 'PAYX', 'ALGN', 'DLTR', 'WBA',
    
    # Healthcare & Biotech
    'AMGN', 'GILD', 'VRTX', 'REGN', 'ISRG', 'MRNA', 'BIIB', 'IDXX', 'DXCM', 'ILMN',
    'GEHC', 'SMCI',
    
    # Consumer Staples & Food
    'PEP', 'MDLZ', 'KDP', 'KHC', 'MNST',
    
    # Industrials & Materials
    'HON', 'ADP', 'CDW', 'CSGP', 'ON', 'FANG', 'BKR', 'GFS',
    
    # Utilities & Energy
    'AEP', 'EXC', 'XEL', 'CEG',
    
    # Other Tech & Services
    'ASML', 'CTSH', 'PYPL', 'CCEP',
    
    # EV & New Tech
    'RIVN', 'LCID', 'PDD'
]

def get_nasdaq_100_list():
    """Return the complete Nasdaq 100 stock list."""
    return NASDAQ_100

def get_tech_heavy_list():
    """Return a subset focused on high-volatility tech stocks."""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 
        'AMD', 'AVGO', 'ADBE', 'CRM', 'INTC', 'QCOM', 'AMAT', 'MRVL',
        'PANW', 'CRWD', 'WDAY', 'DDOG', 'TEAM', 'ZS', 'MDB', 'ARM',
        'ABNB', 'DASH', 'PLTR', 'SMCI'
    ]

def get_mag7():
    """Return the 'Magnificent 7' mega-cap tech stocks."""
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']


if __name__ == "__main__":
    print(f"Total Nasdaq 100 stocks: {len(NASDAQ_100)}")
    print(f"Tech-heavy subset: {len(get_tech_heavy_list())}")
    print(f"Magnificent 7: {len(get_mag7())}")
    print("\nFull list:")
    for i, ticker in enumerate(NASDAQ_100, 1):
        print(f"{i:3d}. {ticker}")
