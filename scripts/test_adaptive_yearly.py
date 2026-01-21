"""
Teste da estratégia BTC Adaptive - Análise detalhada por ano

Compara BTCAdaptive (regime-based) vs Buy & Hold em cada ano
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive import BTCAdaptive
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def run_year(year, start_date, end_date):
    """Rodar backtest para um ano específico"""
    
    # Load data
    data_engine = DataEngine(use_cache=True, auto_indicators=False)
    df = data_engine.load_prices(symbol='BTC-USD', start=start_date, end=end_date)
    
    if df is None or df.empty or len(df) < 250:
        return None
    
    # Buy & Hold
    first_price = df.iloc[0]['close']
    last_price = df.iloc[-1]['close']
    bh_return = ((last_price - first_price) / first_price) * 100
    
    # Strategy
    backtest = BacktestEngine(initial_cash=10000, commission=0.001)
    results = backtest.run_backtest(
        strategy_cls=BTCAdaptive,
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
        'start': start_date,
        'end': end_date,
        'strategy_return': return_pct,
        'bh_return': bh_return,
        'alpha': alpha,
        'total_trades': total_trades,
        'won_trades': won_trades,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'sharpe': sharpe,
        'beats_bh': alpha > 0
    }


def main():
    console.print("\n" + "="*80)
    console.print("🧪 TESTE: BTC ADAPTIVE STRATEGY - ANÁLISE POR ANO")
    console.print("="*80 + "\n")
    
    # Anos para testar
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
        console.print(f"[yellow]📅 Testando {year}...[/yellow]")
        result = run_year(year, start, end)
        if result:
            results.append(result)
            console.print(f"[green]✓[/green] Completo\n")
        else:
            console.print(f"[red]✗[/red] Dados insuficientes\n")
    
    # Tabela de resultados
    console.print("="*80)
    console.print("📊 RESULTADOS POR ANO")
    console.print("="*80 + "\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Ano", style="bold")
    table.add_column("Estratégia", justify="right")
    table.add_column("Buy & Hold", justify="right")
    table.add_column("Alpha", justify="right", style="bold")
    table.add_column("Trades", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("Venceu?", justify="center")
    
    total_alpha = 0
    years_won = 0
    total_trades = 0
    total_won = 0
    
    for r in results:
        alpha_color = "green" if r['alpha'] > 0 else "red"
        beats_icon = "✅" if r['beats_bh'] else "❌"
        
        table.add_row(
            str(r['year']),
            f"{r['strategy_return']:+.1f}%",
            f"{r['bh_return']:+.1f}%",
            f"[{alpha_color}]{r['alpha']:+.1f}%[/{alpha_color}]",
            str(r['total_trades']),
            f"{r['win_rate']:.1f}%",
            f"{r['max_dd']:.1f}%",
            f"{r['sharpe']:.2f}",
            beats_icon
        )
        
        total_alpha += r['alpha']
        if r['beats_bh']:
            years_won += 1
        total_trades += r['total_trades']
        total_won += r['won_trades']
    
    console.print(table)
    
    # Estatísticas agregadas
    console.print("\n" + "="*80)
    console.print("📈 ESTATÍSTICAS AGREGADAS")
    console.print("="*80 + "\n")
    
    total_years = len(results)
    yearly_win_rate = (years_won / total_years) * 100
    avg_alpha = total_alpha / total_years
    overall_win_rate = (total_won / total_trades * 100) if total_trades > 0 else 0
    avg_trades_per_year = total_trades / total_years
    
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Metric", style="bold cyan")
    stats_table.add_column("Value", style="bold white")
    
    stats_table.add_row("Anos analisados", f"{total_years}")
    stats_table.add_row("Anos bateu B&H", f"{years_won} ({yearly_win_rate:.0f}%)")
    stats_table.add_row("Alpha médio/ano", f"{avg_alpha:+.1f}%")
    stats_table.add_row("Total de trades", f"{total_trades}")
    stats_table.add_row("Trades/ano", f"{avg_trades_per_year:.1f}")
    stats_table.add_row("Win rate geral", f"{overall_win_rate:.1f}%")
    
    console.print(stats_table)
    
    # Avaliação
    console.print("\n" + "="*80)
    console.print("🎯 AVALIAÇÃO")
    console.print("="*80 + "\n")
    
    # Critérios de sucesso
    target_yearly_win = 60  # Meta: >60% dos anos
    target_avg_alpha = 0    # Meta: alpha médio > 0%
    
    criteria_met = []
    criteria_failed = []
    
    if yearly_win_rate >= target_yearly_win:
        criteria_met.append(f"✅ Yearly win rate: {yearly_win_rate:.0f}% (meta: ≥{target_yearly_win}%)")
    else:
        criteria_failed.append(f"❌ Yearly win rate: {yearly_win_rate:.0f}% (meta: ≥{target_yearly_win}%)")
    
    if avg_alpha > target_avg_alpha:
        criteria_met.append(f"✅ Alpha médio: {avg_alpha:+.1f}% (meta: >0%)")
    else:
        criteria_failed.append(f"❌ Alpha médio: {avg_alpha:+.1f}% (meta: >0%)")
    
    if total_trades >= total_years * 3:
        criteria_met.append(f"✅ Atividade: {avg_trades_per_year:.1f} trades/ano (mínimo: 3)")
    else:
        criteria_failed.append(f"❌ Atividade: {avg_trades_per_year:.1f} trades/ano (mínimo: 3)")
    
    # Display results
    if criteria_met:
        console.print("[bold green]CRITÉRIOS ATENDIDOS:[/bold green]")
        for criterion in criteria_met:
            console.print(f"  {criterion}")
        console.print()
    
    if criteria_failed:
        console.print("[bold red]CRITÉRIOS NÃO ATENDIDOS:[/bold red]")
        for criterion in criteria_failed:
            console.print(f"  {criterion}")
        console.print()
    
    # Final verdict
    if len(criteria_failed) == 0:
        console.print(Panel.fit(
            "[bold green]✅ SUCESSO![/bold green]\n\n"
            "A estratégia BTC Adaptive atingiu os objetivos:\n"
            f"- Bateu Buy & Hold em {yearly_win_rate:.0f}% dos anos\n"
            f"- Alpha médio positivo de {avg_alpha:+.1f}% por ano\n"
            f"- Manteve atividade razoável com {avg_trades_per_year:.1f} trades/ano",
            title="🎉 VALIDAÇÃO COMPLETA",
            border_style="bold green"
        ))
    elif yearly_win_rate >= 50:
        console.print(Panel.fit(
            "[bold yellow]⚠️  PARCIAL[/bold yellow]\n\n"
            "A estratégia tem potencial mas precisa melhorias:\n"
            f"- Bateu B&H em {yearly_win_rate:.0f}% dos anos (razoável)\n"
            f"- Alpha médio de {avg_alpha:+.1f}%\n\n"
            "Sugestões:\n"
            "- Refinar thresholds de regime detection\n"
            "- Ajustar position sizing por regime\n"
            "- Otimizar take profit / stop loss",
            title="📊 VALIDAÇÃO PARCIAL",
            border_style="bold yellow"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]❌ INSUFICIENTE[/bold red]\n\n"
            f"A estratégia não atingiu objetivos mínimos:\n"
            f"- Bateu B&H em apenas {yearly_win_rate:.0f}% dos anos\n"
            f"- Alpha médio de {avg_alpha:+.1f}%\n\n"
            "Necessário:\n"
            "- Revisar lógica de regime detection\n"
            "- Recalibrar parâmetros de entry/exit\n"
            "- Considerar abordagem alternativa",
            title="🔴 VALIDAÇÃO FALHOU",
            border_style="bold red"
        ))
    
    console.print()


if __name__ == '__main__':
    main()
