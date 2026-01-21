"""
Meta Strategy V2 - CORRIGIDA

FILOSOFIA: Trial 77 É A ESTRATÉGIA BASE. Especialistas APENAS em regimes extremos.

REGRA: 95% do tempo usar Trial 77. Especialistas SÓ em casos óbvios.
"""

import backtrader as bt
import pandas as pd
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from engines.regime_detector import RegimeDetector


class MetaStrategyV2(BTCAdaptiveStrategy):
    """
    MetaStrategy que HERDA de BTCAdaptiveStrategy (Trial 77).
    
    Adiciona apenas:
    1. RegimeDetector
    2. Overrides para regimes extremos (STRONG_BULL_RUN, CRASH, RECOVERY)
    3. TODO o resto é Trial 77 puro
    
    REGRA: Se não tem certeza absoluta, usar Trial 77.
    """
    
    params = (
        # Specialist overrides (apenas quando ativados)
        ('bull_run_position_size', 0.98),
        ('bull_run_trailing', 20.0),
        ('recovery_position_size', 0.90),
        ('recovery_stop_loss', 10.0),
        
        # Regime thresholds (altos para ativar apenas em extremos)
        ('strong_bull_ret20', 20.0),  # Maior que Trial 77
        ('strong_bull_ret60', 40.0),  # Maior que Trial 77
        ('crash_threshold', -20.0),   # Mais extremo
        ('recovery_ret20', 15.0),     # Maior que Trial 77
    )
    
    def __init__(self):
        """Inicializar Trial 77 + regime detector."""
        super().__init__()  # Inicializa TODOS os indicadores do Trial 77
        
        # Adicionar apenas regime detector
        self.regime_detector = RegimeDetector(
            window=60,
            strong_bull_ret20=self.params.strong_bull_ret20,
            strong_bull_ret60=self.params.strong_bull_ret60,
            crash_threshold=self.params.crash_threshold,
            recovery_ret20=self.params.recovery_ret20
        )
        
        # SMAs para regime detection
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma50 = bt.indicators.SMA(self.data.close, period=50)
        self.sma200 = bt.indicators.SMA(self.data.close, period=200)
        
        # State
        self.current_regime = 'NORMAL'
        self.using_specialist = False
    
    def detect_current_regime(self):
        """Detectar apenas regimes EXTREMOS."""
        if len(self.data) < 60:
            return 'NORMAL'
        
        # Criar DataFrame temporário
        temp_data = []
        for i in range(min(len(self.data), 60)):
            idx = -i
            temp_data.append({
                'close': self.data.close[idx],
                'sma20': self.sma20[idx],
                'sma50': self.sma50[idx],
                'sma200': self.sma200[idx]
            })
        
        temp_df = pd.DataFrame(temp_data[::-1])
        temp_df.index = range(len(temp_df))
        
        regime = self.regime_detector.detect(temp_df)
        
        # FILTRAR: apenas regimes EXTREMOS ativam especialistas
        if regime in ['STRONG_BULL_RUN', 'CRASH', 'RECOVERY']:
            return regime
        else:
            return 'NORMAL'  # Usar Trial 77 em todos os outros casos
    
    def next(self):
        """
        Lógica: 
        1. Detectar regime
        2. Se regime extremo E condições específicas → usar especialista
        3. Caso contrário → Trial 77 (super().next())
        """
        
        # Detectar regime
        self.current_regime = self.detect_current_regime()
        
        # === REGIME EXTREMO: CRASH ===
        # Sair imediatamente para preservar capital
        if self.current_regime == 'CRASH' and self.position:
            self.close()
            self.log(f"🛑 CRASH DETECTED - Saindo para preservar capital")
            self.using_specialist = True
            return
        
        # === REGIME EXTREMO: STRONG_BULL_RUN ===
        # Se já em posição, usar trailing stop mais amplo
        if self.current_regime == 'STRONG_BULL_RUN' and self.position:
            current_price = self.data.close[0]
            if not self.highest_since_entry:
                self.highest_since_entry = current_price
            elif current_price > self.highest_since_entry:
                self.highest_since_entry = current_price
            
            # Trailing stop amplo (20%)
            trailing_pct = self.params.bull_run_trailing
            trailing_stop = self.highest_since_entry * (1 - trailing_pct / 100)
            
            if current_price < trailing_stop:
                self.close()
                profit = ((current_price / self.entry_price) - 1) * 100
                self.log(f"🎯 BULL RUN - Trailing stop {trailing_pct}% hit: +{profit:.2f}%")
                self.using_specialist = True
                return
        
        # === REGIME EXTREMO: RECOVERY ===
        # Entrar mais agressivo se não está em posição
        if self.current_regime == 'RECOVERY' and not self.position:
            # Verificar sinais básicos do Trial 77 mas com threshold mais baixo
            buy_signals = 0
            
            if self.rsi[0] < self.params.rsi_oversold + 10:  # Mais flexível
                buy_signals += 1
            
            if self.data.close[0] < self.bb.lines.mid[0]:  # Abaixo da média BB
                buy_signals += 1
            
            if buy_signals >= 1:  # Apenas 1 sinal suficiente em recovery
                size = self._calculate_position_size(self.data.close[0]) * (self.params.recovery_position_size / self.params.position_size)
                self.buy(size=size)
                self.entry_price = self.data.close[0]
                self.highest_since_entry = self.data.close[0]
                self.log(f"🚀 RECOVERY - Entrada agressiva @ ${self.data.close[0]:,.2f}")
                self.using_specialist = True
                return
        
        # === REGIME NORMAL: USAR TRIAL 77 ===
        self.using_specialist = False
        super().next()  # Delegar para BTCAdaptiveStrategy (Trial 77)
