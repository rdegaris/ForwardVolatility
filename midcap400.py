"""
S&P MidCap 400 stock list
"""

def get_midcap400_list():
    """Return list of S&P MidCap 400 stock tickers.
    
    The S&P MidCap 400 Index measures the performance of mid-sized companies,
    representing approximately 7% of the U.S. equity market.
    
    Market cap range: ~$3.7 billion to ~$13.1 billion
    """
    
    # S&P MidCap 400 constituents (as of October 2025)
    # Organized alphabetically for easier maintenance
    tickers = [
        # A
        'ABCB', 'ABG', 'ABM', 'ACHC', 'ACIW', 'ACLS', 'AEO', 'AFG', 'AGCO', 'AIT',
        'AKR', 'ALKS', 'ALLY', 'AM', 'AMED', 'AMG', 'AMN', 'AMWD', 'AN', 'ANF',
        'ANET', 'AOSL', 'AOS', 'APG', 'APOG', 'ARCB', 'ARCO', 'ARW', 'ASPN', 'ASR',
        'ATI', 'ATKR', 'ATR', 'AVA', 'AVNT', 'AVT', 'AWI', 'AWR', 'AX', 'AXS',
        
        # B
        'B', 'BANR', 'BC', 'BCPC', 'BDC', 'BERY', 'BFH', 'BHF', 'BHLB', 'BJ',
        'BKH', 'BKU', 'BLD', 'BLKB', 'BMI', 'BOKF', 'BOX', 'BRC', 'BRX', 'BURL',
        'BWA', 'BWXT', 'BXC', 'BXP', 'BY',
        
        # C
        'CADE', 'CALM', 'CASY', 'CATY', 'CBT', 'CBSH', 'CBZ', 'CBRE', 'CBU', 'CC',
        'CCOI', 'CDAY', 'CDP', 'CELH', 'CENTA', 'CERE', 'CFR', 'CHDN', 'CHE', 'CHRD',
        'CHS', 'CIEN', 'CL', 'CLH', 'CLOV', 'CLX', 'CMA', 'Cmbm', 'CMC', 'CNK',
        'CNM', 'CNO', 'CNS', 'CNX', 'COKE', 'COLB', 'COTY', 'CPB', 'CPF', 'CPK',
        'CRC', 'CREE', 'CRI', 'CRL', 'CRS', 'CRY', 'CSGP', 'CSWI', 'CTRE', 'CUZ',
        'CVBF', 'CVI', 'CVLT', 'CW', 'CWT', 'CXM', 'CXW', 'CYH',
        
        # D
        'DAR', 'DAVA', 'DCI', 'DDS', 'DECK', 'DF', 'DKS', 'DNLI', 'DOX', 'DRI',
        'DSGX', 'DTM', 'DY',
        
        # E
        'EAT', 'EBC', 'EBF', 'EEFT', 'EGP', 'EHC', 'ELS', 'EME', 'ENSG', 'ENS',
        'ENTA', 'ENTG', 'ENV', 'ENVA', 'EPR', 'EQH', 'EQT', 'ESE', 'ESNT', 'ESRT',
        'ESS', 'EWBC', 'EXP', 'EXPE', 'EXPO', 'EXR',
        
        # F
        'FAF', 'FBP', 'FHB', 'FHI', 'FIBK', 'FIGS', 'FIX', 'FL', 'FLS', 'FLR',
        'FNB', 'FNF', 'FOR', 'FORM', 'FOUR', 'FR', 'FRT', 'FSS', 'FULT', 'FUN',
        
        # G
        'G', 'GATX', 'GEF', 'GFF', 'GIII', 'GMS', 'GNL', 'GNRC', 'GNW', 'GO',
        'GRMN', 'GTLS', 'GTES', 'GTY', 'GVA',
        
        # H
        'H', 'HAFC', 'HALO', 'HAE', 'HAS', 'HBAN', 'HBI', 'HCC', 'HCI', 'HEI',
        'HELE', 'HGV', 'HI', 'HIW', 'HL', 'HLI', 'HNI', 'HOG', 'HOMB', 'HP',
        'HPP', 'HR', 'HRB', 'HRI', 'HRL', 'HSIC', 'HST', 'HTH', 'HTLD', 'HUBG',
        'HUN', 'HWC',
        
        # I
        'IACC', 'IART', 'IBP', 'ICLR', 'ICUI', 'IDA', 'IDCC', 'IEX', 'IGT', 'IHRT',
        'INSM', 'INSP', 'INT', 'IOSP', 'IPAR', 'IPG', 'IQV', 'IRT', 'IVZ',
        
        # J
        'J', 'JACK', 'JBHT', 'JBLU', 'JBT', 'JEF', 'JJSF', 'JKHY', 'JLL', 'JOE',
        'JXN',
        
        # K
        'KAI', 'KAR', 'KBH', 'KBR', 'KEX', 'KFRC', 'KFY', 'KIM', 'KMT', 'KN',
        'KNX', 'KRC', 'KRG', 'KTB',
        
        # L
        'LAD', 'LAMR', 'LANC', 'LAWS', 'LBRT', 'LBT', 'LDL', 'LEA', 'LEG', 'LGND',
        'LH', 'LII', 'LIVN', 'LKQ', 'LNC', 'LNT', 'LPLA', 'LPX', 'LSCC', 'LSTR',
        'LTH', 'LXP', 'LYV',
        
        # M
        'MAC', 'MAIN', 'MATX', 'MAN', 'MATW', 'MBI', 'MC', 'MCY', 'MD', 'MDC',
        'MEDP', 'MEG', 'MGM', 'MGY', 'MHK', 'MIDD', 'MKL', 'MLI', 'MMS', 'MOD',
        'MODG', 'MOS', 'MOV', 'MP', 'MPW', 'MRC', 'MRCY', 'MRVL', 'MS', 'MSCI',
        'MSM', 'MTG', 'MTH', 'MTN', 'MTSI', 'MTX', 'MTZ', 'MUR', 'MUSA', 'MXL',
        
        # N
        'NBHC', 'NEU', 'NFG', 'NHI', 'NJR', 'NNN', 'NOV', 'NPO', 'NRG', 'NSA',
        'NSP', 'NTCT', 'NTR', 'NUE', 'NVST', 'NVT', 'NWE', 'NWSA', 'NX', 'NXL',
        
        # O
        'OC', 'OFG', 'OGE', 'OGS', 'OHI', 'OI', 'OII', 'OLN', 'OLO', 'OLP',
        'OMI', 'ONB', 'ORA', 'ORI', 'OSK', 'OUT', 'OVV', 'OZK',
        
        # P
        'PACW', 'PAG', 'PAGS', 'PATK', 'PAYO', 'PBCT', 'PBF', 'PBH', 'PBI', 'PCH',
        'PDM', 'PEB', 'PEGA', 'PENN', 'PEN', 'PES', 'PFS', 'PH', 'PHM', 'PIPR',
        'PK', 'PKG', 'PLNT', 'PLXS', 'PM', 'PNW', 'PODD', 'POST', 'PPBI', 'PPC',
        'PRAA', 'PRG', 'PRGO', 'PRI', 'PRM', 'PRO', 'PSTG', 'PTEN', 'PVH', 'PWR',
        
        # Q
        'QTWO',
        
        # R
        'R', 'RAMP', 'RBA', 'RBC', 'REXR', 'REZI', 'RGA', 'RGLD', 'RGR', 'RH',
        'RHP', 'RIG', 'RITM', 'RKT', 'RL', 'RMBS', 'RMD', 'RNR', 'ROCK', 'ROG',
        'ROIC', 'ROL', 'RRC', 'RRTS', 'RS', 'RSG', 'RTO', 'RUSHA', 'RXO', 'RYI',
        
        # S
        'SABR', 'SAFE', 'SAIA', 'SANM', 'SAH', 'SATS', 'SBAC', 'SBH', 'SBNY', 'SBRA',
        'SCCO', 'SCL', 'SEM', 'SF', 'SFBS', 'SFM', 'SFNC', 'SGH', 'SHAK', 'SHO',
        'SHOO', 'SIG', 'SITE', 'SIX', 'SKT', 'SKX', 'SKY', 'SLG', 'SM', 'SMPL',
        'SN', 'SNCR', 'SNV', 'SNX', 'SON', 'SPB', 'SPGI', 'SPR', 'SPSC', 'SRC',
        'SRCE', 'SSD', 'SSB', 'ST', 'STAG', 'STC', 'STLD', 'STRA', 'STR', 'SUM',
        'SWK', 'SWM', 'SWN', 'SWX', 'SXC', 'SXT',
        
        # T
        'TAC', 'TAP', 'TCBI', 'TCF', 'TEL', 'TEX', 'TFX', 'TGI', 'TGT', 'THC',
        'THG', 'THO', 'TIPT', 'TKR', 'TNC', 'TOL', 'TPB', 'TPH', 'TPL', 'TPR',
        'TRGP', 'TRN', 'TRNO', 'TRMB', 'TRU', 'TRTN', 'TSCO', 'TTC', 'TTI', 'TWNK',
        'TX', 'TXT',
        
        # U
        'UBA', 'UBSI', 'UCB', 'UCBI', 'UDR', 'UE', 'UFS', 'UGI', 'UHS', 'UIS',
        'ULH', 'UMPQ', 'UNF', 'UNFI', 'UNM', 'URBN', 'USFD', 'USM', 'UTL',
        
        # V
        'VAC', 'VAL', 'VFC', 'VHC', 'VIAV', 'VIRT', 'VLY', 'VMI', 'VNO', 'VOYA',
        'VRE', 'VTR', 'VVV',
        
        # W
        'WAB', 'WAL', 'WASH', 'WBS', 'WCC', 'WD', 'WEN', 'WEX', 'WH', 'WHR',
        'WLK', 'WMB', 'WMG', 'WMS', 'WOR', 'WRB', 'WRI', 'WSC', 'WSFS', 'WSM',
        'WSO', 'WST', 'WWE', 'WWW',
        
        # X
        'XHR', 'XPO', 'XYL',
        
        # Z
        'ZION', 'ZWS'
    ]
    
    return sorted(tickers)


def get_mag7():
    """Return list of Magnificent 7 stocks for backward compatibility."""
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']


if __name__ == "__main__":
    midcap = get_midcap400_list()
    print(f"S&P MidCap 400 List: {len(midcap)} tickers")
    print("\nTickers:")
    for i in range(0, len(midcap), 10):
        print("  " + ", ".join(midcap[i:i+10]))
