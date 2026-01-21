"""
Regime-Based Trading Strategy - Estratégia baseada em detecção de regime.

Esta estratégia opera baseada no regime de mercado detectado pela rede neural,
não em previsões de direção de preço.

Regras de operação:
- STRONG_UP: Posição máxima long
- WEAK_UP: Posição parcial long
- SIDEWAYS: Flat ou posição reduzida
- WEAK_DOWN: Posição parcial short (ou hedge)
- STRONG_DOWN: Posição máxima short (ou cash)

Considera também o estado de volatilidade:
- VOL_CRUSH: Pode aumentar alavancagem
- VOL_NORMAL: Posição normal
- VOL_EXPANSION: Reduzir posição, stops mais apertados
"""

import backtrader as bt
import numpy as np
from typing import Dict, Optional

from strategies.base_strategy import BaseStrategy


class RegimeTradingStrategy(BaseStrategy):
    """
    Estratégia que opera baseada em regime de mercado detectado.
    
    Recebe sinais de regime pré-computados e ajusta posição de acordo
    com o regime atual e estado de volatilidade.
    """
    
    params = (
        # Sinais de regime (required)
        ('regime_signals', None),       # Dict: date -> {'signal', 'position', 'regime', 'vol_state', 'confidence'}
        
        # Position sizing por regime
        ('strong_up_size', 1.0),        # 100% posição em regime forte de alta
        ('weak_up_size', 0.6),          # 60% posição em regime fraco de alta
        ('sideways_size', 0.0),         # Flat em regime lateral
        ('weak_down_size', 0.0),        # Cash em regime fraco de baixa (sem short)
        ('strong_down_size', 0.0),      # Cash em regime forte de baixa
        
        # Ajustes por volatilidade
        ('vol_crush_multiplier', 1.2),  # Aumentar posição em vol baixa
        ('vol_expansion_multiplier', 0.5),  # Reduzir posição em vol alta
        
        # Risk management
        ('max_position_size', 0.95),    # Máximo 95% do capital
        ('confidence_threshold', 0.35), # Confiança mínima para operar
        ('stop_loss_pct', 8.0),         # Stop loss base
        ('vol_adjusted_stop', True),    # Ajustar stop por volatilidade
        
        # Regime change handling
        ('smooth_transitions', True),   # Transições suaves entre regimes
        ('min_regime_bars', 3),         # Barras mínimas para confirmar mudança
        
        # Reentry
        ('reentry_cooldown', 0),        # Barras de cooldown após saída
    )
    
    def __init__(self):
        """Inicializar indicadores e tracking."""
        super().__init__()
        
        # Validação
        if self.params.regime_signals is None:
            raise ValueError(
                "regime_signals parameter is required. "
                "Pass dict from NeuralRegimeEngine.get_trading_signals()"
            )
        
        # Indicadores auxiliares
        self.sma_20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma_50 = bt.indicators.SMA(self.data.close, period=50)
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # Tracking
        self.entry_price = None
        self.entry_date = None
        self.current_regime = 'UNKNOWN'
        self.regime_bar_count = 0
        self.cooldown_counter = 0
        self.trade_count = 0
        self.winning_trades = 0
        
        # Histórico para análise
        self.regime_history = []
        self.position_history = []
    
    def next(self):
        """Lógica principal executada a cada barra."""
        current_date = self.data.datetime.date(0)
        current_price = self.data.close[0]
        
        # Obter sinal de regime - tentar múltiplos formatos de data
        signal_data = self.params.regime_signals.get(current_date, None)
        
        # Se não encontrou, tentar como datetime
        if signal_data is None:
            from datetime import datetime
            dt_key = datetime.combine(current_date, datetime.min.time())
            signal_data = self.params.regime_signals.get(dt_key, None)
        
        # Se não encontrou, tentar como string
        if signal_data is None:
            str_key = str(current_date)
            signal_data = self.params.regime_signals.get(str_key, None)
        
        # Se não encontrou, tentar como Timestamp
        if signal_data is None:
            import pandas as pd
            ts_key = pd.Timestamp(current_date)
            signal_data = self.params.regime_signals.get(ts_key, None)
        
        if signal_data is None:
            # Sem sinal para essa data - isso é esperado para as primeiras barras
            return
        
        regime = signal_data.get('regime', 'SIDEWAYS')
        vol_state = signal_data.get('vol_state', 'VOL_NORMAL')
        confidence = signal_data.get('confidence', 0)
        suggested_position = signal_data.get('position', 0)
        
        # Registrar histórico
        self.regime_history.append({
            'date': current_date,
            'regime': regime,
            'vol_state': vol_state,
            'confidence': confidence,
            'price': current_price
        })
        
        # Atualizar cooldown
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
        
        # Verificar mudança de regime
        regime_changed = False
        if regime != self.current_regime:
            self.regime_bar_count = 1
            regime_changed = True
        else:
            self.regime_bar_count += 1
        
        # Se smooth_transitions, esperar confirmação
        if self.params.smooth_transitions and regime_changed:
            if self.regime_bar_count < self.params.min_regime_bars:
                # Ainda esperando confirmação
                return
        
        self.current_regime = regime
        
        # Calcular tamanho de posição desejado
        target_size = self._calculate_target_position(
            regime, vol_state, confidence
        )
        
        # Posição atual
        current_position = self.position.size
        current_value = abs(current_position * current_price) if current_position != 0 else 0
        portfolio_value = self.broker.getvalue()
        current_exposure = current_value / portfolio_value if portfolio_value > 0 else 0
        
        # Log de decisão
        self.position_history.append({
            'date': current_date,
            'regime': regime,
            'target_size': target_size,
            'current_exposure': current_exposure,
            'action': 'pending'
        })
        
        # =====================================================================
        # LÓGICA DE TRADING BASEADA EM REGIME
        # =====================================================================
        
        # Verificar confiança mínima
        if confidence < self.params.confidence_threshold:
            # Baixa confiança -> não fazer nada ou reduzir posição
            if current_position != 0:
                # Reduzir posição em 50% se confiança baixa
                self._reduce_position(0.5)
            return
        
        # Calcular diferença de posição
        position_diff = target_size - current_exposure
        
        # =====================================================================
        # GESTÃO DE POSIÇÃO EXISTENTE
        # =====================================================================
        
        if current_position > 0:  # Posição long aberta
            # Verificar stop loss
            if self.entry_price is not None:
                pnl_pct = (current_price / self.entry_price - 1) * 100
                stop_level = self._get_stop_level(vol_state)
                
                if pnl_pct < -stop_level:
                    self._close_position(f"Stop Loss ({pnl_pct:.1f}%)")
                    return
            
            # Regime mudou para baixa?
            if regime in ['STRONG_DOWN', 'WEAK_DOWN']:
                self._close_position(f"Regime changed to {regime}")
                return
            
            # Ajustar tamanho de posição se necessário
            if abs(position_diff) > 0.1:  # Diferença significativa
                if target_size < current_exposure:
                    # Reduzir posição
                    reduce_pct = (current_exposure - target_size) / current_exposure
                    self._reduce_position(reduce_pct)
                elif target_size > current_exposure and regime in ['STRONG_UP', 'WEAK_UP']:
                    # Aumentar posição
                    self._increase_position(target_size)
        
        # =====================================================================
        # ABERTURA DE NOVA POSIÇÃO
        # =====================================================================
        
        elif current_position == 0:  # Sem posição
            # Verificar cooldown
            if self.cooldown_counter > 0:
                return
            
            # Só abrir posição em regimes de alta
            if regime in ['STRONG_UP', 'WEAK_UP'] and target_size > 0:
                self._open_position(target_size, regime, vol_state)
    
    def _calculate_target_position(
        self, 
        regime: str, 
        vol_state: str, 
        confidence: float
    ) -> float:
        """Calcular tamanho de posição alvo baseado em regime."""
        
        # Base size por regime
        if regime == 'STRONG_UP':
            base_size = self.params.strong_up_size
        elif regime == 'WEAK_UP':
            base_size = self.params.weak_up_size
        elif regime == 'SIDEWAYS':
            base_size = self.params.sideways_size
        elif regime == 'WEAK_DOWN':
            base_size = self.params.weak_down_size
        elif regime == 'STRONG_DOWN':
            base_size = self.params.strong_down_size
        else:
            base_size = 0
        
        # Ajuste por volatilidade
        if vol_state == 'VOL_CRUSH':
            vol_multiplier = self.params.vol_crush_multiplier
        elif vol_state == 'VOL_EXPANSION':
            vol_multiplier = self.params.vol_expansion_multiplier
        else:
            vol_multiplier = 1.0
        
        # Ajuste por confiança
        confidence_multiplier = min(1.0, confidence / 0.7)  # Escala até 70% confiança
        
        # Tamanho final
        target = base_size * vol_multiplier * confidence_multiplier
        
        # Limitar ao máximo
        return min(target, self.params.max_position_size)
    
    def _get_stop_level(self, vol_state: str) -> float:
        """Obter nível de stop ajustado por volatilidade."""
        base_stop = self.params.stop_loss_pct
        
        if not self.params.vol_adjusted_stop:
            return base_stop
        
        if vol_state == 'VOL_EXPANSION':
            return base_stop * 1.5  # Stop mais largo em alta vol
        elif vol_state == 'VOL_CRUSH':
            return base_stop * 0.75  # Stop mais apertado em baixa vol
        else:
            return base_stop
    
    def _open_position(self, target_size: float, regime: str, vol_state: str):
        """Abrir nova posição."""
        cash = self.broker.get_cash()
        price = self.data.close[0]
        
        # Calcular quantidade
        position_value = cash * target_size
        size = position_value / price
        
        if size > 0:
            self.buy(size=size)
            self.entry_price = price
            self.entry_date = self.data.datetime.date(0)
            self.trade_count += 1
            
            self.log(f"🚀 BUY #{self.trade_count} | Size: {target_size:.0%} | "
                    f"Regime: {regime} | Vol: {vol_state}")
    
    def _close_position(self, reason: str):
        """Fechar posição existente."""
        if self.position.size == 0:
            return
        
        exit_price = self.data.close[0]
        pnl_pct = (exit_price / self.entry_price - 1) * 100 if self.entry_price else 0
        
        if pnl_pct > 0:
            self.winning_trades += 1
            emoji = "✅"
        else:
            emoji = "❌"
        
        self.close()
        
        self.log(f"{emoji} CLOSE | PnL: {pnl_pct:+.1f}% | {reason}")
        
        # Reset tracking
        self.entry_price = None
        self.entry_date = None
        self.cooldown_counter = self.params.reentry_cooldown
    
    def _reduce_position(self, reduce_pct: float):
        """Reduzir posição em percentual."""
        if self.position.size == 0:
            return
        
        reduce_size = abs(self.position.size * reduce_pct)
        if reduce_size > 0:
            self.sell(size=reduce_size)
            self.log(f"📉 REDUCE | -{reduce_pct:.0%} | Regime: {self.current_regime}")
    
    def _increase_position(self, target_size: float):
        """Aumentar posição para target."""
        current_value = abs(self.position.size * self.data.close[0])
        portfolio_value = self.broker.getvalue()
        current_exposure = current_value / portfolio_value
        
        if target_size > current_exposure:
            additional_exposure = target_size - current_exposure
            cash = self.broker.get_cash()
            additional_value = min(cash * 0.95, portfolio_value * additional_exposure)
            additional_size = additional_value / self.data.close[0]
            
            if additional_size > 0:
                self.buy(size=additional_size)
                self.log(f"📈 INCREASE | +{additional_exposure:.0%} | Regime: {self.current_regime}")
    
    def stop(self):
        """Chamado quando backtest termina."""
        super().stop()
        
        win_rate = (self.winning_trades / self.trade_count * 100) if self.trade_count > 0 else 0
        
        self.log(f"\n📊 REGIME STRATEGY SUMMARY:")
        self.log(f"   Total Trades: {self.trade_count}")
        self.log(f"   Winning: {self.winning_trades} ({win_rate:.1f}%)")
        self.log(f"   Losing: {self.trade_count - self.winning_trades}")
        
        # Estatísticas de regime
        if self.regime_history:
            regimes = [h['regime'] for h in self.regime_history]
            regime_counts = {}
            for r in regimes:
                regime_counts[r] = regime_counts.get(r, 0) + 1
            
            self.log(f"\n   Regime Distribution:")
            for regime, count in sorted(regime_counts.items()):
                pct = count / len(regimes) * 100
                self.log(f"     {regime}: {count} days ({pct:.1f}%)")
