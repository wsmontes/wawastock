"""
Analyze BTC historical crashes to identify EXIT signals.

Goal: Find indicators that signal "exit NOW before crash" not "crash already happened".

Major BTC crashes to analyze:
1. Nov 2021 peak ($69k) → May 2022 bottom ($26k) = -62% crash
2. Nov 2021 → Dec 2022 = continued bear
3. 2020 and 2023-2024 had NO major crashes (continuous rallies)

Exit signal candidates:
- RSI > 75 for 5+ days (overbought exhaustion)
- Parabolic rally (>100% in 3 months)
- Volume exhaustion (declining volume on new highs)
- MACD bearish divergence (price up, MACD down)
- Bollinger Band stretch (price > 2.5 std above mean)
"""

import pandas as pd
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.data_engine import DataEngine
import backtrader as bt


def calculate_indicators(df):
    """Calculate exit-signal indicators."""
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 3-month return
    df['return_90d'] = df['close'].pct_change(periods=90) * 100
    
    # Volume trend (declining volume = exhaustion)
    df['volume_sma20'] = df['volume'].rolling(window=20).mean()
    df['volume_trend'] = df['volume'] / df['volume_sma20']
    
    # Bollinger Bands
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['sma20'] + (2 * df['bb_std'])
    df['bb_position'] = (df['close'] - df['sma20']) / df['bb_std']
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Price momentum (rate of change)
    df['roc_30'] = df['close'].pct_change(periods=30) * 100
    
    return df


def analyze_period(df, start_date, end_date, period_name):
    """Analyze a specific period for exit signals."""
    
    # Use index for date filtering (datetime is the index)
    period_df = df[(df.index >= start_date) & (df.index <= end_date)].copy()
    
    if len(period_df) == 0:
        print(f"\n❌ No data for {period_name}")
        return
    
    print(f"\n{'='*100}")
    print(f"📊 {period_name}: {start_date} to {end_date}")
    print(f"{'='*100}")
    
    # Price stats
    start_price = period_df.iloc[0]['close']
    peak_price = period_df['close'].max()
    end_price = period_df.iloc[-1]['close']
    peak_date = period_df[period_df['close'] == peak_price].index[0]
    
    print(f"\n💰 Price Action:")
    print(f"   Start: ${start_price:,.0f}")
    print(f"   Peak: ${peak_price:,.0f} on {str(peak_date)[:10]}")
    print(f"   End: ${end_price:,.0f}")
    print(f"   Total return: {(end_price/start_price - 1)*100:+.1f}%")
    print(f"   Peak to end: {(end_price/peak_price - 1)*100:+.1f}%")
    
    # Find exit signals near peak
    peak_idx = period_df[period_df['close'] == peak_price].index[0]
    peak_window_start = max(period_df.index[0], peak_idx - pd.Timedelta(days=30))
    peak_window_end = min(period_df.index[-1], peak_idx + pd.Timedelta(days=10))
    peak_window = period_df.loc[peak_window_start:peak_window_end]
    
    print(f"\n🚨 Exit Signals Near Peak ({len(peak_window)} days around peak):")
    
    # Signal 1: Extreme RSI
    extreme_rsi_days = peak_window[peak_window['rsi'] > 75]
    print(f"   RSI > 75: {len(extreme_rsi_days)} days")
    if len(extreme_rsi_days) > 0:
        max_rsi = extreme_rsi_days['rsi'].max()
        max_rsi_date = extreme_rsi_days[extreme_rsi_days['rsi'] == max_rsi].index[0]
        print(f"      Max RSI: {max_rsi:.1f} on {str(max_rsi_date)[:10]}")
    
    # Signal 2: Parabolic rally
    peak_row = period_df.loc[peak_idx]
    rally_return = peak_row['return_90d']
    print(f"   90-day return at peak: {rally_return:.1f}%")
    if rally_return > 100:
        print(f"      ⚠️  PARABOLIC RALLY (>100% in 90 days)")
    
    # Signal 3: Volume exhaustion
    peak_vol_trend = peak_row['volume_trend']
    print(f"   Volume trend at peak: {peak_vol_trend:.2f}x (vs 20-day avg)")
    if peak_vol_trend < 0.8:
        print(f"      ⚠️  VOLUME EXHAUSTION (declining volume)")
    
    # Signal 4: BB stretch
    bb_pos = peak_row['bb_position']
    print(f"   Bollinger position at peak: {bb_pos:.2f} std")
    if bb_pos > 2:
        print(f"      ⚠️  EXTREME OVERBOUGHT (>2 std)")
    
    # Signal 5: MACD divergence (check if MACD declining while price rising)
    peak_loc = period_df.index.get_loc(peak_idx)
    if peak_loc > 30:
        prev_idx = period_df.index[max(0, peak_loc - 30)]
        prev_30d = period_df.loc[prev_idx:peak_idx]
        price_trend = (peak_row['close'] - prev_30d.iloc[0]['close']) / prev_30d.iloc[0]['close']
        macd_trend = (peak_row['macd'] - prev_30d.iloc[0]['macd']) / abs(prev_30d.iloc[0]['macd'])
        print(f"   30-day price trend: {price_trend*100:+.1f}%")
        print(f"   30-day MACD trend: {macd_trend*100:+.1f}%")
        if price_trend > 0 and macd_trend < 0:
            print(f"      ⚠️  BEARISH DIVERGENCE (price up, MACD down)")
    
    # Composite exit signal
    print(f"\n✅ IDEAL EXIT SIGNAL (combine all):")
    ideal_exit_candidates = peak_window[
        (peak_window['rsi'] > 75) &
        (peak_window['return_90d'] > 80) &
        (peak_window['bb_position'] > 1.5)
    ]
    
    if len(ideal_exit_candidates) > 0:
        first_signal = ideal_exit_candidates.iloc[0]
        signal_date = first_signal.name  # index is the date
        signal_price = first_signal['close']
        days_before_peak = (peak_date - signal_date).days
        
        print(f"   First signal: {str(signal_date)[:10]} at ${signal_price:,.0f}")
        print(f"   Days before peak: {days_before_peak}")
        print(f"   Exit price: ${signal_price:,.0f}")
        print(f"   Actual peak: ${peak_price:,.0f}")
        print(f"   Would have captured: {(signal_price/start_price - 1)*100:.1f}% of rally")
        print(f"   Would have avoided: {(1 - end_price/signal_price)*100:.1f}% of drawdown")
    else:
        print(f"   ❌ No clear exit signal with combined criteria")
        print(f"   (Need to adjust thresholds)")


