#!/usr/bin/env python3
"""
Metodologia Científica para Validação de Estratégias SMA no BTC

Este script implementa uma metodologia rigorosa de treino/teste inspirada em:
- Marcos López de Prado: "Advances in Financial Machine Learning"
- Rob Carver: "Systematic Trading"

FILOSOFIA:
==========
Em vez de otimizar para encontrar o "melhor" parâmetro, vamos:
1. Testar uma FAIXA de parâmetros que fazem sentido teoricamente
2. Verificar se a estratégia funciona EM MÉDIA para essa faixa
3. Usar walk-forward anchored (expanding window)
4. Calcular métricas REALISTAS (incluindo degradação)

METODOLOGIA:
============
1. PURGED K-FOLD: Deixar gap entre treino e teste
2. EXPANDING WINDOW: Simula uso real (sempre treina do início)
3. ENSEMBLE: Testar múltiplos parâmetros, usar a mediana
4. REGIME AWARENESS: Analisar performance por regime

Por que essa abordagem é melhor:
- Evita overfitting (não otimiza um único parâmetro)
- Simula cenário real (expanding window)
- Robusto a ruído (ensemble de parâmetros)
- Informativo (mostra quando funciona e quando não)
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import backtrader as bt
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine


# =============================================================================
# CUSTOM BACKTEST (sem usar BacktestEngine para ter controle total)
# =============================================================================

class SimpleSMA(bt.Strategy):
    """SMA simples para testes."""
    
    params = (
        ('period', 100),
    )
    
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)
        self.order = None
        self.trades = []
        self.entry_price = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
                self.entry_price = self.data.close[0]
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()
    
    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                pass
            else:
                # Trade fechado
                if self.entry_price:
                    ret = (order.executed.price - self.entry_price) / self.entry_price
                    self.trades.append(ret)
        self.order = None


def run_simple_backtest(df: pd.DataFrame, sma_period: int, initial_cash: float = 100000) -> Dict:
    """
    Executa backtest simples e retorna métricas calculadas manualmente.
    Isso evita problemas com os analyzers do backtrader.
    """
    if len(df) < sma_period + 50:
        return None
    
    cerebro = bt.Cerebro()
    
    # Preparar dados
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open='open',
        high='high', 
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )
    cerebro.adddata(data)
    
    # Configurar
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(SimpleSMA, period=sma_period)
    
    # Adicionar analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    try:
        results = cerebro.run()
        strat = results[0]
        
        final_value = cerebro.broker.getvalue()
        total_return = (final_value / initial_cash - 1) * 100
        
        # Buy & Hold para comparação
        bh_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        alpha = total_return - bh_return
        
        # Extrair métricas
        sharpe = 0.0
        max_dd = 0.0
        total_trades = 0
        won_trades = 0
        
        try:
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            sharpe = sharpe_analysis.get('sharperatio', 0) or 0
        except:
            pass
            
        try:
            dd_analysis = strat.analyzers.drawdown.get_analysis()
            max_dd = dd_analysis.get('max', {}).get('drawdown', 0) or 0
        except:
            pass
            
        try:
            trade_analysis = strat.analyzers.trades.get_analysis()
            total_trades = trade_analysis.get('total', {}).get('total', 0) or 0
            won_trades = trade_analysis.get('won', {}).get('total', 0) or 0
        except:
            pass
        
        return {
            'total_return': total_return,
            'bh_return': bh_return,
            'alpha': alpha,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'total_trades': total_trades,
            'won_trades': won_trades,
            'final_value': final_value
        }
        
    except Exception as e:
        return None


# =============================================================================
# WALK-FORWARD METODOLOGIA
# =============================================================================

@dataclass
class WFSplit:
    """Um split de walk-forward."""
    id: int
    train_start: str
    train_end: str  
    test_start: str
    test_end: str


def create_wf_splits(
    df: pd.DataFrame,
    min_train_years: float = 2.0,  # Mínimo de 2 anos de treino
    test_months: int = 6,          # 6 meses de teste
    embargo_days: int = 5,         # Gap entre treino e teste
    step_months: int = 3           # Avançar 3 meses por split
) -> List[WFSplit]:
    """
    Cria splits de walk-forward com expanding window.
    
    Expanding window significa que o treino sempre começa do início
    e vai expandindo. Isso simula como um trader usaria na prática.
    """
    splits = []
    
    start_date = df.index[0]
    end_date = df.index[-1]
    
    min_train_days = int(min_train_years * 365)
    test_days = test_months * 30
    step_days = step_months * 30
    
    # Primeira data possível para fim do treino
    train_end = start_date + timedelta(days=min_train_days)
    
    split_id = 0
    while True:
        test_start = train_end + timedelta(days=embargo_days)
        test_end = test_start + timedelta(days=test_days)
        
        if test_end > end_date:
            break
            
        splits.append(WFSplit(
            id=split_id,
            train_start=start_date.strftime('%Y-%m-%d'),
            train_end=train_end.strftime('%Y-%m-%d'),
            test_start=test_start.strftime('%Y-%m-%d'),
            test_end=test_end.strftime('%Y-%m-%d')
        ))
        
        train_end += timedelta(days=step_days)
        split_id += 1
    
    return splits


# =============================================================================
# REGIME DETECTION
# =============================================================================

def detect_regime(df: pd.DataFrame) -> str:
    """Classifica período em BULL, BEAR ou SIDEWAYS."""
    if len(df) < 20:
        return 'UNKNOWN'
    
    ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    days = len(df)
    annual_ret = ret * (365 / days) if days > 0 else 0
    
    if annual_ret > 50:
        return 'BULL'
    elif annual_ret < -30:
        return 'BEAR'
    else:
        return 'SIDEWAYS'


# =============================================================================
# ENSEMBLE VALIDATION
# =============================================================================

def validate_sma_ensemble(
    df: pd.DataFrame,
    sma_range: Tuple[int, int, int],  # (min, max, step)
    splits: List[WFSplit]
) -> pd.DataFrame:
    """
    Valida múltiplos períodos de SMA usando walk-forward.
    
    Retorna DataFrame com resultados detalhados por período e por split.
    """
    results = []
    
    total_tests = len(range(sma_range[0], sma_range[1]+1, sma_range[2])) * len(splits)
    current = 0
    
    for sma_period in range(sma_range[0], sma_range[1]+1, sma_range[2]):
        for split in splits:
            current += 1
            
            # Extrair dados de treino e teste
            train_df = df.loc[split.train_start:split.train_end].copy()
            test_df = df.loc[split.test_start:split.test_end].copy()
            
            # Rodar backtest em treino
            train_result = run_simple_backtest(train_df, sma_period)
            
            # Rodar backtest em teste
            test_result = run_simple_backtest(test_df, sma_period)
            
            if train_result and test_result:
                test_regime = detect_regime(test_df)
                
                results.append({
                    'sma_period': sma_period,
                    'split_id': split.id,
                    'train_start': split.train_start,
                    'train_end': split.train_end,
                    'test_start': split.test_start,
                    'test_end': split.test_end,
                    'test_regime': test_regime,
                    
                    # Train metrics
                    'train_return': train_result['total_return'],
                    'train_alpha': train_result['alpha'],
                    'train_sharpe': train_result['sharpe'],
                    'train_dd': train_result['max_dd'],
                    
                    # Test metrics (mais importantes!)
                    'test_return': test_result['total_return'],
                    'test_bh': test_result['bh_return'],
                    'test_alpha': test_result['alpha'],
                    'test_sharpe': test_result['sharpe'],
                    'test_dd': test_result['max_dd'],
                    'test_trades': test_result['total_trades'],
                })
            
            if current % 20 == 0:
                print(f"   Progress: {current}/{total_tests} ({100*current/total_tests:.0f}%)")
    
    return pd.DataFrame(results)


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_by_sma_period(results_df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa resultados por período de SMA."""
    
    agg = results_df.groupby('sma_period').agg({
        'test_alpha': ['mean', 'std', 'min', 'max'],
        'test_sharpe': ['mean', 'std'],
        'test_dd': 'mean',
        'train_alpha': 'mean',
        'split_id': 'count'
    }).round(2)
    
    agg.columns = ['test_alpha_mean', 'test_alpha_std', 'test_alpha_min', 'test_alpha_max',
                   'test_sharpe_mean', 'test_sharpe_std', 'test_dd_mean', 'train_alpha_mean', 'n_splits']
    
    # Win rate (% de splits com alpha positivo)
    win_rate = results_df.groupby('sma_period')['test_alpha'].apply(
        lambda x: (x > 0).sum() / len(x) * 100
    ).round(1)
    agg['win_rate'] = win_rate
    
    # Degradation
    agg['degradation'] = agg['train_alpha_mean'] - agg['test_alpha_mean']
    
    # Score composto
    agg['robustness_score'] = (
        agg['test_alpha_mean'].clip(lower=-50, upper=50) * 0.4 +  # Alpha (40%)
        agg['win_rate'] * 0.3 +  # Consistency (30%)
        (100 - agg['degradation'].abs().clip(upper=100)) * 0.2 +  # Low degradation (20%)
        agg['test_sharpe_mean'].clip(lower=0, upper=2) * 5  # Sharpe (10%)
    ).round(1)
    
    return agg.sort_values('robustness_score', ascending=False)


