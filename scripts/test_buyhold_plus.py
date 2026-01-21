"""
Teste: BTC Buy & Hold Plus vs Buy & Hold puro

Objetivo: Superar buy & hold evitando apenas crashes grandes
"""

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_buyhold_plus import BTCBuyHoldPlus
from rich.console import Console
from rich.table import Table

console = Console()

# Parâmetros ULTRA conservadores (quase nunca sai)
params = {
    'rsi_period': 14,
    'rsi_crash': 20,  # Muito oversold
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'volume_period': 20,
    'volume_crash_multiplier': 3.0,  # Volume 3x = pânico extremo
    'drawdown_threshold': -25.0,  # -25% em 20d = crash SEVERO
    'lookback_period': 20,
    'rsi_recovery': 30,
    'macd_recovery_threshold': 0,
    'position_size': 0.98,
}

console.print("[bold cyan]TESTE: Buy & Hold Plus - Beat Buy & Hold[/bold cyan]")
console.print()
console.print("[yellow]FILOSOFIA:[/yellow]")
console.print("  • Default: Buy & Hold (sempre posicionado)")
console.print("  • ÚNICA exceção: Sair em crashes iminentes")
console.print("  • Re-entrar rápido após crash")
console.print("  • Objetivo: Superar +1,233% do buy & hold puro")
console.print()

# Load data
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

if df is None or len(df) < 100:
    console.print("[red]❌ Erro ao carregar dados[/red]")
    exit(1)

# Calcular Buy & Hold puro
first_price = df.iloc[0]['close']
last_price = df.iloc[-1]['close']
buyhold_return = ((last_price - first_price) / first_price) * 100

console.print(f"[bold]📊 BUY & HOLD PURO:[/bold]")
console.print(f"  Primeira compra: ${first_price:,.2f}")
console.print(f"  Preço atual: ${last_price:,.2f}")
console.print(f"  Retorno: [green]+{buyhold_return:.2f}%[/green]")
console.print()

# Run backtest
backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)

console.print("="*80)
console.print("BUY & HOLD PLUS STRATEGY")
console.print("="*80)
console.print()

results = backtest_engine.run_backtest(
    strategy_cls=BTCBuyHoldPlus,
    data_df=df,
    symbol='BTC-USD',
    **params
)

if results:
    strat_return = results['return_pct']
    analyzers = results['analyzers']
    sharpe = analyzers.get('sharpe', 0) or 0
    max_dd = analyzers.get('max_drawdown', 0)
    total_trades = analyzers.get('total_trades', 0)
    won_trades = analyzers.get('won_trades', 0)
    lost_trades = analyzers.get('lost_trades', 0)
    
    console.print()
    console.print("="*80)
    console.print("📊 COMPARAÇÃO: BUY & HOLD PLUS vs BUY & HOLD PURO")
    console.print("="*80)
    
    # Criar tabela comparativa
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Buy & Hold Plus", justify="right", style="green")
    table.add_column("Buy & Hold Puro", justify="right", style="yellow")
    table.add_column("Diferença", justify="right")
    
    diff_return = strat_return - buyhold_return
    diff_style = "green" if diff_return > 0 else "red"
    
    table.add_row(
        "Retorno Total",
        f"+{strat_return:.2f}%",
        f"+{buyhold_return:.2f}%",
        f"[{diff_style}]{diff_return:+.2f}%[/{diff_style}]"
    )
    
    table.add_row(
        "Sharpe Ratio",
        f"{sharpe:.4f}",
        "N/A",
        "-"
    )
    
    table.add_row(
        "Max Drawdown",
        f"{max_dd:.2f}%",
        "~51.9% (2020)",
        f"[green]{max_dd - 51.9:+.2f}%[/green]" if max_dd < 51.9 else f"[red]{max_dd - 51.9:+.2f}%[/red]"
    )
    
    table.add_row(
        "Total Trades",
        f"{total_trades}",
        "1 (compra e segura)",
        f"+{total_trades - 1}"
    )
    
    if total_trades > 0:
        win_rate = (won_trades / total_trades) * 100
        table.add_row(
            "Win Rate",
            f"{win_rate:.2f}%",
            "N/A",
            "-"
        )
    
    console.print(table)
    console.print()
    
    # Veredito
    if strat_return > buyhold_return:
        margin = ((strat_return - buyhold_return) / buyhold_return) * 100
        console.print(f"[bold green]✅ BUY & HOLD PLUS VENCEU![/bold green]")
        console.print(f"   Superou buy & hold por {margin:.1f}%")
    elif abs(strat_return - buyhold_return) < 5:
        console.print(f"[bold yellow]⚖️  EMPATE TÉCNICO[/bold yellow]")
        console.print(f"   Diferença < 5%")
    else:
        console.print(f"[bold red]❌ BUY & HOLD PURO VENCEU[/bold red]")
        console.print(f"   Melhor segurar sem fazer nada...")
    
    console.print()
    console.print("="*80)
    console.print("💡 PRÓXIMOS PASSOS:")
    if strat_return <= buyhold_return:
        console.print("  • Ajustar thresholds de crash (mais sensível ou menos)")
        console.print("  • Testar diferentes períodos de lookback")
        console.print("  • Considerar outros indicadores de crash")
    else:
        console.print("  • Otimizar parâmetros com Optuna")
        console.print("  • Testar em outros períodos")
        console.print("  • Validar robustez da estratégia")
    console.print("="*80)
else:
    console.print("[red]❌ Backtest falhou[/red]")
