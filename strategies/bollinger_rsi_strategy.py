"""
Bollinger Bands + RSI Strategy - Advanced mean reversion with volatility analysis.

This professional strategy combines multiple technical indicators for high-probability
mean reversion trades:
- Bollinger Bands for volatility-adjusted support/resistance
- RSI for momentum confirmation
- ATR-based dynamic position sizing
- Sophisticated exit management with partial profits and trailing stops
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class BollingerRSIStrategy(BaseStrategy):
    """
    Advanced mean reversion strategy using Bollinger Bands, RSI, and ATR.
    
    Parameters:
        bb_period (int): Bollinger Bands period (default: 20)
        bb_dev (float): Bollinger Bands deviation (default: 2.0)
        rsi_period (int): RSI period (default: 14)
        rsi_oversold (int): RSI oversold level (default: 35)
        rsi_overbought (int): RSI overbought level (default: 65)
        atr_period (int): ATR period for position sizing (default: 14)
        risk_per_trade (float): % of equity to risk per trade (default: 0.02 = 2%)
        partial_take_profit (float): % of position to close at first target (default: 0.5 = 50%)
        profit_target_mult (float): Profit target as multiple of ATR (default: 2.0)
        trail_pct (float): Trailing stop % after partial profit (default: 0.015 = 1.5%)
    
    Logic:
        - Buy when price touches lower BB AND RSI < oversold
        - Take 50% profit when price reaches middle BB or RSI > 50
        - Trail remaining position with 1.5% stop
        - Full exit when price touches upper BB or RSI > overbought
        - Position size based on ATR and risk per trade
    """
    
    params = (
        ('bb_period', 20),
        ('bb_dev', 2.0),
        ('rsi_period', 14),
        ('rsi_oversold', 35),
        ('rsi_overbought', 65),
        ('atr_period', 14),
        ('risk_per_trade', 0.02),
        ('partial_take_profit', 0.5),
        ('profit_target_mult', 2.0),
        ('trail_pct', 0.015),
    )
    
    def __init__(self):
        """Initialize strategy indicators."""
        super().__init__()
        self.dataclose = self.datas[0].close
        self.order = None
        self.buy_price = None
        self.highest_price = None
        self.partial_taken = False
        self.initial_size = None
        
        # Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            self.datas[0],
            period=self.params.bb_period,
            devfactor=self.params.bb_dev
        )
        
        # RSI
        self.rsi = bt.indicators.RSI(
            self.datas[0],
            period=self.params.rsi_period
        )
        
        # ATR for position sizing
        self.atr = bt.indicators.ATR(
            self.datas[0],
            period=self.params.atr_period
        )
        
        # Percent B - where price is within BB bands
        self.pct_b = (self.dataclose - self.bb.bot) / (self.bb.top - self.bb.bot)
    
    def notify_order(self, order):
        """Track order execution."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.highest_price = self.buy_price
                self.initial_size = order.executed.size
                self.partial_taken = False
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}, ATR: {self.atr[0]:.2f}')
            elif order.issell():
                if self.buy_price:
                    pnl = order.executed.price - self.buy_price
                    pnl_pct = (pnl / self.buy_price * 100)
                    self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, P&L: {pnl_pct:.2f}%')
                if order.executed.size == self.position.size:
                    self.buy_price = None
                    self.highest_price = None
                    self.partial_taken = False
        
        self.order = None
    
    def next(self):
        """Main strategy logic."""
        if self.order:
            return
        
        # Position management
        if self.position:
            # Initialize highest_price if needed
            if self.highest_price is None:
                self.highest_price = self.dataclose[0]
            
            # Update highest price for trailing stop
            if self.dataclose[0] > self.highest_price:
                self.highest_price = self.dataclose[0]
            
            # Check for partial profit taking (first target: middle BB or RSI > 50)
            if not self.partial_taken:
                if (self.dataclose[0] >= self.bb.mid[0] or self.rsi[0] > 50):
                    partial_size = self.initial_size * self.params.partial_take_profit
                    self.log(f'PARTIAL PROFIT, Taking {self.params.partial_take_profit*100:.0f}% at {self.dataclose[0]:.2f}')
                    self.order = self.sell(size=partial_size)
                    self.partial_taken = True
                    return
            
            # After partial profit, use trailing stop
            if self.partial_taken:
                trail_stop_price = self.highest_price * (1 - self.params.trail_pct)
                if self.dataclose[0] < trail_stop_price:
                    self.log(f'TRAILING STOP, Price: {self.dataclose[0]:.2f}, Trail: {trail_stop_price:.2f}')
                    self.order = self.sell()
                    return
            
            # Full exit conditions
            if self.pct_b[0] > 0.95 or self.rsi[0] > self.params.rsi_overbought:
                self.log(f'FULL EXIT, %B: {self.pct_b[0]:.2f}, RSI: {self.rsi[0]:.2f}')
                self.order = self.sell()
                return
        
        # Entry logic - mean reversion at lower BB with RSI confirmation
        else:
            if self.pct_b[0] < 0.05 and self.rsi[0] < self.params.rsi_oversold:
                # ATR-based position sizing
                equity = self.broker.getvalue()
                risk_amount = equity * self.params.risk_per_trade
                
                # Size based on ATR stop loss (2x ATR)
                stop_distance = self.atr[0] * 2
                size = risk_amount / stop_distance
                
                # Ensure we don't over-leverage
                max_size = (equity * 0.95) / self.dataclose[0]
                size = min(size, max_size)
                
                self.log(f'BUY SIGNAL, %B: {self.pct_b[0]:.2f}, RSI: {self.rsi[0]:.2f}, BB Lower: {self.bb.bot[0]:.2f}')
                self.order = self.buy(size=size)
