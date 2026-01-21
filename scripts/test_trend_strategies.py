#!/usr/bin/env python3
"""
Test Pure Trend Following Strategies

Tests the 3 simple moving average strategies from the study that
historically beat Buy & Hold:

1. EMA-150: ~126% a.a., Sharpe 1.9
2. SMA-50: Sharpe superior to B&H
3. Crossover 20/100: ~116% a.a., Sharpe 1.7

Compares against Buy & Hold and all previous failed attempts.
"""

import sys
import os
from datetime import datetime
import backtrader as bt
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_ema_strategy import BTCEMAStrategy
from strategies.btc_sma_strategy import BTCSMAStrategy
from strategies.btc_crossover_strategy import BTCCrossoverStrategy


def run_strategy_backtest(strategy_class, strategy_name, df, initial_cash=100000):
    """Run backtest for a single strategy."""
    print(f"\n{'='*80}")
    print(f"🧪 Testing: {strategy_name}")
    print(f"{'='*80}\n")
    
    # Create backtest engine
    engine = BacktestEngine(
        initial_cash=initial_cash,
        commission=0.001  # 0.1% commission
    )
    
    # Run backtest using run_backtest method
    results = engine.run_backtest(
        strategy_cls=strategy_class,
        data_df=df,
        symbol='BTC-USD'
    )
    
    return results


def calculate_buy_hold_benchmark(df, initial_cash=100000):
    """Calculate Buy & Hold returns."""
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    
    shares = initial_cash / start_price
    final_value = shares * end_price
    
    total_return = ((final_value / initial_cash) - 1) * 100
    
    return {
        'final_value': final_value,
        'total_return': total_return,
        'start_price': start_price,
        'end_price': end_price
    }


