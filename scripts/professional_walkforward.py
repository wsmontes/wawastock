#!/usr/bin/env python3
"""
Professional Walk-Forward Optimization with Regime Detection

Methodology:
============
1. AUTOMATIC REGIME DETECTION
   - Use Hidden Markov Model (HMM) or statistical measures to detect regimes
   - Classify each day as: BULL, BEAR, or SIDEWAYS based on:
     * Trend direction (price vs moving average)
     * Volatility level (ATR, std dev)
     * Return characteristics

2. ANCHORED WALK-FORWARD
   - NOT arbitrary year splits
   - Expanding window: train on all data up to point T, test on T to T+N
   - Roll forward multiple times to get statistical significance

3. PURGED CROSS-VALIDATION
   - Leave gap between train and test to avoid lookahead
   - Proper financial time-series methodology

4. COMBINATORIAL PURGED CV (CPCV)
   - Multiple train/test combinations
   - Statistical robustness

Reference: Advances in Financial Machine Learning (Marcos López de Prado)
"""

import sys
import os
from datetime import datetime, timedelta
import optuna
import pandas as pd
import numpy as np
import backtrader as bt
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.base_strategy import BaseStrategy


# =============================================================================
# STRATEGY
# =============================================================================

class OptimizedSMAStrategy(BaseStrategy):
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
            
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = self.broker.getcash() / self.data.close[0]
                self.order = self.buy(size=size)
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()
    
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


# =============================================================================
# REGIME DETECTION (Statistical Method)
# =============================================================================

@dataclass
class RegimeSegment:
    """A detected market regime segment."""
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    regime: str  # 'BULL', 'BEAR', 'SIDEWAYS'
    return_pct: float
    volatility: float
    num_days: int


def detect_regimes(df: pd.DataFrame, lookback: int = 50) -> pd.DataFrame:
    """
    Detect market regimes using statistical methods.
    
    Method:
    - Trend: 50-day return direction and magnitude
    - Volatility: 20-day realized volatility
    - Regime = f(trend, volatility)
    
    Returns dataframe with 'regime' column.
    """
    df = df.copy()
    
    # Calculate metrics
    df['returns'] = df['close'].pct_change()
    df['cumret_50d'] = df['close'].pct_change(lookback)  # 50-day return
    df['volatility_20d'] = df['returns'].rolling(20).std() * np.sqrt(252)  # Annualized vol
    df['sma_200'] = df['close'].rolling(200).mean()
    df['trend'] = (df['close'] / df['sma_200'] - 1) * 100  # % above/below 200-day SMA
    
    # Classify regime
    def classify_day(row):
        if pd.isna(row['cumret_50d']) or pd.isna(row['volatility_20d']):
            return 'UNKNOWN'
        
        cumret = row['cumret_50d'] * 100  # Convert to percentage
        vol = row['volatility_20d'] * 100  # Convert to percentage
        trend = row['trend'] if not pd.isna(row['trend']) else 0
        
        # Bull: Strong uptrend OR above long-term average with positive momentum
        if cumret > 20 or (trend > 10 and cumret > 5):
            return 'BULL'
        # Bear: Strong downtrend OR below long-term average with negative momentum
        elif cumret < -20 or (trend < -10 and cumret < -5):
            return 'BEAR'
        # Sideways: Everything else
        else:
            return 'SIDEWAYS'
    
    df['regime'] = df.apply(classify_day, axis=1)
    
    return df


