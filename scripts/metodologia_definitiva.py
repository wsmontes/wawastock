#!/usr/bin/env python3
"""
Metodologia Definitiva de Treino/Teste para BTC

Este script implementa a metodologia recomendada baseada na análise completa:

CONCLUSÃO DA ANÁLISE:
=====================
- SMA NÃO funciona como estratégia primária para BTC
- SMA FUNCIONA como proteção em bear markets (+28% alpha)
- SMA PREJUDICA em bull markets (-33% alpha)

RECOMENDAÇÃO FINAL:
===================
1. Use B&H como estratégia base
2. Adicione detecção de regime
3. Ative proteção SMA apenas em bear markets

Este script demonstra como implementar e validar isso corretamente.
"""

import sys
import os
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import timedelta
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine


# =============================================================================
# REGIME DETECTOR
# =============================================================================

class RegimeDetector:
    """
    Detecta regime de mercado em tempo real.
    
    Regimes:
    - BULL: Tendência forte de alta (trend > 5%, ret60 > 10%)
    - BEAR: Tendência de baixa (trend < -10% OU ret60 < -20%)
    - SIDEWAYS: Sem tendência clara
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._calculate_indicators()
    
    def _calculate_indicators(self):
        """Calcula indicadores para detecção de regime."""
        self.df['sma200'] = self.df['close'].rolling(200).mean()
        self.df['trend'] = (self.df['close'] / self.df['sma200'] - 1) * 100
        self.df['ret60'] = self.df['close'].pct_change(60) * 100
    
    def get_regime(self, date) -> str:
        """Retorna regime para uma data específica."""
        if date not in self.df.index:
            return 'UNKNOWN'
        
        row = self.df.loc[date]
        trend = row['trend']
        ret60 = row['ret60']
        
        if pd.isna(trend) or pd.isna(ret60):
            return 'UNKNOWN'
        
        if trend > 5 and ret60 > 10:
            return 'BULL'
        elif trend < -10 or ret60 < -20:
            return 'BEAR'
        return 'SIDEWAYS'
    
    def classify_period(self, start_date, end_date) -> str:
        """Classifica um período pelo regime dominante."""
        period_df = self.df.loc[start_date:end_date]
        if len(period_df) < 20:
            return 'UNKNOWN'
        
        ret = (period_df['close'].iloc[-1] / period_df['close'].iloc[0] - 1) * 100
        days = len(period_df)
        annual_ret = ret * (365 / days) if days > 0 else 0
        
        if annual_ret > 50:
            return 'BULL'
        elif annual_ret < -30:
            return 'BEAR'
        return 'SIDEWAYS'


# =============================================================================
# ESTRATÉGIA ADAPTATIVA POR REGIME
# =============================================================================

class AdaptiveRegimeStrategy(bt.Strategy):
    """
    Estratégia que adapta comportamento ao regime.
    
    Implementa a recomendação:
    - BULL: B&H (sempre comprado)
    - BEAR: SMA como proteção
    - SIDEWAYS: SMA conservador
    """
    
    params = (
        ('sma_protection', 100),   # SMA para proteção em bear
        ('sma_trend', 200),        # SMA para detectar tendência
        ('regime_lookback', 60),   # Lookback para ret60
        ('warmup_bars', 0),        # Barras de warmup no DataFrame original (antes de indicadores)
    )
    
    def __init__(self):
        self.sma_prot = bt.indicators.SMA(self.data.close, period=self.params.sma_protection)
        self.sma_trend = bt.indicators.SMA(self.data.close, period=self.params.sma_trend)
        self.order = None
        self.regime_history = []
        # Ajustar warmup para compensar as barras consumidas pelo indicador
        # O backtrader só começa a chamar next() após sma_trend (200) barras
        self.adjusted_warmup = max(0, self.params.warmup_bars - self.params.sma_trend + 1)
        
    def get_regime(self):
        """Detecta regime atual."""
        if len(self.data) < max(self.params.sma_trend, self.params.regime_lookback):
            return 'UNKNOWN'
        
        trend = (self.data.close[0] / self.sma_trend[0] - 1) * 100
        
        if len(self.data) >= self.params.regime_lookback:
            ret60 = (self.data.close[0] / self.data.close[-self.params.regime_lookback] - 1) * 100
        else:
            ret60 = 0
        
        if trend > 5 and ret60 > 10:
            return 'BULL'
        elif trend < -10 or ret60 < -20:
            return 'BEAR'
        return 'SIDEWAYS'
        
    def next(self):
        # len(self.data) é o número de barras processadas (após indicador estar pronto)
        current_bar = len(self.data)
        
        # Não operar durante warmup ajustado
        if current_bar <= self.adjusted_warmup:
            return
            
        if self.order:
            return
        
        regime = self.get_regime()
        self.regime_history.append(regime)
        
        if regime == 'UNKNOWN':
            return
        
        # BULL: Sempre comprado (B&H)
        if regime == 'BULL':
            if not self.position:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
        
        # BEAR: Usar SMA como proteção
        elif regime == 'BEAR':
            if not self.position:
                if self.data.close[0] > self.sma_prot[0]:
                    size = self.broker.getcash() * 0.95 / self.data.close[0]
                    self.order = self.buy(size=size)
            else:
                if self.data.close[0] < self.sma_prot[0]:
                    self.order = self.close()
        
        # SIDEWAYS: SMA conservador
        else:
            if not self.position:
                if self.data.close[0] > self.sma_prot[0]:
                    size = self.broker.getcash() * 0.95 / self.data.close[0]
                    self.order = self.buy(size=size)
            else:
                if self.data.close[0] < self.sma_prot[0]:
                    self.order = self.close()
    
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


class BuyAndHold(bt.Strategy):
    """Buy and Hold para comparação."""
    
    def __init__(self):
        self.bought = False
        
    def next(self):
        if not self.bought:
            size = self.broker.getcash() * 0.95 / self.data.close[0]
            self.buy(size=size)
            self.bought = True


class PureSMA(bt.Strategy):
    """SMA puro para comparação."""
    
    params = (
        ('period', 100),
        ('warmup_bars', 0),  # Barras de warmup no DataFrame original
    )
    
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)
        self.order = None
        # Ajustar warmup para compensar as barras consumidas pelo indicador
        self.adjusted_warmup = max(0, self.params.warmup_bars - self.params.period + 1)
        
    def next(self):
        current_bar = len(self.data)
        
        # Não operar durante warmup ajustado
        if current_bar <= self.adjusted_warmup:
            return
            
        if self.order:
            return
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()
    
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


# =============================================================================
# WALK-FORWARD ENGINE
# =============================================================================

class WalkForwardValidator:
    """
    Validador Walk-Forward com configuração recomendada.
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        min_train_days: int = 730,   # 2 anos
        test_days: int = 180,        # 6 meses
        embargo_days: int = 5,
        step_days: int = 90          # 3 meses
    ):
        self.df = df.copy()
        if self.df.index.tz is not None:
            self.df.index = self.df.index.tz_localize(None)
        
        self.min_train_days = min_train_days
        self.test_days = test_days
        self.embargo_days = embargo_days
        self.step_days = step_days
        
        self.regime_detector = RegimeDetector(self.df)
        self.splits = self._create_splits()
    
    def _create_splits(self) -> List[Dict]:
        """Cria splits walk-forward."""
        splits = []
        
        start = self.df.index[0]
        end = self.df.index[-1]
        train_end = start + timedelta(days=self.min_train_days)
        
        split_id = 0
        while True:
            test_start = train_end + timedelta(days=self.embargo_days)
            test_end = test_start + timedelta(days=self.test_days)
            
            if test_end > end:
                break
            
            train_df = self.df[self.df.index <= train_end]
            test_df = self.df[(self.df.index >= test_start) & (self.df.index <= test_end)]
            
            if len(train_df) > 0 and len(test_df) >= 100:
                regime = self.regime_detector.classify_period(test_start, test_end)
                
                splits.append({
                    'id': split_id,
                    'train_start': train_df.index[0],
                    'train_end': train_df.index[-1],
                    'test_start': test_df.index[0],
                    'test_end': test_df.index[-1],
                    'regime': regime
                })
                split_id += 1
            
            train_end += timedelta(days=self.step_days)
        
        return splits
    
    def run_backtest(self, df: pd.DataFrame, strategy_cls, **params) -> Dict:
        """Executa backtest."""
        df = df.copy()
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        cerebro = bt.Cerebro(stdstats=False)
        
        data = bt.feeds.PandasData(
            dataname=df[['open', 'high', 'low', 'close', 'volume']],
            datetime=None
        )
        cerebro.adddata(data)
        
        cerebro.broker.setcash(100000)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.addstrategy(strategy_cls, **params)
        
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
        
        try:
            results = cerebro.run()
            strat = results[0]
            
            final = cerebro.broker.getvalue()
            ret = (final / 100000 - 1) * 100
            
            try:
                max_dd = strat.analyzers.dd.get_analysis()['max']['drawdown'] or 0
            except:
                max_dd = 0
            
            return {'return': ret, 'max_dd': max_dd}
        except:
            return None
    
    def run_backtest_with_warmup(self, full_df: pd.DataFrame, test_df: pd.DataFrame, 
                                  strategy_cls, **params) -> Dict:
        """
        Executa backtest com período de warmup para indicadores.
        O full_df contém warmup + test, o test_df é usado para calcular o período real.
        A estratégia só vai operar a partir do início do test_df.
        """
        full_df = full_df.copy()
        if full_df.index.tz is not None:
            full_df.index = full_df.index.tz_localize(None)
        
        test_start = test_df.index[0]
        if test_start.tzinfo is not None:
            test_start = test_start.tz_localize(None)
        
        # Calcular em qual barra começa o período de teste
        warmup_bars = len(full_df[full_df.index < test_start])
        
        cerebro = bt.Cerebro(stdstats=False)
        
        data = bt.feeds.PandasData(
            dataname=full_df[['open', 'high', 'low', 'close', 'volume']],
            datetime=None
        )
        cerebro.adddata(data)
        
        cerebro.broker.setcash(100000)
        cerebro.broker.setcommission(commission=0.001)
        
        # Passar warmup_bars para a estratégia não operar durante warmup
        cerebro.addstrategy(strategy_cls, warmup_bars=warmup_bars, **params)
        
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
        
        try:
            results = cerebro.run()
            strat = results[0]
            
            final = cerebro.broker.getvalue()
            ret = (final / 100000 - 1) * 100
            
            try:
                max_dd = strat.analyzers.dd.get_analysis()['max']['drawdown'] or 0
            except:
                max_dd = 0
            
            return {'return': ret, 'max_dd': max_dd}
        except Exception as e:
            print(f"      Backtest error: {e}")
            return None
    
    def validate(self) -> pd.DataFrame:
        """Executa validação completa."""
        results = []
        
        for split in self.splits:
            # CORREÇÃO: Incluir dados anteriores para warmup dos indicadores
            # O SMA-200 precisa de pelo menos 200 barras para calcular
            warmup_start = split['test_start'] - timedelta(days=250)  # 250 dias de warmup
            
            # Dados com warmup (para indicadores)
            full_df = self.df[(self.df.index >= warmup_start) & 
                              (self.df.index <= split['test_end'])].copy()
            
            # Dados apenas do período de teste (para B&H)
            test_df = self.df[(self.df.index >= split['test_start']) & 
                              (self.df.index <= split['test_end'])].copy()
            
            if len(test_df) < 100 or len(full_df) < 300:
                print(f"   Skip split {split['id']}: test={len(test_df)}, full={len(full_df)}")
                continue
            
            # Rodar estratégias com dados completos (inclui warmup)
            # Nota: Para comparação justa, usamos o mesmo período de teste
            adaptive_res = self.run_backtest_with_warmup(full_df, test_df, AdaptiveRegimeStrategy)
            bh_res = self.run_backtest(test_df, BuyAndHold)
            sma_res = self.run_backtest_with_warmup(full_df, test_df, PureSMA, period=100)
            
            if adaptive_res and bh_res and sma_res:
                results.append({
                    'split': split['id'],
                    'test_start': split['test_start'].strftime('%Y-%m-%d'),
                    'test_end': split['test_end'].strftime('%Y-%m-%d'),
                    'regime': split['regime'],
                    
                    'adaptive_return': adaptive_res['return'],
                    'adaptive_dd': adaptive_res['max_dd'],
                    'adaptive_alpha': adaptive_res['return'] - bh_res['return'],
                    
                    'sma_return': sma_res['return'],
                    'sma_dd': sma_res['max_dd'],
                    'sma_alpha': sma_res['return'] - bh_res['return'],
                    
                    'bh_return': bh_res['return'],
                    'bh_dd': bh_res['max_dd']
                })
        
        return pd.DataFrame(results)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "="*70)
    print("🎯 METODOLOGIA DEFINITIVA DE TREINO/TESTE PARA BTC")
    print("="*70)
    print("Comparando: B&H vs SMA Puro vs Adaptativo por Regime")
    print("="*70 + "\n")
    
    # Carregar dados
    print("📊 Carregando dados...")
    data_engine = DataEngine()
    df = data_engine.load_prices('BTC-USD', '2018-01-01', '2025-12-31')
    print(f"✅ {len(df)} dias carregados\n")
    
    # Criar validador
    print("📅 Configurando walk-forward...")
    print("   • Min treino: 2 anos")
    print("   • Teste: 6 meses")
    print("   • Embargo: 5 dias")
    print("   • Step: 3 meses")
    
    validator = WalkForwardValidator(df)
    print(f"   • {len(validator.splits)} splits criados\n")
    
    # Executar validação
    print("🔬 Executando validação walk-forward...\n")
    results_df = validator.validate()
    
    if len(results_df) == 0:
        print("❌ Nenhum resultado!")
        return
    
    # Análise
    print("="*70)
    print("📊 RESULTADOS COMPARATIVOS")
    print("="*70 + "\n")
    
    # Médias gerais
    print("Performance Média (todos os splits):")
    print(f"   {'Estratégia':<15} {'Return':<12} {'Alpha':<12} {'Max DD':<10}")
    print("   " + "-"*50)
    
    for strat, alpha_col in [('Adaptive', 'adaptive'), ('SMA-100', 'sma'), ('B&H', 'bh')]:
        avg_ret = results_df[f'{alpha_col}_return'].mean()
        avg_dd = results_df[f'{alpha_col}_dd'].mean()
        if alpha_col == 'bh':
            avg_alpha = 0
        else:
            avg_alpha = results_df[f'{alpha_col}_alpha'].mean()
        print(f"   {strat:<15} {avg_ret:>10.1f}% {avg_alpha:>10.1f}% {avg_dd:>8.1f}%")
    
    # Por regime
    print("\n\nPerformance por Regime:")
    
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['regime'] == regime]
        if len(regime_df) == 0:
            continue
        
        print(f"\n   {regime} ({len(regime_df)} períodos):")
        print(f"   {'Estratégia':<15} {'Return':<12} {'Alpha vs B&H':<15}")
        print("   " + "-"*45)
        
        for strat, col in [('Adaptive', 'adaptive'), ('SMA-100', 'sma'), ('B&H', 'bh')]:
            avg_ret = regime_df[f'{col}_return'].mean()
            if col == 'bh':
                print(f"   {strat:<15} {avg_ret:>10.1f}% {'(baseline)':<15}")
            else:
                avg_alpha = regime_df[f'{col}_alpha'].mean()
                print(f"   {strat:<15} {avg_ret:>10.1f}% {avg_alpha:>+13.1f}%")
    
    # Win rates
    print("\n\n📈 Win Rates (supera B&H):")
    for strat, col in [('Adaptive', 'adaptive'), ('SMA-100', 'sma')]:
        wins = (results_df[f'{col}_alpha'] > 0).sum()
        total = len(results_df)
        print(f"   {strat}: {wins}/{total} ({100*wins/total:.0f}%)")
    
    # Conclusão
    print("\n" + "="*70)
    print("🎯 CONCLUSÃO E RECOMENDAÇÃO")
    print("="*70 + "\n")
    
    adaptive_alpha = results_df['adaptive_alpha'].mean()
    sma_alpha = results_df['sma_alpha'].mean()
    adaptive_wins = (results_df['adaptive_alpha'] > 0).sum() / len(results_df) * 100
    
    if adaptive_alpha > sma_alpha and adaptive_alpha > -5:
        print("✅ ESTRATÉGIA ADAPTATIVA É A MELHOR OPÇÃO!")
        print(f"   Alpha médio: {adaptive_alpha:+.1f}%")
        print(f"   Win rate: {adaptive_wins:.0f}%")
        print("\n   Regra: B&H em bulls, SMA em bears")
    else:
        print("⚠️ NENHUMA ESTRATÉGIA SUPERA B&H CONSISTENTEMENTE")
        print("\n   Recomendação: Use B&H com stop mental em quedas extremas")
    
    # Resumo por regime
    print("\n📊 Resumo da Análise:")
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['regime'] == regime]
        if len(regime_df) > 0:
            best_alpha = max(
                regime_df['adaptive_alpha'].mean(),
                regime_df['sma_alpha'].mean()
            )
            best_strat = 'Adaptive' if regime_df['adaptive_alpha'].mean() >= regime_df['sma_alpha'].mean() else 'SMA'
            print(f"   • {regime}: Melhor = {best_strat} ({best_alpha:+.1f}% alpha)")
    
    # Salvar
    results_df.to_csv('metodologia_definitiva_results.csv', index=False)
    print(f"\n✅ Resultados salvos em metodologia_definitiva_results.csv")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
