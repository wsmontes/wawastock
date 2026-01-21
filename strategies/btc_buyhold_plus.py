"""
BTC Buy & Hold Plus Strategy - Beat Buy & Hold

FILOSOFIA:
- Default: Buy & Hold (sempre posicionado)
- ÚNICA exceção: Sair em crashes iminentes
- Re-entrar rápido após crash

OBJETIVO: Superar buy & hold eliminando apenas os crashes grandes
Target: Ganhar > +1,233% (buy & hold 2020-2025)

Sinais:
1. ENTRADA: Compra inicial no start + re-entradas após crashes
2. SAÍDA: Apenas em sinais de crash forte (múltiplos indicadores)

Crash = RSI < 30 + MACD negativo cruzando + Volume alto + Queda >15% em 20d
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class BTCBuyHoldPlus(BaseStrategy):
    """
    Estratégia que supera Buy & Hold evitando apenas crashes grandes.
    
    Mantém posição permanente exceto quando detecta crash iminente.
    """
    
    params = (
        # Detecção de crash (ULTRA conservador = quase nunca sai)
        ('rsi_period', 14),
        ('rsi_crash', 20),  # RSI MUITO baixo = crash extremo
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('volume_period', 20),
        ('volume_crash_multiplier', 3.0),  # Volume 3x = pânico extremo
        ('drawdown_threshold', -25.0),  # Queda de 25% em 20d = crash SEVERO
        ('lookback_period', 20),
        
        # Re-entrada após crash (mais rápida)
        ('rsi_recovery', 30),  # RSI voltando = fim do crash
        ('macd_recovery_threshold', 0),  # MACD positivo = recuperação
        
        # Position sizing
        ('position_size', 0.98),  # Quase 100% - buy & hold agressivo
    )
    
    def __init__(self):
        """Inicializar indicadores"""
        super().__init__()
        
        # Indicadores de crash
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )
        
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        # Volume médio
        self.volume_sma = bt.indicators.SimpleMovingAverage(
            self.data.volume,
            period=self.params.volume_period
        )
        
        # Drawdown recente (maior baixa em N dias)
        self.highest_high = bt.indicators.Highest(
            self.data.close,
            period=self.params.lookback_period
        )
        
        # Estado
        self.waiting_recovery = False
        
    def next(self):
        """Lógica principal: Buy & Hold com proteção de crash"""
        
        # Calcular drawdown recente
        current_dd = ((self.data.close[0] - self.highest_high[0]) / self.highest_high[0]) * 100
        
        # Volume atual vs média
        volume_ratio = self.data.volume[0] / self.volume_sma[0] if self.volume_sma[0] > 0 else 1.0
        
        # ============================================
        # DETECÇÃO DE CRASH (múltiplos sinais)
        # ============================================
        crash_signals = 0
        
        # Sinal 1: RSI muito baixo (oversold extremo)
        if self.rsi[0] < self.params.rsi_crash:
            crash_signals += 1
        
        # Sinal 2: MACD negativo e caindo
        if self.macd.macd[0] < 0 and self.macd.macd[0] < self.macd.macd[-1]:
            crash_signals += 1
        
        # Sinal 3: Volume de pânico
        if volume_ratio > self.params.volume_crash_multiplier:
            crash_signals += 1
        
        # Sinal 4: Drawdown significativo
        if current_dd < self.params.drawdown_threshold:
            crash_signals += 1
        
        # ============================================
        # LÓGICA DE SAÍDA (crash detectado)
        # ============================================
        if self.position and crash_signals >= 3:
            self.log(f'CRASH DETECTADO! Signals={crash_signals}, RSI={self.rsi[0]:.1f}, DD={current_dd:.1f}%, Vol={volume_ratio:.2f}x')
            self.close()
            self.waiting_recovery = True
            return
        
        # ============================================
        # LÓGICA DE RE-ENTRADA (após crash)
        # ============================================
        if not self.position:
            # Se estamos esperando recuperação
            if self.waiting_recovery:
                recovery_signals = 0
                
                # Sinal 1: RSI saindo da oversold
                if self.rsi[0] > self.params.rsi_recovery:
                    recovery_signals += 1
                
                # Sinal 2: MACD voltando positivo
                if self.macd.macd[0] > self.params.macd_recovery_threshold:
                    recovery_signals += 1
                
                # Sinal 3: Drawdown reduzindo (preço subindo)
                if current_dd > self.params.drawdown_threshold:
                    recovery_signals += 1
                
                if recovery_signals >= 2:
                    size = self.calculate_position_size()
                    self.log(f'RECUPERAÇÃO! Recovery signals={recovery_signals}, RSI={self.rsi[0]:.1f}, DD={current_dd:.1f}%')
                    self.buy(size=size)
                    self.waiting_recovery = False
            else:
                # Entrada inicial: compra no começo se não temos posição
                size = self.calculate_position_size()
                self.log(f'ENTRADA INICIAL - Buy & Hold mode')
                self.buy(size=size)
    
    def calculate_position_size(self):
        """Calcular tamanho da posição"""
        cash = self.broker.getcash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
