"""
Análise anual da estratégia campeã - Como performou em cada ano?
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

console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold cyan]    ANÁLISE ANUAL - ESTRATÉGIA CAMPEÃ vs BUY & HOLD        [/bold cyan]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

years = [
    ('2020', '2020-01-01', '2020-12-31'),
    ('2021', '2021-01-01', '2021-12-31'),
    ('2022', '2022-01-01', '2022-12-31'),
    ('2023', '2023-01-01', '2023-12-31'),
    ('2024', '2024-01-01', '2024-12-31'),
    ('2025', '2025-01-01', '2025-11-24'),
]

data_engine = DataEngine(use_cache=True, auto_indicators=True)
backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)

results_per_year = []

for year_name, start_date, end_date in years:
    console.print(f"[cyan]Rodando {year_name}...[/cyan]")
    
    # Load data para o ano
    df_year = data_engine.load_prices(symbol='BTC-USD', start=start_date, end=end_date)
    
    if df_year is None or len(df_year) < 10:
        console.print(f"[red]Dados insuficientes para {year_name}[/red]\n")
        continue
    
    # Buy & Hold para o ano
    first_price = df_year.iloc[0]['close']
    last_price = df_year.iloc[-1]['close']
    buyhold_return = ((last_price - first_price) / first_price) * 100
    
    # Rodar estratégia
    results = backtest_engine.run_backtest(
        strategy_cls=BTCAdaptiveHold,
        data_df=df_year,
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
        
        results_per_year.append({
            'year': year_name,
            'strategy_return': return_pct,
            'buyhold_return': buyhold_return,
            'alpha': alpha,
            'sharpe': sharpe,
            'dd': max_dd,
            'trades': total_trades,
            'won': won,
            'lost': lost,
            'win_rate': win_rate,
            'first_price': first_price,
            'last_price': last_price,
        })
        
        console.print(f"  → Strategy: {return_pct:+.1f}% | B&H: {buyhold_return:+.1f}% | Alpha: {alpha:+.1f}%\n")

# Criar DataFrame
df_results = pd.DataFrame(results_per_year)

# Tabela de resultados anuais
console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold cyan]              RESULTADOS POR ANO                            [/bold cyan]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

table = Table(title="📊 PERFORMANCE ANUAL", show_header=True, header_style="bold magenta")
table.add_column("Ano", justify="center", style="cyan")
table.add_column("BTC Price", justify="right", style="white")
table.add_column("B&H", justify="right", style="yellow")
table.add_column("Strategy", justify="right", style="green")
table.add_column("Alpha", justify="right", style="blue")
table.add_column("Trades", justify="center", style="magenta")
table.add_column("Win%", justify="right", style="cyan")
table.add_column("DD", justify="right", style="red")

for _, row in df_results.iterrows():
    year = row['year']
    price_range = f"${row['first_price']:,.0f} → ${row['last_price']:,.0f}"
    bh = f"{row['buyhold_return']:+.1f}%"
    strat = f"{row['strategy_return']:+.1f}%"
    alpha = f"{row['alpha']:+.1f}%"
    trades = f"{int(row['trades'])}"
    win = f"{row['win_rate']:.0f}%"
    dd = f"{row['dd']:.1f}%"
    
    # Colorir alpha
    if row['alpha'] > 20:
        alpha_style = "bold green"
    elif row['alpha'] > 0:
        alpha_style = "green"
    elif row['alpha'] > -20:
        alpha_style = "yellow"
    else:
        alpha_style = "red"
    
    table.add_row(year, price_range, bh, strat, alpha, trades, win, dd, style=alpha_style if abs(row['alpha']) > 20 else None)

console.print(table)

# Estatísticas agregadas
console.print(f"\n[bold yellow]📈 ESTATÍSTICAS AGREGADAS (5 anos)[/bold yellow]\n")

total_years = len(df_results)
years_won = len(df_results[df_results['alpha'] > 0])
years_lost = len(df_results[df_results['alpha'] < 0])

console.print(f"[cyan]Anos analisados:[/cyan] {total_years}")
console.print(f"[green]Anos que ganhou do B&H:[/green] {years_won} ({years_won/total_years*100:.0f}%)")
console.print(f"[red]Anos que perdeu para B&H:[/red] {years_lost} ({years_lost/total_years*100:.0f}%)")

console.print(f"\n[cyan]Alpha médio por ano:[/cyan] {df_results['alpha'].mean():+.2f}%")
console.print(f"[cyan]Melhor alpha:[/cyan] {df_results['alpha'].max():+.2f}% ({df_results[df_results['alpha'] == df_results['alpha'].max()]['year'].values[0]})")
console.print(f"[cyan]Pior alpha:[/cyan] {df_results['alpha'].min():+.2f}% ({df_results[df_results['alpha'] == df_results['alpha'].min()]['year'].values[0]})")

console.print(f"\n[cyan]Total de trades:[/cyan] {df_results['trades'].sum():.0f}")
console.print(f"[cyan]Trades por ano (média):[/cyan] {df_results['trades'].mean():.1f}")
console.print(f"[cyan]Win rate médio:[/cyan] {df_results['win_rate'].mean():.1f}%")
console.print(f"[cyan]DD médio:[/cyan] {df_results['dd'].mean():.1f}%")
console.print(f"[cyan]Sharpe médio:[/cyan] {df_results['sharpe'].mean():.3f}")

# Análise por tipo de mercado
console.print(f"\n[bold yellow]📊 PERFORMANCE POR TIPO DE MERCADO[/bold yellow]\n")

bull_years = df_results[df_results['buyhold_return'] > 50]
bear_years = df_results[df_results['buyhold_return'] < 0]
sideways_years = df_results[(df_results['buyhold_return'] >= 0) & (df_results['buyhold_return'] <= 50)]

if len(bull_years) > 0:
    console.print(f"[green]BULL MARKETS ({len(bull_years)} anos):[/green]")
    console.print(f"  → Anos: {', '.join(bull_years['year'].values)}")
    console.print(f"  → B&H médio: {bull_years['buyhold_return'].mean():+.1f}%")
    console.print(f"  → Strategy médio: {bull_years['strategy_return'].mean():+.1f}%")
    console.print(f"  → Alpha médio: {bull_years['alpha'].mean():+.1f}%")

if len(bear_years) > 0:
    console.print(f"\n[red]BEAR MARKETS ({len(bear_years)} anos):[/red]")
    console.print(f"  → Anos: {', '.join(bear_years['year'].values)}")
    console.print(f"  → B&H médio: {bear_years['buyhold_return'].mean():+.1f}%")
    console.print(f"  → Strategy médio: {bear_years['strategy_return'].mean():+.1f}%")
    console.print(f"  → Alpha médio: {bear_years['alpha'].mean():+.1f}%")

if len(sideways_years) > 0:
    console.print(f"\n[yellow]SIDEWAYS MARKETS ({len(sideways_years)} anos):[/yellow]")
    console.print(f"  → Anos: {', '.join(sideways_years['year'].values)}")
    console.print(f"  → B&H médio: {sideways_years['buyhold_return'].mean():+.1f}%")
    console.print(f"  → Strategy médio: {sideways_years['strategy_return'].mean():+.1f}%")
    console.print(f"  → Alpha médio: {sideways_years['alpha'].mean():+.1f}%")

# Conclusões
console.print(f"\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold cyan]                    CONCLUSÕES                              [/bold cyan]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

if years_won >= total_years * 0.7:
    console.print("[green]✅ Estratégia consistente: Ganhou do B&H em 70%+ dos anos[/green]")
elif years_won >= total_years * 0.5:
    console.print("[yellow]⚠️  Estratégia moderada: Ganhou do B&H em ~50% dos anos[/yellow]")
else:
    console.print("[red]❌ Estratégia inconsistente: Ganhou do B&H em <50% dos anos[/red]")

best_market = None
if len(bull_years) > 0 and bull_years['alpha'].mean() > 50:
    best_market = "BULL"
elif len(bear_years) > 0 and bear_years['alpha'].mean() > 20:
    best_market = "BEAR"
elif len(sideways_years) > 0 and sideways_years['alpha'].mean() > 20:
    best_market = "SIDEWAYS"

if best_market:
    console.print(f"[cyan]📊 Melhor performance em mercados: {best_market}[/cyan]")

if df_results['trades'].sum() > 0:
    avg_alpha_per_trade = df_results['alpha'].sum() / df_results['trades'].sum()
    console.print(f"[cyan]💡 Alpha médio por trade: {avg_alpha_per_trade:+.2f}%[/cyan]")

console.print()
