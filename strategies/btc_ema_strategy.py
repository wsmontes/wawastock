"""
BTC EMA-150 Strategy

Pure trend-following strategy based on 150-day Exponential Moving Average.
Based on study showing ~126% annual return and Sharpe ratio of 1.9.

Entry: Price closes above EMA(150)
Exit: Price closes below EMA(150)

Philosophy: Capture the "middle" of major trends, avoiding trying to pick
tops and bottoms. Accept missing 10-20% of moves to avoid 50-80% drawdowns.
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCEMAStrategy(BaseStrategy):
    """
    Simple EMA-150 trend following strategy.
    
    This strategy stays long only when price is above the 150-day EMA,
    moving to cash when price falls below. Extremely simple but historically
    effective at reducing drawdowns while maintaining strong returns.
    """
    
    params = (
        ('ema_period', 150),  # EMA period (150 days per study)
        ('verbose', True),
    )
    
    def __init__(self):
        """Initialize indicators."""
        super().__init__()
        
        # Main trend indicator
        self.ema = bt.indicators.EMA(
            self.data.close,
            period=self.params.ema_period
        )
        
        # Track position
        self.order = None
        self.in_position = False
        
        self.log(f"BTCEMAStrategy initialized with EMA({self.params.ema_period})")
    
    def next(self):
        """Execute strategy logic on each bar."""
        # Skip if order pending
        if self.order:
            return
        
        current_price = self.data.close[0]
        ema_value = self.ema[0]
        
        # Not in position - check for entry signal
        if not self.in_position:
            # Entry: Price closes above EMA
            if current_price > ema_value:
                self.log(f"ENTRY SIGNAL: Close ${current_price:.2f} > EMA ${ema_value:.2f}")
                # Calculate position size (use 95% of cash to leave buffer)
                cash = self.broker.get_cash()
                size = (cash * 0.95) / current_price
                self.order = self.buy(size=size)
                self.in_position = True
        
        # In position - check for exit signal
        else:
            # Exit: Price closes below EMA
            if current_price < ema_value:
                self.log(f"EXIT SIGNAL: Close ${current_price:.2f} < EMA ${ema_value:.2f}")
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
