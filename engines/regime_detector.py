"""
RegimeDetector - Classificador de regime de mercado em tempo real

Usado pelo MetaStrategy para decidir qual especialista ativar.
"""

import pandas as pd


class RegimeDetector:
    """
    Detecta o regime de mercado atual baseado em janela de dados recente.
    
    Regimes identificados:
    - STRONG_BULL_RUN: Bull run forte com estrutura sólida
    - STEADY_BULL: Tendência de alta estável
    - BULL_CORRECTION: Correção em mercado de alta
    - RECOVERY: Recuperação após queda
    - CRASH: Queda acentuada
    - BEAR_MARKET: Mercado de baixa gradual
    - WEAKENING_BULL: Perda de força em tendência de alta
    - CHOPPY_SIDEWAYS: Lateral com alta volatilidade
    - CALM_SIDEWAYS: Lateral com baixa volatilidade
    - UNDEFINED: Não se encaixa em nenhum padrão
    """
    
    def __init__(self, window=60, **thresholds):
        """
        Args:
            window: Janela de dias para análise (default 60)
            **thresholds: Thresholds configuráveis para classificação
        """
        self.window = window
        
        # Thresholds para classificação (permitir customização)
        self.strong_bull_ret20 = thresholds.get('strong_bull_ret20', 15.0)
        self.strong_bull_ret60 = thresholds.get('strong_bull_ret60', 30.0)
        self.bull_correction_ret60 = thresholds.get('bull_correction_ret60', 20.0)
        self.bull_correction_ret20_max = thresholds.get('bull_correction_ret20_max', 5.0)
        self.steady_bull_ret20 = thresholds.get('steady_bull_ret20', 5.0)
        self.steady_bull_ret60 = thresholds.get('steady_bull_ret60', 10.0)
        self.recovery_ret20 = thresholds.get('recovery_ret20', 10.0)
        self.sideways_threshold = thresholds.get('sideways_threshold', 10.0)
        self.sideways_vol_threshold = thresholds.get('sideways_vol_threshold', 4.0)
        self.crash_threshold = thresholds.get('crash_threshold', -15.0)
        self.bear_ret20 = thresholds.get('bear_ret20', -5.0)
        self.bear_ret60 = thresholds.get('bear_ret60', -10.0)
    
    def detect(self, data_slice):
        """
        Detectar regime atual baseado em slice de dados recentes.
        
        Args:
            data_slice: DataFrame com pelo menos window dias de dados
                       Deve conter: close, sma20, sma50, sma200
        
        Returns:
            str: Nome do regime detectado
        """
        if len(data_slice) < self.window:
            return 'INSUFFICIENT_DATA'
        
        # Pegar últimos window dias
        recent = data_slice.tail(self.window).copy()
        
        # Calcular métricas
        recent['return_5d'] = recent['close'].pct_change(5) * 100
        recent['return_20d'] = recent['close'].pct_change(20) * 100
        
        # Pegar valores mais recentes
        latest = recent.iloc[-1]
        
        ret_5d = latest['return_5d'] if 'return_5d' in latest and not pd.isna(latest['return_5d']) else 0
        ret_20d = latest['return_20d'] if 'return_20d' in latest and not pd.isna(latest['return_20d']) else 0
        
        # Calcular return de 60 dias
        if len(recent) >= 60:
            ret_60d = ((recent['close'].iloc[-1] - recent['close'].iloc[-60]) / recent['close'].iloc[-60]) * 100
        else:
            ret_60d = ret_20d * 3  # Aproximação
        
        # Volatilidade
        vol_20d = recent['close'].pct_change().rolling(20).std().iloc[-1] * 100
        
        # Preços e SMAs
        price = latest['close']
        sma20 = latest.get('sma20', price)
        sma50 = latest.get('sma50', price)
        sma200 = latest.get('sma200', price)
        
        # Estrutura de tendência
        trend_up = sma20 > sma50 > sma200 if all([sma20, sma50, sma200]) else False
        trend_down = sma20 < sma50 < sma200 if all([sma20, sma50, sma200]) else False
        
        # CLASSIFICAÇÃO
        
        # REGIME 1: Bull Run Forte
        if ret_20d > self.strong_bull_ret20 and ret_60d > self.strong_bull_ret60 and trend_up:
            return 'STRONG_BULL_RUN'
        
        # REGIME 2: Correção em Bull Market
        elif ret_60d > self.bull_correction_ret60 and ret_20d < self.bull_correction_ret20_max and trend_up:
            return 'BULL_CORRECTION'
        
        # REGIME 3: Tendência de alta estável
        elif ret_20d > self.steady_bull_ret20 and ret_60d > self.steady_bull_ret60 and trend_up:
            return 'STEADY_BULL'
        
        # REGIME 4: Recuperação
        elif ret_20d > self.recovery_ret20 and ret_60d < 0 and price > sma50:
            return 'RECOVERY'
        
        # REGIME 5: Lateral calmo
        elif abs(ret_20d) < self.sideways_threshold and vol_20d <= self.sideways_vol_threshold:
            return 'CALM_SIDEWAYS'
        
        # REGIME 6: Lateral com volatilidade
        elif abs(ret_20d) < self.sideways_threshold and vol_20d > self.sideways_vol_threshold:
            return 'CHOPPY_SIDEWAYS'
        
        # REGIME 7: Crash
        elif ret_20d < self.crash_threshold and trend_down:
            return 'CRASH'
        
        # REGIME 8: Bear market
        elif ret_20d < self.bear_ret20 and ret_60d < self.bear_ret60 and trend_down:
            return 'BEAR_MARKET'
        
        # REGIME 9: Enfraquecimento em bull
        elif ret_20d < 0 and ret_60d > self.steady_bull_ret60 and not trend_down:
            return 'WEAKENING_BULL'
        
        else:
            return 'UNDEFINED'
    
    def get_regime_description(self, regime):
        """Retornar descrição do regime."""
        descriptions = {
            'STRONG_BULL_RUN': 'Bull run forte - maximizar ganhos',
            'STEADY_BULL': 'Alta estável - seguir tendência',
            'BULL_CORRECTION': 'Correção em bull - aguardar ou comprar dip',
            'RECOVERY': 'Recuperação - entrar agressivamente',
            'CRASH': 'Crash - proteger capital',
            'BEAR_MARKET': 'Bear market - ficar fora',
            'WEAKENING_BULL': 'Bull enfraquecendo - cautela',
            'CHOPPY_SIDEWAYS': 'Lateral volátil - evitar overtrading',
            'CALM_SIDEWAYS': 'Lateral calmo - range trading ou esperar',
            'UNDEFINED': 'Indefinido - usar estratégia padrão',
            'INSUFFICIENT_DATA': 'Dados insuficientes'
        }
        return descriptions.get(regime, 'Desconhecido')
