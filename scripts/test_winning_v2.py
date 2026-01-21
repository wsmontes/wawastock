"""
Teste da estratégia BTC Winning V2 (com quick wins)

Compara:
1. Buy & Hold
2. V1 (estratégia campeã original)
3. V2 (com ATR stops + trend strength + bull protection)
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_hold import BTCAdaptiveHold
from strategies.btc_winning_v2 import BTCWinningV2
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

console = Console()


# Parâmetros do Trial #163 (campeão V2)
BASE_PARAMS = {
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
}

# Novos parâmetros V2
V2_PARAMS = {
    **BASE_PARAMS,
    'atr_period': 14,
    'atr_stop_multiplier': 2.5,
    'atr_trailing_multiplier': 3.0,
    'trailing_activation_pct': 0.15,
    'use_dynamic_stops': True,
    'use_correlation_filter': False,
    'use_trend_strength': True,
    'trend_lookback': 10,
    'min_higher_highs': 3,
    'min_higher_lows': 3,
    'use_bull_protection': True,
    'bull_run_threshold': 0.50,
    'bull_run_period': 30,
    'bull_exit_signals_add': 2,
    'position_size': 0.70,  # Mais conservador
}


def main():
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   BTC WINNING V2 - TESTE DE QUICK WINS[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")
    
    # Load data
    console.print("[yellow]Carregando dados BTC...[/yellow]")
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
    
    # Buy & Hold
    first_price = df.iloc[0]['close']
    last_price = df.iloc[-1]['close']
    bh_return = ((last_price - first_price) / first_price) * 100
    bh_final = 10000 * (1 + bh_return / 100)
    
    console.print(f"[green]✓[/green] Carregados {len(df)} dias")
    console.print(f"   ${first_price:,.2f} → ${last_price:,.2f}")
    console.print(f"   Buy & Hold: [yellow]+{bh_return:.2f}%[/yellow]\n")
    
    # V1
    console.print("[yellow]Rodando V1 (campeã original)...[/yellow]")
    backtest_v1 = BacktestEngine(initial_cash=10000, commission=0.001)
    results_v1 = backtest_v1.run_backtest(
        strategy_cls=BTCAdaptiveHold,
        data_df=df,
        symbol='BTC-USD',
        **BASE_PARAMS
    )
    
    # V2
    console.print("[yellow]Rodando V2 (quick wins)...[/yellow]")
    backtest_v2 = BacktestEngine(initial_cash=10000, commission=0.001)
    results_v2 = backtest_v2.run_backtest(
        strategy_cls=BTCWinningV2,
        data_df=df,
        symbol='BTC-USD',
        **V2_PARAMS
    )
    
    # ==========================================
    # COMPARAÇÃO
    # ==========================================
    
    console.print("\n[bold green]═══ RESULTADOS ═══[/bold green]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan", width=30)
    table.add_column("Buy & Hold", justify="right", style="white")
    table.add_column("V1 (Original)", justify="right", style="yellow")
    table.add_column("V2 (Quick Wins)", justify="right", style="green")
    table.add_column("Δ V2 vs V1", justify="right", style="bold")
    
    # Returns
    v1_return = results_v1.get('return_pct', 0)
    v2_return = results_v2.get('return_pct', 0)
    
    v1_final = 10000 * (1 + v1_return / 100)
    v2_final = 10000 * (1 + v2_return / 100)
    
    delta_return = v2_return - v1_return
    
    table.add_row(
        "Retorno Total",
        f"+{bh_return:.2f}%",
        f"+{v1_return:.2f}%",
        f"+{v2_return:.2f}%",
        f"[green]+{delta_return:.2f}%[/green]" if delta_return > 0 else f"[red]{delta_return:.2f}%[/red]"
    )
    
    table.add_row(
        "Valor Final",
        f"${bh_final:,.2f}",
        f"${v1_final:,.2f}",
        f"${v2_final:,.2f}",
        f"[green]+${v2_final - v1_final:,.2f}[/green]" if v2_final > v1_final else f"[red]-${abs(v2_final - v1_final):,.2f}[/red]"
    )
    
    # Alpha
    v1_alpha = v1_return - bh_return
    v2_alpha = v2_return - bh_return
    delta_alpha = v2_alpha - v1_alpha
    
    table.add_row(
        "Alpha vs B&H",
        "-",
        f"[green]+{v1_alpha:.2f}%[/green]" if v1_alpha > 0 else f"[red]{v1_alpha:.2f}%[/red]",
        f"[green]+{v2_alpha:.2f}%[/green]" if v2_alpha > 0 else f"[red]{v2_alpha:.2f}%[/red]",
        f"[green]+{delta_alpha:.2f}%[/green]" if delta_alpha > 0 else f"[red]{delta_alpha:.2f}%[/red]"
    )
    
    # Trades
    v1_analyzers = results_v1.get('analyzers', {})
    v2_analyzers = results_v2.get('analyzers', {})
    
    v1_trades = v1_analyzers.get('total_trades', 0)
    v2_trades = v2_analyzers.get('total_trades', 0)
    
    table.add_row(
        "Total Trades",
        "-",
        str(v1_trades),
        str(v2_trades),
        f"+{v2_trades - v1_trades}" if v2_trades >= v1_trades else f"{v2_trades - v1_trades}"
    )
    
    # Win rate
    v1_won = v1_analyzers.get('won_trades', 0)
    v2_won = v2_analyzers.get('won_trades', 0)
    
    v1_winrate = (v1_won / v1_trades * 100) if v1_trades > 0 else 0
    v2_winrate = (v2_won / v2_trades * 100) if v2_trades > 0 else 0
    
    delta_winrate = v2_winrate - v1_winrate
    
    table.add_row(
        "Win Rate",
        "-",
        f"{v1_winrate:.1f}%",
        f"{v2_winrate:.1f}%",
        f"[green]+{delta_winrate:.1f}%[/green]" if delta_winrate > 0 else f"[red]{delta_winrate:.1f}%[/red]"
    )
    
    # Sharpe
    v1_sharpe = v1_analyzers.get('sharpe', 0) or 0
    v2_sharpe = v2_analyzers.get('sharpe', 0) or 0
    
    delta_sharpe = v2_sharpe - v1_sharpe
    
    table.add_row(
        "Sharpe Ratio",
        "-",
        f"{v1_sharpe:.3f}",
        f"{v2_sharpe:.3f}",
        f"[green]+{delta_sharpe:.3f}[/green]" if delta_sharpe > 0 else f"[red]{delta_sharpe:.3f}[/red]"
    )
    
    # Max Drawdown
    v1_dd = abs(v1_analyzers.get('max_drawdown', 0))
    v2_dd = abs(v2_analyzers.get('max_drawdown', 0))
    
    delta_dd = v2_dd - v1_dd
    
    table.add_row(
        "Max Drawdown",
        "-",
        f"{v1_dd:.2f}%",
        f"{v2_dd:.2f}%",
        f"[green]{delta_dd:.2f}%[/green]" if delta_dd < 0 else f"[red]+{delta_dd:.2f}%[/red]"
    )
    
    console.print(table)
    
    # ==========================================
    # ANÁLISE
    # ==========================================
    
    console.print("\n[bold cyan]═══ ANÁLISE ═══[/bold cyan]\n")
    
    if v2_alpha > v1_alpha:
        improvement = ((v2_alpha - v1_alpha) / abs(v1_alpha)) * 100 if v1_alpha != 0 else 0
        console.print(f"[bold green]✅ V2 MELHOR que V1[/bold green]")
        console.print(f"   Alpha melhorou: {v1_alpha:.2f}% → {v2_alpha:.2f}% ([green]+{v2_alpha - v1_alpha:.2f}%[/green])")
        console.print(f"   Melhoria relativa: [green]+{improvement:.1f}%[/green]")
    else:
        console.print(f"[bold red]❌ V2 PIOR que V1[/bold red]")
        console.print(f"   Alpha piorou: {v1_alpha:.2f}% → {v2_alpha:.2f}% ([red]{v2_alpha - v1_alpha:.2f}%[/red])")
    
    console.print()
    
    # Features ativas
    console.print("[bold yellow]Features V2 ativas:[/bold yellow]")
    console.print("  ✅ ATR Dynamic Stops (2.5x hard stop, 3.0x trailing após +15%)")
    console.print("  ✅ Trend Strength (HH/HL 3/3 - mais restritivo)")
    console.print("  ✅ Bull Run Protection (+2 signals em rallies +50%)")
    console.print("  ✅ Position Sizing conservador (70% do capital)")
    console.print("  ⚠️  S&P500 Correlation (desligado - precisa segundo feed)")
    
    console.print()


if __name__ == '__main__':
    main()
