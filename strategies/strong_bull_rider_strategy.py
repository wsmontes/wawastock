"""
Strong Bull Rider Strategy

EVIDÊNCIA: Regime STRONG_BULL gerou +337.26% em 267 dias (+1.263%/dia, eficiência 0.387)
OBJETIVO: Capturar e surfar bull runs fortes que Trial 77 perdeu por baixa exposição

FILOSOFIA:
- Trial 77 perdeu oportunidades por ter apenas 10.2% de exposição
- STRONG_BULL ocorre 12.4% do tempo mas gera 29.5% do ganho total do B&H
- Esta estratégia COMPLEMENTA Trial 77, não compete

LÓGICA:
1. Detectar início de bull run forte (return_20d > 15%)
2. Confirmar tendência (close > sma20 > sma50)
3. MANTER POSIÇÃO enquanto bull run continuar
4. Sair apenas quando tendência enfraquecer

DIFERENCIAL vs Trial 77:
- Trial 77: 19 parâmetros, sinais múltiplos, baixa exposição
- Strong Bull Rider: Foco único em bull runs, alta exposição, mínimas saídas
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class StrongBullRiderStrategy(BaseStrategy):
    """
    Estratégia focada em capturar bull runs fortes (>15% em 20 dias).
    Complementa Trial 77 aumentando exposição em períodos de alta forte.
    """
    
    params = (
        # Detecção de bull run
        ('bull_threshold', 15.0),     # Return 20d para considerar bull forte
        ('bull_min_threshold', 10.0),  # Return 20d mínimo para manter posição
        
        # Confirmação de tendência
        ('sma_fast', 20),
        ('sma_mid', 50),
        ('sma_slow', 200),
        
        # Risk management
        ('stop_loss_pct', 12.0),       # Stop mais amplo para bull run
        ('trailing_stop_pct', 15.0),   # Trailing após lucro significativo
        ('trailing_activation', 25.0), # Ativar trailing em +25%
        
        # Position sizing
        ('position_size', 0.95),       # 95% do capital (quase all-in)
    )
    
    def __init__(self):
        """Inicializar indicadores."""
        super().__init__()
        
        # SMAs para tendência
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.sma_fast)
        self.sma_mid = bt.indicators.SMA(self.data.close, period=self.params.sma_mid)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.sma_slow)
        
        # Retorno de 20 dias (aproximado)
        self.return_20d = (self.data.close / self.data.close(-20) - 1) * 100
        
        # Volatilidade
        self.volatility = bt.indicators.StdDev(
            self.data.close,
            period=20,
            safepow=True
        )
        
        # Tracking
        self.entry_price = None
        self.highest_price = None
        self.in_strong_bull = False
    
    def next(self):
        """Lógica de trading executada a cada barra."""
        # Verificar se temos dados suficientes
        if len(self.data) < self.params.sma_slow:
            return
        
        current_price = self.data.close[0]
        
        # Se não temos posição
        if not self.position:
            self.in_strong_bull = False
            self.entry_price = None
            self.highest_price = None
            
            # CONDIÇÃO DE ENTRADA: Bull run forte detectado
            bull_detected = self.return_20d[0] > self.params.bull_threshold
            trend_confirmed = (current_price > self.sma_fast[0] > self.sma_mid[0])
            above_long_term = current_price > self.sma_slow[0]
            
            if bull_detected and trend_confirmed and above_long_term:
                # Calcular tamanho da posição
                size = (self.broker.get_cash() * self.params.position_size) / current_price
                
                if size > 0:
                    self.buy(size=size)
                    self.entry_price = current_price
                    self.highest_price = current_price
                    self.in_strong_bull = True
                    
                    self.log(
                        f"🚀 BULL RUN DETECTED @ ${current_price:.2f} | "
                        f"Return 20d: {self.return_20d[0]:.1f}% | "
                        f"SMA20: ${self.sma_fast[0]:.2f} | SMA50: ${self.sma_mid[0]:.2f}"
                    )
        
        # Se temos posição
        else:
            # Atualizar highest price para trailing stop
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            # Calcular P&L atual
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            
            # CONDIÇÕES DE SAÍDA
            exit_signal = None
            
            # 1. Bull run enfraqueceu (return_20d caiu abaixo do mínimo)
            if self.return_20d[0] < self.params.bull_min_threshold:
                exit_signal = "BULL_WEAKENED"
            
            # 2. Quebra de tendência (preço abaixo de SMA20)
            elif current_price < self.sma_fast[0]:
                exit_signal = "TREND_BREAK"
            
            # 3. Stop loss
            elif pnl_pct < -self.params.stop_loss_pct:
                exit_signal = "STOP_LOSS"
            
            # 4. Trailing stop (apenas se lucro > trailing_activation)
            elif pnl_pct > self.params.trailing_activation:
                drawdown_from_peak = ((current_price - self.highest_price) / self.highest_price) * 100
                if drawdown_from_peak < -self.params.trailing_stop_pct:
                    exit_signal = "TRAILING_STOP"
            
            # Executar saída se houver sinal
            if exit_signal:
                self.close()
                self.log(
                    f"📤 EXIT: {exit_signal} @ ${current_price:.2f} | "
                    f"P&L: {pnl_pct:+.2f}% | "
                    f"Return 20d: {self.return_20d[0]:.1f}%"
                )
                
                self.in_strong_bull = False
                self.entry_price = None
                self.highest_price = None
            
            # Log de status (a cada 5 dias)
            elif len(self.data) % 5 == 0:
                pass  # Skip frequent logging to avoid noise
