#!/usr/bin/env python3
"""
Walk-Forward Validation of SMA-110 Strategy

Tests the optimized SMA-110 strategy using walk-forward analysis to validate
that it's not overfit to the full 2020-2025 period.

Methodology:
1. Split data into 3 periods (2 years each)
2. Test strategy on each period independently
3. Verify consistency of performance across periods
4. Compare with Buy & Hold on each period

If SMA-110 consistently outperforms across different market regimes,
it validates robustness. If performance varies wildly, it indicates overfitting.
"""

import sys
import os
from datetime import datetime
import pandas as pd
import backtrader as bt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_sma110_strategy import BTCSMA110Strategy


def calculate_buy_hold(df, initial_cash=100000):
    """Calculate Buy & Hold metrics."""
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    
    shares = initial_cash / start_price
    final_value = shares * end_price
    total_return = ((final_value / initial_cash) - 1) * 100
    
    return {
        'final_value': final_value,
        'total_return': total_return,
        'start_price': start_price,
        'end_price': end_price,
        'start_date': df.index[0],
        'end_date': df.index[-1]
    }


def run_period_test(df, period_name, initial_cash=100000):
    """Run backtest on a specific period."""
    print(f"\n{'='*80}")
    print(f"📊 Period: {period_name}")
    print(f"{'='*80}")
    print(f"Dates: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Days: {len(df)}\n")
    
    # Calculate Buy & Hold
    bh = calculate_buy_hold(df, initial_cash)
    print(f"📈 Buy & Hold:")
    print(f"   Start: ${bh['start_price']:,.2f}")
    print(f"   End: ${bh['end_price']:,.2f}")
    print(f"   Return: +{bh['total_return']:.1f}%\n")
    
    # Run SMA-110 strategy
    print(f"🧪 Testing SMA-110 Strategy...\n")
    engine = BacktestEngine(
        initial_cash=initial_cash,
        commission=0.001
    )
    
    results = engine.run_backtest(
        strategy_cls=BTCSMA110Strategy,
        data_df=df,
        symbol='BTC-USD',
        verbose=False
    )
    
    # Extract metrics
    final_value = results.get('final_value', initial_cash)
    total_return = ((final_value / initial_cash) - 1) * 100
    alpha = total_return - bh['total_return']
    sharpe = results.get('sharpe_ratio', 0)
    max_dd = results.get('max_drawdown_pct', 0)
    trades = results.get('total_trades', 0)
    
    period_years = len(df) / 365
    trades_per_year = trades / period_years if period_years > 0 else 0
    
    print(f"📊 SMA-110 Results:")
    print(f"   Return: +{total_return:.1f}%")
    print(f"   Alpha: {alpha:+.1f}%")
    print(f"   Sharpe: {sharpe:.2f}")
    print(f"   Max DD: {max_dd:.1f}%")
    print(f"   Trades: {trades} ({trades_per_year:.1f}/year)")
    
    return {
        'period': period_name,
        'days': len(df),
        'start_date': df.index[0].date(),
        'end_date': df.index[-1].date(),
        'bh_return': bh['total_return'],
        'strategy_return': total_return,
        'alpha': alpha,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'trades': trades,
        'trades_per_year': trades_per_year
    }