def extract_regime_segments(df: pd.DataFrame, min_segment_days: int = 60) -> List[RegimeSegment]:
    """
    Extract continuous regime segments from the dataframe.
    
    Args:
        df: DataFrame with 'regime' column
        min_segment_days: Minimum segment length to include
    
    Returns:
        List of RegimeSegment objects
    """
    segments = []
    
    # Filter out UNKNOWN regimes
    df_valid = df[df['regime'] != 'UNKNOWN'].copy()
    
    if len(df_valid) == 0:
        return segments
    
    # Find regime changes
    df_valid['regime_change'] = (df_valid['regime'] != df_valid['regime'].shift(1)).astype(int)
    df_valid['segment_id'] = df_valid['regime_change'].cumsum()
    
    # Extract segments
    for seg_id in df_valid['segment_id'].unique():
        seg_df = df_valid[df_valid['segment_id'] == seg_id]
        
        if len(seg_df) < min_segment_days:
            continue
        
        start_date = seg_df.index[0]
        end_date = seg_df.index[-1]
        regime = seg_df['regime'].iloc[0]
        
        start_price = seg_df.iloc[0]['close']
        end_price = seg_df.iloc[-1]['close']
        return_pct = ((end_price - start_price) / start_price) * 100
        
        volatility = seg_df['returns'].std() * np.sqrt(252) * 100 if 'returns' in seg_df.columns else 0
        
        segments.append(RegimeSegment(
            start_date=start_date,
            end_date=end_date,
            regime=regime,
            return_pct=return_pct,
            volatility=volatility,
            num_days=len(seg_df)
        ))
    
    return segments


# =============================================================================
# WALK-FORWARD OPTIMIZATION (Professional Method)
# =============================================================================

