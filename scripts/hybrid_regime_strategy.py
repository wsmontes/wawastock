#!/usr/bin/env python3
"""
Estratégia Híbrida Adaptativa por Regime para BTC

CONCLUSÃO DA ANÁLISE WALK-FORWARD:
===================================
- SMA em BULL: -41.5% alpha (perde para B&H)
- SMA em BEAR: +34.1% alpha (protege bem)
- SMA em SIDEWAYS: +2.2% alpha (neutro)

SOLUÇÃO:
========
Em vez de usar SMA sempre, vamos:
1. Detectar regime de mercado em tempo real
2. Em BULL: ficar comprado (B&H) - não usar SMA
3. Em BEAR: usar SMA como proteção
4. Em SIDEWAYS: usar SMA com parâmetro conservador

Isso combina o melhor dos dois mundos:
- Captura os ganhos dos bull markets (B&H)
- Protege nos bear markets (SMA)

METODOLOGIA DE VALIDAÇÃO:
=========================
Walk-forward com expanding window, testando:
- Estratégia híbrida vs SMA puro vs B&H
- Métricas: Alpha, Sharpe, Max Drawdown, Win Rate
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import backtrader as bt
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine


# =============================================================================
# REGIME DETECTION (Real-time)
# =============================================================================

def calculate_regime_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores para detecção de regime em tempo real.
    
    Usamos:
    - SMA 200 para tendência de longo prazo
    - Retorno de 60 dias para momentum
    - ATR para volatilidade
    """
    df = df.copy()
    
    # Tendência de longo prazo
    df['sma200'] = df['close'].rolling(200).mean()
    df['trend'] = (df['close'] / df['sma200'] - 1) * 100  # % acima/abaixo SMA200
    
    # Momentum (retorno de 60 dias)
    df['ret_60d'] = df['close'].pct_change(60) * 100
    
    # Volatilidade (ATR-like)
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252) * 100
    
    return df


def classify_regime_realtime(trend: float, ret_60d: float, volatility: float) -> str:
    """
    Classifica regime baseado em indicadores.
    
    Regras:
    - BULL: trend > 5% E ret_60d > 10%
    - BEAR: trend < -10% OU ret_60d < -20%
    - SIDEWAYS: resto
    """
    if pd.isna(trend) or pd.isna(ret_60d):
        return 'UNKNOWN'
    
    if trend > 5 and ret_60d > 10:
        return 'BULL'
    elif trend < -10 or ret_60d < -20:
        return 'BEAR'
    else:
        return 'SIDEWAYS'


# =============================================================================
# ESTRATÉGIAS
# =============================================================================

class HybridAdaptiveStrategy(bt.Strategy):
    """
    Estratégia híbrida que adapta comportamento ao regime.
    
    - BULL: Fica comprado (B&H behavior)
    - BEAR: Usa SMA para proteção
    - SIDEWAYS: Usa SMA com threshold
    """
    
    params = (
        ('sma_period', 100),      # SMA para proteção
        ('regime_lookback', 60),  # Lookback para regime
        ('trend_sma', 200),       # SMA para detectar tendência
        ('bull_threshold', 5),    # % acima SMA200 para BULL
        ('bear_threshold', -10),  # % abaixo SMA200 para BEAR
    )
    
    def __init__(self):
        # Indicadores
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_period)
        self.sma_trend = bt.indicators.SMA(self.data.close, period=self.params.trend_sma)
        
        self.order = None
        self.regime = 'UNKNOWN'
        
    def get_current_regime(self):
        """Detecta regime atual."""
        if len(self.data) < self.params.trend_sma:
            return 'UNKNOWN'
        
        # Trend: % acima/abaixo SMA200
        trend = (self.data.close[0] / self.sma_trend[0] - 1) * 100
        
        # Retorno de 60 dias
        if len(self.data) < self.params.regime_lookback:
            ret_60d = 0
        else:
            ret_60d = (self.data.close[0] / self.data.close[-self.params.regime_lookback] - 1) * 100
        
        return classify_regime_realtime(trend, ret_60d, 0)
    
    def next(self):
        if self.order:
            return
        
        self.regime = self.get_current_regime()
        
        if self.regime == 'UNKNOWN':
            return
        
        # Lógica por regime
        if self.regime == 'BULL':
            # Em bull market: ficar comprado sempre
            if not self.position:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
                
        elif self.regime == 'BEAR':
            # Em bear market: usar SMA para proteção
            if not self.position:
                if self.data.close[0] > self.sma[0]:
                    size = self.broker.getcash() * 0.95 / self.data.close[0]
                    self.order = self.buy(size=size)
            else:
                if self.data.close[0] < self.sma[0]:
                    self.order = self.close()
                    
        else:  # SIDEWAYS
            # Em sideways: SMA com mais cuidado
            if not self.position:
                if self.data.close[0] > self.sma[0]:
                    size = self.broker.getcash() * 0.95 / self.data.close[0]
                    self.order = self.buy(size=size)
            else:
                if self.data.close[0] < self.sma[0]:
                    self.order = self.close()
    
    def notify_order(self, order):
        self.order = None


