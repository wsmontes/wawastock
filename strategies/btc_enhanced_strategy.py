"""
BTC Enhanced Strategy - Trial 77 otimizado com lições complementares

BASEADO EM ANÁLISE SISTEMÁTICA:
- Trial 77: +420.42%, 132 trades, DD 51.72%, Sharpe 0.8038
- Bear Avoider: DD 23.23%, Sharpe 0.8963, Win Rate 52%
- Strong Bull Rider: $6,413/trade (2x Trial 77)

MELHORIAS INCORPORADAS:
1. Filtro de Regime (Bear Avoider) - Bloquear entradas em bear markets
2. Seletividade (Strong Bull Rider) - Rejeitar sinais de baixa qualidade
3. Risk Management Aprimorado - Reduzir drawdown mantendo retorno

OBJETIVO:
- Retorno: +500-600%
- Drawdown: <35%
- Sharpe: >0.90
- Trades: ~80-100 (menos overtrading)
- Win Rate: >48%
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCEnhancedStrategy(BaseStrategy):
    """
    Versão otimizada do Trial 77 com proteção de capital e seletividade.
    
    INOVAÇÕES:
    1. Market Regime Filter - Não entra em bear markets
    2. Signal Quality Score - Só entra com múltiplas confirmações fortes
    3. Dynamic Position Sizing - Ajusta exposição por regime
    4. Adaptive Stops - Stop loss baseado em volatilidade de regime
    """
    
    params = (
        # === REGIME DETECTION (do Bear Avoider) ===
        ('regime_period', 20),           # Período para classificar regime
        ('strong_bull_threshold', 15.0), # Return% para STRONG_BULL
        ('bull_threshold', 5.0),         # Return% para BULL
        ('bear_threshold', -10.0),       # Return% para BEAR
        ('strong_bear_threshold', -20.0), # Return% para STRONG_BEAR
        
        # === TREND FILTERS ===
        ('sma_fast', 20),
        ('sma_mid', 50),
        ('sma_slow', 200),
        
        # === SIGNAL QUALITY (melhorado) ===
        ('min_quality_score', 6),        # Mínimo 6/10 pontos para entrar
        
        # === RSI ===
        ('rsi_period', 11),
        ('rsi_oversold', 33),
        ('rsi_overbought', 76),
        
        # === BOLLINGER BANDS ===
        ('bb_period', 19),
        ('bb_dev', 2.35),
        
        # === MACD ===
        ('macd_fast', 11),
        ('macd_slow', 25),
        ('macd_signal', 8),
        
        # === VOLUME ===
        ('volume_period', 18),
        ('volume_threshold', 1.15),
        
        # === ATR ===
        ('atr_period', 13),
        
        # === DYNAMIC POSITION SIZING (por regime) ===
        ('position_strong_bull', 0.95),  # 95% em STRONG_BULL
        ('position_bull', 0.85),         # 85% em BULL
        ('position_weak_bull', 0.70),    # 70% em WEAK_BULL
        ('position_sideways', 0.50),     # 50% em SIDEWAYS
        
        # === ADAPTIVE RISK MANAGEMENT ===
        ('stop_loss_strong_bull', 15.0), # Stop amplo em bull
        ('stop_loss_bull', 10.0),
        ('stop_loss_default', 8.0),
        ('take_profit_pct', 20.0),       # Take profit mais generoso
        ('trailing_stop_pct', 12.0),
        ('trailing_activation', 25.0),   # Ativar em +25%
    )
    
    def __init__(self):
        """Inicializar indicadores."""
        super().__init__()
        
        # SMAs para regime e tendência
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.sma_fast)
        self.sma_mid = bt.indicators.SMA(self.data.close, period=self.params.sma_mid)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.sma_slow)
        
        # Return para regime
        self.return_regime = (self.data.close / self.data.close(-self.params.regime_period) - 1) * 100
        
        # RSI
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
        
        # Volume
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=self.params.volume_period)
        
        # ATR
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # Tracking
        self.entry_price = None
        self.highest_price = None
        self.current_regime = None
        self.entry_regime = None
        self.stop_loss_price = None
    
    def classify_regime(self):
        """Classificar regime de mercado atual."""
        ret = self.return_regime[0]
        
        if ret > self.params.strong_bull_threshold:
            return 'STRONG_BULL'
        elif ret > self.params.bull_threshold:
            return 'BULL'
        elif ret > 0:
            return 'WEAK_BULL'
        elif ret > self.params.bear_threshold:
            return 'WEAK_BEAR'
        elif ret > self.params.strong_bear_threshold:
            return 'BEAR'
        else:
            return 'STRONG_BEAR'
    
    def calculate_signal_quality(self):
        """
        Calcular score de qualidade do sinal (0-10).
        
        Baseado em Strong Bull Rider: seletividade é chave.
        Quanto maior o score, melhor a oportunidade.
        """
        score = 0
        current_price = self.data.close[0]
        
        # 1. RSI oversold (+2 pontos)
        if self.rsi[0] < self.params.rsi_oversold:
            score += 2
        
        # 2. Preço abaixo BB inferior (+2 pontos)
        if current_price < self.bb.lines.bot[0]:
            score += 2
        
        # 3. MACD positivo (+1 ponto)
        if self.macd.macd[0] > self.macd.signal[0]:
            score += 1
        
        # 4. Volume acima da média (+1 ponto)
        if self.data.volume[0] > self.volume_sma[0] * self.params.volume_threshold:
            score += 1
        
        # 5. Preço acima SMA50 (tendência de alta, +2 pontos)
        if current_price > self.sma_mid[0]:
            score += 2
        
        # 6. Golden cross ativo (+2 pontos)
        if self.sma_fast[0] > self.sma_mid[0]:
            score += 2
        
        return score
    
    def get_position_size(self):
        """Retornar tamanho de posição baseado no regime."""
        if self.current_regime == 'STRONG_BULL':
            return self.params.position_strong_bull
        elif self.current_regime == 'BULL':
            return self.params.position_bull
        elif self.current_regime == 'WEAK_BULL':
            return self.params.position_weak_bull
        else:
            return self.params.position_sideways
    
    def get_stop_loss_pct(self):
        """Retornar stop loss baseado no regime."""
        if self.current_regime in ['STRONG_BULL', 'BULL']:
            return self.params.stop_loss_strong_bull
        elif self.current_regime == 'WEAK_BULL':
            return self.params.stop_loss_bull
        else:
            return self.params.stop_loss_default
    
    def next(self):
        """Lógica de trading executada a cada barra."""
        # Verificar dados suficientes
        if len(self.data) < self.params.sma_slow:
            return
        
        current_price = self.data.close[0]
        self.current_regime = self.classify_regime()
        
        # === ENTRADA ===
        if not self.position:
            self.entry_price = None
            self.highest_price = None
            self.entry_regime = None
            self.stop_loss_price = None
            
            # FILTRO 1: NÃO ENTRAR em bear markets (lição do Bear Avoider)
            if self.current_regime in ['BEAR', 'STRONG_BEAR']:
                return
            
            # FILTRO 2: Calcular qualidade do sinal (lição do Strong Bull Rider)
            signal_quality = self.calculate_signal_quality()
            
            # FILTRO 3: Apenas entrar com qualidade suficiente
            if signal_quality < self.params.min_quality_score:
                return
            
            # Calcular tamanho da posição baseado no regime
            position_size = self.get_position_size()
            size = (self.broker.get_cash() * position_size) / current_price
            
            if size > 0:
                self.buy(size=size)
                self.entry_price = current_price
                self.highest_price = current_price
                self.entry_regime = self.current_regime
                
                # Stop loss adaptativo
                stop_pct = self.get_stop_loss_pct()
                self.stop_loss_price = current_price * (1 - stop_pct / 100)
                
                self.log(
                    f"✅ BUY @ ${current_price:.2f} | "
                    f"Regime: {self.current_regime} | "
                    f"Quality: {signal_quality}/10 | "
                    f"Position: {position_size*100:.0f}% | "
                    f"Stop: ${self.stop_loss_price:.2f}"
                )
        
        # === SAÍDA ===
        else:
            # Atualizar highest price
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            
            exit_signal = None
            
            # 1. PRIORIDADE MÁXIMA: Bear market detectado (Bear Avoider)
            if self.current_regime in ['BEAR', 'STRONG_BEAR']:
                exit_signal = "BEAR_DETECTED"
            
            # 2. Stop loss adaptativo
            elif current_price < self.stop_loss_price:
                exit_signal = "STOP_LOSS"
            
            # 3. RSI overbought
            elif self.rsi[0] > self.params.rsi_overbought:
                exit_signal = "RSI_OVERBOUGHT"
            
            # 4. Take profit
            elif pnl_pct > self.params.take_profit_pct:
                exit_signal = "TAKE_PROFIT"
            
            # 5. Trailing stop (apenas se lucro > trailing_activation)
            elif pnl_pct > self.params.trailing_activation:
                drawdown_from_peak = ((current_price - self.highest_price) / self.highest_price) * 100
                if drawdown_from_peak < -self.params.trailing_stop_pct:
                    exit_signal = "TRAILING_STOP"
            
            # 6. Quebra de tendência
            elif current_price < self.sma_fast[0]:
                exit_signal = "TREND_BREAK"
            
            # Executar saída
            if exit_signal:
                self.close()
                self.log(
                    f"📤 SELL: {exit_signal} @ ${current_price:.2f} | "
                    f"P&L: {pnl_pct:+.2f}% | "
                    f"Regime: {self.current_regime}"
                )
                
                self.entry_price = None
                self.highest_price = None
                self.entry_regime = None
                self.stop_loss_price = None
