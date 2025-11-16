#!/usr/bin/env python3
"""Test data loading with actual data engine."""
import sys
sys.path.insert(0, '/Users/wagnermontes/Documents/GitHub/wawastock')

from engines.data_engine import DataEngine
import datetime

print("Creating DataEngine...")
engine = DataEngine()

print("Loading AAPL data...")
df = engine.load_data(
    symbol='AAPL',
    start=datetime.datetime(2023, 11, 1),
    end=datetime.datetime(2023, 11, 10),
    source='YAHOO',
    timeframe='1d'
)

print(f"\n✓ Loaded {len(df)} bars")
print(f"Columns: {df.columns.tolist()}")
print(f"Index type: {type(df.index)}")
print(f"Index dtype: {df.index.dtype}")
print(f"\nFirst rows:")
print(df.head())
print(f"\nLast rows:")
print(df.tail())
