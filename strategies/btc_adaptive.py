"""
BTC Adaptive Strategy - Regime-Based Multi-Strategy System

FILOSOFIA:
- Detecta regime de mercado em tempo real (bull/sideways/bear)
- Ativa sub-estratégia apropriada para cada regime
- Bull: HOLD com trailing stop largo
- Sideways: MEAN REVERSION com take profit rápido
- Bear: PROTEÇÃO com exit agressivo

OBJETIVO:
Bater buy & hold em >60% dos anos através de adaptação ao regime.
"""

import backtrader as bt
import numpy as np
from .base_strategy import BaseStrategy


class BTCAdaptive(BaseStrategy):
    """
    Meta-estratégia que adapta comportamento baseado no regime de mercado.
    """
    
    params = (
        # Regime Detection Parameters (ADJUSTED)
        ('regime_lookback', 60),  # Janela menor = mais responsivo
        ('volatility_period', 14),  # Período ATR
        ('trend_fast_ma', 50),  # SMA rápida
        ('trend_slow_ma', 200),  # SMA lenta
        ('momentum_period', 60),  # Período menor para momentum
        
        # Bull Mode Parameters (hold com trailing largo)
        ('bull_position_size', 0.85),  # Menos agressivo
        ('bull_trailing_pct', 0.18),  # Trailing stop mais largo
        ('bull_entry_rsi_max', 60),  # Mais conservador - evita tops
        
        # Sideways Mode Parameters (mean reversion)
        ('sideways_position_size', 0.70),  # Mais agressivo
        ('sideways_rsi_entry', 40),  # Entry menos extremo
        ('sideways_rsi_exit', 60),  # Exit mais cedo
        ('sideways_take_profit', 0.15),  # TP +15%
        ('sideways_stop_loss', 0.10),  # SL -10%
        
        # Bear Mode Parameters (proteção)
        ('bear_position_size', 0.40),  # Um pouco mais agressivo
        ('bear_rsi_entry', 30),  # Menos extremo
        ('bear_take_profit', 0.10),  # TP +10%
        ('bear_stop_loss', 0.07),  # SL -7%
        ('bear_max_hold_days', 7),  # Mais tempo
        
        # General Parameters
        ('rsi_period', 14),
        ('bb_period', 20),
        ('bb_std', 2.0),
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
    )
    
    def __init__(self):
        super().__init__()
        
        # Indicators for regime detection
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.trend_fast_ma)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.trend_slow_ma)
        self.atr = bt.indicators.ATR(self.data, period=self.params.volatility_period)
        
        # Technical indicators for entries/exits
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.bb = bt.indicators.BollingerBands(self.data.close, 
                                                period=self.params.bb_period,
                                                devfactor=self.params.bb_std)
        self.macd = bt.indicators.MACD(self.data.close,
                                       period_me1=self.params.macd_fast,
                                       period_me2=self.params.macd_slow,
                                       period_signal=self.params.macd_signal)
        
        # State tracking
        self.current_regime = None
        self.entry_price = None
        self.entry_date = None
        self.trailing_stop = None
        self.regime_history = []
        
    def detect_regime(self):
        """
        Detecta regime atual baseado em múltiplos indicadores.
        
        Returns:
            'BULL', 'SIDEWAYS', or 'BEAR'
        """
        if len(self.data) < self.params.regime_lookback:
            return 'SIDEWAYS'  # Default até ter dados suficientes
        
        # 1. Calculate rolling return (90 days)
        price_now = self.data.close[0]
        price_90d_ago = self.data.close[-self.params.regime_lookback]
        rolling_return = ((price_now - price_90d_ago) / price_90d_ago) * 100
        
        # 2. Trend strength (SMA position)
        sma_fast = self.sma_fast[0]
        sma_slow = self.sma_slow[0]
        price_vs_sma = ((price_now - sma_slow) / sma_slow) * 100
        trend_aligned = sma_fast > sma_slow
        
        # 3. Volatility regime (ATR as % of price)
        atr_pct = (self.atr[0] / price_now) * 100
        high_volatility = atr_pct > 5.0
        
        # 4. Momentum consistency (% up days in last 90 days)
        up_days = 0
        total_days = min(self.params.momentum_period, len(self.data) - 1)
        for i in range(1, total_days + 1):
            if self.data.close[-i] > self.data.close[-i-1]:
                up_days += 1
        momentum_consistency = up_days / total_days if total_days > 0 else 0.5
        
        # Classification logic (ADJUSTED - more aggressive)
        # BULL: positive momentum with trend
        if rolling_return > 15 and trend_aligned:  # Lowered from 30% to 15%
            regime = 'BULL'
        
        # BEAR: negative trend with confirmation
        elif rolling_return < -5 or (rolling_return < 5 and not trend_aligned and momentum_consistency < 0.45):
            regime = 'BEAR'
        
        # SIDEWAYS: everything else
        else:
            regime = 'SIDEWAYS'
        
        # Log regime changes
        if regime != self.current_regime:
            self.log(f"🔄 REGIME CHANGE: {self.current_regime} → {regime} "
                    f"(return_90d={rolling_return:.1f}%, vol={atr_pct:.1f}%, "
                    f"momentum={momentum_consistency:.2f})")
            self.current_regime = regime
            self.regime_history.append({
                'date': self.data.datetime.date(0),
                'regime': regime,
                'return_90d': rolling_return,
                'volatility': atr_pct,
                'momentum': momentum_consistency
            })
        
        return regime
    
    def next(self):
        # Detect current market regime
        regime = self.detect_regime()
        
        # Update trailing stop if in position
        if self.position:
            self._update_trailing_stop(regime)
            
            # Check exit conditions based on regime
            if self._check_exit_conditions(regime):
                return
        else:
            # Check entry conditions based on regime
            self._check_entry_conditions(regime)
    
    def _check_entry_conditions(self, regime):
        """Check if should enter based on current regime."""
        
        if regime == 'BULL':
            self._check_bull_entry()
        elif regime == 'SIDEWAYS':
            self._check_sideways_entry()
        elif regime == 'BEAR':
            self._check_bear_entry()
    
    def _check_bull_entry(self):
        """
        Bull Mode Entry: Compra em dips com confirmação.
        """
        # Condições AJUSTADAS - mais oportunidades:
        # 1. RSI razoável (não extremo)
        # 2. Preço acima da SMA200 (trend confirmado)
        # 3. Pequeno pullback da SMA50 (dip)
        
        rsi_ok = 30 < self.rsi[0] < self.params.bull_entry_rsi_max
        above_sma200 = self.data.close[0] > self.sma_slow[0]
        pullback_from_sma50 = self.data.close[0] < self.sma_fast[0] * 1.02  # Até 2% acima
        
        if rsi_ok and above_sma200:  # Simplificado - mais entries
            size = self._calculate_position_size(self.params.bull_position_size)
            self.buy(size=size)
            self.entry_price = self.data.close[0]
            self.entry_date = len(self.data)
            self.trailing_stop = None
            self.log(f"🚀 BULL ENTRY @ ${self.entry_price:.2f} (size={size:.4f}, RSI={self.rsi[0]:.1f})")
    
    def _check_sideways_entry(self):
        """
        Sideways Mode Entry: Mean reversion - compra oversold.
        """
        # Condições:
        # 1. RSI oversold
        # 2. Preço tocou banda inferior BB
        # 3. Volume não muito alto (evita panic)
        
        rsi_oversold = self.rsi[0] < self.params.sideways_rsi_entry
        at_lower_bb = self.data.close[0] < self.bb.lines.bot[0] * 1.02  # Próximo da banda
        
        if rsi_oversold and at_lower_bb:
            size = self._calculate_position_size(self.params.sideways_position_size)
            self.buy(size=size)
            self.entry_price = self.data.close[0]
            self.entry_date = len(self.data)
            self.trailing_stop = None
            self.log(f"📊 SIDEWAYS ENTRY @ ${self.entry_price:.2f} (size={size:.4f}, RSI={self.rsi[0]:.1f})")
    
    def _check_bear_entry(self):
        """
        Bear Mode Entry: Apenas bounces extremos de capitulation.
        """
        # Condições muito restritivas:
        # 1. RSI extremamente oversold
        # 2. Preço muito abaixo da BB inferior
        # 3. Volume spike (capitulation)
        
        rsi_extreme = self.rsi[0] < self.params.bear_rsi_entry
        deep_oversold = self.data.close[0] < self.bb.lines.bot[0] * 0.98
        
        if rsi_extreme and deep_oversold:
            size = self._calculate_position_size(self.params.bear_position_size)
            self.buy(size=size)
            self.entry_price = self.data.close[0]
            self.entry_date = len(self.data)
            self.trailing_stop = None
            self.log(f"🛡️ BEAR ENTRY @ ${self.entry_price:.2f} (size={size:.4f}, RSI={self.rsi[0]:.1f})")
    
    def _update_trailing_stop(self, regime):
        """Update trailing stop based on regime."""
        if not self.position or self.entry_price is None:
            return
        
        current_price = self.data.close[0]
        profit_pct = ((current_price - self.entry_price) / self.entry_price)
        
        # Bull Mode: Trailing stop largo após lucro mínimo
        if regime == 'BULL':
            min_profit = 0.05  # Ativa trailing após +5%
            if profit_pct >= min_profit:
                new_stop = current_price * (1 - self.params.bull_trailing_pct)
                if self.trailing_stop is None or new_stop > self.trailing_stop:
                    self.trailing_stop = new_stop
    
    def _check_exit_conditions(self, regime) -> bool:
        """Check if should exit based on regime and conditions."""
        if not self.position or self.entry_price is None:
            return False
        
        current_price = self.data.close[0]
        profit_pct = ((current_price - self.entry_price) / self.entry_price)
        days_held = len(self.data) - self.entry_date
        
        # Check trailing stop (all regimes)
        if self.trailing_stop and current_price < self.trailing_stop:
            self.close()
            self.log(f"🛑 TRAILING STOP @ ${current_price:.2f} (profit={profit_pct*100:.1f}%, stop=${self.trailing_stop:.2f})")
            self._reset_position_state()
            return True
        
        # Regime-specific exits
        if regime == 'BULL':
            return self._check_bull_exit(profit_pct, days_held)
        elif regime == 'SIDEWAYS':
            return self._check_sideways_exit(profit_pct, days_held)
        elif regime == 'BEAR':
            return self._check_bear_exit(profit_pct, days_held)
        
        return False
    
    def _check_bull_exit(self, profit_pct, days_held) -> bool:
        """Bull Mode Exit: Apenas quebra de trend ou trailing stop."""
        # Exit apenas se:
        # 1. MACD bearish cross
        # 2. Preço rompe SMA200 para baixo com força
        
        macd_bearish = self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] > self.macd.signal[-1]
        break_sma200 = self.data.close[0] < self.sma_slow[0] * 0.95
        
        if macd_bearish and break_sma200:
            self.close()
            self.log(f"📉 BULL EXIT - Trend break @ ${self.data.close[0]:.2f} (profit={profit_pct*100:.1f}%)")
            self._reset_position_state()
            return True
        
        return False
    
    def _check_sideways_exit(self, profit_pct, days_held) -> bool:
        """Sideways Mode Exit: Take profit rápido ou stop loss."""
        # Take profit
        if profit_pct >= self.params.sideways_take_profit:
            self.close()
            self.log(f"💰 SIDEWAYS TP @ ${self.data.close[0]:.2f} (profit={profit_pct*100:.1f}%)")
            self._reset_position_state()
            return True
        
        # Stop loss
        if profit_pct <= -self.params.sideways_stop_loss:
            self.close()
            self.log(f"🛑 SIDEWAYS SL @ ${self.data.close[0]:.2f} (loss={profit_pct*100:.1f}%)")
            self._reset_position_state()
            return True
        
        # RSI overbought exit
        if self.rsi[0] > self.params.sideways_rsi_exit:
            self.close()
            self.log(f"📈 SIDEWAYS EXIT - Overbought @ ${self.data.close[0]:.2f} (profit={profit_pct*100:.1f}%, RSI={self.rsi[0]:.1f})")
            self._reset_position_state()
            return True
        
        return False
    
    def _check_bear_exit(self, profit_pct, days_held) -> bool:
        """Bear Mode Exit: Take profit rápido ou stop loss apertado."""
        # Take profit rápido
        if profit_pct >= self.params.bear_take_profit:
            self.close()
            self.log(f"💰 BEAR TP @ ${self.data.close[0]:.2f} (profit={profit_pct*100:.1f}%)")
            self._reset_position_state()
            return True
        
        # Stop loss apertado
        if profit_pct <= -self.params.bear_stop_loss:
            self.close()
            self.log(f"🛑 BEAR SL @ ${self.data.close[0]:.2f} (loss={profit_pct*100:.1f}%)")
            self._reset_position_state()
            return True
        
        # Max holding period
        if days_held >= self.params.bear_max_hold_days:
            self.close()
            self.log(f"⏰ BEAR EXIT - Max hold @ ${self.data.close[0]:.2f} (profit={profit_pct*100:.1f}%, days={days_held})")
            self._reset_position_state()
            return True
        
        return False
    
    def _calculate_position_size(self, target_pct):
        """Calculate position size based on available cash."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        max_shares = (cash * target_pct) / price
        return max_shares
    
    def _reset_position_state(self):
        """Reset position tracking variables."""
        self.entry_price = None
        self.entry_date = None
        self.trailing_stop = None
    
    def stop(self):
        """Called when strategy ends - log regime statistics."""
        super().stop()
        
        if self.regime_history:
            regime_counts = {}
            for record in self.regime_history:
                regime = record['regime']
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            
            self.log("="*60)
            self.log("📊 REGIME STATISTICS:")
            for regime, count in regime_counts.items():
                self.log(f"   {regime}: {count} transitions")
            self.log("="*60)
