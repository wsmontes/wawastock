"""
Analisar os TOP 10 trials do Optuna - O que eles têm em comum?
"""

import sys
from pathlib import Path
import pandas as pd
from rich.console import Console
from rich.table import Table

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_hold import BTCAdaptiveHold

console = Console()

# Load trials data
trials_file = project_root / 'data' / 'processed' / 'adaptive_hold_all_trials.csv'
df_trials = pd.read_csv(trials_file)

# Sort by value (score) descending
df_trials = df_trials.sort_values('value', ascending=False)

# Top 10
top10 = df_trials.head(10)

console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold cyan]        TOP 10 TRIALS - ANÁLISE DO QUE FUNCIONA             [/bold cyan]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

# Tabela dos top 10
table = Table(title="🏆 TOP 10 MELHORES TRIALS", show_header=True, header_style="bold magenta")
table.add_column("Trial", justify="center", style="cyan")
table.add_column("Score", justify="right", style="green")
table.add_column("State", justify="center")

for idx, row in top10.iterrows():
    trial_num = int(row['number'])
    score = row['value']
    state = row['state']
    table.add_row(f"#{trial_num}", f"{score:.2f}", state)

console.print(table)

# Agora vamos rodar cada um para ver o que realmente aconteceu
console.print("\n[bold yellow]📊 DETALHAMENTO DOS TOP 10[/bold yellow]\n")

# Load data uma vez
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
first_price = df.iloc[0]['close']
last_price = df.iloc[-1]['close']
buyhold_return = ((last_price - first_price) / first_price) * 100

results_list = []

for idx, row in top10.iterrows():
    trial_num = int(row['number'])
    score = row['value']
    
    # Extrair parâmetros
    params = {}
    for col in df_trials.columns:
        if col.startswith('params_'):
            param_name = col.replace('params_', '')
            params[param_name] = row[col]
    
    console.print(f"[cyan]Running Trial #{trial_num} (Score: {score:.2f})[/cyan]")
    
    # Run backtest
    backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
    results = backtest_engine.run_backtest(
        strategy_cls=BTCAdaptiveHold,
        data_df=df,
        symbol='BTC-USD',
        **params
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
        
        results_list.append({
            'trial': trial_num,
            'score': score,
            'return': return_pct,
            'alpha': alpha,
            'sharpe': sharpe,
            'dd': max_dd,
            'trades': total_trades,
            'won': won,
            'lost': lost,
            'win_rate': win_rate,
            'min_exit_signals': params.get('min_exit_signals', 0),
            'min_entry_signals': params.get('min_entry_signals', 0),
            'rsi_exit': params.get('rsi_exit_threshold', 0),
            'macd_exit': params.get('macd_exit_threshold', 0),
            'dd_exit': params.get('drawdown_exit_threshold', 0),
            'position_size': params.get('position_size', 0),
        })
        
        console.print(f"  → Return: {return_pct:.1f}% | Alpha: {alpha:+.1f}% | Trades: {total_trades} | DD: {max_dd:.1f}% | Sharpe: {sharpe:.3f}\n")

# Criar DataFrame com resultados
df_results = pd.DataFrame(results_list)

# Análise comparativa
console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold cyan]              ANÁLISE COMPARATIVA TOP 10                    [/bold cyan]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

# Tabela de resultados
table2 = Table(title="📊 RESULTADOS DETALHADOS", show_header=True, header_style="bold magenta")
table2.add_column("Trial", justify="center", style="cyan")
table2.add_column("Return", justify="right", style="green")
table2.add_column("Alpha", justify="right", style="yellow")
table2.add_column("Trades", justify="center", style="blue")
table2.add_column("DD", justify="right", style="red")
table2.add_column("Sharpe", justify="right", style="magenta")
table2.add_column("Min Exit", justify="center", style="white")

for _, row in df_results.iterrows():
    table2.add_row(
        f"#{int(row['trial'])}",
        f"{row['return']:.1f}%",
        f"{row['alpha']:+.1f}%",
        f"{int(row['trades'])}",
        f"{row['dd']:.1f}%",
        f"{row['sharpe']:.3f}",
        f"{int(row['min_exit_signals'])}"
    )

console.print(table2)

# Estatísticas
console.print(f"\n[bold yellow]📈 ESTATÍSTICAS DOS TOP 10[/bold yellow]")
console.print(f"\nRetorno médio: {df_results['return'].mean():.2f}%")
console.print(f"Alpha médio: {df_results['alpha'].mean():.2f}%")
console.print(f"DD médio: {df_results['dd'].mean():.2f}%")
console.print(f"Sharpe médio: {df_results['sharpe'].mean():.3f}")
console.print(f"Trades médio: {df_results['trades'].mean():.1f}")

# Padrões identificados
console.print(f"\n[bold yellow]🔍 PADRÕES IDENTIFICADOS[/bold yellow]\n")

