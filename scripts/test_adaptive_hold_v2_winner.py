"""
Testar melhor resultado V2 (com trading ativo - mínimo 25 trades)
"""

import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_hold import BTCAdaptiveHold
from rich.console import Console
from rich.table import Table

console = Console()

# Melhores parâmetros do Trial #163
best_params = {
    'rsi_period': 13,
    'rsi_exit_threshold': 25,
    'macd_fast': 15,
    'macd_slow': 30,
    'macd_signal': 7,
    'macd_exit_threshold': -90.2666780921795,
    'volume_period': 11,
    'volume_panic_multiplier': 2.489958289345298,
    'lookback_dd': 22,
    'drawdown_exit_threshold': -24.575154411086988,
    'bb_period': 25,
    'bb_std': 2.1999574801505646,
    'bb_exit_lower_mult': 0.8600218809777013,
    'atr_period': 12,
    'atr_exit_multiplier': 3.9395381754476064,
    'momentum_period': 15,
    'momentum_exit_threshold': -0.12988890749014315,
    'ema_fast': 23,
    'ema_slow': 70,
    'use_ema_cross_exit': False,
    'min_exit_signals': 3,
    'rsi_entry_threshold': 36,
    'macd_entry_threshold': -17.96092268596845,
    'macd_entry_crossover': False,
    'volume_entry_max': 1.2522815948361519,
    'lookback_recovery': 14,
    'recovery_threshold': 0.019131645464711824,
    'bb_entry_position': 0.557063105601927,
    'atr_entry_multiplier': 1.8515162945126216,
    'momentum_entry_threshold': -0.0053740915006914615,
    'use_ema_cross_entry': False,
    'check_higher_lows': False,
    'higher_lows_period': 4,
    'min_entry_signals': 2,
    'position_size': 0.9879331252253547,
    'hold_period_after_exit': 2,
}

# Load data
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

# Calcular buy & hold
first_price = df.iloc[0]['close']
last_price = df.iloc[-1]['close']
buyhold_return = ((last_price - first_price) / first_price) * 100

console.print(f"\n[bold cyan]BTC ADAPTIVE HOLD V2 - COM TRADING ATIVO (25+ TRADES)[/bold cyan]")
console.print(f"\nPeriodo: 2020-01-01 → 2025-11-24")
console.print(f"Preço inicial: ${first_price:,.2f}")
console.print(f"Preço final: ${last_price:,.2f}")
console.print(f"\n[yellow]Buy & Hold Puro: +{buyhold_return:.2f}%[/yellow]\n")

# Run backtest
backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
results = backtest_engine.run_backtest(
    strategy_cls=BTCAdaptiveHold,
    data_df=df,
    symbol='BTC-USD',
    **best_params
)

if results:
    return_pct = results.get('return_pct', 0)
    analyzers = results.get('analyzers', {})
    sharpe = analyzers.get('sharpe', 0) or 0
    max_dd = abs(analyzers.get('max_drawdown', 0))
    total_trades = analyzers.get('total_trades', 0)
    won = analyzers.get('won_trades', 0)
    lost = analyzers.get('lost_trades', 0)
    win_rate = analyzers.get('win_rate', 0)
    
    alpha = return_pct - buyhold_return
    
    # Tabela de comparação
    table = Table(title="\n📊 RESULTADO FINAL", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan", justify="left")
    table.add_column("Buy & Hold", justify="right", style="yellow")
    table.add_column("Adaptive Hold V2", justify="right", style="green")
    table.add_column("Diferença", justify="right", style="red")
    
    table.add_row(
        "Retorno Total",
        f"+{buyhold_return:.2f}%",
        f"+{return_pct:.2f}%",
        f"{alpha:+.2f}%"
    )
    
    table.add_row(
        "Capital Final",
        f"${100000 * (1 + buyhold_return/100):,.2f}",
        f"${100000 * (1 + return_pct/100):,.2f}",
        f"${100000 * (alpha/100):+,.2f}"
    )
    
    table.add_row(
        "Max Drawdown",
        f"{51.9:.1f}%",
        f"{max_dd:.1f}%",
        f"{max_dd - 51.9:+.1f}%"
    )
    
    table.add_row(
        "Sharpe Ratio",
        "~0.65",
        f"{sharpe:.3f}",
        f"{sharpe - 0.65:+.3f}"
    )
    
    table.add_row(
        "Total Trades",
        "1",
        f"{total_trades}",
        f"{total_trades - 1:+d}"
    )
    
    table.add_row(
        "Win Rate",
        "100%",
        f"{win_rate:.1f}%",
        f"{win_rate - 100:+.1f}%"
    )
    
    console.print(table)
    
    # Conclusão
    if alpha > 0:
        console.print(f"\n[bold green]✅ GANHOU DO BUY & HOLD POR {alpha:.2f}%![/bold green]")
        console.print(f"[green]Alpha: +{alpha:.2f}% ({alpha/buyhold_return*100:.1f}% melhor)[/green]")
    else:
        console.print(f"\n[bold red]❌ PERDEU PARA BUY & HOLD POR {abs(alpha):.2f}%[/bold red]")
        console.print(f"[red]Alpha: {alpha:.2f}% ({abs(alpha)/buyhold_return*100:.1f}% pior)[/red]")
    
    # Análise detalhada
    console.print("\n[bold]📊 ANÁLISE DETALHADA[/bold]")
    console.print(f"\n[yellow]Total de trades: {total_trades}[/yellow]")
    console.print(f"[green]→ Trading ATIVO! {total_trades} trades em 5 anos ({total_trades/5:.1f} trades/ano)[/green]")
    console.print(f"[green]→ Win rate: {win_rate:.1f}%[/green]")
    console.print(f"[green]→ Won: {won}, Lost: {lost}[/green]")
    
    console.print(f"\n[yellow]Drawdown: {max_dd:.1f}%[/yellow]")
    if max_dd < 52:
        console.print("[green]→ DD menor que buy & hold puro (51.9%)[/green]")
    elif max_dd < 60:
        console.print("[yellow]→ DD similar ao buy & hold[/yellow]")
    else:
        console.print("[red]→ DD maior que buy & hold puro[/red]")
    
    console.print(f"\n[yellow]Sharpe: {sharpe:.3f}[/yellow]")
    if sharpe > 0.7:
        console.print("[green]→ Risk-adjusted return bom[/green]")
    else:
        console.print("[yellow]→ Risk-adjusted return mediano[/yellow]")
    
    # Cálculo de eficiência
    if total_trades > 0:
        cost_estimate = total_trades * 0.2  # 0.2% por trade (ida+volta)
        console.print(f"\n[yellow]Custo estimado de trading: -{cost_estimate:.1f}%[/yellow]")
        console.print(f"[cyan]→ Retorno bruto estimado: +{return_pct + cost_estimate:.2f}%[/cyan]")
        
        if alpha > cost_estimate:
            console.print(f"[green]→ Alpha ({alpha:.1f}%) > Custos ({cost_estimate:.1f}%) = Estratégia eficiente![/green]")
        else:
            console.print(f"[red]→ Alpha ({alpha:.1f}%) < Custos ({cost_estimate:.1f}%) = Perdeu para custos de trading[/red]")