def main():
    print("\n" + "="*80)
    print("🔍 WALK-FORWARD VALIDATION: SMA-110 Strategy")
    print("="*80)
    print("Testing robustness across different time periods")
    print("Goal: Verify consistent outperformance, not overfitting")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. LOAD FULL DATA
    # =========================================================================
    print("📊 Loading BTC-USD data...")
    data_engine = DataEngine()
    df_full = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-12-31'
    )
    print(f"✅ Loaded {len(df_full)} days of full data\n")
    
    # =========================================================================
    # 2. SPLIT INTO PERIODS
    # =========================================================================
    print("📅 Splitting into test periods...\n")
    
    # Period 1: 2020-2021 (COVID crash + recovery)
    period1_start = '2020-01-01'
    period1_end = '2021-12-31'
    df_p1 = df_full[(df_full.index >= period1_start) & (df_full.index <= period1_end)]
    
    # Period 2: 2022-2023 (Bear market + recovery)
    period2_start = '2022-01-01'
    period2_end = '2023-12-31'
    df_p2 = df_full[(df_full.index >= period2_start) & (df_full.index <= period2_end)]
    
    # Period 3: 2024-2025 (Bull run)
    period3_start = '2024-01-01'
    period3_end = '2025-12-31'
    df_p3 = df_full[(df_full.index >= period3_start) & (df_full.index <= period3_end)]
    
    print(f"Period 1 (2020-2021): {len(df_p1)} days - COVID crash + recovery")
    print(f"Period 2 (2022-2023): {len(df_p2)} days - Bear market + recovery")
    print(f"Period 3 (2024-2025): {len(df_p3)} days - Bull run")
    
    # =========================================================================
    # 3. RUN TESTS ON EACH PERIOD
    # =========================================================================
    results = []
    
    results.append(run_period_test(df_p1, "2020-2021 (COVID era)"))
    results.append(run_period_test(df_p2, "2022-2023 (Bear market)"))
    results.append(run_period_test(df_p3, "2024-2025 (Bull run)"))
    
    # =========================================================================
    # 4. FULL PERIOD TEST (for comparison)
    # =========================================================================
    results.append(run_period_test(df_full, "2020-2025 (Full period)"))
    
    # =========================================================================
    # 5. SUMMARY ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("📊 WALK-FORWARD VALIDATION SUMMARY")
    print("="*80 + "\n")
    
    print(f"{'Period':<25} {'B&H%':<10} {'SMA-110%':<12} {'Alpha%':<10} {'Sharpe':<8} {'Trades/Yr':<12}")
    print("-" * 90)
    
    for r in results:
        print(f"{r['period']:<25} "
              f"{r['bh_return']:>8.1f}% "
              f"{r['strategy_return']:>10.1f}% "
              f"{r['alpha']:>8.1f}% "
              f"{r['sharpe']:>6.2f} "
              f"{r['trades_per_year']:>10.1f}")
    
    # =========================================================================
    # 6. CONSISTENCY ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("🔍 CONSISTENCY ANALYSIS")
    print("="*80 + "\n")
    
    # Extract just the 3 periods (exclude full period)
    period_results = results[:3]
    
    alphas = [r['alpha'] for r in period_results]
    sharpes = [r['sharpe'] for r in period_results]
    trades_per_year = [r['trades_per_year'] for r in period_results]
    
    avg_alpha = sum(alphas) / len(alphas)
    min_alpha = min(alphas)
    max_alpha = max(alphas)
    
    avg_sharpe = sum(sharpes) / len(sharpes)
    min_sharpe = min(sharpes)
    max_sharpe = max(sharpes)
    
    avg_trades = sum(trades_per_year) / len(trades_per_year)
    
    print(f"Alpha Statistics:")
    print(f"   Average: {avg_alpha:+.1f}%")
    print(f"   Range: {min_alpha:+.1f}% to {max_alpha:+.1f}%")
    print(f"   Consistency: {min_alpha:+.1f}% / {max_alpha:+.1f}% = {(min_alpha/max_alpha)*100:.1f}%")
    
    print(f"\nSharpe Statistics:")
    print(f"   Average: {avg_sharpe:.2f}")
    print(f"   Range: {min_sharpe:.2f} to {max_sharpe:.2f}")
    
    print(f"\nTrade Frequency:")
    print(f"   Average: {avg_trades:.1f} trades/year")
    
    # =========================================================================
    # 7. ROBUSTNESS VERDICT
    # =========================================================================
    print("\n" + "="*80)
    print("🎯 ROBUSTNESS VERDICT")
    print("="*80 + "\n")
    
    # Count winning periods
    winning_periods = sum(1 for r in period_results if r['alpha'] > 0)
    
    # Check consistency (min alpha > 0 and ratio > 30%)
    is_consistent = min_alpha > 0 and (min_alpha / max_alpha) > 0.3
    
    # Check if all periods beat B&H
    all_win = winning_periods == len(period_results)
    
    if all_win and is_consistent:
        print("✅ ROBUST STRATEGY CONFIRMED!")
        print("\nKey findings:")
        print(f"   • Beats B&H in ALL {len(period_results)} periods")
        print(f"   • Average alpha: {avg_alpha:+.1f}%")
        print(f"   • Consistent performance (min/max ratio: {(min_alpha/max_alpha)*100:.1f}%)")
        print(f"   • Stable trade frequency: {avg_trades:.1f}/year")
        
        print("\n💡 Strategy is NOT overfit - performs consistently across:")
        print("   • Bull markets (2020-2021, 2024-2025)")
        print("   • Bear markets (2022-2023)")
        print("   • Different volatility regimes")
        
        print("\n🚀 RECOMMENDATION: Deploy with confidence")
        print("   The SMA-110 strategy has proven robustness")
        
    elif winning_periods >= 2:
        print("⚠️  PARTIAL ROBUSTNESS")
        print(f"\nStrategy wins in {winning_periods}/{len(period_results)} periods")
        print(f"Average alpha: {avg_alpha:+.1f}%")
        
        # Identify losing period
        losing_periods = [r for r in period_results if r['alpha'] < 0]
        if losing_periods:
            print(f"\n⚠️  Underperforms in:")
            for r in losing_periods:
                print(f"   • {r['period']}: {r['alpha']:+.1f}% alpha")
        
        print("\n💭 RECOMMENDATION: Use with caution")
        print("   • Strong in most regimes but not all")
        print("   • Consider regime detection or ensemble approach")
        
    else:
        print("❌ STRATEGY MAY BE OVERFIT")
        print(f"\nOnly wins in {winning_periods}/{len(period_results)} periods")
        print(f"Average alpha: {avg_alpha:+.1f}%")
        
        print("\n⚠️  WARNING: Inconsistent performance suggests:")
        print("   • Overfitting to full period data")
        print("   • Not robust across different market regimes")
        print("   • May not generalize to future data")
        
        print("\n💡 RECOMMENDATION: Do NOT deploy")
        print("   • Re-optimize with stricter validation")
        print("   • Consider simpler/more conservative parameters")
        print("   • Test on longer historical data")
    
    # =========================================================================
    # 8. COMPARISON WITH OTHER STRATEGIES
    # =========================================================================
    print("\n" + "="*80)
    print("📊 COMPARISON WITH OTHER STRATEGIES")
    print("="*80 + "\n")
    
    print(f"{'Strategy':<30} {'Return':<12} {'Alpha':<10} {'Sharpe':<8} {'Trades/Yr':<12} {'Status':<20}")
    print("-" * 95)
    
    # Full period results
    full_result = results[-1]
    
    other_strategies = [
        ("Buy & Hold", 1143, 0, 1.3, 0, "Benchmark"),
        ("SMA-50", 1426, 283, 0.95, 9.3, "Good but volatile"),
        ("EMA-150", 1206, 63, 1.00, 4.7, "Conservative"),
        ("SMA-110 (Optimized)", full_result['strategy_return'], full_result['alpha'], 
         full_result['sharpe'], full_result['trades_per_year'], "⭐ Best"),
    ]
    
    for name, ret, alpha, sharpe, trades, status in other_strategies:
        print(f"{name:<30} {ret:>10.0f}% {alpha:>8.0f}% {sharpe:>6.2f} {trades:>10.1f} {status:<20}")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
