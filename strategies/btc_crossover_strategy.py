"""
BTC Crossover Strategy (20/100)

Dual moving average crossover strategy.
Based on study showing ~116% annual return and Sharpe ratio of 1.7.

Entry: SMA(20) crosses above SMA(100)
Exit: SMA(20) crosses below SMA(100)

Philosophy: Golden/Death cross variant. Slower to react than single MA
strategies but generates very reliable signals. The crossover confirms
momentum shift more strongly than simple price vs MA.
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCCrossoverStrategy(BaseStrategy):
    """
    Dual SMA crossover strategy (20-day vs 100-day).
    
    Classic trend-following approach using two moving averages.
    When fast MA crosses above slow MA = bullish (buy).
    When fast MA crosses below slow MA = bearish (sell).
    
    Historically delivers ~116% annual return with Sharpe of 1.7.
    """
    
    params = (
        ('fast_period', 20),   # Fast SMA period
        ('slow_period', 100),  # Slow SMA period
        ('verbose', True),
    )
    
    def __init__(self):
        """Initialize indicators."""
        super().__init__()
        
        # Dual moving averages
        self.sma_fast = bt.indicators.SMA(
            self.data.close,
            period=self.params.fast_period
        )
        
        self.sma_slow = bt.indicators.SMA(
            self.data.close,
            period=self.params.slow_period
        )
        
        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # Track position
        self.order = None
        self.in_position = False
        
        self.log(f"BTCCrossoverStrategy initialized: "
                f"SMA({self.params.fast_period}) x SMA({self.params.slow_period})")
    
    def next(self):
        """Execute strategy logic on each bar."""
        # Skip if order pending
        if self.order:
            return
        
        current_price = self.data.close[0]
        fast_value = self.sma_fast[0]
        slow_value = self.sma_slow[0]
        
        # Not in position - check for entry signal
        if not self.in_position:
            # Entry: Fast SMA crosses above Slow SMA (Golden Cross)
            if self.crossover[0] > 0:
                self.log(f"GOLDEN CROSS: Fast SMA ${fast_value:.2f} > Slow SMA ${slow_value:.2f}")
                self.log(f"ENTRY SIGNAL: Price ${current_price:.2f}")
                # Calculate position size (use 95% of cash to leave buffer)
                cash = self.broker.get_cash()
                size = (cash * 0.95) / current_price
                self.order = self.buy(size=size)
                self.in_position = True
        
        # In position - check for exit signal
        else:
            # Exit: Fast SMA crosses below Slow SMA (Death Cross)
            if self.crossover[0] < 0:
                self.log(f"DEATH CROSS: Fast SMA ${fast_value:.2f} < Slow SMA ${slow_value:.2f}")
                self.log(f"EXIT SIGNAL: Price ${current_price:.2f}")
                self.order = self.close()
                self.in_position = False
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED: Price ${order.executed.price:.2f}, "
                        f"Size {order.executed.size:.4f}, "
                        f"Cost ${order.executed.value:.2f}, "
                        f"Comm ${order.executed.comm:.2f}")
            elif order.issell():
                self.log(f"SELL EXECUTED: Price ${order.executed.price:.2f}, "
                        f"Size {order.executed.size:.4f}, "
                        f"Value ${order.executed.value:.2f}, "
                        f"Comm ${order.executed.comm:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected")
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications."""
        if not trade.isclosed:
            return
        
        self.log(f"TRADE CLOSED: Profit ${trade.pnl:.2f}, Net ${trade.pnlcomm:.2f}")
