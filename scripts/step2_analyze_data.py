"""
Step 2: Analyze Bitcoin data and calculate statistics
Reads the CSV from step 1 and generates detailed analysis.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    print("=" * 80)
    print("STEP 2: ANALYZING BITCOIN DATA")
    print("=" * 80)
    print()
    
    # Load data from step 1
    input_file = project_root / "data" / "processed" / "btc_2020_2025_raw.csv"
    
    if not input_file.exists():
        print(f"❌ ERROR: Data file not found: {input_file}")
        print("Please run step1_download_btc_data.py first")
        return 1
    
    print(f"📂 Loading data from: {input_file}")
    df = pd.read_csv(input_file, index_col=0, parse_dates=True)
    print(f"✅ Loaded {len(df)} rows")
    print()
    
    # Basic stats
    print("=" * 80)
    print("STATISTICAL ANALYSIS")
    print("=" * 80)
    print()
    
    print("PRICE STATISTICS")
    print(f"Min price:  ${df['Close'].min():,.2f}")
    print(f"Max price:  ${df['Close'].max():,.2f}")
    print(f"Mean price: ${df['Close'].mean():,.2f}")
    print(f"Std dev:    ${df['Close'].std():,.2f}")
    print()
    
    # Daily returns
    df['Returns'] = df['Close'].pct_change()
    print("DAILY RETURNS")
    print(f"Mean return:   {df['Returns'].mean() * 100:.4f}%")
    print(f"Std dev:       {df['Returns'].std() * 100:.4f}%")
    print(f"Best day:      {df['Returns'].max() * 100:+.2f}%")
    print(f"Worst day:     {df['Returns'].min() * 100:+.2f}%")
    print()
    
    # Volatility
    annual_vol = df['Returns'].std() * np.sqrt(252) * 100
    print(f"Annual volatility: {annual_vol:.2f}%")
    print()
    
    # Drawdown analysis
    cumulative = (1 + df['Returns']).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min() * 100
    
    print(f"Maximum drawdown: {max_dd:.2f}%")
    print()
    
    # Volume analysis
    print("VOLUME STATISTICS")
    print(f"Mean volume:   {df['Volume'].mean():,.0f}")
    print(f"Max volume:    {df['Volume'].max():,.0f}")
    print(f"Total volume:  {df['Volume'].sum():,.0f}")
    print()
    
    # Save analysis
    log_file = project_root / "logs" / "step2_analysis_log.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("STEP 2: DATA ANALYSIS LOG\n")
        f.write("=" * 80 + "\n")
        f.write(f"Timestamp: {datetime.now()}\n")
        f.write(f"Data points: {len(df)}\n")
        f.write(f"\nPRICE STATISTICS\n")
        f.write(f"Min: ${df['Close'].min():,.2f}\n")
        f.write(f"Max: ${df['Close'].max():,.2f}\n")
        f.write(f"Mean: ${df['Close'].mean():,.2f}\n")
        f.write(f"Std: ${df['Close'].std():,.2f}\n")
        f.write(f"\nDAILY RETURNS\n")
        f.write(f"Mean: {df['Returns'].mean() * 100:.4f}%\n")
        f.write(f"Std: {df['Returns'].std() * 100:.4f}%\n")
        f.write(f"Best: {df['Returns'].max() * 100:+.2f}%\n")
        f.write(f"Worst: {df['Returns'].min() * 100:+.2f}%\n")
        f.write(f"\nRISK METRICS\n")
        f.write(f"Annual volatility: {annual_vol:.2f}%\n")
        f.write(f"Maximum drawdown: {max_dd:.2f}%\n")
    
    print(f"📝 Log saved to: {log_file}")
    print()
    print("✅ STEP 2 COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
