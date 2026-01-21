#!/usr/bin/env python3
"""
Regime-Based Optimization with Optuna

Smart training plan:
1. Split data by MARKET REGIME (not just years)
2. Use shorter periods (weeks/months, not full years)
3. Train on regime examples, test on OTHER examples of SAME regime
4. Validate if parameters are stable WITHIN each regime type

Regime Classification:
- BULL: Strong uptrend (BTC gaining >20% in period)
- BEAR: Strong downtrend (BTC losing >20% in period)  
- SIDEWAYS: Consolidation (BTC +/-20% range)

Strategy:
- Find best SMA for BULL regimes
- Find best SMA for BEAR regimes
- Test if we should even trade in SIDEWAYS
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


def classify_regime(df: pd.DataFrame, start_date: str, end_date: str) -> str:
    """
    Classify market regime based on price change in period.
    
    Returns: 'BULL', 'BEAR', or 'SIDEWAYS'
    """
    period_df = df.loc[start_date:end_date]
    
    if len(period_df) < 2:
        return 'UNKNOWN'
    
    start_price = period_df.iloc[0]['close']
    end_price = period_df.iloc[-1]['close']
    change_pct = ((end_price - start_price) / start_price) * 100
    
    if change_pct > 20:
        return 'BULL'
    elif change_pct < -20:
        return 'BEAR'
    else:
        return 'SIDEWAYS'


def define_regime_periods() -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Define training and test periods for each regime.
    
    Returns dict with structure:
    {
        'BULL': [
            ('2020-03-01', '2020-12-31', 'TRAIN'),  # Post-COVID rally
            ('2024-01-01', '2024-06-30', 'TRAIN'),  # ETF/Halving rally
            ('2024-07-01', '2024-11-24', 'TEST'),   # Recent continuation
        ],
        'BEAR': [...],
        'SIDEWAYS': [...]
    }
    """
    
    periods = {
        'BULL': [
            # Training periods
            ('2020-03-01', '2020-12-31', 'TRAIN'),  # COVID recovery: $5k → $29k
            ('2023-01-01', '2023-06-30', 'TRAIN'),  # Recovery from FTX: $16k → $30k
            ('2024-01-01', '2024-06-30', 'TRAIN'),  # ETF/Halving: $42k → $71k
            
            # Test periods
            ('2021-01-01', '2021-04-30', 'TEST'),   # Early 2021 rally: $29k → $63k
            ('2024-07-01', '2024-11-24', 'TEST'),   # Post-halving: $62k → $98k
        ],
        
        'BEAR': [
            # Training periods
            ('2021-05-01', '2021-07-31', 'TRAIN'),  # May crash: $58k → $29k
            ('2022-01-01', '2022-06-30', 'TRAIN'),  # Early 2022 crash: $46k → $20k
            
            # Test periods
            ('2021-11-01', '2022-12-31', 'TEST'),   # Peak to bottom: $69k → $16k (long bear)
            ('2022-07-01', '2022-11-30', 'TEST'),   # Continued weakness: $20k → $17k
        ],
        
        'SIDEWAYS': [
            # Training periods
            ('2021-08-01', '2021-09-30', 'TRAIN'),  # Summer consolidation: $38k-$48k
            ('2023-07-01', '2023-10-31', 'TRAIN'),  # Mid-2023 range: $29k-$31k
            
            # Test periods
            ('2021-09-01', '2021-10-31', 'TEST'),   # Sept-Oct range: $41k-$55k
            ('2023-11-01', '2023-12-31', 'TEST'),   # Late 2023: $34k-$44k
        ],
    }
    
    return periods


