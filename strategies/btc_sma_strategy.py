"""
BTC SMA-50 Strategy

Pure trend-following strategy based on 50-day Simple Moving Average.
Based on study showing superior Sharpe ratio compared to Buy & Hold.

Entry: Price closes above SMA(50)
Exit: Price closes below SMA(50)

Philosophy: More responsive than EMA-150, captures trends faster but
may experience more whipsaws in sideways markets. Still significantly
outperforms B&H in risk-adjusted returns.
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCSMAStrategy(BaseStrategy):
    """
    Simple SMA-50 trend following strategy.
    
    More aggressive than EMA-150, enters/exits trends faster.
    Historically shows superior Sharpe ratio despite potentially
    more frequent trading.
    """
    
    params = (
        ('sma_period', 50),  # SMA period (50 days per study)
        ('verbose', True),
    )
    
    def __init__(self):
        """Initialize indicators."""
        super().__init__()
        
        # Main trend indicator
        self.sma = bt.indicators.SMA(
            self.data.close,
            period=self.params.sma_period
        )
        
        # Track position
        self.order = None
        self.in_position = False
        
        self.log(f"BTCSMAStrategy initialized with SMA({self.params.sma_period})")
    
    def next(self):
        """Execute strategy logic on each bar."""
        # Skip if order pending
        if self.order:
            return
        
        current_price = self.data.close[0]
        sma_value = self.sma[0]
        
        # Not in position - check for entry signal
        if not self.in_position:
            # Entry: Price closes above SMA
            if current_price > sma_value:
                self.log(f"ENTRY SIGNAL: Close ${current_price:.2f} > SMA ${sma_value:.2f}")
                # Calculate position size (use 95% of cash to leave buffer)
                cash = self.broker.get_cash()
                size = (cash * 0.95) / current_price
                self.order = self.buy(size=size)
                self.in_position = True
        
        # In position - check for exit signal
        else:
            # Exit: Price closes below SMA
            if current_price < sma_value:
                self.log(f"EXIT SIGNAL: Close ${current_price:.2f} < SMA ${sma_value:.2f}")
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
