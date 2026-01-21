"""
BTCTrendFollower - Pure Trend Following Strategy

Philosophy:
- NO PREDICTION: Don't try to time tops or bottoms
- FOLLOW THE TREND: Enter when trend is confirmed, exit when trend breaks
- SIMPLE RULES: SMA alignment is the only signal
- HIGH EXPOSURE: Stay in market during entire trend duration
- ACCEPT DRAWDOWNS: Give back some gains at trend reversals (inevitable)

Entry: SMA20 > SMA50 > SMA200 (bull trend confirmed)
Exit: SMA20 crosses below SMA50 (trend broken)

Why this might work:
- BTC has clear trends that last months (2020 rally, 2021 rally, 2022 bear, 2023 rally, 2024 rally)
- Don't need to catch tops/bottoms, just ride the middle 60-80% of each trend
- Accepts 10-20% drawdowns at reversals as cost of trend following
- No RSI, no MACD, no volume - pure price action
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCTrendFollower(BaseStrategy):
    """Pure trend following: Enter on SMA alignment, exit on SMA break."""
    
    params = (
        # SMA periods for trend detection
        ('sma_fast', 20),   # Fast trend
        ('sma_mid', 50),    # Medium trend
        ('sma_slow', 200),  # Long-term trend
        
        # Position management
        ('position_size', 0.95),  # Almost fully invested when in trend
        
        # Optional: Trailing stop to lock in profits (disabled by default)
        ('use_trailing_stop', False),
        ('trailing_pct', 0.25),  # 25% trailing stop from peak
    )
    
    def __init__(self):
        """Initialize SMAs."""
        super().__init__()
        
        # Simple Moving Averages
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.sma_fast)
        self.sma_mid = bt.indicators.SMA(self.data.close, period=self.params.sma_mid)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.sma_slow)
        
        # Tracking
        self.peak_price = None
        self.entry_price = None
        
    def next(self):
        """Check trend alignment and act accordingly."""
        
        # Skip if not enough data for SMAs
        if len(self.data.close) < self.params.sma_slow:
            return
        
        # Track peak price for trailing stop
        if self.position.size > 0:
            if self.peak_price is None or self.data.close[0] > self.peak_price:
                self.peak_price = self.data.close[0]
        
        # Main logic
        if self.position.size == 0:
            # Not in position: Check for trend alignment (entry signal)
            self._check_entry()
        else:
            # In position: Check for trend break (exit signal)
            self._check_exit()
    
    def _check_entry(self):
        """Entry: SMA20 > SMA50 > SMA200 (bull trend confirmed)."""
        
        # Bull alignment: Fast > Mid > Slow
        bull_alignment = (
            self.sma_fast[0] > self.sma_mid[0] and
            self.sma_mid[0] > self.sma_slow[0]
        )
        
        # Additional confirmation: Price above all SMAs
        price_above_all = (
            self.data.close[0] > self.sma_fast[0] and
            self.data.close[0] > self.sma_mid[0] and
            self.data.close[0] > self.sma_slow[0]
        )
        
        # Only enter when BOTH conditions met
        if bull_alignment and price_above_all:
            # Check we're not entering right after exit (avoid whipsaw)
            # Require at least 5 bars since last exit
            trades = [o for o in self.broker.orders if o.status in [o.Completed]]
            if len(trades) > 0:
                # Simple whipsaw protection: don't re-enter immediately
                return
            
            size = self._calculate_position_size()
            self.buy(size=size)
            self.entry_price = self.data.close[0]
            self.peak_price = self.data.close[0]
            self.log(f'ENTRY: Trend aligned (SMA20={self.sma_fast[0]:.0f} > SMA50={self.sma_mid[0]:.0f} > SMA200={self.sma_slow[0]:.0f})')
    
    def _check_exit(self):
        """Exit: SMA20 crosses below SMA50 (trend broken)."""
        
        # Exit signal: Fast SMA crosses below Mid SMA
        trend_break = (
            self.sma_fast[0] < self.sma_mid[0] and
            self.sma_fast[-1] >= self.sma_mid[-1]  # Was above yesterday
        )
        
        if trend_break:
            self.close()
            gain_pct = ((self.data.close[0] - self.entry_price) / self.entry_price * 100) if self.entry_price else 0
            self.log(f'EXIT: Trend break (SMA20 crossed below SMA50, gain: {gain_pct:+.1f}%)')
            self.entry_price = None
            self.peak_price = None
            return
        
        # Optional: Trailing stop (disabled by default)
        if self.params.use_trailing_stop and self.peak_price:
            trailing_stop_price = self.peak_price * (1 - self.params.trailing_pct)
            if self.data.close[0] < trailing_stop_price:
                self.close()
                gain_pct = ((self.data.close[0] - self.entry_price) / self.entry_price * 100) if self.entry_price else 0
                drawdown_from_peak = ((self.data.close[0] - self.peak_price) / self.peak_price * 100)
                self.log(f'EXIT: Trailing stop ({drawdown_from_peak:.1f}% from peak, total gain: {gain_pct:+.1f}%)')
                self.entry_price = None
                self.peak_price = None
                return
        
        # Emergency stop loss: -30% from entry (should rarely hit with SMA exits)
        if self.entry_price:
            current_loss = ((self.data.close[0] - self.entry_price) / self.entry_price * 100)
            if current_loss < -30:
                self.close()
                self.log(f'EXIT: Emergency stop loss ({current_loss:.1f}%)')
                self.entry_price = None
                self.peak_price = None
                return
    
    def _calculate_position_size(self):
        """Calculate position size based on available cash."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