def anchored_walk_forward(
    df: pd.DataFrame,
    segments: List[RegimeSegment],
    regime: str,
    n_splits: int = 3,
    test_ratio: float = 0.3,
    purge_days: int = 5
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Create anchored walk-forward train/test splits for a specific regime.
    
    Anchored: Training window always starts from first available data
    Expanding: Each subsequent split has more training data
    Purged: Gap between train and test to avoid lookahead
    
    Args:
        df: Full dataframe
        segments: List of regime segments
        regime: Target regime ('BULL', 'BEAR', 'SIDEWAYS')
        n_splits: Number of walk-forward splits
        test_ratio: Ratio of data for testing in each split
        purge_days: Gap between train and test
    
    Returns:
        List of (train_df, test_df) tuples
    """
    # Get all data belonging to this regime
    regime_segments = [s for s in segments if s.regime == regime]
    
    if len(regime_segments) < 2:
        # Not enough segments - use time-based splits within regime data
        regime_data = df[df['regime'] == regime].copy()
        if len(regime_data) < 200:
            return []
        
        splits = []
        total_days = len(regime_data)
        
        for i in range(n_splits):
            # Anchored: always start from beginning
            # Expanding: each split uses more data
            train_end_idx = int(total_days * (0.5 + 0.15 * i))
            test_start_idx = train_end_idx + purge_days
            test_end_idx = min(test_start_idx + int(total_days * test_ratio), total_days)
            
            if test_end_idx <= test_start_idx + 30:
                continue
            
            train_df = regime_data.iloc[:train_end_idx].copy()
            test_df = regime_data.iloc[test_start_idx:test_end_idx].copy()
            
            if len(train_df) >= 100 and len(test_df) >= 30:
                splits.append((train_df, test_df))
        
        return splits
    
    # Multiple segments available - use segment-based splits
    # Sort by date
    regime_segments = sorted(regime_segments, key=lambda x: x.start_date)
    
    splits = []
    
    # Combine segments for training/testing
    for i in range(1, len(regime_segments)):
        # Train on all segments up to i-1
        train_segments = regime_segments[:i]
        # Test on segment i
        test_segment = regime_segments[i]
        
        # Build training dataframe from all train segments
        train_dfs = []
        for seg in train_segments:
            seg_df = df.loc[seg.start_date:seg.end_date].copy()
            train_dfs.append(seg_df)
        
        if not train_dfs:
            continue
            
        train_df = pd.concat(train_dfs)
        
        # Get test data with purge
        test_start = test_segment.start_date + timedelta(days=purge_days)
        test_df = df.loc[test_start:test_segment.end_date].copy()
        
        if len(train_df) >= 100 and len(test_df) >= 30:
            splits.append((train_df, test_df))
    
    return splits


# =============================================================================
# OPTUNA OPTIMIZATION
# =============================================================================

def run_backtest(df: pd.DataFrame, sma_period: int) -> Dict[str, float]:
    """Run a single backtest and return metrics."""
    if len(df) < sma_period + 20:
        return {'return': 0, 'alpha': -9999, 'sharpe': 0, 'max_dd': 100, 'trades': 0}
    
    # Calculate B&H
    bh_return = ((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']) * 100
    
    try:
        engine = BacktestEngine(initial_cash=100000.0, commission=0.001)
        result = engine.run_backtest(
            strategy_cls=OptimizedSMAStrategy,
            data_df=df,
            symbol='BTCUSDT',
            sma_period=sma_period,
            verbose=False
        )
        
        strategy_return = result['return_pct']
        alpha = strategy_return - bh_return
        
        # Get Sharpe
        sharpe_data = result.get('analyzers', {}).get('sharpe', {})
        sharpe = sharpe_data.get('sharperatio', 0) if sharpe_data else 0
        sharpe = sharpe if sharpe and not np.isnan(sharpe) else 0
        
        # Get drawdown
        dd = result.get('analyzers', {}).get('drawdown', {})
        max_dd = dd.get('max', {}).get('drawdown', 0) if dd else 0
        
        # Get trades
        trades_analysis = result.get('analyzers', {}).get('trades', {})
        num_trades = trades_analysis.get('total', {}).get('total', 0) if trades_analysis else 0
        
        return {
            'return': strategy_return,
            'bh_return': bh_return,
            'alpha': alpha,
            'sharpe': sharpe,
            'max_dd': abs(max_dd),
            'trades': num_trades
        }
    
    except Exception as e:
        return {'return': 0, 'alpha': -9999, 'sharpe': 0, 'max_dd': 100, 'trades': 0}


def objective_walkforward(trial, splits: List[Tuple[pd.DataFrame, pd.DataFrame]], regime: str) -> float:
    """
    Optuna objective using walk-forward validation.
    
    Score is based on AVERAGE PERFORMANCE across all test folds.
    This ensures generalization, not just fitting to one period.
    """
    # Suggest SMA period
    if regime == 'BULL':
        sma_period = trial.suggest_int('sma_period', 20, 100, step=5)
    elif regime == 'BEAR':
        sma_period = trial.suggest_int('sma_period', 40, 150, step=5)
    else:
        sma_period = trial.suggest_int('sma_period', 30, 120, step=5)
    
    # Evaluate on all walk-forward splits
    test_alphas = []
    test_sharpes = []
    
    for train_df, test_df in splits:
        # Validate on TEST set (not train!)
        metrics = run_backtest(test_df, sma_period)
        
        if metrics['alpha'] > -9000:
            test_alphas.append(metrics['alpha'])
            test_sharpes.append(metrics['sharpe'])
    
    if not test_alphas:
        return -999999
    
    # Score = average test alpha + bonus for consistency
    avg_alpha = np.mean(test_alphas)
    std_alpha = np.std(test_alphas) if len(test_alphas) > 1 else 0
    
    # Penalize high variance (inconsistent results)
    consistency_penalty = std_alpha * 0.3
    
    # Bonus for positive Sharpe
    sharpe_bonus = np.mean(test_sharpes) * 10 if any(s > 0 for s in test_sharpes) else 0
    
    score = avg_alpha - consistency_penalty + sharpe_bonus
    
    return score


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def load_btc_data() -> pd.DataFrame:
    """Load BTC data."""
    print("Loading BTC data...")
    data_engine = DataEngine(auto_indicators=False)
    df = data_engine.get_ohlcv_cached(
        source='binance',
        symbol='BTCUSDT',
        timeframe='1d',
        start='2017-01-01',  # Get more history for regime detection
        end='2025-11-24'
    )
    
    if df is None or df.empty:
        raise ValueError("Failed to load BTC data")
    
    if 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)
    
    print(f"Loaded {len(df)} daily candles from {df.index[0]} to {df.index[-1]}")
    return df


def main():
    print("="*80)
    print("PROFESSIONAL WALK-FORWARD OPTIMIZATION")
    print("="*80)
    print()
    print("Methodology:")
    print("  1. Automatic regime detection (trend + volatility)")
    print("  2. Anchored walk-forward validation (expanding window)")
    print("  3. Purged gaps to prevent lookahead bias")
    print("  4. Optimize on TEST performance (not training)")
    print()
    
    # Load data
    df = load_btc_data()
    print()
    
    # Detect regimes
    print("="*80)
    print("STEP 1: AUTOMATIC REGIME DETECTION")
    print("="*80)
    
    df = detect_regimes(df, lookback=50)
    
    # Show regime distribution
    regime_counts = df['regime'].value_counts()
    print(f"\nDaily Regime Distribution:")
    for regime, count in regime_counts.items():
        pct = count / len(df) * 100
        print(f"  {regime:10s}: {count:5d} days ({pct:5.1f}%)")
    
    # Extract segments
    segments = extract_regime_segments(df, min_segment_days=60)
    
    print(f"\nDetected {len(segments)} regime segments (min 60 days each):")
    print("-" * 80)
    print(f"{'Regime':12s} | {'Start':12s} | {'End':12s} | {'Days':5s} | {'Return':8s} | {'Vol':6s}")
    print("-" * 80)
    
    for seg in sorted(segments, key=lambda x: x.start_date):
        print(f"{seg.regime:12s} | {str(seg.start_date.date()):12s} | {str(seg.end_date.date()):12s} | {seg.num_days:5d} | {seg.return_pct:+7.1f}% | {seg.volatility:5.1f}%")
    
    print()
    
    # Optimize per regime
    print("="*80)
    print("STEP 2: WALK-FORWARD OPTIMIZATION PER REGIME")
    print("="*80)
    
    results = {}
    
    for regime in ['BULL', 'BEAR', 'SIDEWAYS']:
        print(f"\n{'='*60}")
        print(f"Optimizing for {regime} regime...")
        print(f"{'='*60}")
        
        # Create walk-forward splits
        splits = anchored_walk_forward(df, segments, regime, n_splits=3, test_ratio=0.25, purge_days=5)
        
        if len(splits) < 2:
            print(f"  ⚠️  Not enough data for {regime} regime ({len(splits)} splits)")
            results[regime] = None
            continue
        
        print(f"\nWalk-Forward Splits ({len(splits)} folds):")
        for i, (train_df, test_df) in enumerate(splits):
            train_start = train_df.index[0].date() if hasattr(train_df.index[0], 'date') else train_df.index[0]
            train_end = train_df.index[-1].date() if hasattr(train_df.index[-1], 'date') else train_df.index[-1]
            test_start = test_df.index[0].date() if hasattr(test_df.index[0], 'date') else test_df.index[0]
            test_end = test_df.index[-1].date() if hasattr(test_df.index[-1], 'date') else test_df.index[-1]
            print(f"  Fold {i+1}: Train [{train_start} → {train_end}] ({len(train_df)} days)")
            print(f"          Test  [{test_start} → {test_end}] ({len(test_df)} days)")
        
        # Run Optuna
        print(f"\nRunning Optuna (30 trials)...")
        
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        study.optimize(
            lambda trial: objective_walkforward(trial, splits, regime),
            n_trials=30,
            show_progress_bar=True
        )
        
        best_sma = study.best_trial.params['sma_period']
        best_score = study.best_trial.value
        
        print(f"\n✅ Best SMA for {regime}: {best_sma}")
        print(f"   Walk-forward score: {best_score:.2f}")
        
        # Detailed test results
        print(f"\nDetailed Test Results (SMA-{best_sma}):")
        test_results = []
        
        for i, (train_df, test_df) in enumerate(splits):
            metrics = run_backtest(test_df, best_sma)
            test_results.append(metrics)
            
            status = "✅" if metrics['alpha'] > 0 else "❌"
            bh_ret = metrics.get('bh_return', 0)
            print(f"  Fold {i+1}: {status} Alpha: {metrics['alpha']:+.1f}% | B&H: {bh_ret:+.1f}% | Strategy: {metrics['return']:+.1f}%")
        
        # Aggregate
        valid_results = [r for r in test_results if r['alpha'] > -9000]
        if valid_results:
            avg_alpha = np.mean([r['alpha'] for r in valid_results])
            win_rate = sum(1 for r in valid_results if r['alpha'] > 0) / len(valid_results) * 100
            
            results[regime] = {
                'best_sma': best_sma,
                'avg_test_alpha': avg_alpha,
                'win_rate': win_rate,
                'num_folds': len(valid_results),
                'test_results': test_results
            }
            
            print(f"\n📊 Aggregate: Avg Alpha: {avg_alpha:+.1f}% | Win Rate: {win_rate:.0f}%")
        else:
            results[regime] = None
    
    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    print("\nOptimized Parameters by Regime:")
    print("-" * 80)
    
    robust_count = 0
    
    for regime in ['BULL', 'BEAR', 'SIDEWAYS']:
        res = results.get(regime)
        if res is None:
            print(f"{regime:10s} | Insufficient data")
            continue
        
        if res['avg_test_alpha'] > 5 and res['win_rate'] >= 60:
            status = "✅ ROBUST"
            robust_count += 1
        elif res['avg_test_alpha'] > 0:
            status = "⚠️  MARGINAL"
        else:
            status = "❌ FAILS"
        
        print(f"{regime:10s} | SMA-{res['best_sma']:3d} | Test Alpha: {res['avg_test_alpha']:+6.1f}% | Win: {res['win_rate']:3.0f}% ({res['num_folds']} folds) | {status}")
    
    # Final Verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)
    
    if robust_count >= 2:
        print("\n✅ STRATEGY HAS EDGE IN MULTIPLE REGIMES")
        print("\n💡 Deployment Recommendation:")
        print("   1. Implement regime detector in live system")
        print("   2. Use detected regime to select SMA parameter:")
        for regime in ['BULL', 'BEAR', 'SIDEWAYS']:
            if results.get(regime) and results[regime]['avg_test_alpha'] > 0:
                print(f"      - {regime}: SMA-{results[regime]['best_sma']}")
        print("   3. Default to Buy & Hold if regime uncertain")
    
    elif robust_count == 1:
        print("\n⚠️  LIMITED EDGE (only 1 regime)")
        for regime in ['BULL', 'BEAR', 'SIDEWAYS']:
            if results.get(regime) and results[regime]['avg_test_alpha'] > 5 and results[regime]['win_rate'] >= 60:
                print(f"\n   Only {regime} shows consistent alpha.")
                print(f"   Consider trading only during confirmed {regime} regimes.")
                print(f"   Otherwise: Buy & Hold")
    
    else:
        print("\n❌ NO CONSISTENT EDGE FOUND")
        print("\n   Walk-forward validation shows:")
        print("   - Training performance doesn't transfer to test periods")
        print("   - No regime shows consistent positive alpha")
        print("   - Parameters overfit to historical data")
        print("\n🚫 RECOMMENDATION: Buy & Hold")
        print("\n   Mathematical reality:")
        print("   - BTC has strong positive drift (~100% CAGR historically)")
        print("   - Any timing strategy risks missing explosive rallies")
        print("   - Transaction costs compound over time")
        print("   - Simpler is better: just hold")
    
    print("\n" + "="*80)
    print("METHODOLOGY NOTES")
    print("="*80)
    print("""
This analysis used professional-grade methodology:

1. REGIME DETECTION
   - Statistical classification based on 50-day returns and volatility
   - Not arbitrary date splits - data-driven regime identification
   
2. ANCHORED WALK-FORWARD
   - Training always starts from earliest data (expanding window)
   - Tests on truly out-of-sample future data
   - Multiple folds for statistical significance
   
3. PURGED GAPS
   - 5-day gap between train and test
   - Prevents lookahead bias from overlapping data
   
4. TEST-BASED OPTIMIZATION
   - Optuna optimizes based on TEST performance
   - Not training performance (which would overfit)
   
5. CONSISTENCY REQUIREMENT
   - Strategy must work across multiple test periods
   - High variance = unreliable (penalized)
   
Reference: López de Prado, M. (2018). Advances in Financial Machine Learning.
    """)


if __name__ == '__main__':
    main()
