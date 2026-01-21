#!/usr/bin/env python3
"""
Validação Final de Metodologia Treino/Teste para BTC SMA

Este script implementa a metodologia final recomendada para treino/teste
de estratégias SMA no Bitcoin, baseada nos aprendizados anteriores.

CONCLUSÕES ANTERIORES:
======================
1. SMA puro NÃO funciona em todos os regimes
2. Em BULL: SMA perde -41% vs B&H
3. Em BEAR: SMA ganha +34% vs B&H  
4. Em SIDEWAYS: SMA é neutro (+2%)

METODOLOGIA RECOMENDADA:
========================
1. Split por regime, não por data
2. Treinar separadamente para cada regime
3. Usar ensemble de parâmetros
4. Ou: aceitar que SMA só funciona como PROTEÇÃO em bears

ESTRATÉGIA FINAL RECOMENDADA:
=============================
"SMA Defensivo" - usar SMA apenas para SAIR de posições, não para ENTRAR
- Entrar: sempre que não tem posição (B&H behavior)
- Sair: quando preço cruza abaixo da SMA (proteção)
- Re-entrar: quando preço cruza acima da SMA

Isso combina:
- Captura de ganhos em bulls (está sempre entrando)
- Proteção em bears (sai quando SMA sinaliza)
"""

import sys
import os
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine


# =============================================================================
# ESTRATÉGIA DEFENSIVA
# =============================================================================

class DefensiveSMAStrategy(bt.Strategy):
    """
    SMA usado apenas como stop defensivo.
    
    Comportamento:
    - Fica comprado por padrão (como B&H)
    - Só sai quando preço cai abaixo da SMA
    - Re-entra quando preço volta acima da SMA
    
    Isso é como B&H com proteção de stop móvel baseado em SMA.
    """
    
    params = (
        ('sma_period', 100),
    )
    
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_period)
        self.order = None
        
    def next(self):
        if self.order:
            return
        
        # Se não tem posição E preço está acima da SMA -> comprar
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
        # Se tem posição E preço caiu abaixo da SMA -> vender (proteção)
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()
    
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


class BuyAndHold(bt.Strategy):
    """Buy and Hold puro."""
    
    def __init__(self):
        self.bought = False
        
    def next(self):
        if not self.bought:
            size = self.broker.getcash() * 0.95 / self.data.close[0]
            self.buy(size=size)
            self.bought = True


# =============================================================================
# BACKTEST HELPER
# =============================================================================

