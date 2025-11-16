#!/usr/bin/env python3
"""Test with ultra-simple strategy."""
import backtrader as bt
import sys
sys.path.insert(0, '/Users/wagnermontes/Documents/GitHub/wawastock')

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
import datetime


class UltraSimpleStrategy(bt.Strategy):
    """Ultra simple - just buy and hold."""
    
    def __init__(self):
        pass
    
    def next(self):
        if not self.position and len(self) == 1:
            self.buy()


print("Creating engines...")
data_engine = DataEngine()
backtest_engine = BacktestEngine()

print("Loading data...")
data = data_engine.get_ohlcv(
    source='YAHOO',
    symbol='AAPL',
    timeframe='1d',
    start=datetime.datetime(2023, 11, 1),
    end=datetime.datetime(2023, 11, 10)
)

print(f"Loaded {len(data)} bars")
print(f"Index type: {type(data.index)}")
print(f"Index: {data.index[:5].tolist()}")
print(f"Columns: {data.columns.tolist()}")

print("\nRunning backtest...")
results = backtest_engine.run_backtest(
    strategy_cls=UltraSimpleStrategy,
    data_df=data
)

print("\n✓ Backtest completed!")
print(f"Results: {results}")
