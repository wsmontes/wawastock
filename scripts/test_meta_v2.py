"""
Teste MetaStrategy V2 - Versão corrigida que HERDA do Trial 77
"""

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from strategies.meta_strategy_v2 import MetaStrategyV2
from rich.console import Console

console = Console()

# Trial 77 params
trial77_params = {
    'rsi_period': 11, 'rsi_oversold': 33, 'rsi_overbought': 76,
    'bb_period': 19, 'bb_dev': 2.35, 'volume_period': 18,
    'volume_threshold': 1.15, 'macd_fast': 11, 'macd_slow': 25,
    'macd_signal': 8, 'ema_fast': 8, 'ema_slow': 19,
    'atr_period': 13, 'atr_multiplier': 1.69,
    'take_profit_pct': 15.83, 'trailing_stop_pct': 9.23,
    'position_size': 0.88, 'min_signals_buy': 2, 'min_signals_sell': 2
}

console.print("[bold cyan]TESTE: MetaStrategy V2 (herda Trial 77)[/bold cyan]")
console.print()

data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)

console.print("="*80)
console.print("1. BASELINE: TRIAL 77 PURO")
console.print("="*80)
console.print()

results_trial77 = backtest_engine.run_backtest(
    strategy_cls=BTCAdaptiveStrategy,
    data_df=df,
    symbol='BTC-USD',
    **trial77_params
)

console.print()
console.print("="*80)
console.print("2. META STRATEGY V2: Trial 77 + Especialistas em Extremos")
console.print("="*80)
console.print("Filosofia: 95% Trial 77, 5% especialistas apenas em:")
console.print("  • STRONG_BULL_RUN (ret20d > 20%, ret60d > 40%)")
console.print("  • CRASH (ret20d < -20%)")
console.print("  • RECOVERY (ret20d > 15% após queda)")
console.print()

results_meta = backtest_engine.run_backtest(
    strategy_cls=MetaStrategyV2,
    data_df=df,
    symbol='BTC-USD',
    **trial77_params  # Mesmos parâmetros base
)

console.print()
console.print("="*80)
console.print("ANÁLISE")
console.print("="*80)
console.print()

# Extrair métricas
t77_return = results_trial77.get('return_pct', 0)
t77_sharpe = results_trial77.get('analyzers', {}).get('sharpe', 0) or 0
t77_dd = abs(results_trial77.get('analyzers', {}).get('max_drawdown', 0) or 0)
t77_trades = results_trial77.get('analyzers', {}).get('total_trades', 0)
t77_won = results_trial77.get('analyzers', {}).get('won_trades', 0)
t77_win_rate = (t77_won / t77_trades * 100) if t77_trades > 0 else 0

meta_return = results_meta.get('return_pct', 0)
meta_sharpe = results_meta.get('analyzers', {}).get('sharpe', 0) or 0
meta_dd = abs(results_meta.get('analyzers', {}).get('max_drawdown', 0) or 0)
meta_trades = results_meta.get('analyzers', {}).get('total_trades', 0)
meta_won = results_meta.get('analyzers', {}).get('won_trades', 0)
meta_win_rate = (meta_won / meta_trades * 100) if meta_trades > 0 else 0

console.print(f"Trial 77:")
console.print(f"  Retorno: +{t77_return:.2f}%")
console.print(f"  Sharpe: {t77_sharpe:.4f}")
console.print(f"  Max DD: {t77_dd:.2f}%")
console.print(f"  Trades: {t77_trades}")
console.print(f"  Win Rate: {t77_win_rate:.2f}%")
console.print()

console.print(f"MetaStrategy V2:")
console.print(f"  Retorno: +{meta_return:.2f}%")
console.print(f"  Sharpe: {meta_sharpe:.4f}")
console.print(f"  Max DD: {meta_dd:.2f}%")
console.print(f"  Trades: {meta_trades}")
console.print(f"  Win Rate: {meta_win_rate:.2f}%")
console.print()

# Diferenças
ret_diff = meta_return - t77_return
sharpe_diff = meta_sharpe - t77_sharpe
dd_diff = meta_dd - t77_dd
trades_diff = meta_trades - t77_trades

console.print("Diferenças:")
console.print(f"  Retorno: {ret_diff:+.2f}% ({ret_diff/t77_return*100:+.1f}% rel)")
console.print(f"  Sharpe: {sharpe_diff:+.4f} ({sharpe_diff/t77_sharpe*100:+.1f}% rel)")
console.print(f"  Max DD: {dd_diff:+.2f}% ({'pior' if dd_diff > 0 else 'melhor'})")
console.print(f"  Trades: {trades_diff:+d}")
console.print()

if meta_return > t77_return * 1.05:  # >5% melhor
    console.print("✅ [bold green]META STRATEGY VENCEU![/bold green]")
    console.print("   Especialistas adicionaram valor ao Trial 77")
elif meta_return > t77_return * 0.95:  # Entre -5% e +5%
    console.print("≈ [yellow]RESULTADOS EQUIVALENTES[/yellow]")
    console.print("   Especialistas não adicionaram nem prejudicaram")
else:
    console.print("❌ [bold red]TRIAL 77 VENCEU[/bold red]")
    console.print("   Especialistas prejudicaram a estratégia base")
