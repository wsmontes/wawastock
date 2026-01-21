"""
BTC Winning Strategy V2 - Quick Wins Implementation

MELHORIAS vs V1:
1. Dynamic trailing stops baseados em ATR (volatilidade adaptativa)
2. Higher highs/lows momentum detection (trend strength)
3. Bull run protection (não sai por ruído em rallies fortes)
4. Hard stop + trailing stop com lógica clara

FILOSOFIA:
- Mantém base da estratégia campeã
- Exits adaptativos baseados em volatilidade (ATR)
- Detecta força de trend antes de entrar
- Aguenta correções em bull runs sem sair cedo

AINDA NÃO IMPLEMENTADO:
- S&P500 correlation filter (precisa segundo data feed)
"""

import backtrader as bt
from .base_strategy import BaseStrategy
import pandas as pd


class BTCWinningV2(BaseStrategy):
    """
    Estratégia V2 com melhorias rápidas:
    - ATR-based dynamic stops
    - S&P500 correlation
    - Trend strength detection
    """
    
    params = (
        # ==========================================
        # PARÂMETROS OTIMIZADOS (Trial #49 - Optuna)
        # ==========================================
        ('rsi_period', 17),
        ('rsi_exit_threshold', 24),
        ('rsi_entry_threshold', 38),
        
        ('macd_fast', 12),
        ('macd_slow', 29),
        ('macd_signal', 6),
        ('macd_exit_threshold', -71.87),
        ('macd_entry_threshold', -8.97),
        
        ('volume_period', 10),
        ('volume_panic_multiplier', 2.70),
        ('volume_entry_max', 1.36),
        
        ('bb_period', 24),
        ('bb_std', 1.93),
        ('bb_exit_lower_mult', 0.78),
        ('bb_entry_position', 0.53),
        
        ('momentum_period', 13),
        ('momentum_exit_threshold', -0.075),
        ('momentum_entry_threshold', 0.001),
        
        ('min_exit_signals', 4),
        ('min_entry_signals', 2),
        
        ('position_size', 0.87),
        ('hold_period_after_exit', 3),
        
        # ==========================================
        # PARÂMETROS V2 OTIMIZADOS
        # ==========================================
        
        # ATR Dynamic Stops
        ('atr_period', 17),
        ('atr_stop_multiplier', 2.85),
        ('atr_trailing_multiplier', 3.24),
        ('trailing_activation_pct', 0.20),
        ('use_dynamic_stops', True),
        
        # S&P500 Correlation Filter (PLACEHOLDER - não implementado)
        ('use_correlation_filter', False),
        ('correlation_period', 20),
        ('min_correlation', 0.3),
        
        # Trend Strength (Higher Highs/Lows)
        ('use_trend_strength', True),
        ('trend_lookback', 10),
        ('min_higher_highs', 2),
        ('min_higher_lows', 2),
        
        # Bull Run Protection (não sair cedo em rallies fortes)
        ('use_bull_protection', True),
        ('bull_run_threshold', 0.53),
        ('bull_run_period', 34),
        ('bull_exit_signals_add', 1),
    )
    
    def __init__(self):
        """Inicializar indicadores"""
        super().__init__()
        
        # Indicadores base
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        self.volume_sma = bt.indicators.SimpleMovingAverage(
            self.data.volume,
            period=self.params.volume_period
        )
        
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_std
        )
        
        self.momentum = bt.indicators.Momentum(
            self.data.close,
            period=self.params.momentum_period
        )
        
        # ==========================================
        # NOVOS INDICADORES V2
        # ==========================================
        
        # ATR para stops dinâmicos
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # Tracking de stops dinâmicos
        self.entry_price = None
        self.hard_stop = None  # Stop inicial (não muda)
        self.trailing_stop = None  # Trailing ativado após lucro
        
        # Estado
        self.days_since_exit = 0
        self.days_in_position = 0
        
    def next(self):
        """Lógica principal"""
        
        # ==========================================
        # GESTÃO DE POSIÇÃO
        # ==========================================
        
        if self.position:
            self.days_in_position += 1
            
            # Update dynamic stops
            if self.params.use_dynamic_stops:
                self._update_dynamic_stops()
                
                # Usar o maior entre hard stop e trailing stop
                effective_stop = self.hard_stop
                if self.trailing_stop is not None:
                    effective_stop = max(self.hard_stop, self.trailing_stop)
                
                # Check stop
                if self.data.close[0] <= effective_stop:
                    stop_type = 'TRAILING' if self.trailing_stop and effective_stop == self.trailing_stop else 'HARD'
                    profit_pct = ((self.data.close[0] - self.entry_price) / self.entry_price) * 100
                    self.log(f'{stop_type} STOP hit at {self.data.close[0]:.2f} (stop={effective_stop:.2f}, P&L={profit_pct:+.1f}%)')
                    self.close()
                    self._reset_position_state()
                    return
            
            # Avaliar sinais de EXIT
            exit_signals = self._count_exit_signals()
            
            # Bull run protection: Adiciona +2 sinais necessários
            min_exit = self.params.min_exit_signals
            if self.params.use_bull_protection and self._is_bull_run():
                min_exit = self.params.min_exit_signals + self.params.bull_exit_signals_add
                self.log(f'BULL RUN detected - need {min_exit} exit signals (have {exit_signals})')
            
            if exit_signals >= min_exit:
                profit_pct = ((self.data.close[0] - self.entry_price) / self.entry_price) * 100
                self.log(f'EXIT: {exit_signals} signals detected (needed {min_exit}), P&L={profit_pct:+.1f}%')
                self.close()
                self._reset_position_state()
                return
        
        # ==========================================
        # ENTRADA
        # ==========================================
        else:
            self.days_since_exit += 1
            
            # Respeitar período de espera
            if self.days_since_exit < self.params.hold_period_after_exit:
                return
            
            # Trend strength filter
            if self.params.use_trend_strength:
                if not self._has_trend_strength():
                    # Bloqueado: trend fraco
                    return
            
            # S&P500 correlation filter (placeholder)
            if self.params.use_correlation_filter:
                self.log('WARNING: correlation filter enabled but not implemented')
                # Não bloqueia entrada por enquanto
                pass
            
            # Contar sinais de entrada
            entry_signals = self._count_entry_signals()
            
            if entry_signals >= self.params.min_entry_signals:
                size = self.calculate_position_size()
                self.log(f'ENTRY: {entry_signals} signals detected')
                self.buy(size=size)
                
                # Initialize stops
                self.entry_price = self.data.close[0]
                if self.params.use_dynamic_stops:
                    atr_value = self.atr[0]
                    self.hard_stop = self.entry_price - (atr_value * self.params.atr_stop_multiplier)
                    self.trailing_stop = None
                    self.log(f'Entry at {self.entry_price:.2f}, Hard Stop at {self.hard_stop:.2f} (ATR={atr_value:.2f})')
    
    def _update_dynamic_stops(self):
        """Atualizar trailing stop baseado em ATR (hard stop nunca muda)"""
        if not self.entry_price:
            return
        
        current_price = self.data.close[0]
        atr_value = self.atr[0]
        
        # Calcular lucro atual
        profit_pct = (current_price - self.entry_price) / self.entry_price
        
        # Ativar trailing após threshold de lucro
        if profit_pct >= self.params.trailing_activation_pct:
            new_trailing = current_price - (atr_value * self.params.atr_trailing_multiplier)
            
            # Trailing só sobe, nunca desce
            if self.trailing_stop is None:
                self.trailing_stop = new_trailing
                self.log(f'Trailing ACTIVATED at {self.trailing_stop:.2f} (profit={profit_pct*100:.1f}%)')
            elif new_trailing > self.trailing_stop:
                self.trailing_stop = new_trailing
                # self.log(f'Trailing updated: {self.trailing_stop:.2f}')
    
    def _reset_position_state(self):
        """Resetar todo o estado da posição de forma limpa"""
        self.entry_price = None
        self.hard_stop = None
        self.trailing_stop = None
        self.days_since_exit = 0
        self.days_in_position = 0
    
    def _is_bull_run(self):
        """Detectar se estamos em bull run forte"""
        if len(self.data) < self.params.bull_run_period:
            return False
        
        price_now = self.data.close[0]
        price_then = self.data.close[-self.params.bull_run_period]
        
        gain = (price_now - price_then) / price_then
        
        return gain >= self.params.bull_run_threshold
    
    def _has_trend_strength(self):
        """Verificar se há força no trend (Higher Highs/Lows)"""
        if len(self.data) < self.params.trend_lookback * 2:
            return True  # Dados insuficientes, liberar
        
        lookback = self.params.trend_lookback
        
        # Contar Higher Highs
        higher_highs = 0
        for i in range(1, lookback):
            if self.data.high[-i] > self.data.high[-(i+lookback)]:
                higher_highs += 1
        
        # Contar Higher Lows
        higher_lows = 0
        for i in range(1, lookback):
            if self.data.low[-i] > self.data.low[-(i+lookback)]:
                higher_lows += 1
        
        has_strength = (
            higher_highs >= self.params.min_higher_highs and
            higher_lows >= self.params.min_higher_lows
        )
        
        if not has_strength:
            self.log(f'ENTRY BLOCKED - Trend weak: HH={higher_highs}/{self.params.min_higher_highs}, HL={higher_lows}/{self.params.min_higher_lows}')
        
        return has_strength
    

    
    def _count_exit_signals(self):
        """Contar sinais de EXIT"""
        signals = 0
        
        # 1. RSI extremo
        if self.rsi[0] < self.params.rsi_exit_threshold:
            signals += 1
        
        # 2. MACD muito negativo
        if self.macd.macd[0] < self.params.macd_exit_threshold:
            signals += 1
        
        # 3. Volume de pânico
        volume_ratio = self.data.volume[0] / self.volume_sma[0] if self.volume_sma[0] > 0 else 1.0
        if volume_ratio > self.params.volume_panic_multiplier:
            signals += 1
        
        # 4. Preço abaixo da banda inferior
        bb_distance = (self.data.close[0] - self.bb.lines.bot[0]) / self.bb.lines.bot[0]
        if bb_distance < -self.params.bb_exit_lower_mult:
            signals += 1
        
        # 5. Momentum negativo forte
        if len(self.data) > self.params.momentum_period:
            momentum_pct = (self.momentum[0] / self.data.close[-self.params.momentum_period]) if self.data.close[-self.params.momentum_period] > 0 else 0
            if momentum_pct < self.params.momentum_exit_threshold:
                signals += 1
        
        return signals
    
    def _count_entry_signals(self):
        """Contar sinais de ENTRY"""
        signals = 0
        
        # 1. RSI saindo do oversold
        if self.rsi[0] > self.params.rsi_entry_threshold:
            signals += 1
        
        # 2. MACD positivo ou recuperando
        if self.macd.macd[0] > self.params.macd_entry_threshold:
            signals += 1
        
        # 3. Volume normalizado
        volume_ratio = self.data.volume[0] / self.volume_sma[0] if self.volume_sma[0] > 0 else 1.0
        if volume_ratio < self.params.volume_entry_max:
            signals += 1
        
        # 4. Preço dentro das Bollinger Bands
        bb_range = self.bb.lines.top[0] - self.bb.lines.bot[0]
        bb_position = (self.data.close[0] - self.bb.lines.bot[0]) / bb_range if bb_range > 0 else 0.5
        if bb_position > self.params.bb_entry_position:
            signals += 1
        
        # 5. Momentum positivo
        if len(self.data) > self.params.momentum_period:
            momentum_pct = (self.momentum[0] / self.data.close[-self.params.momentum_period]) if self.data.close[-self.params.momentum_period] > 0 else 0
            if momentum_pct > self.params.momentum_entry_threshold:
                signals += 1
        
        return signals
    
    def calculate_position_size(self):
        """Calcular tamanho da posição"""
        cash = self.broker.getcash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
