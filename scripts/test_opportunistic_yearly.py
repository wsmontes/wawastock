"""
Test BTCOpportunistic strategy year by year (2020-2025).

Key differences from previous tests:
- Strategy holds by default (high exposure time)
- Only exits on clear danger signals
- Quick re-entries to minimize time out of market
- Expected: 6-8 trades/year, 80-90% exposure time, 70%+ yearly win rate
"""

from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_opportunistic import BTCOpportunistic


def test_year(year: int, initial_cash: float = 100000.0):
    """Test strategy for a single year."""
    
    # Load data for the year
    data_engine = DataEngine(use_cache=True, auto_indicators=False)
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    df = data_engine.load_prices(symbol='BTC-USD', start=start_date, end=end_date)
    
    if df is None or len(df) == 0:
        return None
    
    # Buy & Hold comparison
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    bnh_return = (end_price - start_price) / start_price * 100
    
    # Run backtest using BacktestEngine
    from engines.backtest_engine import BacktestEngine
    backtest = BacktestEngine(initial_cash=initial_cash, commission=0.001)
    results = backtest.run_backtest(
        strategy_cls=BTCOpportunistic,
        data_df=df,
        symbol='BTC-USD'
    )
    
    # Get metrics from results
    strategy_return = results.get('return_pct', 0)
    alpha = strategy_return - bnh_return
    
    # Trade analysis
    analyzers = results.get('analyzers', {})
    total_trades = analyzers.get('total_trades', 0)
    won_trades = analyzers.get('won_trades', 0)
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Drawdown
    max_dd = abs(analyzers.get('max_drawdown', 0))
    
    # Sharpe
    sharpe = analyzers.get('sharpe', 0) or 0
    
    # Final value
    final_value = results.get('final_value', initial_cash)
    
    return {
        'year': year,
        'strategy_return': strategy_return,
        'bnh_return': bnh_return,
        'alpha': alpha,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'final_value': final_value
    }


