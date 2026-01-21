"""
Meta Strategy - Orquestrador de Especialistas

FILOSOFIA CORRETA:
- Trial 77 (BTCAdaptiveStrategy) É A ESTRATÉGIA BASE
- Especialistas APENAS cobrem os BURACOS onde Trial 77 falha
- NÃO substituir Trial 77, COMPLEMENTAR onde ela perde

ARQUITETURA:
1. RegimeDetector identifica regime extremo (STRONG_BULL_RUN, CRASH, RECOVERY)
2. Se regime extremo → usar especialista
3. Se regime normal → usar Trial 77 DIRETO (não como fallback)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy
from engines.regime_detector import RegimeDetector


class MetaStrategy(BaseStrategy):
    """
    Estratégia meta que MANTÉM Trial 77 e ADICIONA especialistas.
    
    Trial 77 funciona na maioria dos cenários (10-20% de exposição).
    Especialistas APENAS para regimes extremos:
    - STRONG_BULL_RUN (8% do tempo) → BullRunRider (aumentar exposição)
    - CRASH (<5% do tempo) → CrashAvoider (preservar capital)
    - RECOVERY (2% do tempo) → RecoveryHunter (entrar agressivo)
    
    REGRA: Se em dúvida, usar Trial 77. Especialistas APENAS em certezas absolutas.
    """
    
    params = (
        # === TRIAL 77 PARAMETERS (BASE) ===
        ('rsi_period', 11),
        ('rsi_oversold', 33),
        ('rsi_overbought', 76),
        ('bb_period', 19),
        ('bb_dev', 2.35),
        ('volume_period', 18),
        ('volume_threshold', 1.15),
        ('macd_fast', 11),
        ('macd_slow', 25),
        ('macd_signal', 8),
        ('ema_fast', 8),
        ('ema_slow', 19),
        ('atr_period', 13),
        ('atr_multiplier', 1.69),
        ('take_profit_pct', 15.83),
        ('trailing_stop_pct', 9.23),
        ('position_size', 0.88),
        ('min_signals_buy', 2),
        ('min_signals_sell', 2),
        
        # === SPECIALIST OVERRIDES (apenas quando ativados) ===
        ('bull_run_position_size', 0.98),
        ('bull_run_trailing', 20.0),
        ('bull_run_profit_threshold', 25.0),
        ('recovery_position_size', 0.90),
        ('recovery_stop_loss', 10.0),
        ('recovery_take_profit', 15.0),
        
        # === REGIME DETECTOR THRESHOLDS ===
        ('strong_bull_ret20', 15.0),
        ('strong_bull_ret60', 30.0),
        ('bull_correction_ret60', 20.0),
        ('bull_correction_ret20_max', 5.0),
        ('steady_bull_ret20', 5.0),
        ('steady_bull_ret60', 10.0),
        ('recovery_ret20', 10.0),
        ('sideways_threshold', 10.0),
        ('sideways_vol_threshold', 4.0),
        ('crash_threshold', -15.0),
        ('bear_ret20', -5.0),
        ('bear_ret60', -10.0),
    )
    
    def __init__(self):
        """Inicializar com TODOS os indicadores do Trial 77 + regime detector."""
        super().__init__()
        
        # === REGIME DETECTOR ===
        regime_thresholds = {
            'strong_bull_ret20': self.params.strong_bull_ret20,
            'strong_bull_ret60': self.params.strong_bull_ret60,
            'bull_correction_ret60': self.params.bull_correction_ret60,
            'bull_correction_ret20_max': self.params.bull_correction_ret20_max,
            'steady_bull_ret20': self.params.steady_bull_ret20,
            'steady_bull_ret60': self.params.steady_bull_ret60,
            'recovery_ret20': self.params.recovery_ret20,
            'sideways_threshold': self.params.sideways_threshold,
            'sideways_vol_threshold': self.params.sideways_vol_threshold,
            'crash_threshold': self.params.crash_threshold,
            'bear_ret20': self.params.bear_ret20,
            'bear_ret60': self.params.bear_ret60,
        }
        self.regime_detector = RegimeDetector(window=60, **regime_thresholds)
        
        # === SMAs PARA REGIME DETECTION ===
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma50 = bt.indicators.SMA(self.data.close, period=50)
        self.sma200 = bt.indicators.SMA(self.data.close, period=200)
        
        # === TRIAL 77 INDICATORS (SEMPRE ATIVOS) ===
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_dev
        )
        
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=self.params.volume_period)
        
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow)
        
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # === STATE TRACKING ===
        self.current_regime = None
        self.entry_price = None
        self.highest_price = None
        self.entry_regime = None
        self.using_specialist = False  # Flag se está usando especialista ou Trial 77
    
    def detect_current_regime(self):
        """Detectar regime atual usando dados disponíveis."""
        # Criar DataFrame temporário com dados necessários
        import pandas as pd
        
        # Pegar últimos 200 dias (suficiente para detector)
        lookback = min(200, len(self.data))
        
        data_dict = {
            'close': [self.data.close[-i] for i in range(lookback-1, -1, -1)],
            'sma20': [self.sma20[-i] for i in range(lookback-1, -1, -1)],
            'sma50': [self.sma50[-i] for i in range(lookback-1, -1, -1)],
            'sma200': [self.sma200[-i] for i in range(lookback-1, -1, -1)],
        }
        
        df = pd.DataFrame(data_dict)
        
        return self.regime_detector.detect(df)
    
    def next(self):
        """Lógica meta: detectar regime e delegar para especialista."""
        # Dados insuficientes
        if len(self.data) < 200:
            return
        
        current_price = self.data.close[0]
        
        # Detectar regime atual
        self.current_regime = self.detect_current_regime()
        
        # Log de regime (apenas quando muda)
        if not hasattr(self, 'last_logged_regime') or self.last_logged_regime != self.current_regime:
            self.log(f"📍 REGIME: {self.current_regime}")
            self.last_logged_regime = self.current_regime
        
        # === LÓGICA DE ENTRADA ===
        if not self.position:
            self.entry_price = None
            self.highest_price = None
            self.entry_regime = None
            
            # Selecionar especialista baseado no regime
            if self.current_regime == 'STRONG_BULL_RUN':
                self._specialist_bull_run_entry(current_price)
            
            elif self.current_regime == 'RECOVERY':
                self._specialist_recovery_entry(current_price)
            
            elif self.current_regime in ['CRASH', 'BEAR_MARKET']:
                # CrashAvoider: NÃO ENTRAR
                pass
            
            elif self.current_regime == 'CHOPPY_SIDEWAYS':
                # SidewaysSitter: Ficar fora (overtrading perigoso)
                pass
            
            else:
                # Fallback: usar Trial 77
                self._trial77_entry(current_price)
        
        # === LÓGICA DE SAÍDA ===
        else:
            # Atualizar highest price
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            
            # PRIORIDADE 1: Crash detectado - sair imediatamente
            if self.current_regime in ['CRASH', 'BEAR_MARKET']:
                self.close()
                self.log(f"🚨 EXIT: {self.current_regime} @ ${current_price:.2f} | P&L: {pnl_pct:+.2f}%")
                return
            
            # Delegar saída para especialista do regime de entrada
            if self.entry_regime == 'STRONG_BULL_RUN':
                self._specialist_bull_run_exit(current_price, pnl_pct)
            
            elif self.entry_regime == 'RECOVERY':
                self._specialist_recovery_exit(current_price, pnl_pct)
            
            else:
                # Fallback: usar Trial 77
                self._trial77_exit(current_price, pnl_pct)
    
    # ========== ESPECIALISTA 1: BULL RUN RIDER ==========
    
    def _specialist_bull_run_entry(self, price):
        """Entry agressivo em bull runs fortes."""
        # Confirmar tendência
        if price > self.sma20[0] > self.sma50[0]:
            size = (self.broker.get_cash() * self.params.bull_run_position_size) / price
            
            if size > 0:
                self.buy(size=size)
                self.entry_price = price
                self.highest_price = price
                self.entry_regime = 'STRONG_BULL_RUN'
                self.active_specialist = 'BullRunRider'
                
                self.log(f"🚀 [BullRunRider] BUY @ ${price:.2f} | Position: 98%")
    
    def _specialist_bull_run_exit(self, price, pnl_pct):
        """Exit conservador: apenas trailing stop amplo ou quebra de estrutura."""
        exit_signal = None
        
        # Trailing stop (apenas se lucro > 25%)
        if pnl_pct > 25:
            drawdown_from_peak = ((price - self.highest_price) / self.highest_price) * 100
            if drawdown_from_peak < -self.params.bull_run_trailing:
                exit_signal = "TRAILING_STOP"
        
        # Quebra de estrutura (preço abaixo SMA20)
        elif price < self.sma20[0]:
            exit_signal = "STRUCTURE_BREAK"
        
        if exit_signal:
            self.close()
            self.log(f"📤 [BullRunRider] {exit_signal} @ ${price:.2f} | P&L: {pnl_pct:+.2f}%")
    
    # ========== ESPECIALISTA 2: RECOVERY HUNTER ==========
    
    def _specialist_recovery_entry(self, price):
        """Entry agressivo em recuperações."""
        # Confirmar que está acima SMA50
        if price > self.sma50[0]:
            size = (self.broker.get_cash() * self.params.recovery_position_size) / price
            
            if size > 0:
                self.buy(size=size)
                self.entry_price = price
                self.highest_price = price
                self.entry_regime = 'RECOVERY'
                self.active_specialist = 'RecoveryHunter'
                
                self.log(f"🌱 [RecoveryHunter] BUY @ ${price:.2f} | Position: 90%")
    
    def _specialist_recovery_exit(self, price, pnl_pct):
        """Exit: transferir para BullRunRider ou stop loss."""
        exit_signal = None
        
        # Se evoluiu para STRONG_BULL_RUN, transferir especialista
        if self.current_regime == 'STRONG_BULL_RUN':
            self.entry_regime = 'STRONG_BULL_RUN'
            self.active_specialist = 'BullRunRider'
            self.log(f"🔄 [RecoveryHunter→BullRunRider] Transferência @ ${price:.2f}")
            return
        
        # Stop loss
        if pnl_pct < -10:
            exit_signal = "STOP_LOSS"
        
        # Take profit rápido (recovery pode reverter)
        elif pnl_pct > 15:
            exit_signal = "TAKE_PROFIT"
        
        if exit_signal:
            self.close()
            self.log(f"📤 [RecoveryHunter] {exit_signal} @ ${price:.2f} | P&L: {pnl_pct:+.2f}%")
    
    # ========== FALLBACK: TRIAL 77 ==========
    
    def _trial77_entry(self, price):
        """Entry usando lógica Trial 77."""
        # Contar sinais
        signals = 0
        
        # RSI oversold
        if self.rsi[0] < self.params.rsi_oversold:
            signals += 1
        
        # Abaixo BB inferior
        if price < self.bb.lines.bot[0]:
            signals += 1
        
        # MACD positivo
        if self.macd.macd[0] > self.macd.signal[0]:
            signals += 1
        
        # Volume alto
        if self.data.volume[0] > self.volume_sma[0] * self.params.volume_threshold:
            signals += 1
        
        # Precisa de min_signals_buy
        if signals >= self.params.min_signals_buy:
            size = (self.broker.get_cash() * self.params.position_size) / price
            
            if size > 0:
                self.buy(size=size)
                self.entry_price = price
                self.highest_price = price
                self.entry_regime = self.current_regime
                self.active_specialist = 'Trial77'
                
                self.log(f"✅ [Trial77] BUY @ ${price:.2f} | Signals: {signals} | Position: 88%")
    
    def _trial77_exit(self, price, pnl_pct):
        """Exit usando lógica Trial 77."""
        exit_signal = None
        signals = 0
        
        # RSI overbought
        if self.rsi[0] > self.params.rsi_overbought:
            signals += 1
        
        # MACD bearish
        if self.macd.macd[0] < self.macd.signal[0]:
            signals += 1
        
        # Take profit
        if pnl_pct > self.params.take_profit_pct:
            exit_signal = "TAKE_PROFIT"
        
        # Trailing stop
        elif pnl_pct > 10:
            drawdown = ((price - self.highest_price) / self.highest_price) * 100
            if drawdown < -self.params.trailing_stop_pct:
                exit_signal = "TRAILING_STOP"
        
        # Min signals para vender
        elif signals >= self.params.min_signals_sell:
            exit_signal = "SELL_SIGNALS"
        
        if exit_signal:
            self.close()
            self.log(f"📤 [Trial77] {exit_signal} @ ${price:.2f} | P&L: {pnl_pct:+.2f}%")