def objective_regime(trial, df: pd.DataFrame, regime: str, train_periods: List[Tuple[str, str]]) -> float:
    """
    Optuna objective function for a specific regime.
    
    Args:
        trial: Optuna trial
        df: Full dataframe
        regime: 'BULL', 'BEAR', or 'SIDEWAYS'
        train_periods: List of (start_date, end_date) tuples for training
    
    Returns:
        Score (higher is better)
    """
    # Suggest SMA period based on regime
    if regime == 'BULL':
        # Bull: try faster SMAs to capture momentum
        sma_period = trial.suggest_int('sma_period', 20, 100, step=5)
    elif regime == 'BEAR':
        # Bear: try slower SMAs to exit early
        sma_period = trial.suggest_int('sma_period', 50, 200, step=10)
    else:  # SIDEWAYS
        # Sideways: try full range (but likely nothing will work)
        sma_period = trial.suggest_int('sma_period', 30, 150, step=10)
    
    # Combine all training periods for this regime
    total_return = 0
    total_sharpe = 0
    total_trades = 0
    num_periods = len(train_periods)
    
    for start_date, end_date in train_periods:
        # Get period data
        period_df = df.loc[start_date:end_date].copy()
        
        if len(period_df) < 30:  # Skip if too short
            continue
        
        # Calculate buy & hold for this period
        bh_return = ((period_df.iloc[-1]['close'] - period_df.iloc[0]['close']) 
                     / period_df.iloc[0]['close']) * 100
        
        # Run backtest
        engine = BacktestEngine(
            initial_cash=100000.0,
            commission=0.001
        )
        
        try:
            result = engine.run_backtest(
                strategy_cls=RegimeSMAStrategy,
                data_df=period_df,
                symbol='BTCUSDT',
                sma_period=sma_period,
                verbose=False
            )
            
            strategy_return = result['return_pct']
            
            # Calculate alpha for this period
            alpha = strategy_return - bh_return
            
            # Sharpe-like score (return / volatility proxy)
            sharpe_proxy = strategy_return / max(abs(bh_return), 10)  # Normalize by period volatility
            
            total_return += alpha
            total_sharpe += sharpe_proxy
            
            # Count trades from analyzer
            trades_analysis = result.get('analyzers', {}).get('trades', {})
            if trades_analysis and 'total' in trades_analysis:
                total_trades += trades_analysis['total'].get('total', 0)
        
        except Exception as e:
            continue
    
    if num_periods == 0:
        return -999999
    
    # Average metrics across all training periods
    avg_alpha = total_return / num_periods
    avg_sharpe = total_sharpe / num_periods
    avg_trades_per_period = total_trades / num_periods
    
    # Scoring function
    score = (
        avg_alpha * 0.5 +           # 50% weight on alpha
        avg_sharpe * 30 +            # 30% weight on risk-adjusted return
        min(avg_trades_per_period / 2, 5) * 2  # 20% weight on reasonable trading (cap at 5)
    )
    
    # Penalize too many trades (overtrading)
    if avg_trades_per_period > 10:
        score -= (avg_trades_per_period - 10) * 5
    
    # Penalize too few trades (not catching the trend)
    if avg_trades_per_period < 1:
        score -= 20
    
    return score


