"""
BTC Adaptive Hold Strategy - Otimizável pelo Optuna

FILOSOFIA:
- Base: Buy & Hold com proteção inteligente
- Múltiplas condições ajustáveis para detectar quando SAIR e quando ENTRAR
- Optuna vai descobrir os valores ótimos de TODAS as variáveis

VARIÁVEIS OTIMIZÁVEIS (20+):
1. Detecção de SAÍDA (exit signals):
   - RSI thresholds
   - MACD conditions
   - Volume panic levels
   - Drawdown thresholds
   - Momentum indicators
   - Bollinger Bands
   - ATR volatility
   
2. Detecção de RE-ENTRADA (entry signals):
   - RSI recovery levels
   - MACD crossovers
   - Price action (higher lows, etc)
   - Volume normalization
   
3. Confirmações múltiplas:
   - Quantos sinais necessários para sair (1-5)
   - Quantos sinais necessários para entrar (1-5)
   - Lookback periods variáveis
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class BTCAdaptiveHold(BaseStrategy):
    """
    Estratégia adaptativa de buy & hold com proteção otimizável.
    
    Todas as variáveis são ajustáveis pelo Optuna para encontrar
    a combinação ótima que supera buy & hold puro.
    """
    
    params = (
        # ==========================================
        # EXIT SIGNALS - Quando SAIR do mercado
        # ==========================================
        
        # RSI - Oversold extremo
        ('rsi_period', 14),
        ('rsi_exit_threshold', 25),  # < 25 = possível crash
        
        # MACD - Momentum negativo
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('macd_exit_threshold', -50),  # MACD muito negativo
        
        # Volume - Pânico
        ('volume_period', 20),
        ('volume_panic_multiplier', 2.5),  # Volume anormal
        
        # Drawdown - Queda acentuada
        ('lookback_dd', 20),
        ('drawdown_exit_threshold', -20.0),  # -20% em N dias
        
        # Bollinger Bands - Rompimento inferior
        ('bb_period', 20),
        ('bb_std', 2.0),
        ('bb_exit_lower_mult', 0.5),  # Quanto abaixo da banda inferior
        
        # ATR - Volatilidade extrema
        ('atr_period', 14),
        ('atr_exit_multiplier', 3.0),  # Volatilidade N vezes a média
        
        # Momentum - Queda sustentada
        ('momentum_period', 10),
        ('momentum_exit_threshold', -0.15),  # -15% momentum
        
        # EMA Death Cross - Média rápida cruza abaixo da lenta
        ('ema_fast', 20),
        ('ema_slow', 50),
        ('use_ema_cross_exit', True),
        
        # Confirmação de saída - Quantos sinais necessários
        ('min_exit_signals', 3),  # De 8 possíveis
        
        # ==========================================
        # ENTRY SIGNALS - Quando RE-ENTRAR
        # ==========================================
        
        # RSI - Recovery
        ('rsi_entry_threshold', 35),  # > 35 = saindo do oversold
        
        # MACD - Momentum positivo
        ('macd_entry_threshold', 0),  # MACD voltando positivo
        ('macd_entry_crossover', True),  # MACD cruzou signal
        
        # Volume - Normalização
        ('volume_entry_max', 1.5),  # Volume voltando ao normal
        
        # Drawdown - Recuperação
        ('lookback_recovery', 10),
        ('recovery_threshold', 0.05),  # +5% em N dias
        
        # Bollinger Bands - Volta para dentro
        ('bb_entry_position', 0.3),  # Posição dentro das bandas
        
        # ATR - Volatilidade normalizada
        ('atr_entry_multiplier', 1.5),  # Volatilidade baixa
        
        # Momentum - Positivo
        ('momentum_entry_threshold', 0.0),  # Momentum positivo
        
        # EMA Golden Cross - Média rápida cruza acima da lenta
        ('use_ema_cross_entry', True),
        
        # Higher lows - Preço fazendo fundos crescentes
        ('check_higher_lows', True),
        ('higher_lows_period', 5),
        
        # Confirmação de entrada - Quantos sinais necessários
        ('min_entry_signals', 2),  # De 9 possíveis
        
        # ==========================================
        # OUTROS
        # ==========================================
        ('position_size', 0.98),
        ('hold_period_after_exit', 3),  # Dias para esperar antes de re-entrar
    )
    
    def __init__(self):
        """Inicializar todos os indicadores"""
        super().__init__()
        
        # RSI
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )
        
        # MACD
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        # Volume
        self.volume_sma = bt.indicators.SimpleMovingAverage(
            self.data.volume,
            period=self.params.volume_period
        )
        
        # Drawdown tracking
        self.highest_high = bt.indicators.Highest(
            self.data.close,
            period=self.params.lookback_dd
        )
        
        # Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_std
        )
        
        # ATR
        self.atr = bt.indicators.ATR(
            self.data,
            period=self.params.atr_period
        )
        self.atr_sma = bt.indicators.SimpleMovingAverage(
            self.atr,
            period=self.params.atr_period
        )
        
        # Momentum
        self.momentum = bt.indicators.Momentum(
            self.data.close,
            period=self.params.momentum_period
        )
        
        # EMAs
        self.ema_fast = bt.indicators.EMA(
            self.data.close,
            period=self.params.ema_fast
        )
        self.ema_slow = bt.indicators.EMA(
            self.data.close,
            period=self.params.ema_slow
        )
        
        # Estado
        self.days_since_exit = 0
        
    def next(self):
        """Lógica principal"""
        
        # Se temos posição, avaliar SAÍDA
        if self.position:
            exit_signals = self._count_exit_signals()
            
            if exit_signals >= self.params.min_exit_signals:
                self.log(f'EXIT: {exit_signals} signals detected')
                self.close()
                self.days_since_exit = 0
                return
        
        # Se não temos posição, avaliar ENTRADA
        else:
            self.days_since_exit += 1
            
            # Respeitar período de espera
            if self.days_since_exit < self.params.hold_period_after_exit:
                return
            
            entry_signals = self._count_entry_signals()
            
            if entry_signals >= self.params.min_entry_signals:
                size = self.calculate_position_size()
                self.log(f'ENTRY: {entry_signals} signals detected')
                self.buy(size=size)
    
    def _count_exit_signals(self):
        """Contar quantos sinais de EXIT estão ativos"""
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
        
        # 4. Drawdown grande
        current_dd = ((self.data.close[0] - self.highest_high[0]) / self.highest_high[0]) * 100
        if current_dd < self.params.drawdown_exit_threshold:
            signals += 1
        
        # 5. Preço muito abaixo da banda inferior
        bb_distance = (self.data.close[0] - self.bb.lines.bot[0]) / self.bb.lines.bot[0]
        if bb_distance < -self.params.bb_exit_lower_mult:
            signals += 1
        
        # 6. Volatilidade extrema
        if self.atr[0] > self.atr_sma[0] * self.params.atr_exit_multiplier:
            signals += 1
        
        # 7. Momentum negativo forte
        momentum_pct = (self.momentum[0] / self.data.close[-self.params.momentum_period]) if self.data.close[-self.params.momentum_period] > 0 else 0
        if momentum_pct < self.params.momentum_exit_threshold:
            signals += 1
        
        # 8. Death cross (EMA rápida < EMA lenta)
        if self.params.use_ema_cross_exit:
            if self.ema_fast[0] < self.ema_slow[0] and self.ema_fast[-1] >= self.ema_slow[-1]:
                signals += 1
        
        return signals
    
    def _count_entry_signals(self):
        """Contar quantos sinais de ENTRY estão ativos"""
        signals = 0
        
        # 1. RSI saindo do oversold
        if self.rsi[0] > self.params.rsi_entry_threshold:
            signals += 1
        
        # 2. MACD positivo
        if self.macd.macd[0] > self.params.macd_entry_threshold:
            signals += 1
        
        # 3. MACD crossover
        if self.params.macd_entry_crossover:
            if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:
                signals += 1
        
        # 4. Volume normalizado
        volume_ratio = self.data.volume[0] / self.volume_sma[0] if self.volume_sma[0] > 0 else 1.0
        if volume_ratio < self.params.volume_entry_max:
            signals += 1
        
        # 5. Recuperação de preço
        if len(self.data) > self.params.lookback_recovery:
            recovery = ((self.data.close[0] - self.data.close[-self.params.lookback_recovery]) / 
                       self.data.close[-self.params.lookback_recovery])
            if recovery > self.params.recovery_threshold:
                signals += 1
        
        # 6. Preço dentro das Bollinger Bands
        bb_range = self.bb.lines.top[0] - self.bb.lines.bot[0]
        bb_position = (self.data.close[0] - self.bb.lines.bot[0]) / bb_range if bb_range > 0 else 0.5
        if bb_position > self.params.bb_entry_position:
            signals += 1
        
        # 7. Volatilidade baixa
        if self.atr[0] < self.atr_sma[0] * self.params.atr_entry_multiplier:
            signals += 1
        
        # 8. Momentum positivo
        if len(self.data) > self.params.momentum_period:
            momentum_pct = (self.momentum[0] / self.data.close[-self.params.momentum_period]) if self.data.close[-self.params.momentum_period] > 0 else 0
            if momentum_pct > self.params.momentum_entry_threshold:
                signals += 1
        
        # 9. Golden cross (EMA rápida > EMA lenta)
        if self.params.use_ema_cross_entry:
            if self.ema_fast[0] > self.ema_slow[0] and self.ema_fast[-1] <= self.ema_slow[-1]:
                signals += 1
        
        # 10. Higher lows (fundos crescentes)
        if self.params.check_higher_lows and len(self.data) > self.params.higher_lows_period * 2:
            period = self.params.higher_lows_period
            low1 = min(self.data.close.get(ago=-i) for i in range(period, period * 2))
            low2 = min(self.data.close.get(ago=-i) for i in range(0, period))
            if low2 > low1:
                signals += 1
        
        return signals
    
    def calculate_position_size(self):
        """Calcular tamanho da posição"""
        cash = self.broker.getcash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
