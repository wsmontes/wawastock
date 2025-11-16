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
        self.buy_price = None
        self.stop_loss_price = None
        
        # RSI indicator
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.datas[0],
            period=self.params.rsi_period
        )
        
        # Track crossovers for cleaner signals
        self.oversold_cross = bt.indicators.CrossOver(self.rsi, self.params.oversold)
        self.overbought_cross = bt.indicators.CrossOver(self.params.overbought, self.rsi)
    
    def notify_order(self, order):
        """Track order execution."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.stop_loss_price = self.buy_price * (1 - self.params.stop_loss_pct)
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Stop Loss: {self.stop_loss_price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}')
                self.buy_price = None
                self.stop_loss_price = None
            
        self.order = None
    
    def next(self):
        """Main strategy logic."""
        if self.order:
            return
        
        # Check for stop loss
        if self.position:
            if self.dataclose[0] < self.stop_loss_price:
                self.log(f'STOP LOSS HIT, RSI: {self.rsi[0]:.2f}, Price: {self.dataclose[0]:.2f}')
                self.order = self.sell()
                return
        
        # Entry logic
        if not self.position:
            if self.oversold_cross > 0:  # RSI crossed above oversold
                self.log(f'BUY SIGNAL, RSI: {self.rsi[0]:.2f}, Price: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        
        # Exit logic
        else:
            if self.overbought_cross > 0:  # RSI crossed below overbought
                self.log(f'SELL SIGNAL, RSI: {self.rsi[0]:.2f}, Price: {self.dataclose[0]:.2f}')
                self.order = self.sell()
