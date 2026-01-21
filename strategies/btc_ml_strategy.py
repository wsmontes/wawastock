"""
BTCMLStrategy - Machine Learning Based Crash Prediction Strategy

Uses XGBoost to predict crashes and exit BEFORE they happen.
"""

import backtrader as bt
import numpy as np
import pandas as pd
from typing import Optional

from strategies.base_strategy import BaseStrategy


class BTCMLStrategy(BaseStrategy):
    """
    ML-powered strategy that predicts crashes using XGBoost.
    
    Entry: Buy at start (after warmup)
    Exit: When crash probability > threshold
    Re-entry: When crash probability < threshold OR RSI capitulation
    
    Requires pre-computed crash probabilities passed via strategy params.
    """
    
    params = (
        ('exit_prob_threshold', 0.70),      # Exit when crash prob > 70%
        ('reentry_prob_threshold', 0.30),   # Re-enter when crash prob < 30%
        ('reentry_rsi', 30),                # Or when RSI < 30 (capitulation)
        ('max_days_out', 30),               # Force re-entry after 30 days
        ('position_size', 0.95),            # 95% of capital
        ('multi_timeframe_confirm', True),  # Require weekly confirmation
        ('crash_probs', None),              # Pre-computed crash probabilities (dict: date -> prob)
    )
    
    def __init__(self):
        """Initialize indicators and tracking."""
        super().__init__()
        
        # Indicators
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.sma_50 = bt.indicators.SMA(self.data.close, period=50)
        self.sma_200 = bt.indicators.SMA(self.data.close, period=200)
        
        # For multi-timeframe (weekly)
        self.data_weekly = bt.TimeFrame.Weeks
        self.sma_20_weekly = bt.indicators.SMA(self.data.close, period=20)
        
        # Tracking variables
        self.initial_entry = False
        self.days_out = 0
        self.crash_prob_history = []
        
        # Validation
        if self.params.crash_probs is None:
            raise ValueError("crash_probs parameter is required. Pass dict: {date: probability}")
    
    def next(self):
        """Main strategy logic executed on each bar."""
        # Get current crash probability
        current_date = self.data.datetime.date(0)
        crash_prob = self.params.crash_probs.get(current_date, 0.0)
        
        # Log probability
        self.crash_prob_history.append({
            'date': current_date,
            'prob': crash_prob,
            'price': self.data.close[0],
            'rsi': self.rsi[0]
        })
        
        position_size = self.position.size
        
        # =====================================================================
        # ENTRY LOGIC: Buy once at start
        # =====================================================================
        if not self.initial_entry and len(self.data) >= 200:
            size = self._calculate_position_size()
            self.buy(size=size)
            self.initial_entry = True
            self.log(f"🚀 INITIAL ENTRY - Crash Prob: {crash_prob:.1%}")
            return
        
        # =====================================================================
        # EXIT LOGIC: High crash probability detected
        # =====================================================================
        if position_size > 0:
            # Check multi-timeframe confirmation if enabled
            weekly_bearish = False
            if self.params.multi_timeframe_confirm:
                # Weekly bearish if price < 20-week SMA
                weekly_bearish = self.data.close[0] < self.sma_20_weekly[0]
            
            # Exit conditions
            exit_signal = False
            exit_reason = ""
            
            # Primary: High crash probability
            if crash_prob > self.params.exit_prob_threshold:
                if self.params.multi_timeframe_confirm:
                    # Require weekly confirmation OR extremely high probability
                    if weekly_bearish or crash_prob > 0.85:
                        exit_signal = True
                        exit_reason = f"High crash prob {crash_prob:.1%}"
                        if weekly_bearish:
                            exit_reason += " + Weekly bearish"
                else:
                    exit_signal = True
                    exit_reason = f"Crash prob {crash_prob:.1%}"
            
            if exit_signal:
                self.close()
                self.days_out = 0
                self.log(f"⚠️  EXIT - {exit_reason} (RSI: {self.rsi[0]:.1f})")
        
        # =====================================================================
        # RE-ENTRY LOGIC: Crash probability low or capitulation
        # =====================================================================
        elif position_size == 0 and self.initial_entry:
            self.days_out += 1
            
            reentry_signal = False
            reentry_reason = ""
            
            # Condition 1: Crash probability dropped
            if crash_prob < self.params.reentry_prob_threshold:
                reentry_signal = True
                reentry_reason = f"Crash prob dropped to {crash_prob:.1%}"
            
            # Condition 2: RSI capitulation (extreme oversold)
            elif self.rsi[0] < self.params.reentry_rsi:
                reentry_signal = True
                reentry_reason = f"RSI capitulation {self.rsi[0]:.1f}"
            
            # Condition 3: Forced re-entry (been out too long)
            elif self.days_out >= self.params.max_days_out:
                reentry_signal = True
                reentry_reason = f"Max days out ({self.days_out}d)"
            
            # Condition 4: Strong trend reversal
            elif self.data.close[0] > self.sma_50[0] and self.rsi[0] > 50:
                if crash_prob < 0.5:  # Don't re-enter if still predicting crash
                    reentry_signal = True
                    reentry_reason = "Trend reversed"
            
            if reentry_signal:
                size = self._calculate_position_size()
                self.buy(size=size)
                self.log(f"✅ RE-ENTRY - {reentry_reason} (Crash prob: {crash_prob:.1%}, Out: {self.days_out}d)")
                self.days_out = 0
    
    def _calculate_position_size(self) -> float:
        """Calculate position size based on available cash."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
    
    def stop(self):
        """Called when backtest ends - log summary."""
        super().stop()
        
        # Calculate crash probability statistics
        if self.crash_prob_history:
            probs = [h['prob'] for h in self.crash_prob_history]
            avg_prob = np.mean(probs)
            max_prob = np.max(probs)
            
            high_prob_days = sum(1 for p in probs if p > 0.7)
            
            self.log(f"\n📊 ML STATISTICS:")
            self.log(f"   Avg crash probability: {avg_prob:.1%}")
            self.log(f"   Max crash probability: {max_prob:.1%}")
            self.log(f"   Days with high prob (>70%): {high_prob_days}")
            self.log(f"   Total days analyzed: {len(probs)}")
