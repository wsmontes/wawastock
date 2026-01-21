"""
Debug BTC Winning V2 - Ver logs detalhados
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_winning_v2 import BTCWinningV2
from rich.console import Console

console = Console()

# Parâmetros V2 com diferentes configurações de filtros
PARAMS_V2_STRICT = {
    'rsi_period': 13,
    'rsi_exit_threshold': 25,
    'rsi_entry_threshold': 36,
    'macd_fast': 15,
    'macd_slow': 30,
    'macd_signal': 7,
    'macd_exit_threshold': -90.27,
    'macd_entry_threshold': -18.29,
    'volume_period': 11,
    'volume_panic_multiplier': 2.49,
    'volume_entry_max': 1.25,
    'bb_period': 25,
    'bb_std': 2.20,
    'bb_exit_lower_mult': 0.86,
    'bb_entry_position': 0.56,
    'momentum_period': 15,
    'momentum_exit_threshold': -0.13,
    'momentum_entry_threshold': -0.005,
    'min_exit_signals': 3,
    'min_entry_signals': 2,
    'position_size': 0.988,
    'hold_period_after_exit': 2,
    'atr_period': 14,
    'atr_stop_multiplier': 2.5,
    'atr_trailing_multiplier': 3.0,
    'trailing_activation_pct': 0.15,
    'use_dynamic_stops': True,
    'use_correlation_filter': False,
    'use_trend_strength': True,  # Ativado
    'trend_lookback': 10,
    'min_higher_highs': 3,  # Restritivo
    'min_higher_lows': 3,  # Restritivo
    'use_bull_protection': True,
    'bull_run_threshold': 0.50,
    'bull_run_period': 30,
    'bull_exit_signals_add': 2,
}

PARAMS_V2_RELAXED = {
    **PARAMS_V2_STRICT,
    'use_trend_strength': False,  # Desligar filtro
    'position_size': 0.988,  # Voltar ao agressivo
}


def test_config(name, params):
    console.print(f"\n[bold cyan]Testing: {name}[/bold cyan]")
    
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
    
    backtest = BacktestEngine(initial_cash=10000, commission=0.001)
    results = backtest.run_backtest(
        strategy_cls=BTCWinningV2,
        data_df=df,
        symbol='BTC-USD',
        **params
    )
    
    return_pct = results.get('return_pct', 0)
    analyzers = results.get('analyzers', {})
    trades = analyzers.get('total_trades', 0)
    
    console.print(f"  Return: [green]+{return_pct:.2f}%[/green]")
    console.print(f"  Trades: {trades}")
    console.print(f"  Win Rate: {analyzers.get('won_trades', 0)/trades*100 if trades > 0 else 0:.1f}%")
    console.print(f"  Sharpe: {analyzers.get('sharpe', 0):.3f}")
    console.print(f"  Max DD: {abs(analyzers.get('max_drawdown', 0)):.2f}%")
    
    return results


def main():
    console.print("[bold]BTC WINNING V2 - DEBUG CONFIGURATIONS[/bold]\n")
    
    # Test 1: Strict filters
    console.print("[yellow]Test 1: Filtros RESTRITIVOS (HH/HL 3/3)[/yellow]")
    r1 = test_config("V2 Strict", PARAMS_V2_STRICT)
    
    # Test 2: Relaxed filters
    console.print("\n[yellow]Test 2: Filtros DESLIGADOS[/yellow]")
    r2 = test_config("V2 Relaxed", PARAMS_V2_RELAXED)
    
    # Comparison
    console.print("\n[bold cyan]═══ CONCLUSÃO ═══[/bold cyan]")
    
    r1_trades = r1.get('analyzers', {}).get('total_trades', 0)
    r2_trades = r2.get('analyzers', {}).get('total_trades', 0)
    blocked = r2_trades - r1_trades
    
    console.print(f"Trades bloqueados pelo filtro: [red]{blocked}[/red] ({blocked/r2_trades*100 if r2_trades > 0 else 0:.1f}%)")
    console.print(f"Performance SEM filtro: [green]+{r2.get('return_pct', 0):.2f}%[/green]")
    console.print(f"Performance COM filtro: [yellow]+{r1.get('return_pct', 0):.2f}%[/yellow]")
    
    delta = r2.get('return_pct', 0) - r1.get('return_pct', 0)
    if delta > 0:
        console.print(f"\n[bold red]❌ Filtro PREJUDICOU performance em {delta:.2f}%[/bold red]")
    else:
        console.print(f"\n[bold green]✅ Filtro MELHOROU performance em {abs(delta):.2f}%[/bold green]")


if __name__ == '__main__':
    main()
