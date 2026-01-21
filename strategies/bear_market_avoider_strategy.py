"""
Bear Market Avoider Strategy

EVIDÊNCIA: Regimes BEAR (MODERATE + STRONG) geraram -308.12% em 296 dias
OBJETIVO: Evitar exposição durante quedas prolongadas que destroem capital

FILOSOFIA:
- Trial 77 não evita bears eficientemente (toma stops)
- BEAR markets representam 13.7% do tempo mas causam 27% da perda potencial
- Esta estratégia PROTEGE capital, não busca lucro

LÓGICA:
1. Detectar início de bear market (return_20d < -10%)
2. Confirmar quebra de estrutura (close < sma50)
3. FICAR FORA até recuperação clara
4. Reconhecer bear markets ANTES de perdas grandes

DIFERENCIAL vs Trial 77:
- Trial 77: Usa stops apertados, toma perdas repetidas
- Bear Avoider: Fica fora proativamente, capital preservado
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BearMarketAvoiderStrategy(BaseStrategy):
    """
    Estratégia focada em evitar bear markets (-10% em 20 dias).
    Complementa Trial 77 preservando capital em quedas prolongadas.
    
    IMPORTANTE: Esta estratégia é majoritariamente DEFENSIVA.
    Lucro vem de EVITAR perdas, não de trades ganhos.
    """
    
    params = (
        # Detecção de bear market
        ('bear_threshold', -10.0),     # Return 20d para considerar bear
        ('recovery_threshold', 5.0),   # Return 20d para considerar recuperação
        
        # Confirmação de quebra de estrutura
        ('sma_mid', 50),
        ('sma_slow', 200),
        
        # Entry conservador (apenas em recuperações claras)
        ('entry_return_min', 3.0),     # Mínimo return 5d para entry
        ('entry_volume_mult', 1.2),    # Volume acima da média
        
        # Risk management (stops apertados, pois estratégia é defensiva)
        ('stop_loss_pct', 8.0),
        ('take_profit_pct', 12.0),     # Take profit rápido
        
        # Position sizing conservador
        ('position_size', 0.70),       # 70% do capital (menos agressivo)
    )
    
    def __init__(self):
        """Inicializar indicadores."""
        super().__init__()
        
        # SMAs para estrutura de mercado
        self.sma_mid = bt.indicators.SMA(self.data.close, period=self.params.sma_mid)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.sma_slow)
        
        # Retornos
        self.return_5d = (self.data.close / self.data.close(-5) - 1) * 100
        self.return_20d = (self.data.close / self.data.close(-20) - 1) * 100
        
        # Volume
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=20)
        
        # Tracking
        self.entry_price = None
        self.in_bear_market = False
        self.bear_start_date = None
    
    def next(self):
        """Lógica de trading executada a cada barra."""
        # Verificar se temos dados suficientes
        if len(self.data) < self.params.sma_slow:
            return
        
        current_price = self.data.close[0]
        
        # Detectar bear market (sempre, esteja ou não em posição)
        bear_detected = (
            self.return_20d[0] < self.params.bear_threshold and
            current_price < self.sma_mid[0]
        )
        
        if bear_detected and not self.in_bear_market:
            self.in_bear_market = True
            self.bear_start_date = self.data.datetime.date(0)
            self.log(
                f"🐻 BEAR MARKET DETECTED @ ${current_price:.2f} | "
                f"Return 20d: {self.return_20d[0]:.1f}% | "
                f"Price < SMA50: ${self.sma_mid[0]:.2f}"
            )
        
        # Detectar recuperação
        if self.in_bear_market and self.return_20d[0] > self.params.recovery_threshold:
            days_in_bear = (self.data.datetime.date(0) - self.bear_start_date).days if self.bear_start_date else 0
            self.log(
                f"🌱 RECOVERY DETECTED @ ${current_price:.2f} | "
                f"Return 20d: {self.return_20d[0]:.1f}% | "
                f"Bear duration: {days_in_bear} days"
            )
            self.in_bear_market = False
        
        # Se não temos posição
        if not self.position:
            self.entry_price = None
            
            # NUNCA entrar durante bear market
            if self.in_bear_market:
                return
            
            # CONDIÇÃO DE ENTRADA: Recuperação confirmada pós-bear
            recovery_confirmed = self.return_20d[0] > self.params.recovery_threshold
            short_term_positive = self.return_5d[0] > self.params.entry_return_min
            above_mid_term = current_price > self.sma_mid[0]
            volume_confirmation = self.data.volume[0] > self.volume_sma[0] * self.params.entry_volume_mult
            
            # Apenas entrar se TODAS as condições forem atendidas
            if recovery_confirmed and short_term_positive and above_mid_term and volume_confirmation:
                size = (self.broker.get_cash() * self.params.position_size) / current_price
                
                if size > 0:
                    self.buy(size=size)
                    self.entry_price = current_price
                    
                    self.log(
                        f"✅ ENTRY @ ${current_price:.2f} | "
                        f"Return 20d: {self.return_20d[0]:.1f}% | "
                        f"Return 5d: {self.return_5d[0]:.1f}% | "
                        f"Above SMA50: ${self.sma_mid[0]:.2f}"
                    )
        
        # Se temos posição
        else:
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            
            # CONDIÇÕES DE SAÍDA
            exit_signal = None
            
            # 1. PRIORIDADE MÁXIMA: Bear market detectado
            if bear_detected:
                exit_signal = "BEAR_DETECTED"
            
            # 2. Stop loss
            elif pnl_pct < -self.params.stop_loss_pct:
                exit_signal = "STOP_LOSS"
            
            # 3. Take profit (conservador)
            elif pnl_pct > self.params.take_profit_pct:
                exit_signal = "TAKE_PROFIT"
            
            # 4. Quebra de estrutura
            elif current_price < self.sma_mid[0]:
                exit_signal = "STRUCTURE_BREAK"
            
            # Executar saída se houver sinal
            if exit_signal:
                self.close()
                self.log(
                    f"📤 EXIT: {exit_signal} @ ${current_price:.2f} | "
                    f"P&L: {pnl_pct:+.2f}% | "
                    f"Return 20d: {self.return_20d[0]:.1f}%"
                )
                
                self.entry_price = None
