"""
Neural Trading Strategy - Estratégia que usa previsões de redes neurais.

Integra com o NeuralTradingEngine para gerar sinais de compra/venda
baseados em modelos de deep learning.
"""

import backtrader as bt
import numpy as np
from typing import Dict, Optional

from strategies.base_strategy import BaseStrategy


class NeuralTradingStrategy(BaseStrategy):
    """
    Estratégia baseada em previsões de rede neural.
    
    Recebe um dicionário de sinais pré-computados (date -> signal)
    e executa trades baseado nesses sinais.
    
    Parâmetros:
    - signals: Dict com sinais {date: 1 (buy) ou 0 (sell/hold)}
    - buy_threshold: Probabilidade mínima para compra
    - sell_threshold: Probabilidade para venda
    - position_size: Fração do capital por trade
    - stop_loss_pct: Stop loss em percentual
    - trailing_stop_pct: Trailing stop em percentual
    - max_holding_days: Máximo de dias em posição
    """
    
    params = (
        ('signals', None),          # Dict: date -> signal (0/1)
        ('probabilities', None),    # Dict: date -> probability [0,1]
        ('buy_threshold', 0.6),     # Probabilidade mínima para compra
        ('sell_threshold', 0.4),    # Probabilidade para venda
        ('position_size', 0.95),    # 95% do capital
        ('stop_loss_pct', 5.0),     # Stop loss 5%
        ('trailing_stop_pct', 0.0), # Trailing stop (0 = desabilitado)
        ('take_profit_pct', 0.0),   # Take profit (0 = desabilitado)
        ('max_holding_days', 0),    # Máximo dias (0 = sem limite)
        ('reentry_cooldown', 0),    # Dias de cooldown após venda
        ('use_rsi_filter', False),  # Filtrar por RSI
        ('rsi_period', 14),         # Período RSI
        ('rsi_oversold', 30),       # RSI oversold
        ('rsi_overbought', 70),     # RSI overbought
    )
    
    def __init__(self):
        """Inicializar indicadores e tracking."""
        super().__init__()
        
        # Validação
        if self.params.signals is None:
            raise ValueError(
                "signals parameter is required. "
                "Pass dict: {date: 0/1} from NeuralTradingEngine.get_signals_dict()"
            )
        
        # Indicadores auxiliares
        self.rsi = bt.indicators.RSI(
            self.data.close, 
            period=self.params.rsi_period
        )
        self.sma_20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma_50 = bt.indicators.SMA(self.data.close, period=50)
        
        # Tracking
        self.entry_price = None
        self.entry_date = None
        self.highest_since_entry = None
        self.days_in_position = 0
        self.cooldown_counter = 0
        self.trade_count = 0
        self.winning_trades = 0
        self.signal_history = []
    
    def next(self):
        """Lógica principal executada a cada barra."""
        current_date = self.data.datetime.date(0)
        current_price = self.data.close[0]
        
        # Obter sinal e probabilidade
        signal = self.params.signals.get(current_date, 0)
        prob = 0.5
        if self.params.probabilities:
            prob = self.params.probabilities.get(current_date, 0.5)
        
        # Registrar histórico
        self.signal_history.append({
            'date': current_date,
            'signal': signal,
            'probability': prob,
            'price': current_price,
            'position': self.position.size
        })
        
        position_size = self.position.size
        
        # Atualizar cooldown
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
        
        # =====================================================================
        # POSIÇÃO ABERTA - Verificar saídas
        # =====================================================================
        if position_size > 0:
            self.days_in_position += 1
            
            # Atualizar máxima desde entrada
            if self.highest_since_entry is None:
                self.highest_since_entry = current_price
            else:
                self.highest_since_entry = max(self.highest_since_entry, current_price)
            
            exit_signal = False
            exit_reason = ""
            
            # 1. Stop Loss
            if self.params.stop_loss_pct > 0:
                pnl_pct = (current_price / self.entry_price - 1) * 100
                if pnl_pct < -self.params.stop_loss_pct:
                    exit_signal = True
                    exit_reason = f"Stop Loss ({pnl_pct:.1f}%)"
            
            # 2. Trailing Stop
            if self.params.trailing_stop_pct > 0 and self.highest_since_entry:
                drawdown_from_high = (self.highest_since_entry - current_price) / self.highest_since_entry * 100
                if drawdown_from_high > self.params.trailing_stop_pct:
                    exit_signal = True
                    exit_reason = f"Trailing Stop ({drawdown_from_high:.1f}% from high)"
            
            # 3. Take Profit
            if self.params.take_profit_pct > 0:
                pnl_pct = (current_price / self.entry_price - 1) * 100
                if pnl_pct > self.params.take_profit_pct:
                    exit_signal = True
                    exit_reason = f"Take Profit ({pnl_pct:.1f}%)"
            
            # 4. Max holding days
            if self.params.max_holding_days > 0:
                if self.days_in_position >= self.params.max_holding_days:
                    exit_signal = True
                    exit_reason = f"Max holding ({self.days_in_position} days)"
            
            # 5. Neural signal indica venda
            if self.params.probabilities:
                if prob < self.params.sell_threshold:
                    exit_signal = True
                    exit_reason = f"Neural sell signal (prob={prob:.2f})"
            elif signal == 0:
                exit_signal = True
                exit_reason = "Neural sell signal"
            
            if exit_signal:
                self.close()
                self._record_exit(exit_reason)
        
        # =====================================================================
        # SEM POSIÇÃO - Verificar entradas
        # =====================================================================
        else:
            # Verificar cooldown
            if self.cooldown_counter > 0:
                return
            
            buy_signal = False
            buy_reason = ""
            
            # Condição principal: neural signal
            if self.params.probabilities:
                if prob >= self.params.buy_threshold:
                    buy_signal = True
                    buy_reason = f"Neural buy signal (prob={prob:.2f})"
            elif signal == 1:
                buy_signal = True
                buy_reason = "Neural buy signal"
            
            # Filtros opcionais
            if buy_signal and self.params.use_rsi_filter:
                # Não comprar em overbought
                if self.rsi[0] > self.params.rsi_overbought:
                    buy_signal = False
                    self.log(f"Buy blocked: RSI overbought ({self.rsi[0]:.1f})")
            
            if buy_signal:
                size = self._calculate_position_size()
                self.buy(size=size)
                self._record_entry(buy_reason)
    
    def _calculate_position_size(self) -> float:
        """Calcular tamanho da posição."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        size = (cash * self.params.position_size) / price
        return size
    
    def _record_entry(self, reason: str):
        """Registrar entrada."""
        self.entry_price = self.data.close[0]
        self.entry_date = self.data.datetime.date(0)
        self.highest_since_entry = self.entry_price
        self.days_in_position = 0
        self.trade_count += 1
        self.log(f"🚀 BUY #{self.trade_count} @ {self.entry_price:.2f} - {reason}")
    
    def _record_exit(self, reason: str):
        """Registrar saída."""
        exit_price = self.data.close[0]
        pnl_pct = (exit_price / self.entry_price - 1) * 100 if self.entry_price else 0
        
        if pnl_pct > 0:
            self.winning_trades += 1
            emoji = "✅"
        else:
            emoji = "❌"
        
        self.log(f"{emoji} SELL @ {exit_price:.2f} ({pnl_pct:+.1f}%) - {reason} | Held: {self.days_in_position}d")
        
        # Reset tracking
        self.entry_price = None
        self.entry_date = None
        self.highest_since_entry = None
        self.days_in_position = 0
        self.cooldown_counter = self.params.reentry_cooldown
    
    def notify_trade(self, trade):
        """Callback quando trade é fechado."""
        super().notify_trade(trade)
    
    def stop(self):
        """Chamado quando backtest termina."""
        super().stop()
        
        win_rate = (self.winning_trades / self.trade_count * 100) if self.trade_count > 0 else 0
        
        self.log(f"\n📊 NEURAL STRATEGY SUMMARY:")
        self.log(f"   Total Trades: {self.trade_count}")
        self.log(f"   Winning: {self.winning_trades} ({win_rate:.1f}%)")
        self.log(f"   Losing: {self.trade_count - self.winning_trades}")
        
        # Estatísticas dos sinais
        if self.signal_history:
            signals = [h['signal'] for h in self.signal_history]
            buy_signals = sum(signals)
            self.log(f"   Buy signals: {buy_signals}/{len(signals)} ({buy_signals/len(signals)*100:.1f}%)")