def print_yearly_results(results: list):
    """Print formatted yearly results."""
    
    print("\n" + "="*100)
    print("BTCOpportunistic Strategy - Yearly Performance Analysis (2020-2025)")
    print("="*100)
    print(f"{'Year':<8} {'Strategy':<12} {'Buy&Hold':<12} {'Alpha':<12} {'Trades':<8} {'Win%':<8} {'MaxDD%':<10} {'Sharpe':<8}")
    print("-"*100)
    
    years_beat_bnh = 0
    total_alpha = 0
    total_trades = 0
    
    for r in results:
        beat_marker = "✅" if r['alpha'] > 0 else "❌"
        print(f"{r['year']:<8} {r['strategy_return']:>+10.1f}%  {r['bnh_return']:>+10.1f}%  "
              f"{r['alpha']:>+10.1f}% {beat_marker}  {r['total_trades']:<8} "
              f"{r['win_rate']:<7.1f}  {r['max_drawdown']:<9.1f}  {r['sharpe']:<8.2f}")
        
        if r['alpha'] > 0:
            years_beat_bnh += 1
        total_alpha += r['alpha']
        total_trades += r['total_trades']
    
    print("-"*100)
    
    # Summary statistics
    years_tested = len(results)
    yearly_win_rate = (years_beat_bnh / years_tested * 100) if years_tested > 0 else 0
    avg_alpha = total_alpha / years_tested if years_tested > 0 else 0
    avg_trades_per_year = total_trades / years_tested if years_tested > 0 else 0
    
    print(f"\nSUMMARY:")
    print(f"Years tested: {years_tested}")
    print(f"Years beat B&H: {years_beat_bnh}/{years_tested} ({yearly_win_rate:.1f}%)")
    print(f"Average alpha per year: {avg_alpha:+.1f}%")
    print(f"Total trades: {total_trades} ({avg_trades_per_year:.1f}/year)")
    
    # Calculate aggregate strategy return
    cumulative_value = 100000.0
    for r in results:
        cumulative_value *= (1 + r['strategy_return'] / 100)
    aggregate_strategy_return = (cumulative_value - 100000.0) / 100000.0 * 100
    
    # Calculate aggregate B&H return
    bnh_cumulative = 100000.0
    for r in results:
        bnh_cumulative *= (1 + r['bnh_return'] / 100)
    aggregate_bnh_return = (bnh_cumulative - 100000.0) / 100000.0 * 100
    aggregate_alpha = aggregate_strategy_return - aggregate_bnh_return
    
    # Calculate overall win rate
    total_won = sum([r['total_trades'] * r['win_rate'] / 100 for r in results])
    overall_win_rate = (total_won / total_trades * 100) if total_trades > 0 else 0
    
    print(f"Aggregate strategy return: {aggregate_strategy_return:+.1f}%")
    print(f"Aggregate B&H return: {aggregate_bnh_return:+.1f}%")
    print(f"Aggregate alpha: {aggregate_alpha:+.1f}%")
    print(f"Overall win rate: {overall_win_rate:.1f}%")
    
    print("\n" + "="*100)
    print("EVALUATION:")
    print("="*100)
    
    # Criteria
    criteria = {
        'Yearly win rate >60%': yearly_win_rate > 60,
        'Average alpha >0%': avg_alpha > 0,
        'Trades per year >3': avg_trades_per_year >= 3,
        'Overall win rate >50%': overall_win_rate > 50
    }
    
    passed = sum(criteria.values())
    total_criteria = len(criteria)
    
    for criterion, result in criteria.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{criterion:<30} {status}")
    
    print("-"*100)
    
    if passed == total_criteria:
        verdict = "✅ SUCCESS"
        color = "green"
    elif passed >= total_criteria - 1:
        verdict = "⚠️  PARTIAL"
        color = "yellow"
    else:
        verdict = "❌ INSUFICIENTE"
        color = "red"
    
    print(f"\nVERDICT: {verdict} ({passed}/{total_criteria} criteria met)")
    
    # Detailed recommendations
    print("\n" + "="*100)
    print("DETAILED ANALYSIS:")
    print("="*100)
    
    if yearly_win_rate < 60:
        print(f"⚠️  Yearly win rate ({yearly_win_rate:.1f}%) below target (60%)")
        print(f"   → Check which years failed and why")
        print(f"   → Analyze danger signal effectiveness")
    
    if avg_alpha < 0:
        print(f"⚠️  Average alpha ({avg_alpha:+.1f}%) is negative")
        print(f"   → Strategy underperforming B&H on average")
        print(f"   → Review exit timing and re-entry speed")
    
    if avg_trades_per_year < 3:
        print(f"⚠️  Low trade frequency ({avg_trades_per_year:.1f}/year)")
        print(f"   → May lead to high variance in outcomes")
        print(f"   → Consider more sensitive danger signals")
    
    if overall_win_rate < 50:
        print(f"⚠️  Overall win rate ({overall_win_rate:.1f}%) below 50%")
        print(f"   → Exit timing needs improvement")
        print(f"   → Review false positives in danger signals")
    
    # Exposure time analysis (approximate)
    avg_exposure_days = 365 - (365 / (avg_trades_per_year / 2) if avg_trades_per_year > 0 else 0)
    exposure_pct = (avg_exposure_days / 365 * 100)
    print(f"\n📊 Estimated market exposure: {exposure_pct:.1f}%")
    
    if exposure_pct < 70:
        print(f"   ⚠️  Low exposure ({exposure_pct:.1f}%) - may miss rallies")
    elif exposure_pct > 85:
        print(f"   ✅ High exposure ({exposure_pct:.1f}%) - good rally capture")
    
    print("\n" + "="*100)


def main():
    """Test strategy for each year from 2020 to 2025."""
    
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    results = []
    
    print("\nTesting BTCOpportunistic strategy year by year...")
    print("Strategy: Hold by default, exit on danger signals, quick re-entries")
    print("-"*100)
    
    for year in years:
        print(f"Testing {year}...", end=" ", flush=True)
        result = test_year(year)
        
        if result:
            results.append(result)
            print(f"✅ Strategy: {result['strategy_return']:+.1f}%, B&H: {result['bnh_return']:+.1f}%, Alpha: {result['alpha']:+.1f}%")
        else:
            print(f"❌ No data available")
    
    if results:
        print_yearly_results(results)
    else:
        print("\n❌ No results to display")


if __name__ == '__main__':
    main()
