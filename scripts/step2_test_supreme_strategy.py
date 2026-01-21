#!/usr/bin/env python3
"""
STEP 2: TESTE DA BTC SUPREME STRATEGY

Testa a estratégia multi-regime no período completo 2020-2025.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_supreme_strategy import BTCSupremeStrategy
from rich.console import Console

console = Console()

def main():
    console.print("\n" + "="*80)
    console.print("[bold cyan]STEP 2: TESTE BTC SUPREME STRATEGY (Multi-Regime Adaptive)[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Carregar dados
    console.print("📊 [bold]Carregando dados BTC 2020-2025...[/bold]")
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    
    data_df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-11-24'
    )
    
    console.print(f"✓ Carregados {len(data_df)} dias\n")
    
    # Calcular Buy & Hold
    initial_price = data_df['close'].iloc[0]
    final_price = data_df['close'].iloc[-1]
    buy_hold_return = ((final_price - initial_price) / initial_price) * 100
    
    console.print(f"💰 [bold]Buy & Hold Baseline:[/bold] [cyan]+{buy_hold_return:.2f}%[/cyan]\n")
    
    # Configurar e executar backtest
    console.print("🚀 [bold]Executando BTC Supreme Strategy...[/bold]\n")
    
    backtest_engine = BacktestEngine(
        initial_cash=100000,
        commission=0.001
    )
    
    results = backtest_engine.run_backtest(
        strategy_cls=BTCSupremeStrategy,
        data_df=data_df,
        symbol='BTC-USD'
    )
    
    console.print("\n" + "="*80)
    console.print("[bold green]RESULTADOS FINAIS[/bold green]")
    console.print("="*80 + "\n")
    
    strategy_return = results.get('return_pct', 0)
    outperformance = strategy_return - buy_hold_return
    
    console.print(f"📈 Buy & Hold:             [cyan]+{buy_hold_return:.2f}%[/cyan]")
    console.print(f"🎯 BTC Supreme Strategy:   [{'green' if strategy_return > 0 else 'red'}]{strategy_return:+.2f}%[/{'green' if strategy_return > 0 else 'red'}]")
    console.print(f"{'🏆' if outperformance > 0 else '⚠️'} Outperformance:         [{'green' if outperformance > 0 else 'red'}]{outperformance:+.2f}%[/{'green' if outperformance > 0 else 'red'}]\n")
    
    console.print(f"💼 Total de Trades:        {results.get('trades_total', 0)}")
    console.print(f"✅ Trades Vencedores:      {results.get('trades_won', 0)}")
    console.print(f"❌ Trades Perdedores:      {results.get('trades_lost', 0)}")
    console.print(f"📊 Win Rate:               {results.get('win_rate', 0):.2f}%")
    console.print(f"💵 Trade Médio:            ${results.get('avg_trade', 0):.2f}")
    console.print(f"📉 Max Drawdown:           {results.get('max_drawdown', 0):.2f}%")
    console.print(f"📊 Sharpe Ratio:           {results.get('sharpe', 0):.4f}")
    
    console.print("\n" + "="*80)
    
    if outperformance > 0:
        console.print(f"[bold green]✅ SUCESSO! Estratégia superou B&H em {outperformance:.2f}%[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️  Estratégia ficou {abs(outperformance):.2f}% atrás do B&H[/bold yellow]")
        console.print("[bold]Próximo passo: Otimizar parâmetros específicos para este período[/bold]")
    
    console.print("="*80 + "\n")

if __name__ == "__main__":
    main()
