# Earnings Calendar
# Manually updated earnings dates for tracked tickers
# Format: 'TICKER': 'YYYY-MM-DD'
#
# Sources:
# - Company investor relations pages
# - Nasdaq earnings calendar (https://www.nasdaq.com/market-activity/earnings)
# - Yahoo Finance
#
# UPDATE THIS FILE QUARTERLY!

EARNINGS_CALENDAR = {
    # MAG7
    'AAPL': '2025-10-31',    # Apple - Q4 2024 earnings
    'MSFT': '2025-10-23',    # Microsoft - Q1 2025 earnings  
    'GOOGL': '2025-10-29',   # Alphabet - Q3 2024 earnings
    'GOOG': '2025-10-29',    # Alphabet (Class C) - Q3 2024 earnings
    'AMZN': '2025-10-31',    # Amazon - Q3 2024 earnings
    'NVDA': '2025-11-20',    # NVIDIA - Q3 FY2025 earnings
    'META': '2025-10-30',    # Meta Platforms - Q3 2024 earnings
    'TSLA': '2025-10-23',    # Tesla - Q3 2024 earnings
    
    # Major Tech & Semiconductors (Q3 2024 earnings - Oct/Nov)
    'AMD': '2025-10-29',     # AMD - Q3 2024
    'AVGO': '2025-12-12',    # Broadcom - Q4 FY2024
    'INTC': '2025-10-31',    # Intel - Q3 2024
    'QCOM': '2025-11-06',    # Qualcomm - Q4 FY2024
    'TXN': '2025-10-22',     # Texas Instruments - Q3 2024
    'AMAT': '2025-11-14',    # Applied Materials - Q4 FY2024
    'ADI': '2025-11-26',     # Analog Devices - Q4 FY2024
    'LRCX': '2025-10-23',    # Lam Research - Q1 FY2025
    'KLAC': '2025-10-30',    # KLA Corp - Q1 FY2025
    'MRVL': '2025-12-05',    # Marvell - Q3 FY2025
    'NXPI': '2025-10-28',    # NXP Semiconductors - Q3 2024
    'MCHP': '2025-11-05',    # Microchip - Q2 FY2025
    'ON': '2025-10-28',      # ON Semiconductor - Q3 2024
    'ASML': '2025-10-16',    # ASML - Q3 2024 (ALREADY REPORTED)
    'ARM': '2025-11-06',     # ARM Holdings - Q2 FY2025
    'SMCI': '2025-11-05',    # Super Micro - Q1 FY2025
    
    # Software & Cloud (Q3 2024 earnings)
    'CRM': '2025-12-03',     # Salesforce - Q3 FY2025
    'ADBE': '2025-12-12',    # Adobe - Q4 FY2024
    'INTU': '2025-11-21',    # Intuit - Q1 FY2025
    'SNPS': '2025-11-20',    # Synopsys - Q4 FY2024
    'CDNS': '2025-10-28',    # Cadence - Q3 2024
    'ANSS': '2025-10-30',    # Ansys - Q3 2024
    'WDAY': '2025-11-26',    # Workday - Q3 FY2025
    'ADSK': '2025-11-21',    # Autodesk - Q3 FY2025
    'CTSH': '2025-10-30',    # Cognizant - Q3 2024
    'PANW': '2025-11-20',    # Palo Alto Networks - Q1 FY2025
    'FTNT': '2025-10-30',    # Fortinet - Q3 2024
    'CRWD': '2025-12-03',    # CrowdStrike - Q3 FY2025
    'ZS': '2025-12-03',      # Zscaler - Q1 FY2025
    'DDOG': '2025-11-07',    # Datadog - Q3 2024
    'TEAM': '2025-10-31',    # Atlassian - Q1 FY2025
    'MDB': '2025-12-05',     # MongoDB - Q3 FY2025
    'PLTR': '2025-11-04',    # Palantir - Q3 2024
    
    # Communication & Media
    'NFLX': '2025-10-17',    # Netflix - Q3 2024 (TODAY!)
    'TMUS': '2025-10-23',    # T-Mobile - Q3 2024
    'CMCSA': '2025-10-31',   # Comcast - Q3 2024
    'CHTR': '2025-10-25',    # Charter - Q3 2024
    'WBD': '2025-11-07',     # Warner Bros Discovery - Q3 2024
    'EA': '2025-10-29',      # Electronic Arts - Q2 FY2025
    'TTWO': '2025-11-06',    # Take-Two - Q2 FY2025
    'NTES': '2025-11-14',    # NetEase - Q3 2024
    'ZM': '2025-11-25',      # Zoom - Q3 FY2025
    
    # Internet & E-commerce
    'PYPL': '2025-10-29',    # PayPal - Q3 2024
    'BKNG': '2025-11-06',    # Booking - Q3 2024
    'ABNB': '2025-11-07',    # Airbnb - Q3 2024
    'DASH': '2025-10-30',    # DoorDash - Q3 2024
    'MELI': '2025-11-07',    # MercadoLibre - Q3 2024
    'PDD': '2025-11-21',     # PDD Holdings - Q3 2024
    
    # Consumer & Retail
    'COST': '2025-12-12',    # Costco - Q1 FY2025
    'SBUX': '2025-10-30',    # Starbucks - Q4 2024
    'MAR': '2025-11-04',     # Marriott - Q3 2024
    'LULU': '2025-12-05',    # Lululemon - Q3 FY2025
    'ORLY': '2025-10-30',    # O'Reilly Auto - Q3 2024
    'ROST': '2025-11-21',    # Ross Stores - Q3 FY2025
    'CTAS': '2025-12-18',    # Cintas - Q2 FY2025
    'FAST': '2025-10-16',    # Fastenal - Q3 2024 (ALREADY REPORTED)
    'DLTR': '2025-12-04',    # Dollar Tree - Q3 FY2025
    'WBA': '2025-10-15',     # Walgreens - Q4 FY2024 (ALREADY REPORTED)
    
    # Healthcare & Biotech
    'AMGN': '2025-10-29',    # Amgen - Q3 2024
    'GILD': '2025-10-29',    # Gilead - Q3 2024
    'VRTX': '2025-10-28',    # Vertex - Q3 2024
    'REGN': '2025-11-07',    # Regeneron - Q3 2024
    'ISRG': '2025-10-17',    # Intuitive Surgical - Q3 2024 (TODAY!)
    'MRNA': '2025-11-07',    # Moderna - Q3 2024
    'BIIB': '2025-10-30',    # Biogen - Q3 2024
    'IDXX': '2025-10-30',    # IDEXX - Q3 2024
    'DXCM': '2025-10-24',    # DexCom - Q3 2024
    'ILMN': '2025-11-07',    # Illumina - Q3 2024
    'GEHC': '2025-10-29',    # GE HealthCare - Q3 2024
    
    # Consumer Staples & Food
    'PEP': '2025-10-08',     # PepsiCo - Q3 2024 (ALREADY REPORTED)
    'MDLZ': '2025-10-29',    # Mondelez - Q3 2024
    'KDP': '2025-10-24',     # Keurig Dr Pepper - Q3 2024
    'KHC': '2025-10-30',     # Kraft Heinz - Q3 2024
    'MNST': '2025-11-07',    # Monster Beverage - Q3 2024
    'CCEP': '2025-10-29',    # Coca-Cola Europacific - Q3 2024
    
    # Industrials & Logistics
    'HON': '2025-10-24',     # Honeywell - Q3 2024
    'ADP': '2025-10-30',     # ADP - Q1 FY2025
    'PAYX': '2025-12-18',    # Paychex - Q2 FY2025
    'ODFL': '2025-10-23',    # Old Dominion - Q3 2024
    'PCAR': '2025-10-29',    # Paccar - Q3 2024
    'CSX': '2025-10-16',     # CSX - Q3 2024 (ALREADY REPORTED)
    'VRSK': '2025-10-30',    # Verisk - Q3 2024
    'CPRT': '2025-11-20',    # Copart - Q1 FY2025
    'CDW': '2025-10-30',     # CDW - Q3 2024
    'CSGP': '2025-10-29',    # CoStar - Q3 2024
    'FANG': '2025-11-06',    # Diamondback Energy - Q3 2024
    'BKR': '2025-10-23',     # Baker Hughes - Q3 2024
    'GFS': '2025-10-31',     # GlobalFoundries - Q3 2024
    
    # Utilities
    'AEP': '2025-10-24',     # American Electric - Q3 2024
    'EXC': '2025-10-31',     # Exelon - Q3 2024
    'XEL': '2025-10-24',     # Xcel Energy - Q3 2024
    'CEG': '2025-11-07',     # Constellation Energy - Q3 2024
    
    # EV & New Tech
    'RIVN': '2025-11-07',    # Rivian - Q3 2024
    'LCID': '2025-11-07',    # Lucid - Q3 2024
    
    # Networking & Infrastructure
    'CSCO': '2025-11-13',    # Cisco - Q1 FY2025
}
