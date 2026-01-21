"""
BTC Adaptive Strategy - Estratégia híbrida otimizada para Bitcoin.

Combina múltiplos sinais técnicos:
- Mean reversion: RSI + Bollinger Bands
- Trend following: MACD + EMA crossovers
- Momentum: Volume + ATR
- Risk management: Trailing stops + position sizing dinâmico

Otimizado para capturar reversões de -8% a +14% observadas em BTC 2025.
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BTCAdaptiveStrategy(BaseStrategy):
    """
    Estratégia adaptativa multi-indicador para Bitcoin.
    
    Sinais de COMPRA (todos devem convergir):
    1. RSI < rsi_oversold (mean reversion)
    2. Preço abaixo da banda inferior de Bollinger
    3. Volume > volume_threshold * média
    4. MACD histogram positivo (confirmação de momentum)
    
    Sinais de VENDA:
    1. RSI > rsi_overbought (take profit)
    2. Preço acima da banda superior de Bollinger
    3. MACD bearish crossover
    4. Trailing stop ativado
    """
    
    params = (
        # RSI parameters
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        
        # Bollinger Bands
        ('bb_period', 20),
        ('bb_dev', 2.0),
        
        # MACD
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # EMA trend filters
        ('ema_fast', 20),
        ('ema_slow', 50),
        
        # Volume
        ('volume_period', 20),
        ('volume_threshold', 1.2),  # 20% acima da média
        
        # ATR for volatility
        ('atr_period', 14),
        ('atr_multiplier', 2.0),
        
        # Position sizing
        ('position_size', 0.95),  # 95% do capital
        
        # Risk management
        ('stop_loss_pct', 5.0),      # Stop loss fixo
        ('trailing_stop_pct', 3.0),  # Trailing stop
        ('take_profit_pct', 12.0),   # Take profit target
        
        # Multi-signal requirements
        ('min_signals_buy', 3),      # Mínimo de sinais para comprar
        ('min_signals_sell', 2),     # Mínimo de sinais para vender
    )
    
    def __init__(self):
        """Inicializar indicadores."""
        super().__init__()
        
        # RSI
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )
        
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
        
        # EMAs for trend
        self.ema_fast = bt.indicators.EMA(
            self.data.close,
            period=self.params.ema_fast
        )
        self.ema_slow = bt.indicators.EMA(
            self.data.close,
            period=self.params.ema_slow
        )
        
        # Volume SMA
        self.volume_sma = bt.indicators.SMA(
            self.data.volume,
            period=self.params.volume_period
        )
        
        # ATR for volatility-based stops
        self.atr = bt.indicators.ATR(
            self.data,
            period=self.params.atr_period
        )
        
        # Track entry price and highest price since entry
        self.entry_price = None
        self.highest_since_entry = None
        
    def next(self):
        """Lógica principal da estratégia."""
        
        # Skip if indicators not ready
        if len(self.data) < max(
            self.params.bb_period,
            self.params.macd_slow,
            self.params.ema_slow,
            self.params.volume_period
        ):
            return
        
        current_price = self.data.close[0]
        
        # Se temos posição aberta, gerenciar saída
        if self.position:
            self._manage_exit(current_price)
        else:
            # Sem posição, avaliar entrada
            self._evaluate_entry(current_price)
    
    def _evaluate_entry(self, current_price):
        """Avaliar sinais de entrada."""
        buy_signals = 0
        
        # Signal 1: RSI oversold (mean reversion)
        if self.rsi[0] < self.params.rsi_oversold:
            buy_signals += 1
            self.log(f"✓ RSI oversold: {self.rsi[0]:.1f}")
        
        # Signal 2: Price below lower Bollinger Band
        if current_price < self.bb.lines.bot[0]:
            buy_signals += 1
            deviation_pct = ((current_price / self.bb.lines.bot[0]) - 1) * 100
            self.log(f"✓ Below BB lower: {deviation_pct:.1f}%")
        
        # Signal 3: MACD histogram positive (momentum)
        macd_hist = self.macd.macd[0] - self.macd.signal[0]
        if macd_hist > 0 or (self.macd.macd[0] > self.macd.macd[-1]):
            buy_signals += 1
            self.log(f"✓ MACD momentum: {macd_hist:.2f}")
        
        # Signal 4: High volume
        if self.data.volume[0] > self.volume_sma[0] * self.params.volume_threshold:
            buy_signals += 1
            vol_ratio = self.data.volume[0] / self.volume_sma[0]
            self.log(f"✓ Volume spike: {vol_ratio:.1f}x")
        
        # Signal 5: EMA trend (optional)
        if self.ema_fast[0] > self.ema_slow[0]:
            buy_signals += 1
            self.log(f"✓ EMA uptrend")
        
        # Execute buy if minimum signals met
        if buy_signals >= self.params.min_signals_buy:
            size = self._calculate_position_size(current_price)
            self.buy(size=size)
            self.entry_price = current_price
            self.highest_since_entry = current_price
            self.log(f"🟢 BUY {size:.4f} @ ${current_price:,.2f} ({buy_signals} signals)")
    
    def _manage_exit(self, current_price):
        """Gerenciar saída da posição."""
        if not self.entry_price:
            return
        
        # Update highest price since entry
        if current_price > self.highest_since_entry:
            self.highest_since_entry = current_price
        
        sell_signals = 0
        reasons = []
        
        # Calculate profit/loss
        pnl_pct = ((current_price / self.entry_price) - 1) * 100
        
        # Exit signal 1: Take profit target
        if pnl_pct >= self.params.take_profit_pct:
            sell_signals += 2  # Double weight for take profit
            reasons.append(f"Take Profit {pnl_pct:.1f}%")
        
        # Exit signal 2: Stop loss
        if pnl_pct <= -self.params.stop_loss_pct:
            sell_signals += 3  # Triple weight for stop loss (urgent)
            reasons.append(f"Stop Loss {pnl_pct:.1f}%")
        
        # Exit signal 3: Trailing stop from highest
        drawdown_from_high = ((current_price / self.highest_since_entry) - 1) * 100
        if drawdown_from_high <= -self.params.trailing_stop_pct:
            sell_signals += 2
            reasons.append(f"Trailing Stop {drawdown_from_high:.1f}%")
        
        # Exit signal 4: RSI overbought
        if self.rsi[0] > self.params.rsi_overbought:
            sell_signals += 1
            reasons.append(f"RSI {self.rsi[0]:.1f}")
        
        # Exit signal 5: Price above upper Bollinger
        if current_price > self.bb.lines.top[0]:
            sell_signals += 1
            reasons.append("Above BB")
        
        # Exit signal 6: MACD bearish crossover
        if self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] > self.macd.signal[-1]:
            sell_signals += 1
            reasons.append("MACD Bearish")
        
        # Execute sell if minimum signals met
        if sell_signals >= self.params.min_signals_sell:
            self.close()
            self.log(f"🔴 SELL @ ${current_price:,.2f} | P&L: {pnl_pct:+.2f}% | Reasons: {', '.join(reasons)}")
            self.entry_price = None
            self.highest_since_entry = None
    
    def _calculate_position_size(self, price):
        """Calcular tamanho da posição baseado em ATR."""
        # Use ATR for dynamic position sizing
        # Mais volatilidade = posição menor
        cash = self.broker.get_cash()
        atr_pct = (self.atr[0] / price) * 100
        
        # Reduce position size if high volatility
        if atr_pct > 4.0:
            size_factor = 0.7
        elif atr_pct > 3.0:
            size_factor = 0.85
        else:
            size_factor = 1.0
        
        adjusted_position = self.params.position_size * size_factor
        size = (cash * adjusted_position) / price
        
        return size
    
    def notify_order(self, order):
        """Notificação de ordens."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"✓ BUY EXECUTED @ ${order.executed.price:,.2f}")
            elif order.issell():
                self.log(f"✓ SELL EXECUTED @ ${order.executed.price:,.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"⚠️ Order {order.Status[order.status]}")
