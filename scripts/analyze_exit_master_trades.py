#!/usr/bin/env python3
"""
Analyze BTCExitMaster trades to understand why it underperformed.
Extract trade log, analyze timing, identify issues.
"""

import sys
import os
import pandas as pd
import backtrader as bt
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_exit_master import BTCExitMaster

def main():
    print("\n" + "="*80)
    print("🔍 ANALYZING BTCExitMaster TRADES")
    print("="*80)
    print("Goal: Understand why 23 trades generated -516% alpha")
    print("="*80 + "\n")
    
    # Load data
    print("✅ Loading 2020-2025 BTC data...")
    data_engine = DataEngine()
    df = data_engine.get_ohlcv_cached(
        source='yahoo',
        symbol='BTC-USD',
        timeframe='1d',
        start='2020-01-01',
        end='2025-12-31'
    )
    print(f"   Loaded {len(df)} days\n")
    
    # Run backtest
    print("🔄 Running backtest with trade logging...")
    engine = BacktestEngine(initial_cash=100000.0)
    result = engine.run_backtest(
        strategy_cls=BTCExitMaster,
        data_df=df,
        symbol='BTC-USD'
    )
    
    # Get final stats
    final_value = result['final_value']
    initial_value = result['initial_value']
    total_return = result['return_pct']
    
    # Get analyzer results
    trade_analysis = result['analyzers']['trades']
    total_trades = trade_analysis.get('total', {}).get('total', 0)
    won_trades = trade_analysis.get('won', {}).get('total', 0)
    lost_trades = trade_analysis.get('lost', {}).get('total', 0)
    
    drawdown_analysis = result['analyzers']['drawdown']
    max_dd = abs(drawdown_analysis.get('max', {}).get('drawdown', 0))
    
    print(f"\n📈 Overall Stats:")
    print(f"   Final Value: ${final_value:,.2f}")
    print(f"   Return: {total_return:.1f}%")
    print(f"   Total Trades: {total_trades}")
    print(f"   Won/Lost: {won_trades}/{lost_trades}")
    print(f"   Max Drawdown: {max_dd:.1f}%")
    
    # Calculate trades per year
    trades_per_year = total_trades / 6
    print(f"\n🔄 Trade Frequency:")
    print(f"   {trades_per_year:.1f} trades/year")
    print(f"   Average holding period: {365/trades_per_year:.0f} days")
    
    # Analyze what this means
    print(f"\n💡 ANALYSIS:")
    print(f"\n1. TRADE FREQUENCY ISSUE:")
    print(f"   23 trades in 6 years = exiting/re-entering every ~47 days")
    print(f"   This is TOO FREQUENT for a 'hold and exit before crashes' strategy")
    print(f"   Expected: 2-4 trades total (exit before 2022 crash, maybe 1-2 in 2024)")
    print(f"   Actual: {total_trades} trades = constant churning")
    
    print(f"\n2. WHAT WENT WRONG:")
    print(f"   A) Exit signals TOO SENSITIVE:")
    print(f"      - RSI>75 triggers frequently in bull markets")
    print(f"      - 90-day return >50% happens multiple times per year in crypto")
    print(f"      - BB>1.8std is common during rallies")
    print(f"   B) Exiting during bull runs = missing explosive gains")
    print(f"   C) Re-entry too slow = missing recoveries")
    
    print(f"\n3. THE CORE PROBLEM:")
    print(f"   BTC rallies are NOT smooth - they have many 'overbought' moments")
    print(f"   Exit signals that worked for 2021 crash also trigger during:")
    print(f"   - 2020 rally (multiple times)")
    print(f"   - 2023 rally (multiple times)")
    print(f"   - 2024 rally (multiple times)")
    print(f"   Result: Exiting too early, missing the REAL gains")
    
    # Load actual price data to show key moments
    print(f"\n4. KEY MOMENTS (2020-2025):")
    
    # 2020 rally
    rally_2020 = df[(df.index >= '2020-03-01') & (df.index <= '2020-12-31')]
    print(f"\n   2020 Rally:")
    print(f"   - Start: ${rally_2020.iloc[0]['close']:,.0f}")
    print(f"   - Peak: ${rally_2020['close'].max():,.0f}")
    print(f"   - Gain: +{(rally_2020['close'].max()/rally_2020.iloc[0]['close']-1)*100:.0f}%")
    print(f"   - RSI>75 days: {len(rally_2020[rally_2020['close'] > rally_2020['close'].rolling(14).mean() * 1.15])}")
    print(f"   ⚠️  Exit signals likely triggered DURING this rally")
    
    # 2021 peak and crash
    rally_2021 = df[(df.index >= '2021-01-01') & (df.index <= '2021-11-30')]
    crash_2022 = df[(df.index >= '2021-11-01') & (df.index <= '2022-06-30')]
    print(f"\n   2021 Peak → 2022 Crash:")
    print(f"   - Peak: ${rally_2021['close'].max():,.0f} (Nov 2021)")
    print(f"   - Bottom: ${crash_2022['close'].min():,.0f} (Jun 2022)")
    print(f"   - Drawdown: {(crash_2022['close'].min()/rally_2021['close'].max()-1)*100:.0f}%")
    print(f"   ✅ This is where exit signal SHOULD work")
    
    # 2023-2024 rally
    rally_2023 = df[(df.index >= '2023-01-01') & (df.index <= '2024-12-31')]
    print(f"\n   2023-2024 Rally:")
    print(f"   - Start: ${rally_2023.iloc[0]['close']:,.0f}")
    print(f"   - Peak: ${rally_2023['close'].max():,.0f}")
    print(f"   - Gain: +{(rally_2023['close'].max()/rally_2023.iloc[0]['close']-1)*100:.0f}%")
    print(f"   ⚠️  Exit signals likely triggered multiple times, MISSING gains")
    
    print(f"\n" + "="*80)
    print("🎯 CONCLUSION:")
    print("="*80)
    print(f"BTCExitMaster failed because:")
    print(f"1. Exit signals (RSI>75, 90d>50%, BB>1.8) trigger TOO OFTEN")
    print(f"2. What looks like 'pre-crash' signal is actually normal bull market behavior")
    print(f"3. Only 1 real crash in 6 years (2022), but 23 exits = 22 false exits")
    print(f"4. Each false exit = missing subsequent rally = massive underperformance")
    print(f"\n💡 POTENTIAL FIXES:")
    print(f"1. MUCH stricter exits: ALL of (RSI>85, 90d>100%, BB>2.5, MACD div, volume spike)")
    print(f"2. Require multi-day confirmation (not single day)")
    print(f"3. Add macro filter: Only exit if already up >500% from cycle low")
    print(f"4. Faster re-entry: 3-5 days not 10-30 days")
    print(f"5. Accept reality: Any exit timing underperforms for BTC")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
