#!/usr/bin/env python3
"""Minimal backtrader test to check if it's working."""
import backtrader as bt
import pandas as pd
import datetime


class SimpleStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            self.buy()


# Create sample data
dates = pd.date_range('2023-01-01', periods=50, freq='D')
data = pd.DataFrame({
    'open': [100 + i for i in range(50)],
    'high': [101 + i for i in range(50)],
    'low': [99 + i for i in range(50)],
    'close': [100 + i for i in range(50)],
    'volume': [1000000] * 50
}, index=dates)

print(f"Created {len(data)} bars of test data")

# Create Cerebro
cerebro = bt.Cerebro()
cerebro.broker.setcash(100000)

# Add data
data_feed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data_feed)
cerebro.addstrategy(SimpleStrategy)

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
