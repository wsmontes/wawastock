#!/usr/bin/env python3
"""
NOVA ESTRATÉGIA: Trend Follower com Proteção

Insight da análise:
- BTC subiu +1142% em 5 anos
- Estratégia atual ficou fora 90% do tempo
- Trial 77: apenas 8 entradas em 2.153 dias

NOVA ABORDAGEM:
1. FICAR DENTRO durante tendências de alta
2. SAIR APENAS em reversões confirmadas
3. Re-entrar rapidamente após correções
4. Usar múltiplos timeframes para contexto
"""

import backtrader as bt
import numpy as np


class BTCTrendFollowerStrategy(bt.Strategy):
    """
    Estratégia que maximiza exposição em bull markets.
    
    Filosofia: "The trend is your friend"
    - Entra agressivamente em pullbacks durante uptrends
    - Fica posicionado enquanto tendência principal está intacta
    - Sai apenas em reversões confirmadas
    """
    
    params = (
        # Detecção de tendência primária
        ('sma_fast', 20),
        ('sma_medium', 50),
        ('sma_slow', 200),
        
        # Entrada em pullbacks
        ('rsi_period', 14),
        ('rsi_pullback', 40),  # Compra em pullbacks (não oversold extremo)
        ('rsi_exit', 80),      # Sai em sobrecompra extrema
        
        # Confirmação de momentum
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # Volume
        ('volume_sma', 20),
        ('volume_threshold', 1.2),
        
        # Gestão de risco
        ('position_size', 0.98),      # Quase todo capital
        ('stop_loss_pct', 15.0),      # Stop amplo para não ser stopado em correções normais
        ('trailing_start_pct', 30.0), # Ativa trailing após 30% de lucro
        ('trailing_distance_pct', 20.0), # Trailing 20% abaixo do pico
        
        # Condição de saída de tendência
        ('trend_break_fast_below_medium', True),  # Sai se SMA20 < SMA50
        ('death_cross_exit', True),               # Sai em death cross
    )
    
    def __init__(self):
        """Inicializa indicadores."""
        
        # === TENDÊNCIA ===
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.sma_fast)
        self.sma_medium = bt.indicators.SMA(self.data.close, period=self.params.sma_medium)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.sma_slow)
        
        # === MOMENTUM ===
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        # === VOLUME ===
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=self.params.volume_sma)
        
        # === CONTROLE ===
        self.order = None
        self.entry_price = None
        self.stop_price = None
        self.highest_since_entry = None
        self.trade_count = 0
        
    def log(self, txt, dt=None):
        """Log de eventos."""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
        
    def is_bull_market(self):
        """Detecta se estamos em bull market."""
        # Golden cross: SMA50 > SMA200
        golden_cross = self.sma_medium[0] > self.sma_slow[0]
        
        # Preço acima de ambas as médias
        price_above_mas = self.data.close[0] > self.sma_medium[0]
        
        # SMA20 acima SMA50 (tendência de curto prazo alta)
        short_term_bullish = self.sma_fast[0] > self.sma_medium[0]
        
        return golden_cross and (price_above_mas or short_term_bullish)
    
    def should_enter(self):
        """Determina se deve entrar."""
        if len(self) < self.params.sma_slow:
            return False
        
        # 1. Bull market ativo
        if not self.is_bull_market():
            return False
        
        # 2. Pullback (RSI não muito baixo, queremos pegar correções em uptrend)
        rsi_pullback = 30 < self.rsi[0] < self.params.rsi_pullback
        
        # 3. MACD positivo (momentum geral positivo)
        macd_positive = self.macd.macd[0] > 0
        
        # 4. Preço voltou acima da SMA20 após pullback
        price_recovery = (
            self.data.close[0] > self.sma_fast[0] and
            self.data.close[-1] <= self.sma_fast[-1]
        )
        
        # COMPRA AGRESSIVA: qualquer uma dessas condições em bull market
        return rsi_pullback or price_recovery or (macd_positive and self.data.close[0] > self.sma_fast[0])
    
    def should_exit(self):
        """Determina se deve sair."""
        if not self.position:
            return False, None
        
        # 1. Death cross (reversão de tendência)
        if self.params.death_cross_exit:
            if self.sma_medium[0] < self.sma_slow[0] and self.sma_medium[-1] >= self.sma_slow[-1]:
                return True, 'DEATH_CROSS'
        
        # 2. SMA20 cruzou abaixo SMA50 (tendência de curto prazo virou)
        if self.params.trend_break_fast_below_medium:
            if self.sma_fast[0] < self.sma_medium[0] and self.sma_fast[-1] >= self.sma_medium[-1]:
                return True, 'TREND_BREAK'
        
        # 3. RSI extremamente sobrecomprado (>80) e virando
        if self.rsi[0] > self.params.rsi_exit and self.rsi[0] < self.rsi[-1]:
            return True, 'RSI_OVERBOUGHT'
        
        # 4. Stop loss
        if self.data.close[0] <= self.stop_price:
            return True, 'STOP_LOSS'
        
        # 5. Trailing stop (após lucro significativo)
        if self.entry_price:
            profit_pct = ((self.data.close[0] - self.entry_price) / self.entry_price) * 100
            
            if profit_pct >= self.params.trailing_start_pct:
                # Atualizar pico
                if self.highest_since_entry is None or self.data.close[0] > self.highest_since_entry:
                    self.highest_since_entry = self.data.close[0]
                
                # Trailing stop
                trailing_stop = self.highest_since_entry * (1 - self.params.trailing_distance_pct / 100)
                if self.data.close[0] <= trailing_stop:
                    return True, f'TRAILING_STOP (peak: ${self.highest_since_entry:.2f})'
        
        return False, None
    
    def next(self):
        """Lógica principal executada a cada barra."""
        
        # Aguardar indicadores
        if len(self) < self.params.sma_slow:
            return
        
        # Aguardar ordem pendente
        if self.order:
            return
        
        # Gerenciar posição existente
        if self.position:
            should_exit, reason = self.should_exit()
            if should_exit:
                self.order = self.close()
                self.log(f'EXIT SIGNAL: {reason} @ ${self.data.close[0]:.2f}')
                return
        
        # Verificar entrada
        if not self.position:
            if self.should_enter():
                size = (self.broker.getcash() * self.params.position_size) / self.data.close[0]
                self.order = self.buy(size=size)
                self.log(f'BUY SIGNAL @ ${self.data.close[0]:.2f} | Bull Market: {self.is_bull_market()} | RSI: {self.rsi[0]:.1f}')
    
    def notify_order(self, order):
        """Notificação de ordens."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.stop_price = self.entry_price * (1 - self.params.stop_loss_pct / 100)
                self.highest_since_entry = self.entry_price
                self.trade_count += 1
                
                self.log(f'BUY EXECUTED @ ${self.entry_price:.2f} | Stop: ${self.stop_price:.2f} | Trade #{self.trade_count}')
            
            elif order.issell():
                pnl = order.executed.pnl if hasattr(order.executed, 'pnl') else 0
                pnl_pct = ((order.executed.price - self.entry_price) / self.entry_price * 100) if self.entry_price else 0
                
                self.log(f'SELL EXECUTED @ ${order.executed.price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)')
                
                # Reset
                self.entry_price = None
                self.stop_price = None
                self.highest_since_entry = None
        
        self.order = None