class PureSMAStrategy(bt.Strategy):
    """SMA puro para comparação."""
    
    params = (('period', 100),)
    
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)
        self.order = None
        
    def next(self):
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
        self.order = None


class BuyAndHoldStrategy(bt.Strategy):
    """Buy and Hold para comparação."""
    
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

def run_backtest(df: pd.DataFrame, strategy_cls, initial_cash: float = 100000, **params) -> Dict:
    """Executa backtest e retorna métricas."""
    
    cerebro = bt.Cerebro()
    
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open='open', high='high', low='low', close='close', volume='volume',
        openinterest=-1
    )
    cerebro.adddata(data)
    
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(strategy_cls, **params)
    
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    try:
        results = cerebro.run()
        strat = results[0]
        
        final_value = cerebro.broker.getvalue()
        total_return = (final_value / initial_cash - 1) * 100
        
        # Métricas
        sharpe = 0.0
        max_dd = 0.0
        total_trades = 0
        
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
        except:
            pass
        
        return {
            'final_value': final_value,
            'total_return': total_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'total_trades': total_trades
        }
        
    except:
        return None


# =============================================================================
# WALK-FORWARD VALIDATION
# =============================================================================

@dataclass
class WFSplit:
    id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str


def create_splits(df: pd.DataFrame, min_train_years=2.0, test_months=6, step_months=3) -> List[WFSplit]:
    """Cria splits walk-forward."""
    splits = []
    
    start_date = df.index[0]
    end_date = df.index[-1]
    
    min_train_days = int(min_train_years * 365)
    test_days = test_months * 30
    step_days = step_months * 30
    
    train_end = start_date + timedelta(days=min_train_days)
    
    split_id = 0
    while True:
        test_start = train_end + timedelta(days=5)  # embargo
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


def detect_regime_for_period(df: pd.DataFrame) -> str:
    """Detecta regime dominante de um período."""
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
# MAIN
# =============================================================================

