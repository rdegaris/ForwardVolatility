"""
Pretty table viewer for CSV results with borders
"""
import pandas as pd
import sys

def print_bordered_table(df):
    """Print a DataFrame with ASCII borders."""
    
    # Convert all columns to strings and get max widths
    col_widths = {}
    for col in df.columns:
        col_widths[col] = max(
            len(str(col)),
            df[col].astype(str).str.len().max()
        )
    
    # Create separator line
    sep_line = '+'
    for col in df.columns:
        sep_line += '-' * (col_widths[col] + 2) + '+'
    
    # Print top border
    print(sep_line)
    
    # Print header
    header = '|'
    for col in df.columns:
        header += f' {str(col).ljust(col_widths[col])} |'
    print(header)
    print(sep_line)
    
    # Print rows
    for _, row in df.iterrows():
        row_str = '|'
        for col in df.columns:
            value = str(row[col])
            row_str += f' {value.ljust(col_widths[col])} |'
        print(row_str)
    
    # Print bottom border
    print(sep_line)


if __name__ == '__main__':
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'forward_vol_opportunities_DEMO_20251015_145922.csv'
    
    print('\n' + '=' * 140)
    print('FORWARD VOLATILITY OPPORTUNITIES (FF > 0.4)'.center(140))
    print('=' * 140)
    print()
    
    df = pd.read_csv(csv_file)
    print_bordered_table(df)
    
    print()
    print('=' * 140)
    print('KEY METRICS:'.ljust(140))
    print('=' * 140)
    print('ff_ratio (Forward Factor) = (Front Month IV - Forward Vol) / Forward Vol')
    print('Higher FF indicates front-month IV is elevated relative to the forward period')
    print('FF > 0.4 suggests potential calendar spread opportunity')
    print('=' * 140)
