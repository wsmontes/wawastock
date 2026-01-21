"""
Análise detalhada por ano - BTC Winning V2 (Otimizada)

Compara V2 otimizada vs Buy & Hold ano a ano
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_winning_v2 import BTCWinningV2
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def run_year(year, start_date, end_date):
    """Rodar backtest para um ano específico"""
    
    # Load data
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    df = data_engine.load_prices(symbol='BTC-USD', start=start_date, end=end_date)
    
    # Buy & Hold
    first_price = df.iloc[0]['close']
    last_price = df.iloc[-1]['close']
    bh_return = ((last_price - first_price) / first_price) * 100
    
    # Strategy (usa parâmetros default que já estão otimizados)
    backtest = BacktestEngine(initial_cash=10000, commission=0.001)
    results = backtest.run_backtest(
        strategy_cls=BTCWinningV2,
        data_df=df,
        symbol='BTC-USD'
    )
    
    return_pct = results.get('return_pct', 0)
    analyzers = results.get('analyzers', {})
    
    total_trades = analyzers.get('total_trades', 0)
    won_trades = analyzers.get('won_trades', 0)
    max_dd = abs(analyzers.get('max_drawdown', 0))
    sharpe = analyzers.get('sharpe', 0) or 0
    
    alpha = return_pct - bh_return
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'year': year,
        'strategy_return': return_pct,
        'bh_return': bh_return,
        'alpha': alpha,
        'trades': total_trades,
        'won': won_trades,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'first_price': first_price,
        'last_price': last_price
    }


def main():
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   BTC WINNING V2 - ANÁLISE DETALHADA POR ANO[/bold cyan]")
    console.print("[bold cyan]   (Parâmetros Otimizados - Trial #49)[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")
    
    years = [
        (2020, '2020-01-01', '2020-12-31'),
        (2021, '2021-01-01', '2021-12-31'),
        (2022, '2022-01-01', '2022-12-31'),
        (2023, '2023-01-01', '2023-12-31'),
        (2024, '2024-01-01', '2024-12-31'),
        (2025, '2025-01-01', '2025-11-24'),
    ]
    
    results = []
    
    for year, start, end in years:
        console.print(f"[yellow]Processando {year}...[/yellow]")
        result = run_year(year, start, end)
        results.append(result)
    
    # ==========================================
    # TABELA DETALHADA
    # ==========================================
    
    console.print("\n[bold green]═══ RESULTADOS POR ANO ═══[/bold green]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Ano", style="cyan", width=6)
    table.add_column("Preço Inicial", justify="right", style="white")
    table.add_column("Preço Final", justify="right", style="white")
    table.add_column("B&H Return", justify="right", style="yellow")
    table.add_column("V2 Return", justify="right", style="green")
    table.add_column("Alpha", justify="right", style="bold")
    table.add_column("Trades", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Max DD", justify="right")
    
    total_trades = 0
    total_won = 0
    years_won = 0
    years_beat_bh = 0
    
    for r in results:
        alpha_color = "green" if r['alpha'] > 0 else "red"
        
        table.add_row(
            str(r['year']),
            f"${r['first_price']:,.0f}",
            f"${r['last_price']:,.0f}",
            f"{r['bh_return']:+.1f}%",
            f"{r['strategy_return']:+.1f}%",
            f"[{alpha_color}]{r['alpha']:+.1f}%[/{alpha_color}]",
            str(r['trades']),
            f"{r['win_rate']:.0f}%",
            f"{r['max_dd']:.1f}%"
        )
        
        total_trades += r['trades']
        total_won += r['won']
        
        if r['strategy_return'] > 0:
            years_won += 1
        
        if r['alpha'] > 0:
            years_beat_bh += 1
    
    console.print(table)
    
    # ==========================================
    # ESTATÍSTICAS AGREGADAS
    # ==========================================
    
    console.print("\n[bold cyan]═══ ESTATÍSTICAS GERAIS ═══[/bold cyan]\n")
    
    total_alpha = sum(r['alpha'] for r in results)
    avg_alpha = total_alpha / len(results)
    avg_trades_per_year = total_trades / len(results)
    overall_win_rate = (total_won / total_trades * 100) if total_trades > 0 else 0
    
    console.print(f"[bold]Total de Anos:[/bold] {len(results)}")
    console.print(f"[bold]Anos com Retorno Positivo:[/bold] {years_won}/{len(results)} ([green]{years_won/len(results)*100:.0f}%[/green])")
    console.print(f"[bold]Anos que Bateram B&H:[/bold] {years_beat_bh}/{len(results)} ([green]{years_beat_bh/len(results)*100:.0f}%[/green])")
    console.print()
    console.print(f"[bold]Total de Trades:[/bold] {total_trades}")
    console.print(f"[bold]Trades/Ano:[/bold] {avg_trades_per_year:.1f}")
    console.print(f"[bold]Win Rate Geral:[/bold] {overall_win_rate:.1f}%")
    console.print()
    console.print(f"[bold]Alpha Médio:[/bold] [green]+{avg_alpha:.1f}%[/green] por ano")
    console.print(f"[bold]Alpha Total:[/bold] [green]+{total_alpha:.1f}%[/green]")
    
    # ==========================================
    # ANÁLISE POR TIPO DE MERCADO
    # ==========================================
    
    console.print("\n[bold cyan]═══ ANÁLISE POR TIPO DE MERCADO ═══[/bold cyan]\n")
    
    bull_years = [r for r in results if r['bh_return'] > 50]
    bear_years = [r for r in results if r['bh_return'] < 0]
    sideways_years = [r for r in results if 0 <= r['bh_return'] <= 50]
    
    def print_market_stats(years, label):
        if not years:
            console.print(f"[yellow]{label}:[/yellow] Nenhum ano")
            return
        
        avg_alpha = sum(y['alpha'] for y in years) / len(years)
        alpha_color = "green" if avg_alpha > 0 else "red"
        years_list = ', '.join(str(y['year']) for y in years)
        
        console.print(f"[yellow]{label}:[/yellow] {years_list}")
        console.print(f"  Alpha médio: [{alpha_color}]{avg_alpha:+.1f}%[/{alpha_color}]")
        console.print()
    
    print_market_stats(bull_years, "Bull Markets (>50%)")
    print_market_stats(sideways_years, "Sideways (0-50%)")
    print_market_stats(bear_years, "Bear Markets (<0%)")
    
    # ==========================================
    # CONCLUSÃO
    # ==========================================
    
    console.print("[bold cyan]═══ CONCLUSÃO ═══[/bold cyan]\n")
    
    if years_beat_bh >= len(results) * 0.8:
        console.print("[bold green]✅ EXCELENTE:[/bold green] Estratégia bateu B&H em ≥80% dos anos")
    elif years_beat_bh >= len(results) * 0.6:
        console.print("[bold green]✅ BOM:[/bold green] Estratégia bateu B&H em ≥60% dos anos")
    elif years_beat_bh >= len(results) * 0.5:
        console.print("[bold yellow]⚠️ MODERADO:[/bold yellow] Estratégia bateu B&H em ~50% dos anos")
    else:
        console.print("[bold red]❌ FRACO:[/bold red] Estratégia bateu B&H em <50% dos anos")
    
    # Comparar com V1
    console.print("\n[bold]Comparação com V1 Original:[/bold]")
    console.print("  V1: Ganhou 3/6 anos (50%), alpha médio -12.4%")
    console.print(f"  V2: Ganhou {years_beat_bh}/6 anos ({years_beat_bh/6*100:.0f}%), alpha médio +{avg_alpha:.1f}%")
    
    improvement = years_beat_bh - 3
    if improvement > 0:
        console.print(f"  [bold green]✅ Melhoria: +{improvement} anos ganhando[/bold green]")
    
    console.print()


if __name__ == '__main__':
    main()
