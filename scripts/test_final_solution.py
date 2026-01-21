"""
FINAL TEST: Test Enhanced B&H on full 2020-2025 period.

This is the definitive test to determine if we found the perfect solution.
"""

from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_enhanced_bh import BTCEnhancedBH


def main():
    """Run comprehensive test on full period."""
    
    print("\n" + "="*110)
    print(" "*35 + "🏆 FINAL TEST: THE PERFECT SOLUTION 🏆")
    print("="*110)
    print("Strategy: BTCEnhancedBH - Enhanced Buy & Hold")
    print("Period: 2020-2025 (6 years)")
    print("Approach: Stay 100% invested unless deep bear confirmed")
    print("="*110 + "\n")
    
    # Load full period data
    data_engine = DataEngine(use_cache=True, auto_indicators=False)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-12-31')
    
    if df is None or len(df) == 0:
        print("❌ No data available")
        return
    
    print(f"✅ Loaded {len(df)} days of BTC-USD data\n")
    
    # Calculate Buy & Hold
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    bnh_return = (end_price - start_price) / start_price * 100
    
    print(f"📊 Buy & Hold Performance:")
    print(f"   Start: ${start_price:,.2f}")
    print(f"   End: ${end_price:,.2f}")
    print(f"   Return: {bnh_return:+.1f}%\n")
    
    # Run strategy backtest
    print("🔄 Running Enhanced B&H strategy backtest...")
    backtest = BacktestEngine(initial_cash=100000, commission=0.001)
    results = backtest.run_backtest(
        strategy_cls=BTCEnhancedBH,
        data_df=df,
        symbol='BTC-USD'
    )
    
    # Extract results
    strategy_return = results.get('return_pct', 0)
    final_value = results.get('final_value', 100000)
    alpha = strategy_return - bnh_return
    
    analyzers = results.get('analyzers', {})
    total_trades = analyzers.get('total_trades', 0)
    won_trades = analyzers.get('won_trades', 0)
    lost_trades = analyzers.get('lost_trades', 0)
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    max_dd = abs(analyzers.get('max_drawdown', 0))
    sharpe = analyzers.get('sharpe', 0) or 0
    
    print(f"\n📊 Enhanced B&H Performance:")
    print(f"   Final Value: ${final_value:,.2f}")
    print(f"   Return: {strategy_return:+.1f}%")
    print(f"   Alpha vs B&H: {alpha:+.1f}%")
    print(f"   Total Trades: {total_trades}")
    print(f"   Won/Lost: {won_trades}/{lost_trades}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Max Drawdown: {max_dd:.1f}%")
    print(f"   Sharpe Ratio: {sharpe:.2f}")
    
    print("\n" + "="*110)
    print("🎯 EVALUATION:")
    print("="*110)
    
    # Evaluation
    if total_trades == 0:
        print("❌ CRITICAL FAILURE: Strategy never entered any trades!")
        print("   This means the entry conditions were never met.")
        print("   Possible issues:")
        print("   - SMA200 warmup period too long")
        print("   - Entry conditions too restrictive")
        print("   - Bug in strategy logic")
        return
    
    if strategy_return >= bnh_return * 0.9:  # Within 10% of B&H
        print(f"✅ EXCELLENT: Strategy return ({strategy_return:+.1f}%) matches B&H ({bnh_return:+.1f}%)")
        print(f"   Alpha: {alpha:+.1f}% (goal was ≥0%)")
    elif strategy_return > 0:
        print(f"⚠️  GOOD: Strategy return ({strategy_return:+.1f}%) positive but below B&H ({bnh_return:+.1f}%)")
        print(f"   Alpha: {alpha:+.1f}% (goal was ≥0%)")
    else:
        print(f"❌ POOR: Strategy return ({strategy_return:+.1f}%) negative vs B&H ({bnh_return:+.1f}%)")
        print(f"   Alpha: {alpha:+.1f}% (goal was ≥0%)")
    
    # Trade frequency
    trades_per_year = total_trades / 6
    if trades_per_year <= 2:
        print(f"✅ EXCELLENT: Low trade frequency ({trades_per_year:.1f}/year = {total_trades} total)")
    elif trades_per_year <= 5:
        print(f"⚠️  ACCEPTABLE: Moderate trade frequency ({trades_per_year:.1f}/year = {total_trades} total)")
    else:
        print(f"❌ EXCESSIVE: High trade frequency ({trades_per_year:.1f}/year = {total_trades} total)")
    
    # Win rate
    if win_rate >= 60:
        print(f"✅ EXCELLENT: High win rate ({win_rate:.1f}%)")
    elif win_rate >= 50:
        print(f"⚠️  ACCEPTABLE: Moderate win rate ({win_rate:.1f}%)")
    else:
        print(f"❌ POOR: Low win rate ({win_rate:.1f}%)")
    
    print("\n" + "="*110)
    print("🏁 FINAL VERDICT:")
    print("="*110)
    
    if alpha >= 0 and total_trades > 0 and trades_per_year <= 2:
        print("🏆 PERFECT SOLUTION ACHIEVED!")
        print("   ✅ Positive alpha")
        print("   ✅ Low trade frequency")
        print("   ✅ Enhanced B&H successfully implemented")
        print("\n   RECOMMENDATION: Use BTCEnhancedBH for BTC trading")
    elif strategy_return >= 0 and total_trades > 0:
        print("✅ GOOD SOLUTION")
        print("   ✅ Positive returns")
        print("   ⚠️  But negative alpha vs B&H")
        print("\n   RECOMMENDATION: Consider BTCEnhancedBH, but B&H may be simpler")
    else:
        print("❌ SOLUTION FAILED")
        print("   ❌ Did not meet minimum criteria")
        print("\n   RECOMMENDATION: Use V1 Baseline (50% yearly win rate)")
        print("   CONCLUSION: After 7 approaches, simple RSI remains the best timing strategy")
        print("   REALITY CHECK: BTC's explosive nature makes beating B&H extremely difficult")
    
    print("="*110 + "\n")
    
    # Comparison with all approaches
    print("="*110)
    print("📊 COMPREHENSIVE COMPARISON: ALL 7 APPROACHES")
    print("="*110)
    print(f"{'#':<4} {'Approach':<22} {'Result':<50}")
    print("-"*110)
    print(f"{'1':<4} {'V1 Baseline':<22} {'50% yearly win rate, simple RSI strategy':<50}")
    print(f"{'2':<4} {'V2 Optimized':<22} {'33% yearly win rate, overfitted to full period':<50}")
    print(f"{'3':<4} {'BTCAdaptive':<22} {'33% yearly win rate, regime-based, too few trades':<50}")
    print(f"{'4':<4} {'BTCOpportunistic':<22} {'17% yearly win rate, 7.7% exposure, missed everything':<50}")
    print(f"{'5':<4} {'BTCTrendFollower':<22} {'33% yearly win rate, pure SMA, missed all bulls':<50}")
    print(f"{'6':<4} {'BTCPerfect':<22} {'17% yearly win rate, always-in failed':<50}")
    print(f"{'7':<4} {'BTCEnhancedBH':<22} {f'{strategy_return:+.1f}% return, {alpha:+.1f}% alpha, {total_trades} trades':<50}")
    print("="*110)
    
    print("\n💡 KEY LEARNINGS:")
    print("1. Simplicity > Complexity: V1 baseline (50%) beat all sophisticated approaches")
    print("2. Entry timing is critical: Missing early bull entries = massive negative alpha")
    print("3. BTC is explosive: +100-400%/year rallies make timing strategies inferior to B&H")
    print("4. Trade frequency matters: Too few trades (< 3/year) = high variance")
    print("5. Perfect is impossible: 70%+ yearly win rate may be unrealistic for BTC")
    print("\n🎯 FINAL RECOMMENDATION:")
    if alpha >= 0:
        print("Use BTCEnhancedBH if you want B&H-like returns with bear protection")
    else:
        print("Use V1 Baseline if you want active timing (50% yearly win rate)")
    print("Or simply use Buy & Hold - it's very hard to beat systematically!")
    print("="*110 + "\n")


if __name__ == '__main__':
    main()
