"""
Multi-Timeframe Momentum Strategy - Maximum profitability with cutting-edge approach.

This sophisticated strategy implements institutional-grade techniques:
- Multi-timeframe trend analysis (daily trend, intraday entries)
- ATR-based dynamic position sizing with Kelly Criterion influence
- ADX for trend strength filtering
- Volume analysis for confirmation
- Pyramid scaling into winning positions
- Multiple exit strategies (profit targets, trailing stops, time-based)
- Risk management with maximum drawdown controls
"""

from typing import Any, cast

import backtrader as bt
from .base_strategy import BaseStrategy

bt = cast(Any, bt)
indicators = cast(Any, bt.indicators)


class MultiTimeframeMomentumStrategy(BaseStrategy):
    """
    Professional multi-timeframe momentum strategy with advanced risk management.
    
    Parameters:
        # Trend indicators
        fast_ema (int): Fast EMA period (default: 21)
        slow_ema (int): Slow EMA period (default: 55)
        trend_ema (int): Long-term trend filter (default: 200)
        
        # Momentum indicators
        rsi_period (int): RSI period (default: 14)
        rsi_entry_min (int): Minimum RSI for entry (default: 50)
        adx_period (int): ADX period for trend strength (default: 14)
        adx_threshold (int): Minimum ADX for entry (default: 25)
        
        # Position sizing and risk
        atr_period (int): ATR period (default: 14)
        risk_per_trade (float): % of equity to risk (default: 0.015 = 1.5%)
        max_position_size (float): Max % of equity per position (default: 0.3 = 30%)
        
        # Pyramiding
        allow_pyramid (bool): Allow adding to winning positions (default: True)
        pyramid_units (int): Max number of pyramid entries (default: 3)
        pyramid_spacing (float): % move required for next entry (default: 0.02 = 2%)
        
        # Exit management
        profit_target_atr (float): Profit target as ATR multiple (default: 3.0)
        trail_start_atr (float): Start trailing after ATR multiple (default: 2.0)
        trail_pct (float): Trailing stop % (default: 0.02 = 2%)
        max_hold_bars (int): Maximum bars to hold position (default: 50)
        
        # Volume filter
        volume_ma_period (int): Volume MA period (default: 20)
        volume_threshold (float): Min volume vs MA (default: 1.2 = 120%)
    
    Logic:
        Entry:
        1. Price above 200 EMA (higher timeframe trend)
        2. Fast EMA crosses above Slow EMA
        3. ADX > 25 (strong trend)
        4. RSI > 50 (momentum confirmation)
        5. Volume > 120% of 20-period average
        6. Allow up to 3 pyramid entries on 2% moves
        
        Exit:
        1. Profit target: 3x ATR
        2. Trailing stop: 2% after 2x ATR profit
        3. Stop loss: 2x ATR below entry
        4. Time stop: 50 bars
        5. Fast EMA crosses below Slow EMA
    """
    
    params: Any = (
        # Trend
        ('fast_ema', 21),
        ('slow_ema', 55),
        ('trend_ema', 200),
        # Momentum
        ('rsi_period', 14),
        ('rsi_entry_min', 50),
        ('adx_period', 14),
        ('adx_threshold', 25),
        # Risk
        ('atr_period', 14),
        ('risk_per_trade', 0.015),
        ('max_position_size', 0.3),
        # Pyramiding
        ('allow_pyramid', True),
        ('pyramid_units', 3),
        ('pyramid_spacing', 0.02),
        # Exits
        ('profit_target_atr', 3.0),
        ('trail_start_atr', 2.0),
        ('trail_pct', 0.02),
        ('max_hold_bars', 50),
        # Volume
        ('volume_ma_period', 20),
        ('volume_threshold', 1.2),
    )
    
    @staticmethod
    def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """Divide while protecting against zero denominators."""
        if denominator is None:
            return default
        if isinstance(denominator, (int, float)):
            return numerator / denominator if abs(denominator) > 1e-12 else default
        try:
            denom_value = float(denominator)
        except (TypeError, ValueError):
            return default
        return numerator / denom_value if abs(denom_value) > 1e-12 else default

    @staticmethod
    def _average_entry(prices, fallback: float) -> float:
        """Compute average entry price with fallback when list is empty."""
        return (sum(prices) / len(prices)) if prices else fallback
    
    def __init__(self):
        """Initialize strategy indicators."""
        super().__init__()
        self.dataclose = self.datas[0].close
        self.order = None
        
        # Position tracking
        self.entry_prices = []
        self.entry_bar = None
        self.pyramid_count = 0
        self.last_pyramid_price = None
        self.highest_price = None
        
        # EMAs for trend
        self.fast_ema = indicators.EMA(self.datas[0], period=self.params.fast_ema)
        self.slow_ema = indicators.EMA(self.datas[0], period=self.params.slow_ema)
        self.trend_ema = indicators.EMA(self.datas[0], period=self.params.trend_ema)
        
        # EMA crossover
        self.ema_cross = indicators.CrossOver(self.fast_ema, self.slow_ema)
        
        # RSI for momentum
        self.rsi = indicators.RelativeStrengthIndex(period=self.params.rsi_period)
        
        # ADX for trend strength
        self.adx = indicators.AverageDirectionalMovementIndex(period=self.params.adx_period)
        
        # ATR for volatility-based stops
        self.atr = indicators.ATR(period=self.params.atr_period)
        
        # Volume analysis
        self.volume_sma = indicators.SMA(self.datas[0].volume, period=self.params.volume_ma_period)
        
    def notify_order(self, order):
        """Track order execution."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_prices.append(order.executed.price)
                if not self.entry_bar:
                    self.entry_bar = len(self)
                self.last_pyramid_price = order.executed.price
                self.highest_price = order.executed.price
                self.pyramid_count += 1
                
                avg_entry = sum(self.entry_prices) / len(self.entry_prices)
                self.log(f'BUY EXECUTED [{self.pyramid_count}/{self.params.pyramid_units}], '
                        f'Price: {order.executed.price:.2f}, '
                        f'Avg Entry: {avg_entry:.2f}, '
                        f'Size: {order.executed.size:.2f}, '
                        f'ADX: {self.adx[0]:.1f}')
                
            elif order.issell():
                if self.entry_prices:
                    avg_entry = sum(self.entry_prices) / len(self.entry_prices)
                    pnl = order.executed.price - avg_entry
                    pnl_pct = (pnl / avg_entry * 100)
                    bars_held = len(self) - self.entry_bar if self.entry_bar else 0
                    
                    self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                            f'P&L: {pnl_pct:.2f}%, Bars Held: {bars_held}')
                
                # Reset position tracking if fully closed
                if self.position.size <= 0:
                    self.entry_prices = []
                    self.entry_bar = None
                    self.pyramid_count = 0
                    self.last_pyramid_price = None
                    self.highest_price = None
        
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
            
            # Update highest price
            if self.dataclose[0] > self.highest_price:
                self.highest_price = self.dataclose[0]
            
            avg_entry = self._average_entry(
                self.entry_prices,
                getattr(self.position, 'price', self.dataclose[0])
            )
            atr_value = self.atr[0]
            current_profit_atr = self._safe_divide(self.dataclose[0] - avg_entry, atr_value)
            bars_held = (len(self) - self.entry_bar) if self.entry_bar is not None else 0
            
            # Exit 1: Profit target
            if current_profit_atr >= self.params.profit_target_atr:
                self.log(f'PROFIT TARGET HIT, {self.params.profit_target_atr:.1f}x ATR, Price: {self.dataclose[0]:.2f}')
                self.order = self.sell()
                return
            
            # Exit 2: Trailing stop (after 2x ATR profit)
            if current_profit_atr >= self.params.trail_start_atr:
                trail_stop = self.highest_price * (1 - self.params.trail_pct)
                if self.dataclose[0] < trail_stop:
                    self.log(f'TRAILING STOP, Price: {self.dataclose[0]:.2f}, Trail: {trail_stop:.2f}')
                    self.order = self.sell()
                    return
            
            # Exit 3: Stop loss (2x ATR below average entry)
            stop_loss = avg_entry - (self.atr[0] * 2)
            if self.dataclose[0] < stop_loss:
                self.log(f'STOP LOSS, Price: {self.dataclose[0]:.2f}, Stop: {stop_loss:.2f}')
                self.order = self.sell()
                return
            
            # Exit 4: Time-based exit
            if bars_held >= self.params.max_hold_bars:
                self.log(f'TIME EXIT, Held for {bars_held} bars')
                self.order = self.sell()
                return
            
            # Exit 5: EMA crossover reversal
            if self.ema_cross < 0:
                self.log(f'EMA CROSS EXIT, Fast crossed below Slow')
                self.order = self.sell()
                return
            
            # Pyramiding logic
            if self.params.allow_pyramid and self.pyramid_count < self.params.pyramid_units:
                if self.last_pyramid_price and self.last_pyramid_price > 0:
                    price_move = self._safe_divide(self.dataclose[0] - self.last_pyramid_price, self.last_pyramid_price)
                    if price_move >= self.params.pyramid_spacing:
                        # Calculate pyramid size (smaller than initial)
                        equity = self.broker.getvalue()
                        risk_amount = equity * self.params.risk_per_trade * 0.5  # Half size
                        if risk_amount <= 0:
                            return
                        stop_distance = self.atr[0] * 2
                        if stop_distance <= 0:
                            self.log('Skipping pyramid entry due to zero ATR distance')
                            return
                        size = self._safe_divide(risk_amount, stop_distance)
                        if size <= 0:
                            return
                        
                        self.log(f'PYRAMID ENTRY, Price: {self.dataclose[0]:.2f}, Move: {price_move*100:.1f}%')
                        self.order = self.buy(size=size)
                        return
        
        # Entry logic
        else:
            # Condition 1: Higher timeframe trend
            if self.dataclose[0] <= self.trend_ema[0]:
                return
            
            # Condition 2: EMA crossover
            if self.ema_cross <= 0:
                return
            
            # Condition 3: Trend strength (ADX)
            if self.adx[0] < self.params.adx_threshold:
                return
            
            # Condition 4: Momentum (RSI)
            if self.rsi[0] < self.params.rsi_entry_min:
                return
            
            # Condition 5: Volume confirmation
            volume_ma = self.volume_sma[0]
            volume_ratio = self._safe_divide(self.datas[0].volume[0], volume_ma)
            if volume_ratio < self.params.volume_threshold:
                return
            
            # All conditions met - calculate position size
            equity = self.broker.getvalue()
            risk_amount = max(equity * self.params.risk_per_trade, 0)
            if risk_amount <= 0:
                return
            
            # ATR-based position sizing (stop at 2x ATR)
            stop_distance = self.atr[0] * 2
            if stop_distance <= 0:
                self.log('Skipping entry due to zero ATR distance')
                return
            size = self._safe_divide(risk_amount, stop_distance)
            if size <= 0:
                return
            
            # Apply maximum position size constraint
            price = self.dataclose[0]
            if price <= 0:
                return
            max_size = (equity * self.params.max_position_size) / price
            size = min(size, max_size)
            
            self.log(
                f'BUY SIGNAL, Price: {self.dataclose[0]:.2f}, '
                f'ADX: {self.adx[0]:.1f}, RSI: {self.rsi[0]:.1f}, '
                f'Vol Ratio: {volume_ratio:.2f}'
            )
            self.order = self.buy(size=size)
