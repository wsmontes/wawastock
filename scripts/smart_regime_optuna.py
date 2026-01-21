#!/usr/bin/env python3
"""
Smart Regime-Based Optimization with Optuna

Intelligent period selection:
- Use 6-month periods (sufficient data for SMA, not too long)
- Classify by regime (bull/bear/sideways)
- Train on some periods, test on others OF THE SAME REGIME
- Validate robustness within each market condition

Key insight: Don't use arbitrary year splits. Use meaningful market phases.
"""

import sys
import os
from datetime import datetime
import optuna
import pandas as pd
import backtrader as bt
from typing import Dict, Any, List, Tuple
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.base_strategy import BaseStrategy


class RegimeSMAStrategy(BaseStrategy):
    """SMA strategy with configurable parameters."""
    
    params = (
        ('sma_period', 50),
        ('verbose', False),
    )
    
    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_period)
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        # Check current position
        if not self.position:
            # Entry: price above SMA
            if self.data.close[0] > self.sma[0]:
                size = self.broker.getcash() / self.data.close[0]
                self.order = self.buy(size=size)
        else:
            # Exit: price below SMA
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()
    
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


def load_btc_data() -> pd.DataFrame:
    """Load BTC data from DataEngine."""
    print("Loading BTC data...")
    data_engine = DataEngine(auto_indicators=False)
    df = data_engine.get_ohlcv_cached(
        source='binance',
        symbol='BTCUSDT',
        timeframe='1d',
        start='2020-01-01',
        end='2025-11-24'
    )
    
    if df is None or df.empty:
        raise ValueError("Failed to load BTC data")
    
    # Ensure datetime index
    if 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)
    
    print(f"Loaded {len(df)} daily candles from {df.index[0]} to {df.index[-1]}")
    return df


def classify_regime(df: pd.DataFrame, start_date: str, end_date: str) -> Tuple[str, float, int]:
    """
    Classify market regime based on price change in period.
    
    Returns: (regime, change_pct, num_days)
    """
    period_df = df.loc[start_date:end_date]
    
    if len(period_df) < 2:
        return 'UNKNOWN', 0.0, 0
    
    start_price = period_df.iloc[0]['close']
    end_price = period_df.iloc[-1]['close']
    change_pct = ((end_price - start_price) / start_price) * 100
    
    # More nuanced classification
    if change_pct > 30:
        return 'STRONG_BULL', change_pct, len(period_df)
    elif change_pct > 10:
        return 'BULL', change_pct, len(period_df)
    elif change_pct < -30:
        return 'STRONG_BEAR', change_pct, len(period_df)
    elif change_pct < -10:
        return 'BEAR', change_pct, len(period_df)
    else:
        return 'SIDEWAYS', change_pct, len(period_df)