def main():
    print("\n" + "="*80)
    print("📊 PURE TREND FOLLOWING STRATEGIES TEST")
    print("="*80)
    print("Testing strategies from study that beat Buy & Hold")
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
    print(f"✅ Loaded {len(df)} days of data\n")
    
    # =========================================================================
    # 2. CALCULATE BUY & HOLD BENCHMARK
    # =========================================================================
    print("📈 Calculating Buy & Hold Benchmark...")
    bh_results = calculate_buy_hold_benchmark(df)
    print(f"   Start: ${bh_results['start_price']:,.2f}")
    print(f"   End: ${bh_results['end_price']:,.2f}")
    print(f"   Return: +{bh_results['total_return']:.1f}%")
    print(f"   Final Value: ${bh_results['final_value']:,.2f}\n")
    
    # =========================================================================
    # 3. TEST STRATEGIES
    # =========================================================================
    strategies = [
        (BTCEMAStrategy, "EMA-150 Strategy", "Study: ~126% a.a., Sharpe 1.9"),
        (BTCSMAStrategy, "SMA-50 Strategy", "Study: Superior Sharpe vs B&H"),
        (BTCCrossoverStrategy, "Crossover 20/100", "Study: ~116% a.a., Sharpe 1.7"),
    ]
    
    results_summary = []
    
    for strategy_class, name, note in strategies:
        print(f"📝 {note}")
        results = run_strategy_backtest(strategy_class, name, df)
        
        if results:
            # Calculate metrics
            final_value = results['final_value']
            total_return = ((final_value / 100000) - 1) * 100
            alpha = total_return - bh_results['total_return']
            
            trades = results.get('total_trades', 0)
            trades_per_year = trades / 6
            
            results_summary.append({
                'strategy': name,
                'final_value': final_value,
                'total_return': total_return,
                'alpha': alpha,
                'trades': trades,
                'trades_per_year': trades_per_year,
                'sharpe': results.get('sharpe_ratio', 0),
                'max_drawdown': results.get('max_drawdown_pct', 0)
            })
    
    # =========================================================================
    # 4. RESULTS COMPARISON
    # =========================================================================
    print("\n" + "="*80)
    print("📊 RESULTS SUMMARY")
    print("="*80 + "\n")
    
    print(f"{'Strategy':<25} {'Return':<12} {'Alpha':<10} {'Trades':<8} {'Sharpe':<8} {'Max DD':<10}")
    print("-" * 90)
    
    # Buy & Hold baseline
    print(f"{'Buy & Hold':<25} {bh_results['total_return']:>10.1f}% {'0.0%':<10} {'0':<8} {'-':<8} {'-':<10}")
    
    # Strategies
    for r in results_summary:
        print(f"{r['strategy']:<25} "
              f"{r['total_return']:>10.1f}% "
              f"{r['alpha']:>8.1f}% "
              f"{r['trades_per_year']:>6.1f}/yr "
              f"{r['sharpe']:>6.2f} "
              f"{r['max_drawdown']:>8.1f}%")
    
    # =========================================================================
    # 5. COMPARISON WITH PREVIOUS FAILURES
    # =========================================================================
    print("\n" + "="*80)
    print("📊 COMPARISON: ALL STRATEGIES TESTED")
    print("="*80 + "\n")
    
    print(f"{'Strategy':<30} {'Return':<12} {'Alpha':<10} {'Trades/Yr':<12} {'Result':<20}")
    print("-" * 95)
    
    # Previous failures
    previous = [
        ("Buy & Hold", 1143, 0, 0, "✅ Benchmark"),
        ("BTCExitMaster", 627, -516, 3.8, "❌ Too many exits"),
        ("BTCMLStrategy (XGBoost)", 803, -340, 0.2, "❌ No predictive power"),
        ("RLStrategy (Sequential)", 6970, 5827, 43.8, "❌ Overfit (test: -348%)"),
        ("RLStrategy (Alternate)", 219, -924, 55.0, "❌ Overtrading"),
    ]
    
    for name, ret, alpha, trades, result in previous:
        print(f"{name:<30} {ret:>10.0f}% {alpha:>8.0f}% {trades:>10.1f} {result:<20}")
    
    print()
    
    # New strategies
    for r in results_summary:
        status = "✅ BEATS B&H!" if r['alpha'] > 0 else "⚠️  Check results"
        print(f"{r['strategy']:<30} "
              f"{r['total_return']:>10.1f}% "
              f"{r['alpha']:>8.1f}% "
              f"{r['trades_per_year']:>10.1f} "
              f"{status:<20}")
    
    # =========================================================================
    # 6. ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("💡 ANALYSIS")
    print("="*80 + "\n")
    
    # Check if any strategy beat B&H
    winners = [r for r in results_summary if r['alpha'] > 0]
    
    if winners:
        print("🎉 SUCCESS! Strategies that beat Buy & Hold:\n")
        for w in winners:
            print(f"✅ {w['strategy']}")
            print(f"   Return: +{w['total_return']:.1f}% (alpha: +{w['alpha']:.1f}%)")
            print(f"   Trades: {w['trades_per_year']:.1f} per year")
            print(f"   Sharpe: {w['sharpe']:.2f}")
            print(f"   Max Drawdown: {w['max_drawdown']:.1f}%")
            print()
        
        print("🔑 KEY SUCCESS FACTORS:")
        print("   • Simple rules (just moving averages)")
        print("   • Few trades (not overtrading)")
        print("   • Trend following (not predicting)")
        print("   • Capital preservation during downtrends")
    else:
        print("⚠️  UNEXPECTED: None of the strategies beat B&H")
        print("\nPossible reasons:")
        print("   • Different period than study (2020-2025 vs 2012-2023)")
        print("   • Transaction costs impact")
        print("   • Strong bull market with few corrections")
        print("   • Study's annualized returns may include longer history")
        
        print("\n📊 Best performers (by alpha):")
        sorted_results = sorted(results_summary, key=lambda x: x['alpha'], reverse=True)
        for i, r in enumerate(sorted_results[:3], 1):
            print(f"   {i}. {r['strategy']}: {r['alpha']:+.1f}% alpha, "
                  f"{r['trades_per_year']:.1f} trades/yr")
    
    # Check drawdown improvement
    print("\n📉 DRAWDOWN COMPARISON:")
    print("   Study expectation: ~30-40% max drawdown")
    print(f"   Buy & Hold (our period): ~76% drawdown (2021-2022 crash)")
    for r in results_summary:
        improvement = 76 - abs(r['max_drawdown'])
        print(f"   {r['strategy']}: {r['max_drawdown']:.1f}% "
              f"({improvement:+.1f}% improvement)")
    
    print("\n" + "="*80)
    print("🎯 FINAL VERDICT")
    print("="*80 + "\n")
    
    if winners:
        print("✅ HYPOTHESIS VALIDATED")
        print("Simple trend-following strategies CAN beat Buy & Hold!")
        print("\nKey insight: Complexity was the enemy all along.")
        print("• ML, RL, multiple indicators → Overfit and overtrade")
        print("• Single moving average → Robust and selective")
    else:
        print("⚠️  HYPOTHESIS NOT VALIDATED IN THIS PERIOD")
        print("Simple strategies did not beat B&H in 2020-2025.")
        print("\nPossible explanations:")
        print("• Study covered 2012-2023 (longer bull run)")
        print("• Our 2020-2025 includes different market structure")
        print("• Need to test on longer historical period")
        print("\nNext steps:")
        print("• Test on data back to 2015 or 2012")
        print("• Add trailing stops for drawdown protection")
        print("• Try parameter optimization (EMA-100, EMA-200)")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
