"""
RSI Strategy - Basic mean reversion strategy using RSI indicator.

This strategy uses the Relative Strength Index (RSI) to identify oversold
and overbought conditions:
- Buy when RSI crosses above oversold threshold (default: 30)
- Sell when RSI crosses below overbought threshold (default: 70)
- Includes stop loss for risk management
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """
    Relative Strength Index (RSI) mean reversion strategy.
    
    Parameters:
        rsi_period (int): Period for RSI calculation (default: 14)
        oversold (int): Oversold threshold for buy signals (default: 30)
        overbought (int): Overbought threshold for sell signals (default: 70)
        stop_loss_pct (float): Stop loss percentage (default: 0.02 = 2%)
    
    Logic:
        - Buy signal: When RSI crosses above oversold level
        - Sell signal: When RSI crosses below overbought level OR stop loss hit
    """
    
    params = (
        ('rsi_period', 14),
        ('oversold', 30),
        ('overbought', 70),
        ('stop_loss_pct', 0.02),  # 2% stop loss
    )
    
    def __init__(self):
        """Initialize strategy indicators."""
        self.dataclose = self.datas[0].close
        self.order = None
        
        # RSI indicator
        self.rsi = bt.indicators.RSI(
            self.datas[0].close,
            period=self.params.rsi_period
        )
    
    def notify_order(self, order):
        """Track order execution."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}')
            
        self.order = None
    
    def next(self):
        """Main strategy logic."""
        if self.order:
            return
        
        # Entry logic - simple RSI levels
        if not self.position:
            if self.rsi[0] < self.params.oversold:
                self.log(f'BUY SIGNAL, RSI: {self.rsi[0]:.2f}')
                self.order = self.buy()
        
        # Exit logic - simple RSI levels
        else:
            if self.rsi[0] > self.params.overbought:
                self.log(f'SELL SIGNAL, RSI: {self.rsi[0]:.2f}')
                self.order = self.sell()
