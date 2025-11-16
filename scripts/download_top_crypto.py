"""
Download top cryptocurrencies data from 2020 to present.

This script fetches daily data for the largest cryptocurrencies.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from datetime import datetime


# Top 50 cryptocurrencies by market cap
TOP_CRYPTO = [
    # Top 10
    'BTC-USD', 'ETH-USD', 'USDT-USD', 'BNB-USD', 'SOL-USD',
    'USDC-USD', 'XRP-USD', 'DOGE-USD', 'ADA-USD', 'TRX-USD',
    
    # 11-20
    'AVAX-USD', 'SHIB-USD', 'DOT-USD', 'LINK-USD', 'BCH-USD',
    'NEAR-USD', 'MATIC-USD', 'LTC-USD', 'UNI-USD', 'LEO-USD',
    
    # 21-30
    'DAI-USD', 'ATOM-USD', 'ETC-USD', 'XLM-USD', 'OKB-USD',
    'ICP-USD', 'FIL-USD', 'APT-USD', 'ARB-USD', 'VET-USD',
    
    # 31-40
    'HBAR-USD', 'MKR-USD', 'OP-USD', 'AAVE-USD', 'GRT-USD',
    'ALGO-USD', 'SAND-USD', 'MANA-USD', 'THETA-USD', 'FTM-USD',
    
    # 41-50
    'AXS-USD', 'XTZ-USD', 'EGLD-USD', 'FLOW-USD', 'CHZ-USD',
    'ZEC-USD', 'ENJ-USD', 'KLAY-USD', 'LRC-USD', 'BAT-USD'
]


def download_all_crypto():
    """Download data for all top cryptocurrencies."""
    
    print("=" * 80)
    print("DOWNLOADING TOP 50 CRYPTOCURRENCIES")
    print("=" * 80)
    print(f"Symbols: {len(TOP_CRYPTO)}")
    print(f"Period: 2020-01-01 to {datetime.now().date()}")
    print(f"Timeframe: 1d (daily)")
    print(f"Source: Yahoo Finance (crypto pairs in USD)")
    print("=" * 80)
    print()
    
    # Initialize data engine
    engine = DataEngine(use_cache=True)
    
    success_count = 0
    failed = []
    
    for i, symbol in enumerate(TOP_CRYPTO, 1):
        print(f"\n[{i}/{len(TOP_CRYPTO)}] {symbol}")
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
    print(f"Total symbols: {len(TOP_CRYPTO)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed symbols: {', '.join(failed)}")
    
    print("\n" + "=" * 80)
    print("Data stored in: data/parquet/stocks/us/1d/")
    print("Note: Crypto symbols ending in -USD are stored with Yahoo source")
    print("=" * 80)


if __name__ == "__main__":
    download_all_crypto()