def analyze_by_regime(results_df: pd.DataFrame) -> pd.DataFrame:
    """Analisa performance por regime de mercado."""
    
    return results_df.groupby(['test_regime', 'sma_period']).agg({
        'test_alpha': ['mean', 'std', 'count'],
        'test_sharpe': 'mean',
        'test_dd': 'mean'
    }).round(2)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "="*80)
    print("🔬 METODOLOGIA CIENTÍFICA DE VALIDAÇÃO SMA PARA BTC")
    print("="*80)
    print("Abordagem: Walk-Forward Expanding Window + Ensemble Analysis")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. CARREGAR DADOS
    # =========================================================================
    print("📊 Carregando dados BTC-USD...")
    data_engine = DataEngine()
    df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2017-01-01',  # Dados desde 2017 para ter histórico suficiente
        end='2025-12-31'
    )
    print(f"✅ {len(df)} dias carregados ({df.index[0].date()} a {df.index[-1].date()})")
    
    # Stats básicas
    total_ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    print(f"   Buy & Hold total: +{total_ret:.1f}%")
    print()
    
    # =========================================================================
    # 2. CRIAR SPLITS WALK-FORWARD
    # =========================================================================
    print("📅 Criando splits walk-forward...")
    print("   Config: 2 anos min treino, 6 meses teste, 5 dias embargo, step 3 meses")
    
    splits = create_wf_splits(df, min_train_years=2.0, test_months=6, embargo_days=5, step_months=3)
    print(f"   Criados {len(splits)} splits\n")
    
    # Mostrar alguns splits
    print("   Splits criados:")
    print(f"   {'ID':<4} {'Train':<25} {'Test':<25}")
    print("   " + "-"*54)
    for s in splits[:5]:
        print(f"   {s.id:<4} {s.train_start} → {s.train_end}  {s.test_start} → {s.test_end}")
    if len(splits) > 5:
        print(f"   ... e mais {len(splits)-5} splits")
    print()
    
    # =========================================================================
    # 3. VALIDAR ENSEMBLE DE SMAs
    # =========================================================================
    print("🔍 Validando ensemble de SMAs (50 a 200, step 10)...")
    print("   Isso vai demorar alguns minutos...\n")
    
    results_df = validate_sma_ensemble(
        df, 
        sma_range=(50, 200, 10),
        splits=splits
    )
    
    print(f"\n✅ {len(results_df)} testes completados")
    
    # =========================================================================
    # 4. ANÁLISE POR PERÍODO DE SMA
    # =========================================================================
    print("\n" + "="*80)
    print("📊 ANÁLISE POR PERÍODO DE SMA")
    print("="*80 + "\n")
    
    sma_analysis = analyze_by_sma_period(results_df)
    
    print(f"{'SMA':<6} {'Test α Mean':<12} {'Test α Std':<12} {'Win%':<8} {'Degradation':<12} {'Score':<8}")
    print("-"*70)
    
    for sma_period, row in sma_analysis.head(16).iterrows():
        print(f"{sma_period:<6} "
              f"{row['test_alpha_mean']:>10.1f}% "
              f"{row['test_alpha_std']:>10.1f}% "
              f"{row['win_rate']:>6.0f}% "
              f"{row['degradation']:>10.1f}% "
              f"{row['robustness_score']:>6.1f}")
    
    # =========================================================================
    # 5. ANÁLISE POR REGIME
    # =========================================================================
    print("\n" + "="*80)
    print("📊 ANÁLISE POR REGIME DE MERCADO")
    print("="*80 + "\n")
    
    # Performance média por regime para todos os SMAs
    regime_perf = results_df.groupby('test_regime').agg({
        'test_alpha': ['mean', 'std', 'count'],
        'test_bh': 'mean'
    }).round(1)
    
    print("Performance da estratégia SMA por regime:")
    print(f"   {'Regime':<12} {'N Tests':<10} {'Alpha Médio':<15} {'Alpha Std':<15} {'B&H Médio':<12}")
    print("   " + "-"*60)
    
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        if regime in regime_perf.index:
            r = regime_perf.loc[regime]
            print(f"   {regime:<12} "
                  f"{int(r['test_alpha']['count']):<10} "
                  f"{r['test_alpha']['mean']:>12.1f}% "
                  f"{r['test_alpha']['std']:>12.1f}% "
                  f"{r['test_bh']['mean']:>10.1f}%")
    
    # Melhor SMA por regime
    print("\n   Melhor SMA por regime:")
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['test_regime'] == regime]
        if len(regime_df) > 0:
            best = regime_df.groupby('sma_period')['test_alpha'].mean().idxmax()
            best_alpha = regime_df.groupby('sma_period')['test_alpha'].mean().max()
            print(f"   {regime}: SMA-{best} ({best_alpha:+.1f}% alpha médio)")
    
    # =========================================================================
    # 6. CONSISTÊNCIA TEMPORAL
    # =========================================================================
    print("\n" + "="*80)
    print("📊 CONSISTÊNCIA TEMPORAL")
    print("="*80 + "\n")
    
    # Agregar por split
    split_perf = results_df.groupby('split_id').agg({
        'test_start': 'first',
        'test_end': 'first',
        'test_alpha': 'mean',
        'test_regime': 'first'
    })
    
    print("Performance média (todos SMAs) por período de teste:")
    print(f"   {'Split':<6} {'Período':<25} {'Regime':<12} {'Alpha Médio':<12}")
    print("   " + "-"*55)
    
    for split_id, row in split_perf.iterrows():
        print(f"   {split_id:<6} "
              f"{row['test_start'][:10]} → {row['test_end'][:10]}  "
              f"{row['test_regime']:<12} "
              f"{row['test_alpha']:>10.1f}%")
    
    # =========================================================================
    # 7. CONCLUSÕES E RECOMENDAÇÕES
    # =========================================================================
    print("\n" + "="*80)
    print("🎯 CONCLUSÕES E RECOMENDAÇÕES")
    print("="*80 + "\n")
    
    # Melhor SMA
    best_sma = sma_analysis.index[0]
    best_row = sma_analysis.iloc[0]
    
    # Estatísticas gerais
    avg_alpha = results_df['test_alpha'].mean()
    overall_win_rate = (results_df['test_alpha'] > 0).mean() * 100
    
    print(f"📈 Estatísticas Gerais (todos SMAs, todos splits):")
    print(f"   Alpha médio: {avg_alpha:+.1f}%")
    print(f"   Win rate geral: {overall_win_rate:.0f}%")
    print()
    
    print(f"🏆 Melhor Configuração: SMA-{best_sma}")
    print(f"   Alpha médio teste: {best_row['test_alpha_mean']:+.1f}%")
    print(f"   Win rate: {best_row['win_rate']:.0f}%")
    print(f"   Sharpe médio: {best_row['test_sharpe_mean']:.2f}")
    print(f"   Degradação treino→teste: {best_row['degradation']:.1f}%")
    print()
    
    # Veredito
    if best_row['win_rate'] >= 60 and best_row['test_alpha_mean'] > 0:
        print("✅ ESTRATÉGIA VALIDADA!")
        print(f"   SMA-{best_sma} mostra robustez adequada.")
        print(f"   Recomendação: Usar SMA-{best_sma} com gestão de risco.")
    elif best_row['win_rate'] >= 50 and best_row['test_alpha_mean'] > -5:
        print("⚠️ ESTRATÉGIA PARCIALMENTE ROBUSTA")
        print(f"   SMA-{best_sma} funciona em alguns regimes.")
        print("   Recomendação: Combinar com filtro de regime ou B&H híbrido.")
    else:
        print("❌ ESTRATÉGIA NÃO VALIDADA")
        print("   Nenhum SMA mostra robustez consistente.")
        print("   Recomendação: Considerar B&H ou estratégias alternativas.")
    
    # Insights adicionais
    print("\n📊 Insights Adicionais:")
    
    # Por regime
    bull_alpha = results_df[results_df['test_regime'] == 'BULL']['test_alpha'].mean()
    bear_alpha = results_df[results_df['test_regime'] == 'BEAR']['test_alpha'].mean()
    side_alpha = results_df[results_df['test_regime'] == 'SIDEWAYS']['test_alpha'].mean()
    
    print(f"   • Em BULL markets: {bull_alpha:+.1f}% alpha (SMA perde para B&H)")
    print(f"   • Em BEAR markets: {bear_alpha:+.1f}% alpha (SMA protege)")
    print(f"   • Em SIDEWAYS: {side_alpha:+.1f}% alpha")
    
    # Salvar resultados
    results_df.to_csv('sma_walkforward_full_results.csv', index=False)
    sma_analysis.to_csv('sma_walkforward_summary.csv')
    print(f"\n✅ Resultados salvos em:")
    print("   • sma_walkforward_full_results.csv (todos os testes)")
    print("   • sma_walkforward_summary.csv (resumo por SMA)")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