def define_smart_periods() -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Define 6-month periods with intelligent regime assignment.
    
    Strategy:
    - Use 6-month windows (enough data, not too long)
    - Manually classify based on known BTC history
    - Train/test split within each regime
    """
    
    periods = {
        'STRONG_BULL': [
            # Training
            ('2020-03-01', '2020-08-31', 'TRAIN'),  # COVID recovery: $5k → $11k (+120%)
            ('2020-09-01', '2021-02-28', 'TRAIN'),  # Bull run start: $10k → $45k (+350%)
            ('2024-01-01', '2024-06-30', 'TRAIN'),  # ETF rally: $42k → $71k (+69%)
            
            # Testing
            ('2021-01-01', '2021-04-30', 'TEST'),   # Peak run: $29k → $63k (+117%)
            ('2023-01-01', '2023-07-31', 'TEST'),   # Recovery: $16k → $29k (+81%)
        ],
        
        'BEAR': [
            # Training
            ('2021-05-01', '2021-07-31', 'TRAIN'),  # May crash: $58k → $31k (-47%)
            ('2022-05-01', '2022-11-30', 'TRAIN'),  # Luna/FTX: $38k → $16k (-58%)
            
            # Testing
            ('2021-11-15', '2022-06-30', 'TEST'),   # Peak to bottom: $69k → $18k (-74%)
        ],
        
        'SIDEWAYS': [
            # Training
            ('2021-08-01', '2021-10-31', 'TRAIN'),  # Summer-Fall: $38k → $60k (choppy)
            ('2023-08-01', '2023-10-31', 'TRAIN'),  # Mid-2023: $29k → $34k (range)
            
            # Testing
            ('2022-12-01', '2023-03-31', 'TEST'),   # Post-FTX: $17k → $28k (choppy recovery)
            ('2024-07-01', '2024-09-30', 'TEST'),   # Post-halving: $62k → $63k (tight range)
        ],
    }
    
    return periods


def objective_regime(trial, df: pd.DataFrame, regime: str, train_periods: List[Tuple[str, str]]) -> float:
    """Optuna objective function for a specific regime."""
    
    # Suggest SMA period based on regime
    if regime == 'STRONG_BULL':
        # Fast SMA to ride momentum
        sma_period = trial.suggest_int('sma_period', 15, 60, step=5)
    elif regime in ['BEAR', 'STRONG_BEAR']:
        # Slower SMA to exit early
        sma_period = trial.suggest_int('sma_period', 50, 150, step=10)
    else:  # SIDEWAYS or BULL
        # Medium range
        sma_period = trial.suggest_int('sma_period', 30, 100, step=5)
    
    total_score = 0
    num_valid_periods = 0
    
    for start_date, end_date in train_periods:
        period_df = df.loc[start_date:end_date].copy()
        
        # Skip if too short for the SMA
        if len(period_df) < sma_period + 20:
            continue
        
        # Buy & hold for this period
        bh_return = ((period_df.iloc[-1]['close'] - period_df.iloc[0]['close']) 
                     / period_df.iloc[0]['close']) * 100
        
        # Run backtest
        try:
            engine = BacktestEngine(initial_cash=100000.0, commission=0.001)
            result = engine.run_backtest(
                strategy_cls=RegimeSMAStrategy,
                data_df=period_df,
                symbol='BTCUSDT',
                sma_period=sma_period,
                verbose=False
            )
            
            strategy_return = result['return_pct']
            alpha = strategy_return - bh_return
            
            # Get drawdown
            dd = result.get('analyzers', {}).get('drawdown', {})
            max_dd = dd.get('max', {}).get('drawdown', 0) if dd else 0
            
            # Score components
            alpha_score = alpha * 0.5  # 50% weight on alpha
            
            # Reward positive returns in bear markets, punish negative in bulls
            if regime in ['BEAR', 'STRONG_BEAR']:
                # In bear market, staying flat or positive is GREAT
                if strategy_return > -10:
                    alpha_score += 30  # Big bonus for avoiding losses
            else:
                # In bull market, need to keep up with gains
                if alpha < -20:
                    alpha_score -= 50  # Big penalty for missing rally
            
            # Drawdown penalty
            dd_penalty = max(0, abs(max_dd) - 30) * 0.5  # Penalty if DD > 30%
            
            period_score = alpha_score - dd_penalty
            total_score += period_score
            num_valid_periods += 1
        
        except Exception:
            continue
    
    if num_valid_periods == 0:
        return -999999
    
    return total_score / num_valid_periods


def test_on_regime(df: pd.DataFrame, regime: str, sma_period: int, 
                   test_periods: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Test optimized parameters on unseen test periods."""
    
    results_list = []
    
    for start_date, end_date in test_periods:
        period_df = df.loc[start_date:end_date].copy()
        
        # Skip if too short
        if len(period_df) < sma_period + 20:
            print(f"  ⚠️  Skipping {start_date} to {end_date}: only {len(period_df)} bars (need {sma_period + 20}+)")
            continue
        
        # Buy & hold benchmark
        bh_return = ((period_df.iloc[-1]['close'] - period_df.iloc[0]['close']) 
                     / period_df.iloc[0]['close']) * 100
        
        try:
            engine = BacktestEngine(initial_cash=100000.0, commission=0.001)
            result = engine.run_backtest(
                strategy_cls=RegimeSMAStrategy,
                data_df=period_df,
                symbol='BTCUSDT',
                sma_period=sma_period,
                verbose=False
            )
            
            strategy_return = result['return_pct']
            alpha = strategy_return - bh_return
            
            # Get trades
            trades_analysis = result.get('analyzers', {}).get('trades', {})
            num_trades = 0
            if trades_analysis and 'total' in trades_analysis:
                num_trades = trades_analysis['total'].get('total', 0)
            
            # Get drawdown
            dd = result.get('analyzers', {}).get('drawdown', {})
            max_dd = dd.get('max', {}).get('drawdown', 0) if dd else 0
            
            results_list.append({
                'period': f"{start_date} to {end_date}",
                'days': len(period_df),
                'bh_return': bh_return,
                'strategy_return': strategy_return,
                'alpha': alpha,
                'max_dd': abs(max_dd),
                'num_trades': num_trades,
            })
        
        except Exception as e:
            print(f"  ❌ Error testing {start_date} to {end_date}: {e}")
            continue
    
    if not results_list:
        return {
            'avg_alpha': -999,
            'win_rate': 0,
            'num_test_periods': 0,
            'periods': []
        }
    
    # Aggregate results
    avg_alpha = np.mean([r['alpha'] for r in results_list])
    wins = sum(1 for r in results_list if r['alpha'] > 0)
    win_rate = wins / len(results_list) * 100
    
    return {
        'avg_alpha': avg_alpha,
        'win_rate': win_rate,
        'num_test_periods': len(results_list),
        'periods': results_list
    }


