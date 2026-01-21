#!/usr/bin/env python3
"""
Robust SMA Validation for BTC

Metodologia melhorada para treino/teste de estratégias SMA:

PROBLEMAS DAS ABORDAGENS ANTERIORES:
=====================================
1. Splits anuais arbitrários ignoram ciclos de mercado (BTC = ~4 anos)
2. Período de treino muito curto (1 ano = ~250 dias é insuficiente para SMA-200)
3. Regimes de mercado desequilibrados entre treino/teste
4. Função objetivo mal definida (só alpha ignora risco)

NOVA METODOLOGIA:
=================
1. EXPANDING WINDOW: Começar com mínimo de dados, expandir progressivamente
2. REGIME-AWARE: Garantir que treino tenha exemplos de bull/bear/sideways
3. EMBARGO PERIOD: Gap entre treino e teste para evitar leakage
4. MULTIPLE METRICS: Avaliar Sharpe, Sortino, Calmar além de alpha
5. PARAMETER STABILITY: Verificar se parâmetros são estáveis entre períodos
6. OUT-OF-SAMPLE DEGRADATION: Medir quanto a performance cai em dados novos

Inspirado em:
- Marcos López de Prado: "Advances in Financial Machine Learning"
- Método CPCV (Combinatorial Purged Cross-Validation)
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
from engines.backtest_engine import BacktestEngine
from strategies.base_strategy import BaseStrategy


# =============================================================================
# STRATEGY
# =============================================================================

class SimpleSMAStrategy(BaseStrategy):
    """SMA crossover strategy for optimization."""
    
    params = (
        ('sma_period', 100),
        ('verbose', False),
    )
    
    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_period)
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
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


# =============================================================================
# REGIME DETECTION
# =============================================================================

@dataclass
class MarketRegime:
    """Market regime classification for a period."""
    regime: str  # BULL, BEAR, SIDEWAYS
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    return_pct: float
    volatility: float
    days: int


def classify_regime(df: pd.DataFrame) -> str:
    """Classify a period into BULL, BEAR, or SIDEWAYS based on characteristics."""
    if len(df) < 20:
        return 'UNKNOWN'
    
    total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    volatility = df['close'].pct_change().std() * np.sqrt(252) * 100
    
    # Annualize return
    days = len(df)
    annual_return = total_return * (365 / days) if days > 0 else 0
    
    # Classification thresholds
    if annual_return > 50 and total_return > 0:
        return 'BULL'
    elif annual_return < -30 or total_return < -20:
        return 'BEAR'
    else:
        return 'SIDEWAYS'


def detect_regime_periods(df: pd.DataFrame, window_days: int = 90) -> List[MarketRegime]:
    """
    Detect market regime periods using rolling windows.
    
    Uses overlapping windows to identify regime characteristics,
    then consolidates into continuous regime segments.
    """
    regimes = []
    
    # Process in rolling windows
    step = window_days // 2  # 50% overlap
    
    i = 0
    while i + window_days <= len(df):
        window_df = df.iloc[i:i+window_days]
        
        regime = classify_regime(window_df)
        total_return = (window_df['close'].iloc[-1] / window_df['close'].iloc[0] - 1) * 100
        volatility = window_df['close'].pct_change().std() * np.sqrt(252) * 100
        
        regimes.append(MarketRegime(
            regime=regime,
            start_date=window_df.index[0],
            end_date=window_df.index[-1],
            return_pct=total_return,
            volatility=volatility,
            days=window_days
        ))
        
        i += step
    
    return regimes


def get_regime_distribution(regimes: List[MarketRegime]) -> Dict[str, float]:
    """Get the distribution of regimes as percentages."""
    total = len(regimes)
    if total == 0:
        return {}
    
    counts = {}
    for r in regimes:
        counts[r.regime] = counts.get(r.regime, 0) + 1
    
    return {k: v / total * 100 for k, v in counts.items()}


# =============================================================================
# BACKTEST RUNNER
# =============================================================================

def run_backtest(df: pd.DataFrame, sma_period: int, initial_cash: float = 100000) -> Dict[str, Any]:
    """Run a single backtest and return comprehensive metrics."""
    
    if len(df) < sma_period + 50:
        return None
    
    # Calculate Buy & Hold
    bh_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    
    try:
        engine = BacktestEngine(initial_cash=initial_cash, commission=0.001)
        results = engine.run_backtest(
            strategy_cls=SimpleSMAStrategy,
            data_df=df,
            symbol='BTC-USD',
            sma_period=sma_period,
            verbose=False
        )
        
        final_value = results.get('final_value', initial_cash)
        total_return = (final_value / initial_cash - 1) * 100
        sharpe = results.get('sharpe_ratio', 0)
        max_dd = abs(results.get('max_drawdown_pct', 0))
        trades = results.get('total_trades', 0)
        
        # Calculate additional metrics
        period_years = len(df) / 365
        trades_per_year = trades / period_years if period_years > 0 else 0
        
        # Calmar ratio (return / max_dd)
        calmar = total_return / max_dd if max_dd > 0 else 0
        
        return {
            'total_return': total_return,
            'bh_return': bh_return,
            'alpha': total_return - bh_return,
            'sharpe': sharpe if sharpe else 0,
            'max_dd': max_dd,
            'calmar': calmar,
            'trades': trades,
            'trades_per_year': trades_per_year,
            'days': len(df),
            'start': df.index[0],
            'end': df.index[-1]
        }
        
    except Exception as e:
        return None


# =============================================================================
# EXPANDING WINDOW WALK-FORWARD
# =============================================================================

@dataclass
class WalkForwardSplit:
    """A single walk-forward split."""
    split_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    embargo_days: int
    train_days: int
    test_days: int


def create_expanding_window_splits(
    df: pd.DataFrame,
    min_train_days: int = 500,  # ~2 anos mínimo de treino
    test_days: int = 180,       # 6 meses de teste
    embargo_days: int = 10,     # Gap para evitar leakage
    step_days: int = 90,        # Avançar 3 meses por split
    n_splits: int = None        # Número máximo de splits
) -> List[WalkForwardSplit]:
    """
    Create expanding window walk-forward splits.
    
    Expanding window: treino começa sempre do início, mas cresce a cada split.
    Isso simula como um trader usaria a estratégia na prática.
    
    Timeline:
    [=======TRAIN=======][embargo][===TEST===]
          expanding ↗              fixed size
    """
    splits = []
    total_days = len(df)
    
    split_id = 0
    train_end_idx = min_train_days
    
    while train_end_idx + embargo_days + test_days <= total_days:
        train_start = df.index[0]
        train_end = df.index[train_end_idx - 1]
        test_start = df.index[train_end_idx + embargo_days]
        test_end_idx = min(train_end_idx + embargo_days + test_days, total_days) - 1
        test_end = df.index[test_end_idx]
        
        splits.append(WalkForwardSplit(
            split_id=split_id,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            embargo_days=embargo_days,
            train_days=train_end_idx,
            test_days=test_end_idx - train_end_idx - embargo_days + 1
        ))
        
        split_id += 1
        train_end_idx += step_days
        
        if n_splits and split_id >= n_splits:
            break
    
    return splits


# =============================================================================
# GRID SEARCH COM VALIDAÇÃO
# =============================================================================

def evaluate_sma_period(
    df: pd.DataFrame,
    sma_period: int,
    splits: List[WalkForwardSplit]
) -> Dict[str, Any]:
    """
    Evaluate a single SMA period across all walk-forward splits.
    
    Returns aggregate metrics and per-split details.
    """
    train_results = []
    test_results = []
    
    for split in splits:
        # Train data
        train_df = df.loc[split.train_start:split.train_end].copy()
        test_df = df.loc[split.test_start:split.test_end].copy()
        
        # Run backtest on both
        train_res = run_backtest(train_df, sma_period)
        test_res = run_backtest(test_df, sma_period)
        
        if train_res and test_res:
            train_results.append(train_res)
            test_results.append(test_res)
    
    if not test_results:
        return None
    
    # Aggregate metrics
    def safe_mean(lst, key):
        values = [r[key] for r in lst if r and key in r]
        return sum(values) / len(values) if values else 0
    
    def safe_std(lst, key):
        values = [r[key] for r in lst if r and key in r]
        return pd.Series(values).std() if len(values) > 1 else 0
    
    return {
        'sma_period': sma_period,
        
        # Train metrics
        'train_alpha_mean': safe_mean(train_results, 'alpha'),
        'train_sharpe_mean': safe_mean(train_results, 'sharpe'),
        'train_dd_mean': safe_mean(train_results, 'max_dd'),
        
        # Test metrics (KEY!)
        'test_alpha_mean': safe_mean(test_results, 'alpha'),
        'test_alpha_std': safe_std(test_results, 'alpha'),
        'test_sharpe_mean': safe_mean(test_results, 'sharpe'),
        'test_sharpe_std': safe_std(test_results, 'sharpe'),
        'test_dd_mean': safe_mean(test_results, 'max_dd'),
        'test_calmar_mean': safe_mean(test_results, 'calmar'),
        
        # Consistency
        'n_positive_alpha': sum(1 for r in test_results if r['alpha'] > 0),
        'n_splits': len(test_results),
        'win_rate': sum(1 for r in test_results if r['alpha'] > 0) / len(test_results) * 100,
        
        # Overfitting indicator
        'alpha_degradation': safe_mean(train_results, 'alpha') - safe_mean(test_results, 'alpha'),
        'sharpe_degradation': safe_mean(train_results, 'sharpe') - safe_mean(test_results, 'sharpe'),
        
        # Raw results
        'train_results': train_results,
        'test_results': test_results
    }


def grid_search_sma(
    df: pd.DataFrame,
    splits: List[WalkForwardSplit],
    sma_range: Tuple[int, int, int] = (50, 200, 10)  # start, end, step
) -> pd.DataFrame:
    """
    Grid search over SMA periods with walk-forward validation.
    """
    results = []
    
    for sma_period in range(sma_range[0], sma_range[1] + 1, sma_range[2]):
        eval_result = evaluate_sma_period(df, sma_period, splits)
        if eval_result:
            results.append(eval_result)
    
    return pd.DataFrame(results)


# =============================================================================
# ROBUSTNESS SCORING
# =============================================================================

def calculate_robustness_score(row: pd.Series) -> float:
    """
    Calculate a composite robustness score for a parameter set.
    
    Score components:
    - Test alpha (40%): Higher is better
    - Win rate (25%): Consistency across periods
    - Low degradation (20%): Small train→test performance drop
    - Sharpe (15%): Risk-adjusted returns
    
    Returns score from 0-100.
    """
    score = 0
    
    # Test alpha component (40 points max)
    # Normalize: 0-50% alpha = 0-40 points
    alpha_score = min(40, max(0, row['test_alpha_mean'] * 0.8))
    score += alpha_score
    
    # Win rate component (25 points max)
    win_score = row['win_rate'] * 0.25
    score += win_score
    
    # Degradation component (20 points max)
    # Lower degradation is better
    # 0% degradation = 20 points, 50%+ degradation = 0 points
    degradation_pct = row['alpha_degradation'] / max(abs(row['train_alpha_mean']), 1) * 100
    degradation_score = max(0, 20 - degradation_pct * 0.4)
    score += degradation_score
    
    # Sharpe component (15 points max)
    sharpe_score = min(15, max(0, row['test_sharpe_mean'] * 10))
    score += sharpe_score
    
    return score


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def main():
    print("\n" + "="*80)
    print("🔬 ROBUST SMA VALIDATION FOR BTC")
    print("="*80)
    print("Methodology: Expanding Window Walk-Forward with Regime Analysis")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. LOAD DATA
    # =========================================================================
    print("📊 Loading BTC-USD data...")
    data_engine = DataEngine()
    df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2018-01-01',  # Mais dados para treino adequado
        end='2025-12-31'
    )
    print(f"✅ Loaded {len(df)} days ({df.index[0].date()} to {df.index[-1].date()})\n")
    
    # =========================================================================
    # 2. REGIME ANALYSIS
    # =========================================================================
    print("📈 Analyzing market regimes...")
    regimes = detect_regime_periods(df, window_days=90)
    regime_dist = get_regime_distribution(regimes)
    
    print("   Regime distribution:")
    for regime, pct in sorted(regime_dist.items()):
        print(f"      {regime}: {pct:.1f}%")
    print()
    
    # =========================================================================
    # 3. CREATE WALK-FORWARD SPLITS
    # =========================================================================
    print("📅 Creating walk-forward splits...")
    print("   Configuration:")
    print("      Min train period: 500 days (~2 years)")
    print("      Test period: 180 days (6 months)")
    print("      Embargo: 10 days")
    print("      Step: 90 days")
    print()
    
    splits = create_expanding_window_splits(
        df,
        min_train_days=500,
        test_days=180,
        embargo_days=10,
        step_days=90
    )
    
    print(f"   Created {len(splits)} walk-forward splits:\n")
    print(f"   {'Split':<8} {'Train Period':<30} {'Test Period':<30} {'Train Days':<12} {'Test Days':<10}")
    print("   " + "-"*90)
    
    for s in splits[:5]:  # Show first 5
        print(f"   {s.split_id:<8} "
              f"{str(s.train_start.date())} → {str(s.train_end.date()):<12} "
              f"{str(s.test_start.date())} → {str(s.test_end.date()):<12} "
              f"{s.train_days:<12} "
              f"{s.test_days:<10}")
    
    if len(splits) > 5:
        print(f"   ... and {len(splits) - 5} more splits")
    print()
    
    # Validate splits have diverse regimes in test
    print("   Validating regime diversity in test periods...")
    test_regimes = []
    for split in splits:
        test_df = df.loc[split.test_start:split.test_end]
        regime = classify_regime(test_df)
        test_regimes.append(regime)
    
    regime_counts = pd.Series(test_regimes).value_counts()
    print(f"   Test regime distribution: {dict(regime_counts)}")
    print()
    
    # =========================================================================
    # 4. GRID SEARCH COM WALK-FORWARD
    # =========================================================================
    print("🔍 Running grid search with walk-forward validation...")
    print("   Testing SMA periods: 50 to 200 (step 10)")
    print("   This will take a few minutes...\n")
    
    results_df = grid_search_sma(df, splits, sma_range=(50, 200, 10))
    
    # Add robustness score
    results_df['robustness_score'] = results_df.apply(calculate_robustness_score, axis=1)
    
    # Sort by robustness score
    results_df = results_df.sort_values('robustness_score', ascending=False)
    
    # =========================================================================
    # 5. RESULTS ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("📊 GRID SEARCH RESULTS (sorted by robustness)")
    print("="*80 + "\n")
    
    print(f"{'SMA':<6} {'Test α':<10} {'α Std':<10} {'Test Sharpe':<12} {'Win%':<8} {'Degradation':<12} {'Score':<8}")
    print("-"*70)
    
    for _, row in results_df.head(15).iterrows():
        print(f"{int(row['sma_period']):<6} "
              f"{row['test_alpha_mean']:>8.1f}% "
              f"{row['test_alpha_std']:>8.1f}% "
              f"{row['test_sharpe_mean']:>10.2f} "
              f"{row['win_rate']:>6.0f}% "
              f"{row['alpha_degradation']:>10.1f}% "
              f"{row['robustness_score']:>6.1f}")
    
    # =========================================================================
    # 6. TOP PARAMETER ANALYSIS
    # =========================================================================
    best = results_df.iloc[0]
    
    print("\n" + "="*80)
    print("🏆 BEST PARAMETER ANALYSIS")
    print("="*80 + "\n")
    
    print(f"Best SMA Period: {int(best['sma_period'])}")
    print(f"\nMetrics across {int(best['n_splits'])} walk-forward splits:")
    print(f"   Test Alpha: {best['test_alpha_mean']:+.1f}% ± {best['test_alpha_std']:.1f}%")
    print(f"   Test Sharpe: {best['test_sharpe_mean']:.2f} ± {best['test_sharpe_std']:.2f}")
    print(f"   Win Rate: {best['win_rate']:.0f}%")
    print(f"   Max Drawdown (avg): {best['test_dd_mean']:.1f}%")
    print(f"   Calmar Ratio: {best['test_calmar_mean']:.2f}")
    
    print(f"\nOverfitting Analysis:")
    print(f"   Train Alpha: {best['train_alpha_mean']:+.1f}%")
    print(f"   Test Alpha: {best['test_alpha_mean']:+.1f}%")
    print(f"   Degradation: {best['alpha_degradation']:.1f}% (train→test)")
    
    # Per-split breakdown
    print(f"\nPer-Split Test Results:")
    print(f"   {'Split':<8} {'Period':<25} {'Alpha':<12} {'Sharpe':<10}")
    print("   " + "-"*55)
    
    for i, res in enumerate(best['test_results'][:8]):
        print(f"   {i:<8} "
              f"{str(res['start'].date())} → {str(res['end'].date()):<8} "
              f"{res['alpha']:>10.1f}% "
              f"{res['sharpe']:>8.2f}")
    
    # =========================================================================
    # 7. ROBUSTNESS VERDICT
    # =========================================================================
    print("\n" + "="*80)
    print("🎯 ROBUSTNESS VERDICT")
    print("="*80 + "\n")
    
    # Criteria for robust strategy
    is_robust = True
    issues = []
    
    # Criterion 1: Win rate > 60%
    if best['win_rate'] < 60:
        is_robust = False
        issues.append(f"Low win rate ({best['win_rate']:.0f}% < 60%)")
    
    # Criterion 2: Positive average test alpha
    if best['test_alpha_mean'] <= 0:
        is_robust = False
        issues.append(f"Negative test alpha ({best['test_alpha_mean']:.1f}%)")
    
    # Criterion 3: Reasonable degradation (< 50% of train alpha)
    if best['train_alpha_mean'] > 0:
        degradation_ratio = best['alpha_degradation'] / best['train_alpha_mean']
        if degradation_ratio > 0.5:
            is_robust = False
            issues.append(f"High degradation ({degradation_ratio*100:.0f}% of train alpha)")
    
    # Criterion 4: Consistent results (std < mean for alpha)
    if best['test_alpha_std'] > abs(best['test_alpha_mean']) * 2:
        is_robust = False
        issues.append(f"High variance (std={best['test_alpha_std']:.1f}%, mean={best['test_alpha_mean']:.1f}%)")
    
    if is_robust:
        print("✅ STRATEGY IS ROBUST!")
        print(f"\nKey findings:")
        print(f"   • Consistent performance across {int(best['n_splits'])} periods")
        print(f"   • Win rate: {best['win_rate']:.0f}%")
        print(f"   • Expected alpha: {best['test_alpha_mean']:+.1f}% per period")
        print(f"   • Reasonable train→test degradation")
        print(f"\n🚀 RECOMMENDED PARAMETER: SMA-{int(best['sma_period'])}")
    else:
        print("⚠️ STRATEGY HAS ROBUSTNESS ISSUES")
        print(f"\nProblems identified:")
        for issue in issues:
            print(f"   • {issue}")
        print(f"\n💡 Recommendations:")
        print("   • Consider using a more conservative/longer SMA")
        print("   • Combine with regime detection")
        print("   • Add additional filters (RSI, MACD)")
    
    # =========================================================================
    # 8. PARAMETER STABILITY ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("📊 PARAMETER STABILITY ANALYSIS")
    print("="*80 + "\n")
    
    # Find top 5 parameters
    top_params = results_df.nsmallest(5, 'test_alpha_std')  # Most stable
    
    print("Most stable parameters (lowest variance):")
    print(f"   {'SMA':<8} {'Test α Mean':<12} {'Test α Std':<12} {'Win%':<8}")
    print("   " + "-"*40)
    
    for _, row in top_params.iterrows():
        print(f"   {int(row['sma_period']):<8} "
              f"{row['test_alpha_mean']:>10.1f}% "
              f"{row['test_alpha_std']:>10.1f}% "
              f"{row['win_rate']:>6.0f}%")
    
    # Save results
    output_file = 'robust_sma_validation_results.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ Full results saved to: {output_file}")
    
    # =========================================================================
    # 9. FINAL RECOMMENDATION
    # =========================================================================
    print("\n" + "="*80)
    print("🎯 FINAL RECOMMENDATION")
    print("="*80 + "\n")
    
    # Get parameters that are both robust and stable
    good_params = results_df[
        (results_df['win_rate'] >= 50) & 
        (results_df['test_alpha_mean'] > 0)
    ]
    
    if len(good_params) > 0:
        # Average of good parameters (more robust than single best)
        avg_sma = int(good_params['sma_period'].mean())
        median_sma = int(good_params['sma_period'].median())
        
        print(f"Based on walk-forward analysis with {len(splits)} periods:")
        print(f"\n   📊 Statistics of successful parameters:")
        print(f"      • Range: SMA-{int(good_params['sma_period'].min())} to SMA-{int(good_params['sma_period'].max())}")
        print(f"      • Average: SMA-{avg_sma}")
        print(f"      • Median: SMA-{median_sma}")
        
        print(f"\n   🎯 Recommended parameter: SMA-{median_sma}")
        print(f"      (using median for robustness)")
        
        # Expected performance
        median_result = results_df[results_df['sma_period'] == median_sma].iloc[0]
        print(f"\n   📈 Expected performance with SMA-{median_sma}:")
        print(f"      • Test Alpha: {median_result['test_alpha_mean']:+.1f}% per 6-month period")
        print(f"      • Win Rate: {median_result['win_rate']:.0f}%")
        print(f"      • Sharpe: {median_result['test_sharpe_mean']:.2f}")
        print(f"      • Max DD: {median_result['test_dd_mean']:.1f}%")
    else:
        print("⚠️ No parameters passed robustness criteria!")
        print("\nSuggestions:")
        print("   • Use a simple buy-and-hold strategy")
        print("   • Try a different strategy type")
        print("   • Add filters (regime, volatility)")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
