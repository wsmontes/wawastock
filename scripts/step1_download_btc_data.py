"""
Step 1: Download Bitcoin historical data (2020-2025)
Generates detailed log with data summary.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import yfinance as yf

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    print("=" * 80)
    print("STEP 1: DOWNLOADING BITCOIN DATA (2020-2025)")
    print("=" * 80)
    print()
    
    # Parameters
    symbol = "BTC-USD"
    start_date = "2020-01-01"
    end_date = "2025-11-24"
    
    print(f"📊 Symbol: {symbol}")
    print(f"📅 Period: {start_date} to {end_date}")
    print()
    
    # Download data
    print("⏳ Downloading data from Yahoo Finance...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if df.empty:
            print("❌ ERROR: No data downloaded!")
            return 1
            
        print(f"✅ Downloaded {len(df)} trading days")
        print()
        
        # Data summary
        print("=" * 80)
        print("DATA SUMMARY")
        print("=" * 80)
        print(f"First date: {df.index[0]}")
        print(f"Last date:  {df.index[-1]}")
        print(f"Total days: {len(df)}")
        print()
        
        # Price analysis
        first_price = df['Close'].iloc[0]
        last_price = df['Close'].iloc[-1]
        price_change = last_price - first_price
        price_change_pct = (price_change / first_price) * 100
        
        print("PRICE ANALYSIS")
        print(f"Starting price: ${first_price:,.2f}")
        print(f"Ending price:   ${last_price:,.2f}")
        print(f"Change:         ${price_change:+,.2f} ({price_change_pct:+.2f}%)")
        print()
        
        # Buy & Hold calculation
        print(f"📈 BUY & HOLD RETURN: {price_change_pct:+.2f}%")
        print()
        
        # Stats by year
        print("YEARLY BREAKDOWN")
        print("-" * 80)
        df['Year'] = df.index.year
        for year in sorted(df['Year'].unique()):
            year_data = df[df['Year'] == year]
            year_first = year_data['Close'].iloc[0]
            year_last = year_data['Close'].iloc[-1]
            year_change_pct = ((year_last - year_first) / year_first) * 100
            print(f"{year}: {len(year_data):3d} days | "
                  f"${year_first:>10,.2f} → ${year_last:>10,.2f} | "
                  f"{year_change_pct:+7.2f}%")
        print()
        
        # Save to CSV for next step
        output_file = project_root / "data" / "processed" / "btc_2020_2025_raw.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file)
        print(f"💾 Data saved to: {output_file}")
        print()
        
        # Create log file
        log_file = project_root / "logs" / "step1_download_log.txt"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("STEP 1: BITCOIN DATA DOWNLOAD LOG\n")
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Period: {start_date} to {end_date}\n")
            f.write(f"Total days: {len(df)}\n")
            f.write(f"\nFirst date: {df.index[0]}\n")
            f.write(f"Last date: {df.index[-1]}\n")
            f.write(f"\nStarting price: ${first_price:,.2f}\n")
            f.write(f"Ending price: ${last_price:,.2f}\n")
            f.write(f"Buy & Hold Return: {price_change_pct:+.2f}%\n")
            f.write(f"\nData file: {output_file}\n")
            
        print(f"📝 Log saved to: {log_file}")
        print()
        print("✅ STEP 1 COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
