"""
Show organized summary of stocks and crypto data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.local_data_store_v2 import LocalDataStoreV2


def show_organized_summary():
    """Display organized summary separating stocks and crypto."""
    
    store = LocalDataStoreV2()
    
    # Get all files
    query = """
        SELECT 
            symbol,
            timeframe,
            min_date,
            max_date,
            row_count
        FROM data_files
        ORDER BY symbol
    """
    
    df = store.conn.execute(query).df()
    
    if df.empty:
        print("No data files found")
        return
    
    # Separate stocks and crypto
    stocks = df[~df['symbol'].str.contains('-USD')].copy()
    crypto = df[df['symbol'].str.contains('-USD')].copy()
    
    print("=" * 80)
    print("CACHED DATA SUMMARY")
    print("=" * 80)
    
    # Overall stats
    print(f"\n📊 OVERALL:")
    print(f"  Total symbols: {len(df)}")
    print(f"  Total bars: {df['row_count'].sum():,}")
    print(f"  Storage: data/parquet/stocks/us/1d/")
    
    # Stocks section
    if not stocks.empty:
        print(f"\n{'='*80}")
        print(f"📈 US STOCKS ({len(stocks)} symbols)")
        print("=" * 80)
        print(f"  Total bars: {stocks['row_count'].sum():,}")
        print(f"  Date range: {stocks['min_date'].min()} to {stocks['max_date'].max()}")
        print(f"\n  Symbols:")
        
        # Group by sector (rough grouping by symbol)
        stock_symbols = sorted(stocks['symbol'].tolist())
        for i in range(0, len(stock_symbols), 10):
            print(f"    {', '.join(stock_symbols[i:i+10])}")
    
    # Crypto section
    if not crypto.empty:
        print(f"\n{'='*80}")
        print(f"₿ CRYPTOCURRENCIES ({len(crypto)} symbols)")
        print("=" * 80)
        print(f"  Total bars: {crypto['row_count'].sum():,}")
        print(f"  Date range: {crypto['min_date'].min()} to {crypto['max_date'].max()}")
        print(f"\n  Top 20 by bars (data availability):")
        
        top20 = crypto.nlargest(20, 'row_count')
        for _, row in top20.iterrows():
            symbol = row['symbol'].replace('-USD', '')
            print(f"    {symbol:<8} {row['row_count']:>5,} bars  "
                  f"({str(row['min_date'])[:10]} to {str(row['max_date'])[:10]})")
        
        if len(crypto) > 20:
            print(f"\n  ... and {len(crypto) - 20} more cryptocurrencies")
    
    print("\n" + "=" * 80)
    print("💡 USAGE EXAMPLES:")
    print("=" * 80)
    print("  # Test stock strategy:")
    print("  python main.py run-recipe --name rsi --symbol NVDA")
    print("  python main.py run-recipe --name macd_ema --symbol TSLA")
    print()
    print("  # Test crypto strategy:")
    print("  python main.py run-recipe --name rsi --symbol BTC-USD")
    print("  python main.py run-recipe --name bollinger_rsi --symbol ETH-USD")
    print("=" * 80)


if __name__ == "__main__":
    show_organized_summary()