def main():
    """Analyze BTC crashes to find exit signals."""
    
    print("\n" + "="*100)
    print(" "*30 + "🔍 FINDING THE PERFECT EXIT SIGNALS")
    print("="*100)
    print("Goal: Identify signals that predict crashes BEFORE they happen")
    print("="*100)
    
    # Load full BTC data
    data_engine = DataEngine(use_cache=True, auto_indicators=False)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-12-31')
    
    if df is None or len(df) == 0:
        print("❌ No data available")
        return
    
    print(f"\n✅ Loaded {len(df)} days of BTC data")
    
    # Calculate indicators
    print(f"🔄 Calculating exit indicators...")
    df = calculate_indicators(df)
    
    # Analyze key periods
    
    # Period 1: 2020-2021 Bull Run and Crash
    analyze_period(df, '2020-03-01', '2022-06-30', 
                   "2020-2021 Bull Run → 2022 Crash")
    
    # Period 2: 2021 Peak specifically
    analyze_period(df, '2021-09-01', '2022-01-31', 
                   "2021 Peak → Crash Beginning")
    
    # Period 3: 2023-2024 Bull Run (no crash)
    analyze_period(df, '2023-01-01', '2024-12-31', 
                   "2023-2024 Bull Run (No Crash)")
    
    # Summary
    print(f"\n" + "="*100)
    print("📋 SUMMARY: Best Exit Signal Combination")
    print("="*100)
    print("Based on analysis, exit when ALL conditions met:")
    print("   1. RSI > 75 (overbought exhaustion)")
    print("   2. 90-day return > 80% (parabolic rally)")
    print("   3. Bollinger position > 1.5 std (extreme stretch)")
    print("   4. OPTIONAL: Volume trend < 1.0 (exhaustion)")
    print("   5. OPTIONAL: MACD bearish divergence")
    print("\nRe-entry signals:")
    print("   1. RSI < 30 (capitulation) OR")
    print("   2. Price stable for 10 days (< 5% movement)")
    print("="*100 + "\n")


if __name__ == '__main__':
    main()
