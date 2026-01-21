#!/usr/bin/env python3
"""
BITCOIN SUPREME STRATEGY - Estratégia Adaptativa Multi-Regime

Baseada na análise profunda do período 2020-2025:
- 51.7% do tempo SIDEWAYS - usar range trading
- 24.1% STRONG_BULL - usar trend following agressivo  
- 9.8% BULL - usar trend following moderado
- 9.8% STRONG_BEAR - sair e preservar capital
- 4.7% BEAR - trading defensivo

Indicadores mais preditivos (correlação 30d):
1. RSI (0.1242) - melhor indicador
2. Momentum 20d (0.1149)
3. BB Position (0.1005)
4. MACD (0.0840)

730 dias de oportunidades >10% identificados
406 dias de risco >-10% identificados
"""

import backtrader as bt
import numpy as np


class BTCSupremeStrategy(bt.Strategy):
    """
    Estratégia suprema para Bitcoin com adaptação a regimes de mercado.
    
    Combina:
    - Detecção de regime de mercado
    - Múltiplos sinais de entrada otimizados por regime
    - Gestão de risco dinâmica
    - Maximização de oportunidades
    """
    
    params = (
        # Detecção de regime
        ('regime_fast_period', 50),
        ('regime_slow_period', 200),
        ('regime_roc_period', 20),
        
        # RSI - indicador mais forte
        ('rsi_period', 14),
        ('rsi_oversold_aggressive', 25),   # Para SIDEWAYS
        ('rsi_oversold_conservative', 35), # Para BULL
        ('rsi_overbought', 75),
        
        # Bollinger Bands - segundo melhor
        ('bb_period', 20),
        ('bb_dev', 2.0),
        
        # MACD
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # EMAs para tendência
        ('ema_fast', 20),
        ('ema_slow', 50),
        
        # Momentum
        ('momentum_period', 20),
        
        # Volume
        ('volume_period', 20),
        ('volume_surge_threshold', 1.5),
        
        # ATR para stops
        ('atr_period', 14),
        
        # Gestão de risco por regime
        ('position_size_bull', 0.95),      # Agressivo em bull
        ('position_size_sideways', 0.80),   # Moderado em sideways
        ('position_size_bear', 0.50),       # Conservador em bear
        
        # Stops por regime
        ('stop_loss_bull', 5.0),            # 5% em bull
        ('stop_loss_sideways', 3.0),        # 3% em sideways
        ('stop_loss_bear', 2.0),            # 2% em bear
        
        # Take profit
        ('take_profit_multiplier', 2.5),    # 2.5x o stop
        
        # Trailing stop
        ('trailing_stop_activation', 5.0),   # Ativa após 5% de lucro
        ('trailing_stop_distance', 3.0),     # 3% abaixo do pico
    )
    
    def __init__(self):
        """Inicializa indicadores e variáveis."""
        
        # === DETECÇÃO DE REGIME ===
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.regime_fast_period)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.regime_slow_period)
        self.roc = bt.indicators.ROC(self.data.close, period=self.params.regime_roc_period)
        
        # === INDICADORES PRINCIPAIS ===
        # RSI - mais preditivo
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        
        # Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_dev
        )
        
        # MACD
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        # EMAs
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow)
        
        # Momentum
        self.momentum = bt.indicators.Momentum(self.data.close, period=self.params.momentum_period)
        
        # Volume
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=self.params.volume_period)
        
        # ATR para stops
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # === VARIÁVEIS DE CONTROLE ===
        self.order = None
        self.entry_price = None
        self.stop_price = None
        self.take_profit_price = None
        self.highest_since_entry = None
        self.current_regime = None
        
    def log(self, txt, dt=None):
        """Log de eventos."""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
        
    def get_regime(self):
        """Detecta regime de mercado atual."""
        if len(self) < self.params.regime_slow_period:
            return 'SIDEWAYS'
        
        trend = self.sma_fast[0] > self.sma_slow[0]
        roc_val = self.roc[0]
        
        if trend:
            if roc_val > 10:
                return 'STRONG_BULL'
            elif roc_val > 2:
                return 'BULL'
            else:
                return 'SIDEWAYS'
        else:
            if roc_val < -10:
                return 'STRONG_BEAR'
            elif roc_val < -2:
                return 'BEAR'
            else:
                return 'SIDEWAYS'
    
    def get_buy_signals(self, regime):
        """Calcula sinais de compra baseado no regime."""
        signals = []
        
        # Signal 1: RSI oversold (ajustado por regime)
        if regime in ['SIDEWAYS', 'BULL']:
            threshold = self.params.rsi_oversold_aggressive if regime == 'SIDEWAYS' else self.params.rsi_oversold_conservative
            if self.rsi[0] < threshold and self.rsi[0] > self.rsi[-1]:
                signals.append('RSI_OVERSOLD')
        
        # Signal 2: Bollinger Band bounce
        if self.data.close[0] <= self.bb.lines.bot[0] and self.data.close[0] > self.data.close[-1]:
            signals.append('BB_BOUNCE')
        
        # Signal 3: MACD bullish cross
        if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:
            signals.append('MACD_CROSS')
        
        # Signal 4: EMA alignment (trend following)
        if regime in ['BULL', 'STRONG_BULL']:
            if self.ema_fast[0] > self.ema_slow[0] and self.data.close[0] > self.ema_fast[0]:
                signals.append('EMA_ALIGNMENT')
        
        # Signal 5: Momentum positivo
        if self.momentum[0] > 0 and self.momentum[0] > self.momentum[-1]:
            signals.append('MOMENTUM_UP')
        
        # Signal 6: Volume surge
        if self.data.volume[0] > self.volume_sma[0] * self.params.volume_surge_threshold:
            signals.append('VOLUME_SURGE')
        
        return signals
    
    def get_sell_signals(self, regime):
        """Calcula sinais de venda baseado no regime."""
        signals = []
        
        # Signal 1: RSI overbought
        if self.rsi[0] > self.params.rsi_overbought:
            signals.append('RSI_OVERBOUGHT')
        
        # Signal 2: BB upper band
        if self.data.close[0] >= self.bb.lines.top[0]:
            signals.append('BB_TOP')
        
        # Signal 3: MACD bearish cross
        if self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] >= self.macd.signal[-1]:
            signals.append('MACD_CROSS_DOWN')
        
        # Signal 4: EMA breakdown
        if self.ema_fast[0] < self.ema_slow[0]:
            signals.append('EMA_BREAKDOWN')
        
        # Signal 5: Momentum negativo
        if self.momentum[0] < 0:
            signals.append('MOMENTUM_DOWN')
        
        # Signal 6: Strong bear regime (sair imediatamente)
        if regime == 'STRONG_BEAR':
            signals.append('REGIME_BEAR')
        
        return signals
    
    def next(self):
        """Lógica principal executada a cada barra."""
        
        # Pular se indicadores não estiverem prontos
        if len(self) < self.params.regime_slow_period:
            return
        
        # Detectar regime atual
        self.current_regime = self.get_regime()
        
        # Gerenciar posição existente
        if self.position:
            self.manage_position()
        
        # Aguardar ordem pendente
        if self.order:
            return
        
        # Lógica de entrada
        if not self.position:
            self.check_entry()
    
    def check_entry(self):
        """Verifica condições de entrada."""
        regime = self.current_regime
        
        # Não entrar em mercado bear
        if regime in ['STRONG_BEAR', 'BEAR']:
            return
        
        buy_signals = self.get_buy_signals(regime)
        
        # Número mínimo de sinais baseado no regime
        min_signals = 3 if regime == 'SIDEWAYS' else 2
        
        if len(buy_signals) >= min_signals:
            # Calcular tamanho da posição baseado no regime
            if regime == 'STRONG_BULL':
                position_size = self.params.position_size_bull
            elif regime in ['BULL', 'SIDEWAYS']:
                position_size = self.params.position_size_sideways
            else:
                position_size = self.params.position_size_bear
            
            size = (self.broker.getcash() * position_size) / self.data.close[0]
            self.order = self.buy(size=size)
            self.log(f'BUY SIGNAL ({regime}) - Signals: {buy_signals}')
    
    def manage_position(self):
        """Gerencia posição aberta com stops dinâmicos."""
        regime = self.current_regime
        current_price = self.data.close[0]
        
        # Atualizar preço mais alto desde entrada
        if self.highest_since_entry is None or current_price > self.highest_since_entry:
            self.highest_since_entry = current_price
        
        # Stop loss
        if current_price <= self.stop_price:
            self.order = self.close()
            self.log(f'STOP LOSS at {current_price:.2f}')
            return
        
        # Take profit
        if current_price >= self.take_profit_price:
            self.order = self.close()
            self.log(f'TAKE PROFIT at {current_price:.2f}')
            return
        
        # Trailing stop
        profit_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        if profit_pct >= self.params.trailing_stop_activation:
            trailing_stop = self.highest_since_entry * (1 - self.params.trailing_stop_distance / 100)
            if current_price <= trailing_stop:
                self.order = self.close()
                self.log(f'TRAILING STOP at {current_price:.2f} (Peak: {self.highest_since_entry:.2f})')
                return
        
        # Sinais de saída
        sell_signals = self.get_sell_signals(regime)
        min_sell_signals = 2 if regime != 'STRONG_BEAR' else 1
        
        if len(sell_signals) >= min_sell_signals:
            self.order = self.close()
            self.log(f'SELL SIGNAL ({regime}) - Signals: {sell_signals}')
    
    def notify_order(self, order):
        """Notificação de ordens."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                
                # Definir stops baseado no regime
                regime = self.current_regime
                if regime == 'STRONG_BULL':
                    stop_pct = self.params.stop_loss_bull
                elif regime in ['BULL', 'SIDEWAYS']:
                    stop_pct = self.params.stop_loss_sideways
                else:
                    stop_pct = self.params.stop_loss_bear
                
                self.stop_price = self.entry_price * (1 - stop_pct / 100)
                self.take_profit_price = self.entry_price * (1 + stop_pct * self.params.take_profit_multiplier / 100)
                self.highest_since_entry = self.entry_price
                
                self.log(f'BUY EXECUTED at {self.entry_price:.2f} | Stop: {self.stop_price:.2f} | Target: {self.take_profit_price:.2f}')
            
            elif order.issell():
                pnl = order.executed.pnl if hasattr(order.executed, 'pnl') else 0
                self.log(f'SELL EXECUTED at {order.executed.price:.2f} | P&L: ${pnl:.2f}')
                
                # Reset
                self.entry_price = None
                self.stop_price = None
                self.take_profit_price = None
                self.highest_since_entry = None
        
        self.order = None
