#!/usr/bin/env python3
"""
Testa o Trial 77 que obteve +829.57% (melhor resultado observado).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from rich.console import Console

console = Console()

def main():
    console.print("\n" + "="*80)
    console.print("[bold cyan]TESTE: TRIAL 77 - MELHOR RESULTADO (+829.57%)[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Parâmetros do Trial 77
    trial_77_params = {
        'rsi_period': 18,
        'rsi_oversold': 28,
        'rsi_overbought': 70,
        'bb_period': 20,
        'bb_dev': 1.95,
        'macd_fast': 10,
        'macd_slow': 30,
        'macd_signal': 12,
        'ema_fast': 15,
        'ema_slow': 50,
        'volume_threshold': 1.39,
        'atr_period': 17,
        'atr_multiplier': 1.73,
        'position_size': 0.88,
        'stop_loss_pct': 6.35,
        'trailing_stop_pct': 4.32,
        'take_profit_pct': 13.22,
        'min_signals_buy': 2,
        'min_signals_sell': 3
    }
    
    console.print("📊 [bold]Carregando dados BTC 2020-2025...[/bold]")
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    
    data_df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-11-24'
    )
    
    console.print(f"✓ {len(data_df)} dias carregados\n")
    
    # Calcular Buy & Hold
    initial_price = data_df['close'].iloc[0]
    final_price = data_df['close'].iloc[-1]
    buy_hold_return = ((final_price - initial_price) / initial_price) * 100
    
    console.print(f"💰 [bold]Buy & Hold:[/bold] [cyan]+{buy_hold_return:.2f}%[/cyan]\n")
    
    console.print("⚙️  [bold]Parâmetros Trial 77:[/bold]")
    for key, value in trial_77_params.items():
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
        **trial_77_params
    )
    
    console.print("\n" + "="*80)
    console.print("[bold green]RESULTADO FINAL[/bold green]")
    console.print("="*80 + "\n")
    
    strategy_return = results.get('return_pct', 0)
    outperformance = strategy_return - buy_hold_return
    
    console.print(f"📈 Buy & Hold:           [cyan]+{buy_hold_return:.2f}%[/cyan]")
    console.print(f"🎯 Trial 77 Strategy:    [{'green' if strategy_return > 0 else 'red'}]{strategy_return:+.2f}%[/{'green' if strategy_return > 0 else 'red'}]")
    console.print(f"{'🏆' if outperformance > 0 else '⚠️'} Outperformance:        [{'green' if outperformance > 0 else 'red'}]{outperformance:+.2f}%[/{'green' if outperformance > 0 else 'red'}]\n")
    
    console.print(f"💼 Total de Trades:      {results.get('trades_total', 0)}")
    console.print(f"✅ Win Rate:             {results.get('win_rate', 0):.2f}%")
    console.print(f"📉 Max Drawdown:         {results.get('max_drawdown', 0):.2f}%")
    console.print(f"📊 Sharpe Ratio:         {results.get('sharpe', 0):.4f}")
    
    console.print("\n" + "="*80)
    
    if outperformance > 0:
        console.print(f"[bold green]✅ SUCESSO! Estratégia superou B&H em {outperformance:.2f}%![/bold green]")
    else:
        console.print(f"[bold yellow]⚠️  Ficou {abs(outperformance):.2f}% atrás do B&H[/bold yellow]")
    
    console.print("="*80 + "\n")

if __name__ == "__main__":
    main()