def main():
    print("\n" + "="*80)
    print("🎯 ESTRATÉGIA HÍBRIDA ADAPTATIVA POR REGIME")
    print("="*80)
    print("Combina B&H em bulls + SMA em bears para melhor performance")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. CARREGAR DADOS
    # =========================================================================
    print("📊 Carregando dados...")
    data_engine = DataEngine()
    df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2017-01-01',
        end='2025-12-31'
    )
    print(f"✅ {len(df)} dias ({df.index[0].date()} a {df.index[-1].date()})\n")
    
    # =========================================================================
    # 2. CRIAR SPLITS
    # =========================================================================
    print("📅 Criando splits walk-forward...")
    splits = create_splits(df, min_train_years=2.0, test_months=6, step_months=3)
    print(f"   {len(splits)} splits criados\n")
    
    # =========================================================================
    # 3. COMPARAR ESTRATÉGIAS
    # =========================================================================
    print("🔬 Comparando estratégias em walk-forward...\n")
    
    results = []
    
    for split in splits:
        test_df = df.loc[split.test_start:split.test_end].copy()
        
        if len(test_df) < 100:
            continue
        
        regime = detect_regime_for_period(test_df)
        
        # Rodar cada estratégia
        hybrid_res = run_backtest(test_df, HybridAdaptiveStrategy, sma_period=100)
        sma_res = run_backtest(test_df, PureSMAStrategy, period=100)
        bh_res = run_backtest(test_df, BuyAndHoldStrategy)
        
        if hybrid_res and sma_res and bh_res:
            results.append({
                'split': split.id,
                'test_start': split.test_start,
                'test_end': split.test_end,
                'regime': regime,
                
                'hybrid_return': hybrid_res['total_return'],
                'hybrid_dd': hybrid_res['max_dd'],
                'hybrid_sharpe': hybrid_res['sharpe'],
                
                'sma_return': sma_res['total_return'],
                'sma_dd': sma_res['max_dd'],
                'sma_sharpe': sma_res['sharpe'],
                
                'bh_return': bh_res['total_return'],
                'bh_dd': bh_res['max_dd'],
                'bh_sharpe': bh_res['sharpe'],
            })
            
            print(f"   Split {split.id}: {regime:<10} | "
                  f"Hybrid: {hybrid_res['total_return']:+.1f}% | "
                  f"SMA: {sma_res['total_return']:+.1f}% | "
                  f"B&H: {bh_res['total_return']:+.1f}%")
    
    results_df = pd.DataFrame(results)
    
    # =========================================================================
    # 4. ANÁLISE DE RESULTADOS
    # =========================================================================
    print("\n" + "="*80)
    print("📊 RESULTADOS COMPARATIVOS")
    print("="*80 + "\n")
    
    # Médias gerais
    print("Performance Média (todos os períodos):")
    print(f"   {'Estratégia':<15} {'Return':<12} {'Max DD':<12} {'Sharpe':<10}")
    print("   " + "-"*50)
    
    for strat in ['hybrid', 'sma', 'bh']:
        avg_ret = results_df[f'{strat}_return'].mean()
        avg_dd = results_df[f'{strat}_dd'].mean()
        avg_sharpe = results_df[f'{strat}_sharpe'].mean()
        print(f"   {strat.upper():<15} {avg_ret:>10.1f}% {avg_dd:>10.1f}% {avg_sharpe:>8.2f}")
    
    # Por regime
    print("\n\nPerformance por Regime:")
    
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['regime'] == regime]
        if len(regime_df) == 0:
            continue
            
        print(f"\n   {regime}:")
        for strat in ['hybrid', 'sma', 'bh']:
            avg_ret = regime_df[f'{strat}_return'].mean()
            print(f"      {strat.upper():<10}: {avg_ret:+.1f}%")
    
    # Alpha vs B&H
    print("\n\nAlpha (vs Buy & Hold):")
    results_df['hybrid_alpha'] = results_df['hybrid_return'] - results_df['bh_return']
    results_df['sma_alpha'] = results_df['sma_return'] - results_df['bh_return']
    
    print(f"   Hybrid Alpha médio: {results_df['hybrid_alpha'].mean():+.1f}%")
    print(f"   SMA Alpha médio: {results_df['sma_alpha'].mean():+.1f}%")
    
    # Win rates
    print(f"\nWin Rates (supera B&H):")
    hybrid_wins = (results_df['hybrid_alpha'] > 0).sum()
    sma_wins = (results_df['sma_alpha'] > 0).sum()
    total = len(results_df)
    
    print(f"   Hybrid: {hybrid_wins}/{total} ({100*hybrid_wins/total:.0f}%)")
    print(f"   SMA: {sma_wins}/{total} ({100*sma_wins/total:.0f}%)")
    
    # =========================================================================
    # 5. CONCLUSÃO
    # =========================================================================
    print("\n" + "="*80)
    print("🎯 CONCLUSÃO")
    print("="*80 + "\n")
    
    hybrid_alpha = results_df['hybrid_alpha'].mean()
    sma_alpha = results_df['sma_alpha'].mean()
    
    if hybrid_alpha > sma_alpha and hybrid_alpha > -5:
        print("✅ ESTRATÉGIA HÍBRIDA É SUPERIOR!")
        print(f"   Alpha médio: {hybrid_alpha:+.1f}% (vs {sma_alpha:+.1f}% do SMA puro)")
        print("\n   A combinação de B&H em bulls + SMA em bears funciona melhor.")
    elif hybrid_alpha > -10:
        print("⚠️ ESTRATÉGIA HÍBRIDA PARCIALMENTE EFETIVA")
        print(f"   Alpha médio: {hybrid_alpha:+.1f}%")
        print("\n   Melhora sobre SMA puro, mas ainda não supera B&H consistentemente.")
    else:
        print("❌ NENHUMA ESTRATÉGIA É ROBUSTA")
        print("   Considere B&H simples ou outras abordagens.")
    
    print("\n📊 Insights:")
    
    # Por regime
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        regime_df = results_df[results_df['regime'] == regime]
        if len(regime_df) > 0:
            hybrid_regime = regime_df['hybrid_alpha'].mean()
            print(f"   • Em {regime}: Hybrid alpha = {hybrid_regime:+.1f}%")
    
    # Salvar
    results_df.to_csv('hybrid_strategy_validation.csv', index=False)
    print(f"\n✅ Resultados salvos em hybrid_strategy_validation.csv")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
