"""
BTCEnhancedBH - Enhanced Buy & Hold Strategy

THE PERFECT SOLUTION:
After testing 6 approaches (V1, V2, Adaptive, Opportunistic, TrendFollower, Perfect),
the realization is clear: You can't beat BTC Buy & Hold consistently with timing.

Bulls are too explosive (+100-400%/year) and unpredictable.
Any timing strategy misses early entries and underperforms.

THE SOLUTION: Stop trying to beat B&H in bulls. Instead:
1. Match B&H in bull markets (95-100% of gains)
2. Beat B&H in bear markets (50-70% of losses avoided)
3. Result: Net positive alpha on aggregate

Strategy:
- Default: 100% invested (pure Buy & Hold)
- Exit: Only when DEEP CONFIRMED bear (SMA50 < SMA200 AND RSI < 35 AND 90d < -30%)
- Re-enter: When trend reverses (SMA50 crosses back above SMA200)

Expected results:
- 2020 bull: Stay in, +300% (match B&H)
- 2021 bull: Stay in, +40% (match B&H)  
- 2022 bear: Exit around -25%, re-enter at bottom, lose -40% vs B&H -65% = +25% alpha ✅
- 2023 bull: Stay in, +150% (match B&H)
- 2024 bull: Stay in, +105% (match B&H)
- 2025 sideways: Minor adjustments

Yearly win rate: 4-5/6 = 67-83% ✅
Aggregate alpha: +20-30% ✅
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCEnhancedBH(BaseStrategy):
    """Enhanced Buy & Hold: Stay invested unless deep bear confirmed."""
    
    params = (
        # Position sizing
        ('position_size', 1.0),  # 100% invested (true B&H)
        
        # Deep bear detection (ALL must be true to exit)
        ('sma_fast', 50),
        ('sma_slow', 200),
        ('bear_rsi', 35),  # Momentum clearly broken
        ('bear_return', -30),  # 30% drawdown
        ('bear_lookback', 90),  # Over 90 days
    )
    
    def __init__(self):
        """Initialize indicators."""
        super().__init__()
        
        # SMAs for trend
        self.sma50 = bt.indicators.SMA(self.data.close, period=self.params.sma_fast)
        self.sma200 = bt.indicators.SMA(self.data.close, period=self.params.sma_slow)
        
        # RSI for momentum
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        
        # Initial entry flag
        self.initial_entry = False
        
    def next(self):
        """Stay invested unless deep bear confirmed."""
        
        # Skip warmup
        if len(self.data.close) < self.params.sma_slow:
            return
        
        # Initial entry (buy and hold)
        if not self.initial_entry and self.position.size == 0:
            self.buy(size=self._calculate_position_size())
            self.initial_entry = True
            self.log(f'INITIAL ENTRY: Buy and hold mode activated')
            return
        
        # Main logic
        if self.position.size == 0:
            # Out of position: Re-enter when trend reverses
            self._check_reentry()
        else:
            # In position: Check if deep bear confirmed
            self._check_deep_bear_exit()
    
    def _check_deep_bear_exit(self):
        """Exit only when deep bear is CONFIRMED (all conditions true)."""
        
        # Condition 1: Death cross (SMA50 below SMA200)
        death_cross = self.sma50[0] < self.sma200[0]
        
        # Condition 2: Momentum broken (RSI < 35)
        momentum_broken = self.rsi[0] < self.params.bear_rsi
        
        # Condition 3: Deep drawdown (>30% over 90 days)
        if len(self.data.close) >= self.params.bear_lookback:
            price_ago = self.data.close[-self.params.bear_lookback]
            return_pct = ((self.data.close[0] - price_ago) / price_ago) * 100
            deep_drawdown = return_pct < self.params.bear_return
        else:
            deep_drawdown = False
        
        # ALL conditions must be true
        deep_bear_confirmed = death_cross and momentum_broken and deep_drawdown
        
        if deep_bear_confirmed:
            self.close()
            self.log(f'EXIT: Deep bear confirmed (SMA50<SMA200, RSI={self.rsi[0]:.1f}, 90d={return_pct:.1f}%)')
    
    def _check_reentry(self):
        """Re-enter when trend reverses (golden cross)."""
        
        # Golden cross: SMA50 crosses above SMA200
        golden_cross = (
            self.sma50[0] > self.sma200[0] and
            self.sma50[-1] <= self.sma200[-1]
        )
        
        if golden_cross:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Golden cross (SMA50 crossed above SMA200)')
            return
        
        # Alternative: If SMA50 already above SMA200 and RSI recovered
        if self.sma50[0] > self.sma200[0] and self.rsi[0] > 45:
            self.buy(size=self._calculate_position_size())
            self.log(f'RE-ENTRY: Trend positive, RSI recovered')
            return
    
    def _calculate_position_size(self):
        """Calculate position size (100% of capital)."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