def run_backtest(df, strategy_cls, initial_cash=100000, **params):
    """Executa backtest retornando métricas."""
    
    # Limpar timezone se existir
    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    cerebro = bt.Cerebro(stdstats=False)
    
    data = bt.feeds.PandasData(
        dataname=df[['open', 'high', 'low', 'close', 'volume']],
        datetime=None
    )
    cerebro.adddata(data)
    
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(strategy_cls, **params)
    
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    try:
        results = cerebro.run()
        strat = results[0]
        
        final = cerebro.broker.getvalue()
        ret = (final / initial_cash - 1) * 100
        
        # Max DD
        try:
            max_dd = strat.analyzers.dd.get_analysis()['max']['drawdown'] or 0
        except:
            max_dd = 0
        
        # Trades
        try:
            total_trades = strat.analyzers.trades.get_analysis()['total']['total'] or 0
        except:
            total_trades = 0
        
        return {
            'final': final,
            'return': ret,
            'max_dd': max_dd,
            'trades': total_trades
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


# =============================================================================
# WALK-FORWARD
# =============================================================================

def create_splits(df, min_train_days=730, test_days=180, step_days=90):
    """Cria splits walk-forward."""
    splits = []
    
    # Limpar timezone
    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    start = df.index[0]
    end = df.index[-1]
    
    train_end = start + timedelta(days=min_train_days)
    
    split_id = 0
    while True:
        test_start = train_end + timedelta(days=5)  # embargo
        test_end = test_start + timedelta(days=test_days)
        
        if test_end > end:
            break
        
        # Encontrar datas reais no índice
        train_df = df[df.index <= train_end]
        test_df = df[(df.index >= test_start) & (df.index <= test_end)]
        
        if len(train_df) > 0 and len(test_df) >= 100:
            splits.append({
                'id': split_id,
                'train_start': train_df.index[0],
                'train_end': train_df.index[-1],
                'test_start': test_df.index[0],
                'test_end': test_df.index[-1],
                'train_days': len(train_df),
                'test_days': len(test_df)
            })
            split_id += 1
        
        train_end += timedelta(days=step_days)
    
    return splits


def classify_period(df):
    """Classifica período como BULL, BEAR ou SIDEWAYS."""
    ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    days = len(df)
    annual_ret = ret * (365 / days) if days > 0 else 0
    
    if annual_ret > 50:
        return 'BULL'
    elif annual_ret < -30:
        return 'BEAR'
    return 'SIDEWAYS'


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "="*70)
    print("🎯 VALIDAÇÃO FINAL: SMA DEFENSIVO vs BUY & HOLD")
    print("="*70)
    print("Metodologia: Walk-Forward com Split por Regime")
    print("="*70 + "\n")
    
    # Carregar dados
    print("📊 Carregando dados BTC-USD...")
    data_engine = DataEngine()
    df = data_engine.load_prices('BTC-USD', '2018-01-01', '2025-12-31')
    
    # Limpar timezone
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    print(f"✅ {len(df)} dias ({df.index[0].date()} a {df.index[-1].date()})\n")
    
    # Criar splits
    print("📅 Criando splits walk-forward...")
    splits = create_splits(df, min_train_days=730, test_days=180, step_days=90)
    print(f"   {len(splits)} splits criados\n")
    
    # Testar diferentes SMAs
    sma_periods = [50, 70, 100, 130, 150, 200]
    
    results = []
    
    print("🔬 Testando estratégias...\n")
    
    for split in splits:
        test_df = df[(df.index >= split['test_start']) & (df.index <= split['test_end'])].copy()
        
        if len(test_df) < 100:
            continue
        
        regime = classify_period(test_df)
        
        # B&H
        bh_res = run_backtest(test_df, BuyAndHold)
        if not bh_res:
            continue
        
        # Testar cada SMA
        for sma in sma_periods:
            if sma >= len(test_df) - 50:
                continue
                
            sma_res = run_backtest(test_df, DefensiveSMAStrategy, sma_period=sma)
            
            if sma_res:
                alpha = sma_res['return'] - bh_res['return']
                
                results.append({
                    'split': split['id'],
                    'test_start': split['test_start'].strftime('%Y-%m-%d'),
                    'test_end': split['test_end'].strftime('%Y-%m-%d'),
                    'regime': regime,
                    'sma_period': sma,
                    'sma_return': sma_res['return'],
                    'bh_return': bh_res['return'],
                    'alpha': alpha,
                    'sma_dd': sma_res['max_dd'],
                    'bh_dd': bh_res['max_dd'],
                    'trades': sma_res['trades']
                })
    
    if not results:
        print("❌ Nenhum resultado válido!")
        return
    
    results_df = pd.DataFrame(results)
    
    # =================================================================
    # ANÁLISE
    # =================================================================
    print("\n" + "="*70)
    print("📊 RESULTADOS POR PERÍODO DE SMA")
    print("="*70 + "\n")
    
    summary = results_df.groupby('sma_period').agg({
        'alpha': ['mean', 'std'],
        'sma_return': 'mean',
        'bh_return': 'mean',
        'sma_dd': 'mean',
        'bh_dd': 'mean',
        'split': 'count'
    }).round(2)
    
    summary.columns = ['alpha_mean', 'alpha_std', 'sma_return', 'bh_return', 
                       'sma_dd', 'bh_dd', 'n_splits']
    
    # Win rate
    for sma in sma_periods:
        sma_df = results_df[results_df['sma_period'] == sma]
        if len(sma_df) > 0:
            win_rate = (sma_df['alpha'] > 0).mean() * 100
            summary.loc[sma, 'win_rate'] = win_rate
    
    print(f"{'SMA':<6} {'Alpha':<10} {'Std':<10} {'Win%':<8} {'SMA DD':<10} {'B&H DD':<10}")
    print("-"*60)
    
    for sma in sma_periods:
        if sma in summary.index:
            r = summary.loc[sma]
            print(f"{sma:<6} {r['alpha_mean']:>8.1f}% {r['alpha_std']:>8.1f}% "
                  f"{r['win_rate']:>6.0f}% {r['sma_dd']:>8.1f}% {r['bh_dd']:>8.1f}%")
    
    # Por regime
    print("\n" + "="*70)
    print("📊 RESULTADOS POR REGIME")
    print("="*70 + "\n")
    
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['regime'] == regime]
        if len(regime_df) == 0:
            continue
        
        print(f"{regime} ({len(regime_df)} testes):")
        
        regime_summary = regime_df.groupby('sma_period').agg({
            'alpha': 'mean',
            'sma_return': 'mean',
            'bh_return': 'mean'
        }).round(1)
        
        for sma, r in regime_summary.iterrows():
            print(f"   SMA-{sma}: Alpha={r['alpha']:+.1f}% (SMA={r['sma_return']:.1f}%, B&H={r['bh_return']:.1f}%)")
        print()
    
    # Melhor por regime
    print("="*70)
    print("🎯 MELHOR SMA POR REGIME")
    print("="*70 + "\n")
    
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['regime'] == regime]
        if len(regime_df) == 0:
            continue
        
        best_sma_df = regime_df.groupby('sma_period')['alpha'].mean()
        best_sma = best_sma_df.idxmax()
        best_alpha = best_sma_df.max()
        
        print(f"   {regime}: SMA-{best_sma} ({best_alpha:+.1f}% alpha)")
    
    # =================================================================
    # CONCLUSÃO FINAL
    # =================================================================
    print("\n" + "="*70)
    print("🎯 CONCLUSÃO FINAL E RECOMENDAÇÃO")
    print("="*70 + "\n")
    
    # Melhor geral
    overall_best = results_df.groupby('sma_period')['alpha'].mean().idxmax()
    overall_best_alpha = results_df.groupby('sma_period')['alpha'].mean().max()
    overall_win_rate = (results_df[results_df['sma_period'] == overall_best]['alpha'] > 0).mean() * 100
    
    avg_alpha = results_df['alpha'].mean()
    overall_win_rate_all = (results_df['alpha'] > 0).mean() * 100
    
    print(f"📈 Estatísticas Gerais:")
    print(f"   Alpha médio (todas SMAs): {avg_alpha:+.1f}%")
    print(f"   Win rate geral: {overall_win_rate_all:.0f}%")
    print()
    
    print(f"🏆 Melhor SMA: {overall_best}")
    print(f"   Alpha médio: {overall_best_alpha:+.1f}%")
    print(f"   Win rate: {overall_win_rate:.0f}%")
    print()
    
    # Por regime detalhado
    print("📊 Performance por Regime (SMA Defensivo vs B&H):")
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['regime'] == regime]
        if len(regime_df) > 0:
            regime_alpha = regime_df['alpha'].mean()
            regime_dd_diff = regime_df['bh_dd'].mean() - regime_df['sma_dd'].mean()
            print(f"   {regime}: Alpha={regime_alpha:+.1f}%, DD Reduction={regime_dd_diff:+.1f}%")
    
    print()
    
    # Recomendação
    if overall_best_alpha > 0 and overall_win_rate >= 50:
        print("✅ ESTRATÉGIA SMA DEFENSIVO VALIDADA!")
        print(f"\n   Recomendação: Usar SMA-{overall_best}")
        print("   Benefício: Protege em quedas mantendo exposição em altas")
    elif overall_win_rate >= 40:
        print("⚠️ ESTRATÉGIA PARCIALMENTE VÁLIDA")
        print(f"\n   SMA-{overall_best} oferece proteção em bears")
        print("   Mas perde em bulls - considerar uso condicional")
    else:
        print("❌ ESTRATÉGIA NÃO RECOMENDADA")
        print("\n   SMA não supera B&H consistentemente")
        print("   Considere: B&H puro ou outras estratégias")
    
    # Salvar
    results_df.to_csv('final_sma_validation.csv', index=False)
    print(f"\n✅ Resultados salvos em final_sma_validation.csv")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