trades_1 = df_results[df_results['trades'] == 1]
trades_multi = df_results[df_results['trades'] > 1]

console.print(f"[cyan]Trials com 1 trade (buy & hold):[/cyan] {len(trades_1)}/10")
if len(trades_1) > 0:
    console.print(f"  → Alpha médio: {trades_1['alpha'].mean():+.2f}%")
    console.print(f"  → DD médio: {trades_1['dd'].mean():.2f}%")
    console.print(f"  → Min Exit Signals médio: {trades_1['min_exit_signals'].mean():.1f}")

console.print(f"\n[cyan]Trials com múltiplos trades:[/cyan] {len(trades_multi)}/10")
if len(trades_multi) > 0:
    console.print(f"  → Alpha médio: {trades_multi['alpha'].mean():+.2f}%")
    console.print(f"  → DD médio: {trades_multi['dd'].mean():.2f}%")
    console.print(f"  → Trades médio: {trades_multi['trades'].mean():.1f}")
    console.print(f"  → Win rate médio: {trades_multi['win_rate'].mean():.1f}%")

# Correlações
console.print(f"\n[bold yellow]🔗 CORRELAÇÕES[/bold yellow]\n")

correlations = {
    'Min Exit Signals vs Alpha': df_results[['min_exit_signals', 'alpha']].corr().iloc[0, 1],
    'Min Exit Signals vs Trades': df_results[['min_exit_signals', 'trades']].corr().iloc[0, 1],
    'Trades vs Alpha': df_results[['trades', 'alpha']].corr().iloc[0, 1],
    'DD vs Alpha': df_results[['dd', 'alpha']].corr().iloc[0, 1],
    'Position Size vs Alpha': df_results[['position_size', 'alpha']].corr().iloc[0, 1],
}

for name, corr in correlations.items():
    emoji = "🟢" if abs(corr) > 0.5 else "🟡" if abs(corr) > 0.3 else "⚪"
    console.print(f"{emoji} {name}: {corr:.3f}")

# Parâmetros comuns
console.print(f"\n[bold yellow]🎯 VALORES MAIS COMUNS NOS TOP 10[/bold yellow]\n")

common_params = {
    'Min Exit Signals': df_results['min_exit_signals'].mode().values[0] if len(df_results['min_exit_signals'].mode()) > 0 else 'N/A',
    'Min Entry Signals': df_results['min_entry_signals'].mode().values[0] if len(df_results['min_entry_signals'].mode()) > 0 else 'N/A',
    'RSI Exit (médio)': df_results['rsi_exit'].mean(),
    'MACD Exit (médio)': df_results['macd_exit'].mean(),
    'DD Exit (médio)': df_results['dd_exit'].mean(),
    'Position Size (médio)': df_results['position_size'].mean(),
}

for name, value in common_params.items():
    if isinstance(value, (int, float)):
        console.print(f"[cyan]{name}:[/cyan] {value:.2f}")
    else:
        console.print(f"[cyan]{name}:[/cyan] {value}")

# Conclusões
console.print(f"\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold cyan]                    CONCLUSÕES                              [/bold cyan]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

if len(trades_1) >= 7:  # Maioria com 1 trade
    console.print("[yellow]✓ Maioria dos top 10 fizeram apenas 1 trade (buy & hold)[/yellow]")
    console.print("[yellow]✓ Exit signals muito restritivos (min_exit_signals alto)[/yellow]")
    console.print("[yellow]✓ Alpha vem de timing de entrada, não de proteção[/yellow]")
    console.print("[yellow]✓ DD muito alto (>75%) - sem proteção contra crashes[/yellow]")
    
    console.print("\n[bold red]⚠️  PROBLEMA:[/bold red]")
    console.print("[red]→ Estratégia converge para buy & hold puro[/red]")
    console.print("[red]→ Não está realmente 'batendo' buy & hold com skill[/red]")
    console.print("[red]→ Apenas um timing de entrada ligeiramente diferente[/red]")
    
    console.print("\n[bold green]💡 SUGESTÕES:[/bold green]")
    console.print("[green]1. Adicionar CONSTRAINT: DD máximo de 60%[/green]")
    console.print("[green]2. Adicionar CONSTRAINT: Mínimo de 2-3 exits em crashes[/green]")
    console.print("[green]3. Mudar objetivo: Maximizar Sharpe ratio, não alpha absoluto[/green]")
    console.print("[green]4. Penalizar mais fortemente estratégias com DD > 60%[/green]")
else:
    console.print("[green]✓ Diversidade de estratégias nos top 10[/green]")
    console.print("[green]✓ Alguns fazem múltiplos trades com sucesso[/green]")
    console.print(f"[green]✓ Win rate razoável: {trades_multi['win_rate'].mean():.1f}%[/green]")

console.print()
