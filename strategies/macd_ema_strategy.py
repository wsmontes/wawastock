"""
MACD + EMA Strategy - Intermediary trend-following strategy.

This strategy combines MACD crossover with EMA filter for trend confirmation:
- Only takes trades in the direction of the long-term trend (200 EMA)
- Uses MACD crossover for entry timing
- Implements dynamic position sizing based on account equity
- Uses trailing stop loss for profit protection
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class MACDEMAStrategy(BaseStrategy):
    """
    MACD + EMA trend-following strategy with position sizing.
    
    Parameters:
        macd_fast (int): Fast EMA for MACD (default: 12)
        macd_slow (int): Slow EMA for MACD (default: 26)
        macd_signal (int): Signal line period (default: 9)
        trend_ema (int): Long-term trend EMA (default: 200)
        position_size_pct (float): % of equity per trade (default: 0.95 = 95%)
        stop_loss_pct (float): Initial stop loss % (default: 0.03 = 3%)
        trail_pct (float): Trailing stop % (default: 0.02 = 2%)
    
    Logic:
        - Only buy when price is above 200 EMA (uptrend)
        - Buy when MACD crosses above signal line
        - Sell when MACD crosses below signal or trailing stop hit
        - Position size: 95% of available equity
    """
    
    params = (
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('trend_ema', 200),
        ('position_size_pct', 0.95),
        ('stop_loss_pct', 0.03),
        ('trail_pct', 0.02),
    )
    
    def __init__(self):
        """Initialize strategy indicators."""
        super().__init__()
        self.dataclose = self.datas[0].close
        self.order = None
        self.buy_price = None
        self.highest_price = None
        
        # MACD indicator
        self.macd = bt.indicators.MACD(
            self.datas[0],
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        # Trend filter - 200 EMA
        self.trend_ema = bt.indicators.ExponentialMovingAverage(
            self.datas[0],
            period=self.params.trend_ema
        )
        
        # MACD crossover signal
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
    
    def notify_order(self, order):
        """Track order execution."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.highest_price = self.buy_price
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}')
            elif order.issell():
                pnl = order.executed.price - self.buy_price if self.buy_price else 0
                pnl_pct = (pnl / self.buy_price * 100) if self.buy_price else 0
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, P&L: {pnl_pct:.2f}%')
                self.buy_price = None
                self.highest_price = None
        
        self.order = None
    
    def next(self):
        """Main strategy logic."""
        if self.order:
            return
        
        # Update trailing stop
        if self.position:
            # Initialize highest_price if needed
            if self.highest_price is None:
                self.highest_price = self.dataclose[0]
            
            if self.dataclose[0] > self.highest_price:
                self.highest_price = self.dataclose[0]
            
            # Check trailing stop
            trail_stop_price = self.highest_price * (1 - self.params.trail_pct)
            if self.dataclose[0] < trail_stop_price:
                self.log(f'TRAILING STOP HIT, Price: {self.dataclose[0]:.2f}, Trail: {trail_stop_price:.2f}')
                self.order = self.sell()
                return
            
            # Check MACD exit signal
            if self.macd_cross < 0:
                self.log(f'SELL SIGNAL, MACD crossed below signal, Price: {self.dataclose[0]:.2f}')
                self.order = self.sell()
                return
        
        # Entry logic
        else:
            # Check trend filter - only buy in uptrend
            if self.dataclose[0] > self.trend_ema[0]:
                if self.macd_cross > 0:  # MACD crossed above signal
                    # Calculate position size based on equity
                    equity = self.broker.getvalue()
                    size = (equity * self.params.position_size_pct) / self.dataclose[0]
                    
                    self.log(f'BUY SIGNAL, MACD: {self.macd.macd[0]:.4f}, Signal: {self.macd.signal[0]:.4f}, Price: {self.dataclose[0]:.2f}')
                    self.order = self.buy(size=size)
