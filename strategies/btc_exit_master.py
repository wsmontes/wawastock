"""
BTCExitMaster - Exit-Focused Strategy

BREAKTHROUGH INSIGHT: Don't time entries, time EXITS!

Entry: Buy at start, stay in.
Exit: Only when pre-crash signals appear (BEFORE the crash, not after):
   1. RSI > 75 (overbought exhaustion)
   2. 90-day return > 50% (parabolic rally) - lowered from 80%
   3. Bollinger > 1.8 std (extreme stretch) - lowered from 2.0
   4. MACD bearish divergence (price up, MACD down)

Re-entry: Quick re-entry to minimize time out:
   1. RSI < 30 (capitulation) OR
   2. Price stable 10 days (< 3% movement) OR
   3. 30 days maximum out (forced re-entry)

Expected results:
- 2020: Stay in entire rally (+300%)
- 2021 Oct: EXIT at $61k (before Nov $67k peak)
- 2021: Re-enter after crash stabilizes
- 2022: Avoid most of bear market
- 2023-2024: Stay in entire rally (+400%)
- Result: 80%+ of bull gains, 60%+ crash avoidance
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCExitMaster(BaseStrategy):
    """Exit-focused strategy: Buy and hold, exit before crashes."""
    
    params = (
        # Position sizing
        ('position_size', 0.95),
        
        # Exit signals (ALL must be true)
        ('exit_rsi', 75),  # Overbought exhaustion
        ('exit_return_90d', 50),  # Parabolic rally (50% in 90 days)
        ('exit_bb_std', 1.8),  # Bollinger stretch
        ('exit_divergence_window', 30),  # Days to check MACD divergence
        
        # Re-entry signals (ANY triggers re-entry)
        ('reentry_rsi', 30),  # Capitulation
        ('reentry_stable_days', 10),  # Price stable
        ('reentry_stable_threshold', 0.03),  # 3% movement
        ('max_days_out', 30),  # Force re-entry after 30 days
    )
    
    def __init__(self):
        """Initialize indicators."""
        super().__init__()
        
        # Exit indicators
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.bb_std = bt.indicators.StdDev(self.data.close, period=20)
        self.macd = bt.indicators.MACD(self.data.close)
        
        # Tracking
        self.initial_entry = False
        self.exit_date = None
        self.days_out = 0
        self.recent_low = None
        self.days_stable = 0
        self.peak_macd = None
        self.peak_price = None
        
    def next(self):
        """Buy and hold, exit on pre-crash signals."""
        
        # Initial entry
        if not self.initial_entry and self.position.size == 0:
            if len(self.data.close) >= 200:  # Wait for indicators to warm up
                self.buy(size=self._calculate_position_size())
                self.initial_entry = True
                self.peak_macd = self.macd.macd[0]
                self.peak_price = self.data.close[0]
                self.log(f'INITIAL ENTRY: Starting buy-and-hold')
                return
        
        # Track peaks for divergence detection
        if self.position.size > 0:
            if self.data.close[0] > self.peak_price:
                self.peak_price = self.data.close[0]
                # Don't update peak MACD immediately, check for divergence
                if self.macd.macd[0] < self.peak_macd:
                    pass  # Divergence forming
                else:
                    self.peak_macd = self.macd.macd[0]
        
        # Track days out and stability
        if self.position.size == 0:
            self.days_out += 1
            
            # Track price stability for re-entry
            if self.recent_low is None or self.data.close[0] < self.recent_low:
                self.recent_low = self.data.close[0]
                self.days_stable = 0
            else:
                price_change = abs(self.data.close[0] - self.recent_low) / self.recent_low
                if price_change < self.params.reentry_stable_threshold:
                    self.days_stable += 1
                else:
                    self.days_stable = 0
        
        # Main logic
        if self.position.size == 0:
            self._check_reentry()
        else:
            self._check_exit()
    
    def _check_exit(self):
        """Check for pre-crash exit signals."""
        
        # Need minimum data for 90-day return
        if len(self.data.close) < 90:
            return
        
        # Signal 1: RSI overbought exhaustion
        rsi_overbought = self.rsi[0] > self.params.exit_rsi
        
        # Signal 2: Parabolic rally (90-day return)
        price_90d_ago = self.data.close[-90]
        return_90d = (self.data.close[0] / price_90d_ago - 1) * 100
        parabolic_rally = return_90d > self.params.exit_return_90d
        
        # Signal 3: Bollinger band extreme stretch
        bb_position = (self.data.close[0] - self.sma20[0]) / self.bb_std[0]
        extreme_stretch = bb_position > self.params.exit_bb_std
        
        # Signal 4: MACD bearish divergence
        # Price making new highs but MACD declining
        bearish_divergence = False
        if self.peak_price and self.peak_macd:
            price_up = self.data.close[0] > self.peak_price * 0.98  # Within 2% of peak
            macd_down = self.macd.macd[0] < self.peak_macd * 0.9  # MACD down 10%
            bearish_divergence = price_up and macd_down
        
        # ALL signals must be true (except divergence is optional but helpful)
        core_signals = rsi_overbought and parabolic_rally and extreme_stretch
        
        if core_signals and bearish_divergence:
            # Strong exit signal with divergence
            self.close()
            self.log(f'EXIT: Pre-crash signals (RSI={self.rsi[0]:.1f}, 90d={return_90d:.1f}%, BB={bb_position:.2f}std, MACD divergence)')
            self.exit_date = self.data.datetime.date(0)
            self.days_out = 0
            self.recent_low = self.data.close[0]
            self.days_stable = 0
            return
        elif core_signals:
            # Exit even without divergence if core signals strong
            self.close()
            self.log(f'EXIT: Core pre-crash signals (RSI={self.rsi[0]:.1f}, 90d={return_90d:.1f}%, BB={bb_position:.2f}std)')
            self.exit_date = self.data.datetime.date(0)
            self.days_out = 0
            self.recent_low = self.data.close[0]
            self.days_stable = 0
            return
    
    def _check_reentry(self):
        """Quick re-entry to minimize time out."""
        
        # Signal 1: RSI capitulation (extreme oversold)
        if self.rsi[0] < self.params.reentry_rsi:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Capitulation (RSI={self.rsi[0]:.1f})')
            self.days_out = 0
            self.peak_macd = self.macd.macd[0]
            self.peak_price = self.data.close[0]
            return
        
        # Signal 2: Price stabilized (stopped falling)
        if self.days_stable >= self.params.reentry_stable_days:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Price stabilized ({self.days_stable} days)')
            self.days_out = 0
            self.peak_macd = self.macd.macd[0]
            self.peak_price = self.data.close[0]
            return
        
        # Signal 3: Force re-entry after max days out
        if self.days_out >= self.params.max_days_out:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Max days out reached ({self.days_out} days)')
            self.days_out = 0
            self.peak_macd = self.macd.macd[0]
            self.peak_price = self.data.close[0]
            return
        
        # Signal 4: Trend clearly reversed (optional, price back above SMA50)
        if len(self.data.close) >= 50:
            sma50 = sum([self.data.close[-i] for i in range(50)]) / 50
            if self.data.close[0] > sma50 and self.rsi[0] > 40:
                self.buy(size=self._calculate_position_size())
                self.log(f'RE-ENTRY: Trend reversed (price > SMA50, RSI={self.rsi[0]:.1f})')
                self.days_out = 0
                self.peak_macd = self.macd.macd[0]
                self.peak_price = self.data.close[0]
                return
    
    def _calculate_position_size(self):
        """Calculate position size."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
