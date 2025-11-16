#!/usr/bin/env python3
"""Test backtest with real AAPL data."""
import backtrader as bt
import pandas as pd
from pathlib import Path
import pyarrow.parquet as pq


class TestStrategy(bt.Strategy):
    """Minimal strategy - just buy and hold."""
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        
    def next(self):
        # Only buy once at start
        if not self.position and len(self) == 1:
            print(f"Buying at {self.dataclose[0]:.2f}")
            self.order = self.buy()


# Load data from parquet files
data_dir = Path("/Users/wagnermontes/Documents/GitHub/wawastock/data/parquet/candles/YAHOO/AAPL/1d/2023")

print(f"Loading data from {data_dir}")
parquet_files = sorted(data_dir.glob("*.parquet"))
print(f"Found {len(parquet_files)} parquet files")

# Load and concatenate
dfs = []
for pf in parquet_files[:100]:  # Just first 100 days to test
    df = pd.read_parquet(pf)
    dfs.append(df)

data = pd.concat(dfs, ignore_index=False)
data = data.sort_index()
print(f"Loaded {len(data)} bars")
print(f"Date range: {data.index[0]} to {data.index[-1]}")
print(f"Columns: {data.columns.tolist()}")
print(f"\nFirst few rows:")
print(data.head())

# Create Cerebro
print("\nCreating Cerebro...")
cerebro = bt.Cerebro()
cerebro.broker.setcash(100000)

# Add data
print("Adding data feed...")
data_feed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data_feed)
cerebro.addstrategy(TestStrategy)

print("Starting backtest...")
initial = cerebro.broker.getvalue()
print(f"Initial: ${initial:,.2f}")

try:
    cerebro.run()
    final = cerebro.broker.getvalue()
    print(f"Final: ${final:,.2f}")
    print("✓ Test passed!")
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
