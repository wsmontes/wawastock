"""
Show summary of downloaded stocks data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.local_data_store_v2 import LocalDataStoreV2
import pandas as pd


def show_summary():
    """Display summary of cached data."""
    
    store = LocalDataStoreV2()
    
    # Get all files
    query = """
        SELECT 
            source,
            symbol,
            timeframe,
            min_date,
            max_date,
            row_count,
            file_path
        FROM data_files
        ORDER BY symbol
    """
    
    df = store.conn.execute(query).df()
    
    if df.empty:
        print("No data files found")
        return
    
    print("=" * 80)
    print("CACHED DATA SUMMARY")
    print("=" * 80)
    print(f"\nTotal files: {len(df)}")
    print(f"Total bars: {df['row_count'].sum():,}")
    
    # Group by source
    print("\n" + "-" * 80)
    print("BY SOURCE:")
    print("-" * 80)
    for source, group in df.groupby('source'):
        print(f"\n{source}:")
        print(f"  Files: {len(group)}")
        print(f"  Symbols: {', '.join(sorted(group['symbol'].unique()))}")
        print(f"  Date range: {group['min_date'].min()} to {group['max_date'].max()}")
        print(f"  Total bars: {group['row_count'].sum():,}")
    
    # Show all symbols with details
    print("\n" + "-" * 80)
    print("DETAILED LIST:")
    print("-" * 80)
    print(f"\n{'Symbol':<8} {'Timeframe':<10} {'First Date':<12} {'Last Date':<12} {'Bars':>8}")
    print("-" * 60)
    
    for _, row in df.iterrows():
        print(f"{row['symbol']:<8} {row['timeframe']:<10} {str(row['min_date']):<12} "
              f"{str(row['max_date']):<12} {row['row_count']:>8,}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    show_summary()
