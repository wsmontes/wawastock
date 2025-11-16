"""
Sample SMA strategy - Simple Moving Average crossover strategy.

This strategy uses two SMAs (fast and slow) to generate trading signals:
- Buy when fast SMA crosses above slow SMA
- Sell when fast SMA crosses below slow SMA
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class SampleSMAStrategy(BaseStrategy):
    """
    Simple Moving Average (SMA) crossover strategy.
    
    Parameters:
        fast_period (int): Period for the fast SMA (default: 10)
        slow_period (int): Period for the slow SMA (default: 20)
    
    Logic:
        - Buy signal: When fast SMA crosses above slow SMA (golden cross)
        - Sell signal: When fast SMA crosses below slow SMA (death cross)
    """
    
    # Strategy parameters
    params = (
        ('fast_period', 10),  # Fast moving average period
        ('slow_period', 20),  # Slow moving average period
    )
    
    def __init__(self):
        """
        Initialize strategy indicators.
        
        Creates two SMA indicators based on the close price.
        Also creates a crossover indicator to detect when SMAs cross.
        """
        # Keep reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        
        # Track pending orders
        self.order = None
        
        # Create SMA indicators
        self.fast_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], 
            period=self.params.fast_period
        )
        
        self.slow_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], 
            period=self.params.slow_period
        )
        
        # Crossover signal: +1 when fast crosses above slow, -1 when below
        self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)
    
    def next(self):
        """
        Main strategy logic - called for each bar in the data.
        
        Implements the SMA crossover trading logic:
        - If fast SMA crosses above slow SMA and we're not in the market -> BUY
        - If fast SMA crosses below slow SMA and we're in the market -> SELL
        """
        # Check if we have a pending order
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Not in the market - look for buy signal
            if self.crossover > 0:  # Fast SMA crossed above slow SMA
                self.log(f'BUY SIGNAL, Fast SMA: {self.fast_sma[0]:.2f}, Slow SMA: {self.slow_sma[0]:.2f}')
                self.order = self.buy()
        
        else:
            # In the market - look for sell signal
            if self.crossover < 0:  # Fast SMA crossed below slow SMA
                self.log(f'SELL SIGNAL, Fast SMA: {self.fast_sma[0]:.2f}, Slow SMA: {self.slow_sma[0]:.2f}')
                self.order = self.sell()
    
    def notify_order(self, order):
        """
        Override to track order completion and reset order reference.
        """
        # Call parent implementation for logging
        super().notify_order(order)
        
        # Reset order reference when order is completed or canceled
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None
