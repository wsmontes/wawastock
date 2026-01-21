#!/usr/bin/env python3
"""
Walk-Forward Optimization with Optuna

Proper methodology to avoid overfitting:
1. Split data into 3 periods (train/test for each)
2. Optimize on each training period independently
3. Test optimized parameters on corresponding test period
4. Compare results to validate robustness

This tests if optimization generalizes to unseen data, not just
if it fits the training data well.

Periods:
- Period 1: Train 2020, Test 2021
- Period 2: Train 2022, Test 2023  
- Period 3: Train 2024, Test 2025

If optimized parameters work on test periods consistently,
strategy is robust. If not, it's overfit.
"""

import sys
import os
from datetime import datetime
import optuna
import pandas as pd
import backtrader as bt
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.base_strategy import BaseStrategy


class WalkForwardSMAStrategy(BaseStrategy):
    """SMA strategy with configurable parameters for optimization."""
    
    params = (
        ('sma_period', 50),
        ('verbose', False),
    )
    
    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_period)
        self.order = None
        self.in_position = False
    
    def next(self):
        if self.order:
            return
        
        current_price = self.data.close[0]
        sma_value = self.sma[0]
        
        if not self.in_position:
            if current_price > sma_value:
                cash = self.broker.get_cash()
                size = (cash * 0.95) / current_price
                self.order = self.buy(size=size)
                self.in_position = True
        else:
            if current_price < sma_value:
                self.order = self.close()
                self.in_position = False
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            pass
        self.order = None


def calculate_bh_return(df):
    """Calculate Buy & Hold return."""
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    return ((end_price / start_price) - 1) * 100


def objective_train(trial, df, bh_return):
    """Objective function for training period optimization."""
    sma_period = trial.suggest_int('sma_period', 20, 200, step=10)
    
    engine = BacktestEngine(initial_cash=100000, commission=0.001)
    
    try:
        results = engine.run_backtest(
            strategy_cls=WalkForwardSMAStrategy,
            data_df=df,
            symbol='BTC-USD',
            sma_period=sma_period,
            verbose=False
        )
        
        final_value = results.get('final_value', 100000)
        total_return = ((final_value / 100000) - 1) * 100
        alpha = total_return - bh_return
        sharpe = results.get('sharpe_ratio', 0)
        max_dd = abs(results.get('max_drawdown_pct', 100))
        trades = results.get('total_trades', 0)
        
        # Penalize bad performance
        if alpha < -100:
            return -1000
        
        # Penalize overtrading
        period_years = len(df) / 365
        trades_per_year = trades / period_years if period_years > 0 else 0
        trade_penalty = max(0, (trades_per_year - 20) * 10)
        
        # Penalize high drawdown
        dd_penalty = max(0, (max_dd - 60) * 5)
        
        # Score: weighted combination
        sharpe_score = sharpe * 40
        alpha_score = (alpha / 100) * 30
        dd_score = (100 - max_dd) / 100 * 20
        trade_score = max(0, (20 - trades_per_year) / 20) * 10
        
        total_score = sharpe_score + alpha_score + dd_score + trade_score - trade_penalty - dd_penalty
        
        # Store metrics
        trial.set_user_attr('total_return', total_return)
        trial.set_user_attr('alpha', alpha)
        trial.set_user_attr('sharpe', sharpe)
        trial.set_user_attr('max_dd', max_dd)
        trial.set_user_attr('trades', trades)
        trial.set_user_attr('trades_per_year', trades_per_year)
        
        return total_score
        
    except Exception as e:
        return -1000


def test_parameters(df, sma_period, bh_return):
    """Test specific parameters on a dataset."""
    engine = BacktestEngine(initial_cash=100000, commission=0.001)
    
    results = engine.run_backtest(
        strategy_cls=WalkForwardSMAStrategy,
        data_df=df,
        symbol='BTC-USD',
        sma_period=sma_period,
        verbose=False
    )
    
    final_value = results.get('final_value', 100000)
    total_return = ((final_value / 100000) - 1) * 100
    alpha = total_return - bh_return
    sharpe = results.get('sharpe_ratio', 0)
    max_dd = abs(results.get('max_drawdown_pct', 0))
    trades = results.get('total_trades', 0)
    
    return {
        'total_return': total_return,
        'alpha': alpha,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'trades': trades
    }


