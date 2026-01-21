#!/usr/bin/env python3
"""
Test Reinforcement Learning Trading Strategy

Uses Stable-Baselines3 PPO to learn optimal entry/exit policy.
This is proper ML for trading - learns from rewards, not classification.
"""

import sys
import os
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.ml_features_engine import MLFeaturesEngine
from engines.rl_trading_engine import RLTradingEngine


def main():
    print("\n" + "="*80)
    print("🤖 REINFORCEMENT LEARNING TRADING STRATEGY")
    print("="*80)
    print("Using PPO (Proximal Policy Optimization)")
    print("Agent learns optimal entry/exit policy from rewards")
    print("Period: 2020-2025 (6 years)")
    print("Split: Alternate Months (Odd=Train, Even=Test)")
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
    
    # Ensure datetime index
    if 'datetime' not in df.columns and df.index.name != 'datetime':
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'])
            df.set_index('datetime', inplace=True)
        else:
            df.index.name = 'datetime'
    
    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
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
    # 2. GENERATE FEATURES (using professional TA library)
    # =========================================================================
    print("🔧 Generating features using TA library...")
    feature_engine = MLFeaturesEngine()
    features = feature_engine.extract_features(df)
    print(f"✅ Generated {len(features.columns)} features\n")
    
    # =========================================================================
    # 3. SPLIT DATA: Alternate Months (Odd=Train, Even=Test)
    # =========================================================================
    print("🔀 Splitting data by alternate months...")
    print("   Odd months (Jan, Mar, May, Jul, Sep, Nov) → Training")
    print("   Even months (Feb, Apr, Jun, Aug, Oct, Dec) → Testing\n")
    
    # Create month-based masks
    months = df.index.month
    train_mask = (months % 2 == 1)  # Odd months: 1, 3, 5, 7, 9, 11
    test_mask = (months % 2 == 0)   # Even months: 2, 4, 6, 8, 10, 12
    
    df_train = df[train_mask].copy()
    df_test = df[test_mask].copy()
    features_train = features[train_mask].copy()
    features_test = features[test_mask].copy()
    
    print(f"📊 Data Split (Alternate Months):")
    print(f"   Train: {len(df_train)} days from odd months ({df_train.index[0].date()} to {df_train.index[-1].date()})")
    print(f"   Test:  {len(df_test)} days from even months ({df_test.index[0].date()} to {df_test.index[-1].date()})\n")
    
    # =========================================================================
    # 4. TRAIN RL AGENT
    # =========================================================================
    print("🎓 Training RL Agent (PPO)...")
    rl_engine = RLTradingEngine(
        algorithm='PPO',
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        verbose=0
    )
    
    # Train on 2020-2023 data
    training_results = rl_engine.train(
        df=df_train,
        features=features_train,
        total_timesteps=100000,  # 100K steps
        window_size=30,
        save_path='data/models/rl_ppo_btc.zip'
    )
    
    # =========================================================================
    # 5. TEST ON UNSEEN DATA (Even Months)
    # =========================================================================
    print("="*80)
    print("🧪 TESTING ON UNSEEN DATA (Even Months)")
    print("="*80 + "\n")
    
    actions, test_results = rl_engine.predict(
        df=df_test,
        features=features_test,
        window_size=30
    )
    
    # Calculate test period B&H
    test_bh_return = ((df_test.iloc[-1]['close'] / df_test.iloc[0]['close']) - 1) * 100
    
    # Calculate RL return
    initial_balance = 100000.0
    rl_final_balance = test_results['final_balance']
    rl_return = ((rl_final_balance / initial_balance) - 1) * 100
    alpha = rl_return - test_bh_return
    
    # =========================================================================
    # 6. FULL PERIOD TEST (for comparison)
    # =========================================================================
    print("="*80)
    print("🔄 FULL PERIOD TEST (2020-2025)")
    print("="*80 + "\n")
    
    actions_full, full_results = rl_engine.predict(
        df=df,
        features=features,
        window_size=30
    )
    
    rl_full_return = ((full_results['final_balance'] / initial_balance) - 1) * 100
    alpha_full = rl_full_return - bh_return
    
    # =========================================================================
    # 7. ANALYZE RESULTS
    # =========================================================================
    print("\n" + "="*80)
    print("📊 RESULTS SUMMARY")
    print("="*80 + "\n")
    
    print("🧪 TEST PERIOD (Even Months - Unseen Data):")
    print(f"   Buy & Hold: +{test_bh_return:.1f}%")
    print(f"   RL Strategy: +{rl_return:.1f}%")
    print(f"   Alpha: {alpha:+.1f}%")
    print(f"   Total Trades: {test_results['total_trades']}")
    print(f"   Win Rate: {test_results['win_rate']*100:.1f}%")
    print(f"   Trades/Year: {test_results['total_trades'] / (len(df_test)/365):.1f}\n")
    
    print("📊 FULL PERIOD (2020-2025 - All Data):")
    print(f"   Buy & Hold: +{bh_return:.1f}%")
    print(f"   RL Strategy: +{rl_full_return:.1f}%")
    print(f"   Alpha: {alpha_full:+.1f}%")
    print(f"   Total Trades: {full_results['total_trades']}")
    print(f"   Win Rate: {full_results['win_rate']*100:.1f}%")
    print(f"   Trades/Year: {full_results['total_trades'] / 6:.1f}\n")
    
    # =========================================================================
    # 8. ACTION ANALYSIS
    # =========================================================================
    print("="*80)
    print("🎯 ACTION ANALYSIS")
    print("="*80 + "\n")
    
    # Full period actions
    in_market_days = np.sum(actions_full == 1)
    out_market_days = np.sum(actions_full == 0)
    market_exposure = (in_market_days / len(actions_full)) * 100
    
    print(f"Market Exposure: {market_exposure:.1f}%")
    print(f"   In market: {in_market_days} days")
    print(f"   Out of market: {out_market_days} days\n")
    
    # Identify key exit/entry points
    position_changes = np.diff(actions_full, prepend=0)
    entries = np.where(position_changes == 1)[0]
    exits = np.where(position_changes == -1)[0]
    
    print(f"Entry/Exit Points:")
    print(f"   Entries: {len(entries)}")
    print(f"   Exits: {len(exits)}\n")
    
    if len(exits) > 0:
        print("🔴 KEY EXITS:")
        for i, exit_idx in enumerate(exits[:10]):  # Show first 10
            if exit_idx < len(df):
                date = df.index[exit_idx].date()
                price = df.iloc[exit_idx]['close']
                print(f"   {i+1}. {date}: ${price:,.0f}")
    
    # =========================================================================
    # 9. EVALUATION
    # =========================================================================
    print("\n" + "="*80)
    print("🎯 EVALUATION")
    print("="*80 + "\n")
    
    # Score the strategy
    score = 0
    
    # Test period alpha (most important - generalization)
    if alpha > 0:
        score += 3
        alpha_verdict = "✅ POSITIVE ALPHA on unseen data!"
    elif alpha > -100:
        score += 1
        alpha_verdict = "⚠️  MINOR UNDERPERFORMANCE on test"
    else:
        alpha_verdict = "❌ MAJOR UNDERPERFORMANCE on test"
    
    # Trade frequency
    trades_per_year_full = full_results['total_trades'] / 6
    if trades_per_year_full <= 5:
        score += 1
        trade_verdict = "✅ LOW FREQUENCY (selective)"
    elif trades_per_year_full <= 10:
        trade_verdict = "⚠️  MODERATE FREQUENCY"
    else:
        trade_verdict = "❌ HIGH FREQUENCY (overtrading)"
    
    # Win rate
    if full_results['win_rate'] >= 0.6:
        score += 1
        win_verdict = "✅ GOOD WIN RATE"
    elif full_results['win_rate'] >= 0.5:
        win_verdict = "⚠️  MODERATE WIN RATE"
    else:
        win_verdict = "❌ POOR WIN RATE"
    
    # Market exposure
    if 70 <= market_exposure <= 95:
        score += 1
        exposure_verdict = "✅ OPTIMAL EXPOSURE (captures rallies, avoids crashes)"
    elif market_exposure > 95:
        exposure_verdict = "⚠️  ALMOST ALWAYS IN (close to B&H)"
    else:
        exposure_verdict = "❌ LOW EXPOSURE (missing rallies)"
    
    print(f"Test Alpha: {alpha_verdict}")
    print(f"Trade Frequency: {trade_verdict}")
    print(f"Win Rate: {win_verdict}")
    print(f"Market Exposure: {exposure_verdict}\n")
    
    print(f"📊 OVERALL SCORE: {score}/6\n")
    
    if score >= 5:
        final_verdict = "🏆 EXCELLENT - RL works!"
    elif score >= 3:
        final_verdict = "⚠️  PROMISING - Needs tuning"
    else:
        final_verdict = "❌ FAILED - RL doesn't help"
    
    print(f"VERDICT: {final_verdict}\n")
    
    # =========================================================================
    # 10. COMPARISON WITH PREVIOUS STRATEGIES
    # =========================================================================
    print("="*80)
    print("📊 COMPARISON: ALL STRATEGIES")
    print("="*80 + "\n")
    
    comparison = [
        ("Buy & Hold", f"+{bh_return:.0f}%", "0%", "0", "Benchmark"),
        ("BTCExitMaster", "+627%", "-516%", "3.8", "Simple signals"),
        ("BTCMLStrategy", "+803%", "-340%", "0.2", "XGBoost classification"),
        ("RLStrategy (PPO)", f"+{rl_full_return:.0f}%", f"{alpha_full:+.0f}%", f"{trades_per_year_full:.1f}", "🤖 REINFORCEMENT LEARNING"),
    ]
    
    print(f"{'Strategy':<20} {'Return':>10} {'Alpha':>10} {'Trades/Yr':>10} {'Notes':<30}")
    print("-" * 85)
    for name, ret, alpha_val, trades, notes in comparison:
        print(f"{name:<20} {ret:>10} {alpha_val:>10} {trades:>10} {notes:<30}")
    
    # =========================================================================
    # 11. KEY INSIGHTS
    # =========================================================================
    print("\n" + "="*80)
    print("💡 KEY INSIGHTS")
    print("="*80 + "\n")
    
    print("1. REINFORCEMENT LEARNING APPROACH:")
    print(f"   - Agent learns from REWARDS (portfolio value)")
    print(f"   - Not classification (predict crashes)")
    print(f"   - Learns optimal policy: when to hold vs exit")
    print(f"   - Trained on: 2020-2023 ({len(df_train)} days)")
    print(f"   - Tested on: 2023-2025 ({len(df_test)} days)\n")
    
    print("2. TEST PERIOD PERFORMANCE:")
    if alpha > 0:
        print(f"   ✅ RL beat B&H on unseen data: {alpha:+.1f}% alpha")
        print(f"   ✅ Agent generalized well to new market conditions")
    else:
        print(f"   ❌ RL underperformed on test: {alpha:+.1f}% alpha")
        print(f"   ⚠️  Agent may have overfit to training data")
    
    print(f"\n3. MARKET EXPOSURE:")
    print(f"   - {market_exposure:.1f}% in market")
    if market_exposure > 90:
        print(f"   ⚠️  Almost identical to B&H (always in)")
        print(f"   → Agent learned that staying in is optimal")
    elif market_exposure < 50:
        print(f"   ⚠️  Too conservative (out of market too much)")
        print(f"   → Agent may be too risk-averse")
    else:
        print(f"   ✅ Selective exposure (exits during downturns)")
    
    print("\n" + "="*80)
    print("🎯 FINAL RECOMMENDATION")
    print("="*80 + "\n")
    
    if alpha > 0 and score >= 4:
        print("🎉 SUCCESS! RL beats Buy & Hold!")
        print("   → Reinforcement Learning IS the solution")
        print("   → Agent learned optimal entry/exit policy")
        print("   → Can be used for live trading\n")
    elif alpha_full > -200 and market_exposure > 80:
        print("⚠️  RL LEARNED THAT B&H IS OPTIMAL")
        print(f"   → Agent stays in market {market_exposure:.0f}% of time")
        print(f"   → This validates that B&H is hard to beat")
        print(f"   → RL independently discovered B&H strategy\n")
    else:
        print("❌ RL DOESN'T SOLVE THE PROBLEM")
        print(f"   → Even RL can't consistently beat B&H")
        print(f"   → Fundamental issue remains: BTC timing is hard")
        print(f"   → Recommendation: Accept B&H or try:")
        print(f"      • More training data (longer history)")
        print(f"      • Different reward functions")
        print(f"      • Ensemble of RL agents\n")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
