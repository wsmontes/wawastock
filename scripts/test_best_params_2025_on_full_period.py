#!/usr/bin/env python3
"""
Testa os melhores parâmetros de 2025 no período completo 2020-2025.

Parâmetros ótimos do Trial 13 (2025):
- Total Return: +32.83% vs B&H -10.41%
- Sharpe: 1.55, Win Rate: 61.11%, Trades: 18
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from rich.console import Console

console = Console()

def main():
    console.print("\n" + "="*80)
    console.print("[bold cyan]TESTE: Parâmetros Ótimos 2025 aplicados em 2020-2025[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Parâmetros ótimos do Trial 13 (2025)
    best_params_2025 = {
        'rsi_period': 13,
        'rsi_oversold': 28,
        'rsi_overbought': 74,
        'bb_period': 18,
        'bb_dev': 2.13,
        'macd_fast': 11,
        'macd_slow': 24,
        'macd_signal': 8,
        'ema_fast': 18,
        'ema_slow': 47,
        'volume_threshold': 1.15,
        'atr_period': 12,
        'atr_multiplier': 1.89,
        'position_size': 0.95,
        'stop_loss_pct': 2.84,
        'trailing_stop_pct': 1.53,
        'take_profit_pct': 8.67,
        'min_signals_buy': 2,
        'min_signals_sell': 2
    }
    
    console.print("📊 [bold]Carregando dados BTC 2020-2025...[/bold]")
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    
    data_df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-11-24'
    )
    
    console.print(f"✓ Carregados {len(data_df)} dias")
    console.print(f"  Período: {data_df.index[0]} até {data_df.index[-1]}")
    
    # Calcular Buy & Hold
    initial_price = data_df['close'].iloc[0]
    final_price = data_df['close'].iloc[-1]
    buy_hold_return = ((final_price - initial_price) / initial_price) * 100
    
    console.print(f"\n💰 [bold]Buy & Hold Baseline:[/bold]")
    console.print(f"  Preço inicial: ${initial_price:,.2f}")
    console.print(f"  Preço final: ${final_price:,.2f}")
    console.print(f"  Retorno: [cyan]+{buy_hold_return:.2f}%[/cyan]\n")
    
    console.print("⚙️  [bold]Configurando backtest com parâmetros ótimos 2025...[/bold]")
    for key, value in best_params_2025.items():
        console.print(f"  {key}: {value}")
    
    console.print("\n🚀 [bold]Executando backtest...[/bold]\n")
    
    backtest_engine = BacktestEngine(
        initial_cash=100000,
        commission=0.001
    )
    
    results = backtest_engine.run_backtest(
        strategy_cls=BTCAdaptiveStrategy,
        data_df=data_df,
        symbol='BTC-USD',
        **best_params_2025
    )
    
    console.print("\n" + "="*80)
    console.print("[bold green]RESULTADOS[/bold green]")
    console.print("="*80 + "\n")
    
    strategy_return = results.get('return_pct', 0)
    outperformance = strategy_return - buy_hold_return
    
    console.print(f"📈 Buy & Hold:           [cyan]+{buy_hold_return:.2f}%[/cyan]")
    console.print(f"🎯 Estratégia Otimizada: [{'green' if strategy_return > 0 else 'red'}]{strategy_return:+.2f}%[/{'green' if strategy_return > 0 else 'red'}]")
    console.print(f"{'📊' if outperformance > 0 else '⚠️'} Outperformance:        [{'green' if outperformance > 0 else 'red'}]{outperformance:+.2f}%[/{'green' if outperformance > 0 else 'red'}]\n")
    
    console.print(f"💼 Total de Trades:      {results.get('trades_total', 0)}")
    console.print(f"✅ Win Rate:             {results.get('win_rate', 0):.2f}%")
    console.print(f"📉 Max Drawdown:         {results.get('max_drawdown', 0):.2f}%")
    console.print(f"📊 Sharpe Ratio:         {results.get('sharpe', 0):.4f}")
    
    console.print("\n" + "="*80)
    
    if outperformance > 0:
        console.print(f"[bold green]✅ SUCESSO! Estratégia superou B&H em {outperformance:.2f}%[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️  Estratégia não superou B&H (diferença: {outperformance:.2f}%)[/bold yellow]")
    
    console.print("="*80 + "\n")

if __name__ == "__main__":
    main()
