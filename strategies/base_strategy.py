"""
Base strategy module - Base class for all trading strategies.
"""

import backtrader as bt
from utils.logger import get_logger


class BaseStrategy(bt.Strategy):
    """
    Base class for all trading strategies in the framework.
    
    Provides common functionality and helpers that can be used
    by all strategy implementations.
    
    Subclasses should implement:
    - __init__: to define indicators
    - next: to define trading logic
    """
    
    def __init__(self):
        """Initialize base strategy with logger."""
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
    
    def log(self, txt, dt=None):
        """
        Logging helper for strategy events.
        
        Args:
            txt: Text to log
            dt: Optional datetime (uses current data datetime if not provided)
        """
        dt = dt or self.datas[0].datetime.date(0)
        self.logger.debug(f'{dt.isoformat()} {txt}')
    
    def notify_order(self, order):
        """
        Callback for order status changes.
        
        Logs when orders are executed, canceled, or have errors.
        """
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - nothing to do
            return
        
        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
    
    def notify_trade(self, trade):
        """
        Callback for trade closure.
        
        Logs when a trade (position) is closed with its P&L.
        """
        if not trade.isclosed:
            return
        
        self.log(f'TRADE PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}')
