#!/usr/bin/env python3
"""
Test ML-Based Crash Prediction Strategy

Complete workflow:
1. Load BTC data (2020-2025)
2. Train XGBoost crash predictor with walk-forward validation
3. Generate crash probabilities for entire period
4. Run strategy with ML predictions
5. Compare vs Buy & Hold
6. Analyze feature importance
"""

import sys
import os
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.ml_crash_predictor import CrashPredictorEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_ml_strategy import BTCMLStrategy


def main():
    print("\n" + "="*80)
    print("🤖 ML-BASED CRASH PREDICTION STRATEGY")
    print("="*80)
    print("Using XGBoost with 50+ features to predict crashes")
    print("Period: 2020-2025 (6 years)")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. LOAD DATA
    # =========================================================================
    print("📊 Loading BTC-USD data...")
    data_engine = DataEngine()
    df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-12-31'
    )
    
    # Ensure we have the required columns
    if 'datetime' not in df.columns and df.index.name != 'datetime':
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'])
            df.set_index('datetime', inplace=True)
        else:
            df.index.name = 'datetime'
    
    print(f"✅ Loaded {len(df)} days of data\n")
    
    # Calculate Buy & Hold benchmark
    bh_start = df.iloc[0]['close']
    bh_end = df.iloc[-1]['close']
    bh_return = ((bh_end / bh_start) - 1) * 100
    
    print(f"📈 Buy & Hold Benchmark:")
    print(f"   Start: ${bh_start:,.2f}")
    print(f"   End: ${bh_end:,.2f}")
    print(f"   Return: +{bh_return:.1f}%\n")
    
    # =========================================================================
    # 2. TRAIN ML MODEL
    # =========================================================================
    print("🎯 Training XGBoost Crash Predictor...")
    print("   Crash definition: >-30% drop in next 30 days")
    print("   Validation: Walk-forward (5 folds)\n")
    
    predictor = CrashPredictorEngine(
        crash_threshold=-0.30,
        lookahead_days=30,
        min_train_days=730
    )
    
    # Train with walk-forward validation
    training_results = predictor.train_walk_forward(
        df=df,
        n_splits=5,
        save_path='data/models/crash_predictor_v1.pkl'
    )
    
    # =========================================================================
    # 3. GENERATE CRASH PROBABILITIES
    # =========================================================================
    print("\n" + "="*80)
    print("🔮 Generating crash probabilities for entire period...")
    print("="*80 + "\n")
    
    crash_probs_series = predictor.predict_crash_probability(df)
    
    # Convert to dict for strategy (date -> probability)
    crash_probs_dict = crash_probs_series.to_dict()
    
    # Statistics
    print(f"📊 Crash Probability Statistics:")
    print(f"   Mean: {crash_probs_series.mean():.1%}")
    print(f"   Median: {crash_probs_series.median():.1%}")
    print(f"   Max: {crash_probs_series.max():.1%}")
    print(f"   Days with prob > 50%: {(crash_probs_series > 0.5).sum()}")
    print(f"   Days with prob > 70%: {(crash_probs_series > 0.7).sum()}")
    print(f"   Days with prob > 85%: {(crash_probs_series > 0.85).sum()}\n")
    
    # Show top crash probability days
    top_crash_days = crash_probs_series.nlargest(10)
    print("🔴 TOP 10 HIGHEST CRASH PROBABILITY DAYS:")
    print("-" * 80)
    for date, prob in top_crash_days.items():
        price = df.loc[date, 'close']
        print(f"   {date.strftime('%Y-%m-%d')}: {prob:.1%} (Price: ${price:,.0f})")
    
    # =========================================================================
    # 4. RUN ML STRATEGY
    # =========================================================================
    print("\n" + "="*80)
    print("🤖 Running ML Strategy Backtest...")
    print("="*80 + "\n")
    
    print("Strategy parameters:")
    print("   Exit threshold: 70% crash probability")
    print("   Re-entry threshold: 30% crash probability")
    print("   Max days out: 30 days")
    print("   Multi-timeframe confirmation: Enabled\n")
    
    engine = BacktestEngine(initial_cash=100000.0)
    result = engine.run_backtest(
        strategy_cls=BTCMLStrategy,
        data_df=df,
        symbol='BTC-USD',
        exit_prob_threshold=0.70,
        reentry_prob_threshold=0.30,
        reentry_rsi=30,
        max_days_out=30,
        position_size=0.95,
        multi_timeframe_confirm=True,
        crash_probs=crash_probs_dict
    )
    
    # =========================================================================
    # 5. EXTRACT RESULTS
    # =========================================================================
    final_value = result['final_value']
    ml_return = result['return_pct']
    alpha = ml_return - bh_return
    
    # Get trade analysis
    analyzers = result.get('analyzers', {})
    total_trades = analyzers.get('total_trades', 0)
    won_trades = analyzers.get('won_trades', 0)
    lost_trades = analyzers.get('lost_trades', 0)
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Get drawdown
    max_dd = abs(analyzers.get('max_drawdown', 0))
    
    # Get Sharpe ratio
    sharpe_ratio = analyzers.get('sharpe', 0) or 0
    
    # =========================================================================
    # 6. DISPLAY RESULTS
    # =========================================================================
    print("\n" + "="*80)
    print("📊 ML STRATEGY RESULTS")
    print("="*80 + "\n")
    
    print(f"💰 Returns:")
    print(f"   Final Value: ${final_value:,.2f}")
    print(f"   ML Return: +{ml_return:.1f}%")
    print(f"   B&H Return: +{bh_return:.1f}%")
    print(f"   Alpha: {alpha:+.1f}%\n")
    
    print(f"📈 Trading Activity:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Trades/Year: {total_trades/6:.1f}")
    print(f"   Won/Lost: {won_trades}/{lost_trades}")
    print(f"   Win Rate: {win_rate:.1f}%\n")
    
    print(f"🛡️  Risk Metrics:")
    print(f"   Max Drawdown: {max_dd:.1f}%")
    print(f"   Sharpe Ratio: {sharpe_ratio:.2f}\n")
    
    # =========================================================================
    # 7. EVALUATION
    # =========================================================================
    print("="*80)
    print("🎯 EVALUATION")
    print("="*80 + "\n")
    
    # Score the strategy
    score = 0
    
    # Alpha scoring (most important)
    if alpha > 0:
        score += 3
        alpha_verdict = "✅ POSITIVE ALPHA - Beats B&H!"
    elif alpha > -100:
        score += 1
        alpha_verdict = "⚠️  MINOR UNDERPERFORMANCE"
    else:
        alpha_verdict = "❌ MAJOR UNDERPERFORMANCE"
    
    # Trade frequency scoring
    trades_per_year = total_trades / 6
    if trades_per_year <= 3:
        score += 1
        trade_verdict = "✅ LOW FREQUENCY (selective exits)"
    elif trades_per_year <= 6:
        trade_verdict = "⚠️  MODERATE FREQUENCY"
    else:
        trade_verdict = "❌ HIGH FREQUENCY (too many exits)"
    
    # Win rate scoring
    if win_rate >= 60:
        score += 1
        win_verdict = "✅ GOOD WIN RATE"
    elif win_rate >= 50:
        win_verdict = "⚠️  MODERATE WIN RATE"
    else:
        win_verdict = "❌ POOR WIN RATE"
    
    # Risk scoring
    if max_dd < 50:
        score += 1
        risk_verdict = "✅ CONTROLLED RISK"
    else:
        risk_verdict = "❌ HIGH DRAWDOWN"
    
    print(f"Alpha: {alpha_verdict}")
    print(f"Trade Frequency: {trade_verdict}")
    print(f"Win Rate: {win_verdict}")
    print(f"Risk: {risk_verdict}\n")
    
    print(f"📊 OVERALL SCORE: {score}/6\n")
    
    if score >= 5:
        final_verdict = "🏆 EXCELLENT - ML strategy works!"
    elif score >= 3:
        final_verdict = "⚠️  GOOD - Shows promise, needs tuning"
    elif score >= 2:
        final_verdict = "⚠️  MODERATE - Marginal improvement"
    else:
        final_verdict = "❌ FAILED - ML doesn't help"
    
    print(f"VERDICT: {final_verdict}\n")
    
    # =========================================================================
    # 8. FEATURE IMPORTANCE ANALYSIS
    # =========================================================================
    print("="*80)
    print("🔍 TOP 20 MOST IMPORTANT FEATURES")
    print("="*80 + "\n")
    
    feature_importance = predictor.get_feature_importance(top_n=20)
    for idx, row in feature_importance.iterrows():
        print(f"   {row['feature']:30s} {row['importance']:.4f}")
    
    # =========================================================================
    # 9. COMPARISON WITH PREVIOUS STRATEGIES
    # =========================================================================
    print("\n" + "="*80)
    print("📊 COMPARISON: ALL STRATEGIES")
    print("="*80 + "\n")
    
    comparison = [
        ("Buy & Hold", f"+{bh_return:.0f}%", "0%", "0", "Benchmark"),
        ("V1 Baseline", "?", "?", "~3", "50% yearly win"),
        ("V2 Optimized", "+104%", "+104%", "~4", "33% yearly, overfitted"),
        ("BTCAdaptive", "-77%", "-77%", "2.7", "Too conservative"),
        ("BTCOpportunistic", "-80%", "-80%", "2.2", "Missed rallies"),
        ("BTCTrendFollower", "-93%", "-93%", "0.8", "Missed bulls"),
        ("BTCPerfect", "-46%", "-46%", "2.0", "Bad timing"),
        ("BTCEnhancedBH", "0%", "-1143%", "0", "Never entered"),
        ("BTCExitMaster", "+627%", "-516%", "3.8", "Too many exits"),
        ("BTCMLStrategy", f"+{ml_return:.0f}%", f"{alpha:+.0f}%", f"{trades_per_year:.1f}", "🤖 ML-POWERED"),
    ]
    
    print(f"{'Strategy':<20} {'Return':>10} {'Alpha':>10} {'Trades/Yr':>10} {'Notes':<25}")
    print("-" * 80)
    for name, ret, alpha_val, trades, notes in comparison:
        print(f"{name:<20} {ret:>10} {alpha_val:>10} {trades:>10} {notes:<25}")
    
    # =========================================================================
    # 10. FINAL INSIGHTS
    # =========================================================================
    print("\n" + "="*80)
    print("💡 KEY INSIGHTS")
    print("="*80 + "\n")
    
    print("1. ML MODEL PERFORMANCE:")
    avg_metrics = training_results['average_metrics']
    print(f"   - Walk-forward AUC: {avg_metrics['auc']:.3f}")
    print(f"   - Precision: {avg_metrics['precision']:.3f}")
    print(f"   - Recall: {avg_metrics['recall']:.3f}")
    
    if avg_metrics['auc'] > 0.7:
        print("   ✅ Model has predictive power (AUC > 0.7)")
    else:
        print("   ⚠️  Model struggles to predict crashes (AUC < 0.7)")
    
    print("\n2. STRATEGY EXECUTION:")
    if trades_per_year < 4:
        print("   ✅ ML successfully reduced false exits (vs 3.8 for BTCExitMaster)")
    else:
        print("   ⚠️  Still generating too many exits")
    
    print("\n3. ALPHA COMPARISON:")
    if alpha > -516:
        improvement = -516 - alpha
        print(f"   ✅ ML improved alpha by {improvement:+.0f}% vs BTCExitMaster")
    else:
        print(f"   ❌ ML performed worse than simple signals")
    
    print("\n4. FEATURE ANALYSIS:")
    top_features = feature_importance.head(5)['feature'].tolist()
    print(f"   Most predictive: {', '.join(top_features[:3])}")
    
    print("\n" + "="*80)
    print("🎯 RECOMMENDATION")
    print("="*80 + "\n")
    
    if alpha > 0:
        print("🎉 SUCCESS! ML-based strategy beats Buy & Hold!")
        print("   → Use BTCMLStrategy for live trading")
        print("   → Monitor top features for signals")
        print("   → Consider ensemble with other strategies\n")
    elif alpha > -200:
        print("⚠️  CLOSE BUT NOT QUITE")
        print("   → ML shows promise but needs tuning:")
        print("   → Try different probability thresholds (0.75, 0.80)")
        print("   → Adjust lookahead window (20 days instead of 30)")
        print("   → Add more features (on-chain data, sentiment)")
        print("   → Consider hybrid: 70% B&H + 30% ML\n")
    else:
        print("❌ ML DOESN'T SOLVE THE PROBLEM")
        print("   → Even sophisticated ML can't beat B&H for BTC")
        print("   → Fundamental issue: Any exit = risk of missing rallies")
        print("   → Recommendation: Accept B&H or focus on:")
        print("     • Position sizing (scale in/out)")
        print("     • DCA timing (buy dips)")
        print("     • Portfolio diversification\n")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