def test_on_regime(df: pd.DataFrame, regime: str, sma_period: int, test_periods: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Test optimized parameters on unseen test periods of the same regime.
    
    Returns:
        Dict with aggregate results across all test periods
    """
    results_list = []
    
    for start_date, end_date in test_periods:
        period_df = df.loc[start_date:end_date].copy()
        
        if len(period_df) < 30:
            continue
        
        # Buy & hold benchmark
        bh_start = period_df.iloc[0]['close']
        bh_end = period_df.iloc[-1]['close']
        bh_return = ((bh_end - bh_start) / bh_start) * 100
        
        # Run strategy
        engine = BacktestEngine(
            initial_cash=100000.0,
            commission=0.001
        )
        
        try:
            result = engine.run_backtest(
                strategy_cls=RegimeSMAStrategy,
                data_df=period_df,
                symbol='BTCUSDT',
                sma_period=sma_period,
                verbose=False
            )
            
            strategy_return = result['return_pct']
            alpha = strategy_return - bh_return
            
            # Get trades from analyzer
            trades_analysis = result.get('analyzers', {}).get('trades', {})
            num_trades = 0
            if trades_analysis and 'total' in trades_analysis:
                num_trades = trades_analysis['total'].get('total', 0)
            
            results_list.append({
                'period': f"{start_date} to {end_date}",
                'bh_return': bh_return,
                'strategy_return': strategy_return,
                'alpha': alpha,
                'num_trades': num_trades,
            })
        
        except Exception as e:
            print(f"Error testing {start_date} to {end_date}: {e}")
            continue
    
    if not results_list:
        return {
            'avg_alpha': -999,
            'win_rate': 0,
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
    print("REGIME-BASED OPTUNA OPTIMIZATION")
    print("="*80)
    print()
    
    # Load data
    df = load_btc_data()
    print()
    
    # Define periods
    regime_periods = define_regime_periods()
    
    # Verify regime classifications
    print("="*80)
    print("REGIME CLASSIFICATION VERIFICATION")
    print("="*80)
    for regime, periods in regime_periods.items():
        print(f"\n{regime} Regime:")
        for start, end, split in periods:
            actual_regime = classify_regime(df, start, end)
            period_df = df.loc[start:end]
            change = ((period_df.iloc[-1]['close'] - period_df.iloc[0]['close']) / period_df.iloc[0]['close']) * 100
            status = "✅" if actual_regime == regime else f"⚠️  (Actually {actual_regime})"
            print(f"  {split:5s} | {start} to {end} | Change: {change:+6.1f}% {status}")
    print()
    
    # Optimize for each regime
    regime_results = {}
    
    for regime in ['BULL', 'BEAR', 'SIDEWAYS']:
        print("="*80)
        print(f"OPTIMIZING FOR {regime} REGIME")
        print("="*80)
        
        periods = regime_periods[regime]
        train_periods = [(start, end) for start, end, split in periods if split == 'TRAIN']
        test_periods = [(start, end) for start, end, split in periods if split == 'TEST']
        
        print(f"\nTraining on {len(train_periods)} periods:")
        for start, end in train_periods:
            print(f"  - {start} to {end}")
        
        print(f"\nWill test on {len(test_periods)} periods:")
        for start, end in test_periods:
            print(f"  - {start} to {end}")
        print()
        
        # Run Optuna optimization
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        print(f"Running 50 trials for {regime} regime...")
        study.optimize(
            lambda trial: objective_regime(trial, df, regime, train_periods),
            n_trials=50,
            show_progress_bar=True
        )
        
        best_params = study.best_trial.params
        best_sma = best_params['sma_period']
        
        print(f"\n✅ Best SMA for {regime}: {best_sma}")
        print(f"   Training score: {study.best_trial.value:.2f}")
        print()
        
        # Test on unseen periods
        print(f"Testing SMA-{best_sma} on {len(test_periods)} TEST periods...")
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
        
        for period_result in test_results['periods']:
            alpha_status = "✅" if period_result['alpha'] > 0 else "❌"
            print(f"{alpha_status} {period_result['period']}")
            print(f"   B&H: {period_result['bh_return']:+.1f}% | Strategy: {period_result['strategy_return']:+.1f}% | Alpha: {period_result['alpha']:+.1f}%")
            print(f"   Trades: {period_result['num_trades']}")
        
        print(f"\n📊 AGGREGATE TEST METRICS:")
        print(f"   Average Alpha: {test_results['avg_alpha']:+.1f}%")
        print(f"   Win Rate: {test_results['win_rate']:.0f}% ({int(test_results['win_rate']/100*test_results['num_test_periods'])}/{test_results['num_test_periods']})")
        print()
    
    # Final summary
    print("="*80)
    print("FINAL SUMMARY - REGIME-BASED OPTIMIZATION")
    print("="*80)
    print()
    
    print("Optimized Parameters by Regime:")
    print("-" * 80)
    for regime in ['BULL', 'BEAR', 'SIDEWAYS']:
        results = regime_results[regime]
        test_res = results['test_results']
        
        status = "✅ ROBUST" if test_res['avg_alpha'] > 5 and test_res['win_rate'] >= 60 else "❌ NOT ROBUST"
        
        print(f"\n{regime:9s} | SMA-{results['best_sma']:3d} | Test Alpha: {test_res['avg_alpha']:+6.1f}% | Win Rate: {test_res['win_rate']:3.0f}% | {status}")
    
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)
    
    # Check if any regime is truly robust
    robust_regimes = []
    for regime, results in regime_results.items():
        test_res = results['test_results']
        if test_res['avg_alpha'] > 5 and test_res['win_rate'] >= 60:
            robust_regimes.append(regime)
    
    if robust_regimes:
        print(f"\n✅ ROBUST REGIMES: {', '.join(robust_regimes)}")
        print(f"\n💡 RECOMMENDATION:")
        print(f"   Use regime detection to identify market state, then apply:")
        for regime in robust_regimes:
            sma = regime_results[regime]['best_sma']
            print(f"   - {regime}: SMA-{sma}")
        print(f"   - Other regimes: Stay in Buy & Hold or don't trade")
    else:
        print(f"\n❌ NO ROBUST REGIMES FOUND")
        print(f"\n💡 CONCLUSION:")
        print(f"   Even with regime-based optimization, no consistent edge found.")
        print(f"   Parameters that work in training don't generalize to test periods.")
        print(f"\n   🚫 RECOMMENDATION: Stick with Buy & Hold")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