def main():
    print("\n" + "="*80)
    print("🔬 WALK-FORWARD OPTIMIZATION WITH OPTUNA")
    print("="*80)
    print("Proper validation: Optimize on train, test on unseen data")
    print("Goal: Find parameters that generalize, not overfit")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. LOAD AND SPLIT DATA
    # =========================================================================
    print("📊 Loading BTC-USD data...")
    data_engine = DataEngine()
    df_full = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-12-31'
    )
    print(f"✅ Loaded {len(df_full)} days of data\n")
    
    # Define periods
    periods = [
        {
            'name': 'Period 1',
            'train_start': '2020-01-01', 'train_end': '2020-12-31',
            'test_start': '2021-01-01', 'test_end': '2021-12-31'
        },
        {
            'name': 'Period 2',
            'train_start': '2022-01-01', 'train_end': '2022-12-31',
            'test_start': '2023-01-01', 'test_end': '2023-12-31'
        },
        {
            'name': 'Period 3',
            'train_start': '2024-01-01', 'train_end': '2024-12-31',
            'test_start': '2025-01-01', 'test_end': '2025-12-31'
        }
    ]
    
    print("📅 Walk-Forward Periods:")
    for p in periods:
        print(f"   {p['name']}:")
        print(f"      Train: {p['train_start']} to {p['train_end']}")
        print(f"      Test:  {p['test_start']} to {p['test_end']}")
    print()
    
    # =========================================================================
    # 2. WALK-FORWARD OPTIMIZATION
    # =========================================================================
    all_results = []
    
    for period in periods:
        print("\n" + "="*80)
        print(f"🔍 {period['name']}: {period['train_start'][:4]} → {period['test_start'][:4]}")
        print("="*80 + "\n")
        
        # Split data
        train_df = df_full[(df_full.index >= period['train_start']) & 
                           (df_full.index <= period['train_end'])]
        test_df = df_full[(df_full.index >= period['test_start']) & 
                          (df_full.index <= period['test_end'])]
        
        print(f"📊 Data split:")
        print(f"   Train: {len(train_df)} days ({train_df.index[0].date()} to {train_df.index[-1].date()})")
        print(f"   Test:  {len(test_df)} days ({test_df.index[0].date()} to {test_df.index[-1].date()})\n")
        
        # Calculate B&H for both periods
        train_bh = calculate_bh_return(train_df)
        test_bh = calculate_bh_return(test_df)
        
        print(f"📈 Buy & Hold benchmark:")
        print(f"   Train: +{train_bh:.1f}%")
        print(f"   Test:  +{test_bh:.1f}%\n")
        
        # Optimize on training period
        print("🔬 Optimizing on training data (50 trials)...")
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        study.optimize(
            lambda trial: objective_train(trial, train_df, train_bh),
            n_trials=50,
            show_progress_bar=True
        )
        
        best_trial = study.best_trial
        best_sma = best_trial.params['sma_period']
        
        print(f"\n✅ Best parameters on TRAIN:")
        print(f"   SMA Period: {best_sma}")
        print(f"   Train Return: +{best_trial.user_attrs['total_return']:.1f}%")
        print(f"   Train Alpha: {best_trial.user_attrs['alpha']:+.1f}%")
        print(f"   Train Sharpe: {best_trial.user_attrs['sharpe']:.2f}")
        print(f"   Train Max DD: {best_trial.user_attrs['max_dd']:.1f}%")
        print(f"   Train Trades: {best_trial.user_attrs['trades']}")
        
        # Test on unseen test period
        print(f"\n🧪 Testing on UNSEEN test data...")
        test_results = test_parameters(test_df, best_sma, test_bh)
        
        print(f"\n📊 Results on TEST (unseen data):")
        print(f"   Test Return: +{test_results['total_return']:.1f}%")
        print(f"   Test Alpha: {test_results['alpha']:+.1f}%")
        print(f"   Test Sharpe: {test_results['sharpe']:.2f}")
        print(f"   Test Max DD: {test_results['max_dd']:.1f}%")
        print(f"   Test Trades: {test_results['trades']}")
        
        # Store results
        all_results.append({
            'period': period['name'],
            'train_years': f"{period['train_start'][:4]}",
            'test_years': f"{period['test_start'][:4]}",
            'best_sma': best_sma,
            'train_bh': train_bh,
            'train_return': best_trial.user_attrs['total_return'],
            'train_alpha': best_trial.user_attrs['alpha'],
            'test_bh': test_bh,
            'test_return': test_results['total_return'],
            'test_alpha': test_results['alpha'],
            'test_sharpe': test_results['sharpe'],
            'test_dd': test_results['max_dd'],
            'test_trades': test_results['trades']
        })
    
    # =========================================================================
    # 3. SUMMARY ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("📊 WALK-FORWARD VALIDATION SUMMARY")
    print("="*80 + "\n")
    
    print(f"{'Period':<12} {'Train':<8} {'Test':<8} {'SMA':<6} {'Train α':<10} {'Test α':<10} {'Test Sharpe':<12} {'Test DD':<10}")
    print("-" * 95)
    
    for r in all_results:
        print(f"{r['period']:<12} "
              f"{r['train_years']:<8} "
              f"{r['test_years']:<8} "
              f"{r['best_sma']:<6} "
              f"{r['train_alpha']:>8.1f}% "
              f"{r['test_alpha']:>8.1f}% "
              f"{r['test_sharpe']:>10.2f} "
              f"{r['test_dd']:>8.1f}%")
    
    # =========================================================================
    # 4. ROBUSTNESS ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("🔍 ROBUSTNESS ANALYSIS")
    print("="*80 + "\n")
    
    test_alphas = [r['test_alpha'] for r in all_results]
    test_sharpes = [r['test_sharpe'] for r in all_results]
    best_smas = [r['best_sma'] for r in all_results]
    
    avg_test_alpha = sum(test_alphas) / len(test_alphas)
    min_test_alpha = min(test_alphas)
    max_test_alpha = max(test_alphas)
    
    avg_test_sharpe = sum(test_sharpes) / len(test_sharpes)
    
    winning_periods = sum(1 for alpha in test_alphas if alpha > 0)
    
    print(f"Test Alpha Statistics:")
    print(f"   Average: {avg_test_alpha:+.1f}%")
    print(f"   Range: {min_test_alpha:+.1f}% to {max_test_alpha:+.1f}%")
    print(f"   Winning periods: {winning_periods}/{len(test_alphas)}")
    
    print(f"\nTest Sharpe Statistics:")
    print(f"   Average: {avg_test_sharpe:.2f}")
    
    print(f"\nOptimized SMA Periods:")
    print(f"   Values: {', '.join(map(str, best_smas))}")
    print(f"   Average: {sum(best_smas)/len(best_smas):.0f}")
    print(f"   Range: {min(best_smas)} to {max(best_smas)}")
    
    # Parameter stability
    sma_std = pd.Series(best_smas).std()
    sma_mean = pd.Series(best_smas).mean()
    sma_cv = (sma_std / sma_mean) * 100 if sma_mean != 0 else 0
    
    print(f"\nParameter Stability:")
    print(f"   Coefficient of Variation: {sma_cv:.1f}%")
    if sma_cv < 20:
        print(f"   ✅ Stable parameters (CV < 20%)")
    elif sma_cv < 40:
        print(f"   ⚠️  Moderate stability (20% < CV < 40%)")
    else:
        print(f"   ❌ Unstable parameters (CV > 40%)")
    
    # =========================================================================
    # 5. FINAL VERDICT
    # =========================================================================
    print("\n" + "="*80)
    print("🎯 FINAL VERDICT")
    print("="*80 + "\n")
    
    # Check consistency
    is_consistent = (min_test_alpha / max_test_alpha if max_test_alpha != 0 else 0) > 0.3
    all_win = winning_periods == len(test_alphas)
    stable_params = sma_cv < 40
    
    if all_win and is_consistent and stable_params:
        print("✅ ROBUST STRATEGY VALIDATED!")
        print("\nKey findings:")
        print(f"   • Wins in ALL {len(test_alphas)} test periods")
        print(f"   • Average test alpha: {avg_test_alpha:+.1f}%")
        print(f"   • Stable parameters across periods (CV: {sma_cv:.1f}%)")
        print(f"   • Recommended SMA: {int(sum(best_smas)/len(best_smas))}")
        
        print("\n🚀 DEPLOYMENT RECOMMENDATION: ✅ APPROVED")
        print("   Strategy shows genuine robustness across different market regimes")
        
    elif winning_periods >= 2 and stable_params:
        print("⚠️  PARTIALLY ROBUST")
        print(f"\nWins in {winning_periods}/{len(test_alphas)} test periods")
        print(f"Average test alpha: {avg_test_alpha:+.1f}%")
        
        losing_periods = [r for r in all_results if r['test_alpha'] < 0]
        if losing_periods:
            print(f"\n⚠️  Underperforms in:")
            for r in losing_periods:
                print(f"   • {r['period']} ({r['test_years']}): {r['test_alpha']:+.1f}% alpha")
        
        print("\n💭 DEPLOYMENT RECOMMENDATION: ⚠️  USE WITH CAUTION")
        print("   Consider ensemble with other strategies or regime detection")
        
    else:
        print("❌ STRATEGY NOT ROBUST")
        print(f"\nOnly wins in {winning_periods}/{len(test_alphas)} test periods")
        print(f"Average test alpha: {avg_test_alpha:+.1f}%")
        
        if not stable_params:
            print(f"\n⚠️  Unstable parameters (CV: {sma_cv:.1f}%)")
            print("   Different optimal periods for each regime suggests overfitting")
        
        print("\n🚫 DEPLOYMENT RECOMMENDATION: ❌ DO NOT DEPLOY")
        print("   Strategy fails generalization test - likely overfit")
        print("   Consider:")
        print("   • Using fixed conservative parameters (e.g., SMA-150)")
        print("   • Simpler strategy with less optimization")
        print("   • Longer training periods with more data")
    
    # =========================================================================
    # 6. COMPARISON WITH PREVIOUS APPROACHES
    # =========================================================================
    print("\n" + "="*80)
    print("📊 COMPARISON: Walk-Forward vs Full-Period Optimization")
    print("="*80 + "\n")
    
    print("Previous approach (SMA-110, optimized on full 2020-2025):")
    print("   Full period alpha: +897% ← Looks amazing!")
    print("   But fails on 2/3 independent test periods ← Overfit!")
    
    print(f"\nWalk-forward approach (optimized separately for each period):")
    print(f"   Average test alpha: {avg_test_alpha:+.1f}%")
    print(f"   Wins {winning_periods}/{len(test_alphas)} test periods")
    print(f"   Parameters: {', '.join(f'SMA-{sma}' for sma in best_smas)}")
    
    if avg_test_alpha > 0:
        print(f"\n✅ Walk-forward shows REAL alpha: {avg_test_alpha:+.1f}%")
        print("   This is the true expected performance on unseen data")
    else:
        print(f"\n❌ Walk-forward reveals strategy doesn't work")
        print("   Full-period optimization was misleading")
    
    print("\n💡 KEY LESSON:")
    print("   Always validate with walk-forward on truly unseen test data!")
    print("   Full-period optimization can be deceptive")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
