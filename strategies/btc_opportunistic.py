"""
BTCOpportunistic Strategy - "Hold by Default, Exit on Danger"

Philosophy:
- Inverted approach: Instead of timing entries (hard), time exits (easier)
- Hold by default to capture bull runs (solve the -272% alpha problem)
- Exit only on clear danger signals: parabolic exhaustion, trend breaks, momentum divergence
- Re-enter quickly to minimize time out of market
- Goal: 80-90% exposure time, 6-8 trades/year, 70%+ yearly win rate

Danger Signals (Exit triggers):
1. Parabolic exhaustion: RSI>80 + steep price angle + extended rally
2. Trend breakdown: Close below SMA50 after being above for >30 days
3. Momentum divergence: New price high but MACD lower than previous peak
4. Volume climax: Spike >5x average volume (potential blow-off top)

Re-Entry Signals (Get back in quickly):
1. Capitulation: RSI<25 + volume spike (panic selling exhaustion)
2. Trend resumption: Price closes back above SMA50
3. Momentum reset: MACD crosses back up + RSI>40 (bull resuming)

Key Differences from Previous Approaches:
- V1/V2: Conservative entries → missed bulls → negative alpha
- Adaptive: Regime switching → too few trades → high variance
- Opportunistic: Always exposed unless danger → capture rallies → positive alpha
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCOpportunistic(BaseStrategy):
    """Opportunistic strategy: Hold by default, exit only on clear danger signals."""
    
    params = (
        # Position management
        ('position_size', 0.95),  # Almost fully invested by default
        
        # Danger signal detection
        ('rsi_exhaustion', 80),  # Extreme overbought
        ('rsi_period', 14),
        ('exhaustion_days', 3),  # How many days RSI>80 to trigger
        
        ('sma_short', 50),  # Trend reference
        ('sma_long', 200),
        ('trend_break_days', 30),  # Must be above SMA50 for this long before break counts
        
        ('volume_spike_factor', 5.0),  # Volume > 5x average = climax
        ('volume_period', 20),  # Rolling average for comparison
        
        # Re-entry signals
        ('rsi_capitulation', 25),  # Extreme oversold
        ('rsi_momentum_resume', 40),  # Minimum RSI for momentum re-entry
        
        # Risk management
        ('stop_loss_pct', 0.20),  # Emergency stop at -20% (prevent -50% crashes)
        ('take_profit_pct', 0.30),  # Lock in gains at +30% from entry (optional)
    )
    
    def __init__(self):
        """Initialize indicators for danger detection."""
        super().__init__()
        
        # Indicators
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.sma50 = bt.indicators.SMA(self.data.close, period=self.params.sma_short)
        self.sma200 = bt.indicators.SMA(self.data.close, period=self.params.sma_long)
        self.macd = bt.indicators.MACD(self.data.close)
        self.volume_avg = bt.indicators.SMA(self.data.volume, period=self.params.volume_period)
        
        # Tracking variables
        self.days_above_sma50 = 0
        self.days_rsi_exhaustion = 0
        self.entry_price = None
        self.previous_macd = None
        self.previous_price_high = None
        
        # Trade statistics
        self.exits_taken = 0
        self.successful_exits = 0  # Exits that avoided drawdown >10%
        
    def next(self):
        """Main strategy logic: Hold by default, exit on danger, re-enter quickly."""
        
        # Track position entry price
        if self.position.size > 0 and self.entry_price is None:
            self.entry_price = self.data.close[0]
        
        # Track days above SMA50 for trend break detection
        if self.data.close[0] > self.sma50[0]:
            self.days_above_sma50 += 1
        else:
            self.days_above_sma50 = 0
        
        # Track RSI exhaustion days
        if self.rsi[0] > self.params.rsi_exhaustion:
            self.days_rsi_exhaustion += 1
        else:
            self.days_rsi_exhaustion = 0
        
        # Main logic branches
        if self.position.size == 0:
            # Not in position: Look for re-entry signals
            self._check_reentry()
        else:
            # In position: Monitor for danger signals to exit
            self._check_exit_danger()
    
    def _check_reentry(self):
        """Check for re-entry signals after exiting on danger."""
        
        # Signal 1: Capitulation (panic selling exhaustion)
        volume_spike = (self.data.volume[0] > self.volume_avg[0] * self.params.volume_spike_factor 
                       if len(self.volume_avg) > 0 else False)
        
        capitulation = (self.rsi[0] < self.params.rsi_capitulation and volume_spike)
        
        if capitulation:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Capitulation (RSI={self.rsi[0]:.1f}, Volume spike)')
            return
        
        # Signal 2: Trend resumption (price back above SMA50)
        trend_resumption = (self.data.close[0] > self.sma50[0] and 
                           self.data.close[-1] <= self.sma50[-1])  # Just crossed up
        
        if trend_resumption and self.rsi[0] > 35:  # Not oversold
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Trend resumption (close back above SMA50)')
            return
        
        # Signal 3: Momentum reset (MACD cross up + RSI healthy)
        macd_cross_up = (self.macd.macd[0] > self.macd.signal[0] and 
                        self.macd.macd[-1] <= self.macd.signal[-1])
        
        momentum_reset = (macd_cross_up and 
                         self.rsi[0] > self.params.rsi_momentum_resume and 
                         self.rsi[0] < 70)  # Not overbought
        
        if momentum_reset:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Momentum reset (MACD cross up, RSI={self.rsi[0]:.1f})')
            return
        
        # Signal 4: Simple mean reversion after >10 days out
        # If we've been out too long and conditions not terrible, get back in
        days_out = len([o for o in self.broker.orders if o.status in [o.Completed] and o.issell()]) * 5
        if days_out > 10 and self.rsi[0] < 60 and self.data.close[0] > self.sma200[0]:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Too long out of market (RSI={self.rsi[0]:.1f}, above SMA200)')
            return
    
    def _check_exit_danger(self):
        """Monitor for danger signals to exit position."""
        
        current_pnl_pct = ((self.data.close[0] - self.entry_price) / self.entry_price * 100 
                          if self.entry_price else 0)
        
        # Emergency stop loss
        if current_pnl_pct < -self.params.stop_loss_pct * 100:
            self.close()
            self.log(f'EXIT: Emergency stop loss ({current_pnl_pct:.1f}%)')
            self.exits_taken += 1
            self.entry_price = None
            return
        
        # Danger Signal 1: Parabolic exhaustion
        # RSI>80 for multiple days + steep price angle
        if self.days_rsi_exhaustion >= self.params.exhaustion_days:
            # Check if rally has been steep (>40% in 30 days)
            if len(self.data.close) >= 30:
                rally_return = (self.data.close[0] / self.data.close[-30] - 1) * 100
                if rally_return > 40:
                    self.close()
                    self.log(f'EXIT: Parabolic exhaustion (RSI>{self.params.rsi_exhaustion} for {self.days_rsi_exhaustion}d, +{rally_return:.1f}% rally)')
                    self.exits_taken += 1
                    self.entry_price = None
                    self.days_rsi_exhaustion = 0
                    return
        
        # Danger Signal 2: Trend breakdown
        # Close below SMA50 after being above for extended period
        trend_break = (self.days_above_sma50 >= self.params.trend_break_days and 
                      self.data.close[0] < self.sma50[0])
        
        if trend_break:
            self.close()
            self.log(f'EXIT: Trend breakdown (close below SMA50 after {self.days_above_sma50}d above)')
            self.exits_taken += 1
            self.entry_price = None
            self.days_above_sma50 = 0
            return
        
        # Danger Signal 3: Momentum divergence
        # New price high but MACD lower than previous peak
        if len(self.data.close) >= 2:
            current_price = self.data.close[0]
            current_macd = self.macd.macd[0]
            
            # Check if we have a new high
            if len(self.data.close) >= 20:
                recent_high = max([self.data.close[-i] for i in range(1, 20)])
                is_new_high = current_price > recent_high
                
                if is_new_high and self.previous_macd is not None:
                    # Check if MACD is lower (bearish divergence)
                    if current_macd < self.previous_macd and self.rsi[0] > 70:
                        self.close()
                        self.log(f'EXIT: Momentum divergence (new high but MACD lower, RSI={self.rsi[0]:.1f})')
                        self.exits_taken += 1
                        self.entry_price = None
                        return
                
                # Update tracking
                if is_new_high:
                    self.previous_price_high = current_price
                    self.previous_macd = current_macd
        
        # Danger Signal 4: Volume climax
        # Massive volume spike often signals blow-off top
        volume_spike = (self.data.volume[0] > self.volume_avg[0] * self.params.volume_spike_factor 
                       if len(self.volume_avg) > 0 else False)
        
        if volume_spike and self.rsi[0] > 75:
            self.close()
            self.log(f'EXIT: Volume climax ({self.data.volume[0]/self.volume_avg[0]:.1f}x avg volume, RSI={self.rsi[0]:.1f})')
            self.exits_taken += 1
            self.entry_price = None
            return
        
        # Optional: Take profit at +30% to lock in gains
        # Only if we see early warning signs (RSI>75 or MACD bearish cross)
        if current_pnl_pct > self.params.take_profit_pct * 100:
            macd_bearish = self.macd.macd[0] < self.macd.signal[0]
            if self.rsi[0] > 75 or macd_bearish:
                self.close()
                self.log(f'EXIT: Take profit ({current_pnl_pct:.1f}%, RSI={self.rsi[0]:.1f})')
                self.exits_taken += 1
                self.entry_price = None
                return
    
    def _calculate_position_size(self):
        """Calculate position size based on available cash."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
    
    def stop(self):
        """Log final statistics."""
        super().stop()
        if self.exits_taken > 0:
            self.log(f'Total exits taken: {self.exits_taken}')
            self.log(f'Exit success rate: {self.successful_exits/self.exits_taken*100:.1f}%')
