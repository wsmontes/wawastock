"""
Download top 50 US stocks data from 2020 to present.

This script fetches daily data for the largest US companies.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from datetime import datetime


# Top 50 US stocks by market cap (as of 2024)
TOP_50_STOCKS = [
    # Mega cap tech
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
    
    # Large cap tech
    'AVGO', 'ORCL', 'ADBE', 'CRM', 'CSCO', 'INTC', 'AMD', 'QCOM',
    
    # Finance
    'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'AXP',
    
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT',
    
    # Consumer
    'WMT', 'PG', 'KO', 'PEP', 'COST', 'NKE', 'MCD', 'DIS',
    
    # Energy & Industrial
    'XOM', 'CVX', 'CAT', 'BA', 'HON', 'UPS'
]


def download_all_stocks():
    """Download data for all top 50 stocks."""
    
    print("=" * 80)
    print("DOWNLOADING TOP 50 US STOCKS")
    print("=" * 80)
    print(f"Symbols: {len(TOP_50_STOCKS)}")
    print(f"Period: 2020-01-01 to {datetime.now().date()}")
    print(f"Timeframe: 1d (daily)")
    print("=" * 80)
    print()
    
    # Initialize data engine
    engine = DataEngine(use_cache=True)
    
    success_count = 0
    failed = []
    
    for i, symbol in enumerate(TOP_50_STOCKS, 1):
        print(f"\n[{i}/{len(TOP_50_STOCKS)}] {symbol}")
        print("-" * 40)
        
        try:
            df = engine.load_prices(
                symbol=symbol,
                start="2020-01-01",
                end=datetime.now().strftime("%Y-%m-%d")
            )
            
            if not df.empty:
                print(f"  ✓ SUCCESS: {len(df)} bars loaded")
                success_count += 1
            else:
                print(f"  ✗ FAILED: No data returned")
                failed.append(symbol)
                
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed.append(symbol)
    
    # Summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Total symbols: {len(TOP_50_STOCKS)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed symbols: {', '.join(failed)}")
    
    print("\n" + "=" * 80)
    print("Data stored in: data/parquet/stocks/us/1d/")
    print("=" * 80)


if __name__ == "__main__":
    download_all_stocks()