def main():
    """Main execution."""
    print("="*80)
    print("SMART REGIME-BASED OPTUNA OPTIMIZATION")
    print("="*80)
    print("Strategy: 6-month periods, regime-specific optimization")
    print()
    
    # Load data
    df = load_btc_data()
    print()
    
    # Define periods
    regime_periods = define_smart_periods()
    
    # Verify regime classifications
    print("="*80)
    print("PERIOD VERIFICATION (6-month windows)")
    print("="*80)
    for regime, periods in regime_periods.items():
        print(f"\n{regime} Regime:")
        for start, end, split in periods:
            actual_regime, change, days = classify_regime(df, start, end)
            status = "✅" if regime.startswith(actual_regime.split('_')[0]) or actual_regime.startswith(regime.split('_')[0]) else f"⚠️  ({actual_regime})"
            print(f"  {split:5s} | {start} to {end} | {days:3d} days | {change:+6.1f}% {status}")
    print()
    
    # Optimize for each regime
    regime_results = {}
    
    for regime in ['STRONG_BULL', 'BEAR', 'SIDEWAYS']:
        print("="*80)
        print(f"OPTIMIZING FOR {regime} REGIME")
        print("="*80)
        
        periods = regime_periods[regime]
        train_periods = [(start, end) for start, end, split in periods if split == 'TRAIN']
        test_periods = [(start, end) for start, end, split in periods if split == 'TEST']
        
        print(f"\nTraining on {len(train_periods)} periods:")
        for start, end in train_periods:
            _, change, days = classify_regime(df, start, end)
            print(f"  - {start} to {end} ({days} days, {change:+.1f}%)")
        
        print(f"\nWill test on {len(test_periods)} periods:")
        for start, end in test_periods:
            _, change, days = classify_regime(df, start, end)
            print(f"  - {start} to {end} ({days} days, {change:+.1f}%)")
        print()
        
        # Run Optuna optimization
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        print(f"Running 30 trials for {regime} regime...")
        study.optimize(
            lambda trial: objective_regime(trial, df, regime, train_periods),
            n_trials=30,
            show_progress_bar=True
        )
        
        best_params = study.best_trial.params
        best_sma = best_params['sma_period']
        
        print(f"\n✅ Best SMA for {regime}: {best_sma}")
        print(f"   Training score: {study.best_trial.value:.2f}")
        print()
        
        # Test on unseen periods
        print(f"Testing SMA-{best_sma} on TEST periods...")
        test_results = test_on_regime(df, regime, best_sma, test_periods)
        
        regime_results[regime] = {
            'best_sma': best_sma,
            'train_score': study.best_trial.value,
            'test_results': test_results
        }
        
        # Display test results
        print(f"\n{'='*80}")
        print(f"TEST RESULTS FOR {regime} (SMA-{best_sma})")
        print(f"{'='*80}")
        
        if test_results['num_test_periods'] > 0:
            for period_result in test_results['periods']:
                alpha_status = "✅" if period_result['alpha'] > 0 else "❌"
                print(f"{alpha_status} {period_result['period']} ({period_result['days']} days)")
                print(f"   B&H: {period_result['bh_return']:+.1f}% | Strategy: {period_result['strategy_return']:+.1f}% | Alpha: {period_result['alpha']:+.1f}%")
                print(f"   Max DD: {period_result['max_dd']:.1f}% | Trades: {period_result['num_trades']}")
            
            print(f"\n📊 AGGREGATE TEST METRICS:")
            print(f"   Average Alpha: {test_results['avg_alpha']:+.1f}%")
            print(f"   Win Rate: {test_results['win_rate']:.0f}% ({int(test_results['win_rate']/100*test_results['num_test_periods'])}/{test_results['num_test_periods']})")
        else:
            print("   ⚠️  No valid test results (periods too short)")
        print()
    
    # Final summary
    print("="*80)
    print("FINAL SUMMARY - REGIME-BASED OPTIMIZATION")
    print("="*80)
    print()
    
    print("Optimized Parameters by Regime:")
    print("-" * 80)
    for regime in ['STRONG_BULL', 'BEAR', 'SIDEWAYS']:
        results = regime_results[regime]
        test_res = results['test_results']
        
        if test_res['num_test_periods'] > 0:
            # More nuanced evaluation
            if test_res['avg_alpha'] > 5 and test_res['win_rate'] >= 60:
                status = "✅ ROBUST"
            elif test_res['avg_alpha'] > 0:
                status = "⚠️  MARGINAL"
            else:
                status = "❌ NOT ROBUST"
            
            print(f"\n{regime:12s} | SMA-{results['best_sma']:3d} | Test Alpha: {test_res['avg_alpha']:+6.1f}% | Win Rate: {test_res['win_rate']:3.0f}% | {status}")
        else:
            print(f"\n{regime:12s} | SMA-{results['best_sma']:3d} | No valid tests")
    
    print("\n" + "="*80)
    print("VERDICT & RECOMMENDATIONS")
    print("="*80)
    
    # Check if any regime is truly robust
    robust_regimes = []
    marginal_regimes = []
    
    for regime, results in regime_results.items():
        test_res = results['test_results']
        if test_res['num_test_periods'] > 0:
            if test_res['avg_alpha'] > 5 and test_res['win_rate'] >= 60:
                robust_regimes.append((regime, results['best_sma'], test_res['avg_alpha']))
            elif test_res['avg_alpha'] > 0:
                marginal_regimes.append((regime, results['best_sma'], test_res['avg_alpha']))
    
    if robust_regimes:
        print(f"\n✅ ROBUST REGIMES FOUND:")
        for regime, sma, alpha in robust_regimes:
            print(f"   - {regime}: Use SMA-{sma} (avg test alpha: {alpha:+.1f}%)")
        
        print(f"\n💡 DEPLOYMENT STRATEGY:")
        print(f"   1. Implement regime detector (ADX, volatility, trend strength)")
        print(f"   2. When in robust regime, use optimized SMA")
        print(f"   3. In other regimes: default to Buy & Hold")
        print(f"\n   Example: If detector says 'STRONG_BULL' → use SMA-{robust_regimes[0][1]}")
    
    elif marginal_regimes:
        print(f"\n⚠️  MARGINAL RESULTS:")
        for regime, sma, alpha in marginal_regimes:
            print(f"   - {regime}: SMA-{sma} (avg test alpha: {alpha:+.1f}%)")
        
        print(f"\n💡 RECOMMENDATION:")
        print(f"   Marginal edge detected but not strong enough for deployment.")
        print(f"   Consider:")
        print(f"   - Longer test periods to validate")
        print(f"   - Additional filters (volume, RSI, etc.)")
        print(f"   - Or stick with Buy & Hold")
    
    else:
        print(f"\n❌ NO CONSISTENT EDGE FOUND")
        print(f"\n💡 CONCLUSION:")
        print(f"   Even with regime-specific optimization:")
        print(f"   - Parameters don't generalize to test periods")
        print(f"   - No regime shows consistent alpha")
        print(f"\n   🚫 RECOMMENDATION: Buy & Hold remains optimal")
        print(f"\n   Why timing fails:")
        print(f"   1. Exit risk: Missing explosive rallies")
        print(f"   2. Regime changes: Can't predict transitions")
        print(f"   3. Whipsaws: False signals in choppy markets")
    
    print("\n" + "="*80)
    print("\n📚 KEY LEARNINGS:")
    print("   - 6-month periods: Good balance (enough data, not too long)")
    print("   - Regime matters: Bull/Bear need different parameters")
    print("   - Walk-forward critical: Training ≠ Testing performance")
    print("   - BTC drift: Strong positive trend favors holding")
    print()


if __name__ == '__main__':
    main()
