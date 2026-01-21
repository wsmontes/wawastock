"""
Optuna optimization for BTC Winning V2

Otimiza os parâmetros da V2 incluindo os novos:
- ATR stops (hard + trailing)
- Trend strength filters
- Bull run protection
- Position sizing

Constraint: Mínimo 25 trades (5 trades/ano)
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import optuna
from optuna.samplers import TPESampler
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_winning_v2 import BTCWinningV2

console = Console()

# Load data once
console.print("[yellow]Loading BTC data...[/yellow]")
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

# Buy & Hold benchmark
first_price = df.iloc[0]['close']
last_price = df.iloc[-1]['close']
buyhold_return = ((last_price - first_price) / first_price) * 100

console.print(f"[green]✓[/green] Loaded {len(df)} days")
console.print(f"Buy & Hold: [yellow]+{buyhold_return:.2f}%[/yellow]\n")


def objective(trial):
    """Optuna objective function"""
    
    # ==========================================
    # PARÂMETROS BASE (ranges da V1)
    # ==========================================
    params = {
        'rsi_period': trial.suggest_int('rsi_period', 10, 20),
        'rsi_exit_threshold': trial.suggest_int('rsi_exit_threshold', 20, 35),
        'rsi_entry_threshold': trial.suggest_int('rsi_entry_threshold', 30, 45),
        
        'macd_fast': trial.suggest_int('macd_fast', 10, 20),
        'macd_slow': trial.suggest_int('macd_slow', 25, 40),
        'macd_signal': trial.suggest_int('macd_signal', 5, 10),
        'macd_exit_threshold': trial.suggest_float('macd_exit_threshold', -100, -50),
        'macd_entry_threshold': trial.suggest_float('macd_entry_threshold', -30, 0),
        
        'volume_period': trial.suggest_int('volume_period', 8, 15),
        'volume_panic_multiplier': trial.suggest_float('volume_panic_multiplier', 2.0, 3.5),
        'volume_entry_max': trial.suggest_float('volume_entry_max', 1.0, 1.5),
        
        'bb_period': trial.suggest_int('bb_period', 20, 30),
        'bb_std': trial.suggest_float('bb_std', 1.8, 2.5),
        'bb_exit_lower_mult': trial.suggest_float('bb_exit_lower_mult', 0.7, 1.0),
        'bb_entry_position': trial.suggest_float('bb_entry_position', 0.4, 0.7),
        
        'momentum_period': trial.suggest_int('momentum_period', 10, 20),
        'momentum_exit_threshold': trial.suggest_float('momentum_exit_threshold', -0.20, -0.05),
        'momentum_entry_threshold': trial.suggest_float('momentum_entry_threshold', -0.01, 0.01),
        
        'min_exit_signals': trial.suggest_int('min_exit_signals', 2, 4),
        'min_entry_signals': trial.suggest_int('min_entry_signals', 2, 4),
        
        'hold_period_after_exit': trial.suggest_int('hold_period_after_exit', 1, 5),
        
        # ==========================================
        # NOVOS PARÂMETROS V2
        # ==========================================
        
        # ATR Dynamic Stops
        'atr_period': trial.suggest_int('atr_period', 10, 20),
        'atr_stop_multiplier': trial.suggest_float('atr_stop_multiplier', 1.5, 3.5),
        'atr_trailing_multiplier': trial.suggest_float('atr_trailing_multiplier', 2.0, 4.0),
        'trailing_activation_pct': trial.suggest_float('trailing_activation_pct', 0.10, 0.25),
        'use_dynamic_stops': True,
        
        # Trend Strength
        'use_trend_strength': trial.suggest_categorical('use_trend_strength', [True, False]),
        'trend_lookback': trial.suggest_int('trend_lookback', 5, 15),
        'min_higher_highs': trial.suggest_int('min_higher_highs', 1, 5),
        'min_higher_lows': trial.suggest_int('min_higher_lows', 1, 5),
        
        # Bull Run Protection
        'use_bull_protection': trial.suggest_categorical('use_bull_protection', [True, False]),
        'bull_run_threshold': trial.suggest_float('bull_run_threshold', 0.30, 0.70),
        'bull_run_period': trial.suggest_int('bull_run_period', 20, 45),
        'bull_exit_signals_add': trial.suggest_int('bull_exit_signals_add', 1, 3),
        
        # Position Sizing
        'position_size': trial.suggest_float('position_size', 0.70, 0.99),
        
        # Correlation filter desligado (não implementado)
        'use_correlation_filter': False,
    }
    
    # Run backtest
    try:
        backtest = BacktestEngine(initial_cash=10000, commission=0.001)
        results = backtest.run_backtest(
            strategy_cls=BTCWinningV2,
            data_df=df,
            symbol='BTC-USD',
            **params
        )
        
        return_pct = results.get('return_pct', 0)
        analyzers = results.get('analyzers', {})
        
        total_trades = analyzers.get('total_trades', 0)
        won_trades = analyzers.get('won_trades', 0)
        max_dd = abs(analyzers.get('max_drawdown', 0))
        sharpe = analyzers.get('sharpe', 0) or 0
        
        # ==========================================
        # CONSTRAINT: Minimum 25 trades
        # ==========================================
        MIN_TRADES = 25
        
        if total_trades < MIN_TRADES:
            # Rejeitar: penalidade proporcional
            penalty = (MIN_TRADES - total_trades) * 50
            return -penalty
        
        # ==========================================
        # SCORE FUNCTION
        # ==========================================
        
        # Alpha vs Buy & Hold
        alpha = return_pct - buyhold_return
        
        # Base score = alpha
        score = alpha
        
        # Bonuses
        if sharpe > 0.5:
            score += 50
        if sharpe > 0.8:
            score += 50
        
        win_rate = (won_trades / total_trades) if total_trades > 0 else 0
        if win_rate > 0.5:
            score += 30
        
        # Penalties
        if max_dd > 80:
            score -= 50
        if max_dd > 90:
            score -= 100
        
        # Trading efficiency (alpha per trade)
        if total_trades > 0:
            alpha_per_trade = alpha / total_trades
            if alpha_per_trade > 10:  # >10% alpha por trade
                score += 50
        
        return score
        
    except Exception as e:
        console.print(f"[red]Error in trial: {e}[/red]")
        return -10000


def main():
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   OPTUNA OPTIMIZATION - BTC WINNING V2[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")
    
    console.print("[yellow]Configuração:[/yellow]")
    console.print("  • Trials: 200")
    console.print("  • Constraint: ≥25 trades (5/ano)")
    console.print("  • Novos parâmetros V2: ATR stops, trend strength, bull protection")
    console.print("  • Sampler: TPE (Tree-structured Parzen Estimator)")
    console.print()
    
    # Create study
    study = optuna.create_study(
        direction='maximize',
        sampler=TPESampler(seed=42)
    )
    
    # Optimize
    console.print("[bold green]Starting optimization...[/bold green]\n")
    
    study.optimize(
        objective,
        n_trials=200,
        show_progress_bar=True
    )
    
    # ==========================================
    # RESULTS
    # ==========================================
    
    console.print("\n[bold green]═══ OPTIMIZATION COMPLETE ═══[/bold green]\n")
    
    best_trial = study.best_trial
    
    console.print(f"[bold]Best Trial: #{best_trial.number}[/bold]")
    console.print(f"Score: [green]{best_trial.value:.2f}[/green]\n")
    
    # Run best trial to get full metrics
    console.print("[yellow]Running best configuration...[/yellow]")
    
    backtest = BacktestEngine(initial_cash=10000, commission=0.001)
    results = backtest.run_backtest(
        strategy_cls=BTCWinningV2,
        data_df=df,
        symbol='BTC-USD',
        **best_trial.params
    )
    
    return_pct = results.get('return_pct', 0)
    analyzers = results.get('analyzers', {})
    
    total_trades = analyzers.get('total_trades', 0)
    won_trades = analyzers.get('won_trades', 0)
    max_dd = abs(analyzers.get('max_drawdown', 0))
    sharpe = analyzers.get('sharpe', 0) or 0
    
    alpha = return_pct - buyhold_return
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    console.print(f"\n[bold cyan]Performance:[/bold cyan]")
    console.print(f"  Return: [green]+{return_pct:.2f}%[/green]")
    console.print(f"  Buy & Hold: [yellow]+{buyhold_return:.2f}%[/yellow]")
    console.print(f"  Alpha: [green]+{alpha:.2f}%[/green]")
    console.print(f"  Trades: {total_trades}")
    console.print(f"  Win Rate: {win_rate:.1f}%")
    console.print(f"  Sharpe: {sharpe:.3f}")
    console.print(f"  Max DD: {max_dd:.2f}%")
    
    # ==========================================
    # SAVE RESULTS
    # ==========================================
    
    console.print("\n[yellow]Saving results...[/yellow]")
    
    # Save all trials
    trials_df = study.trials_dataframe()
    trials_df.to_csv('winning_v2_all_trials.csv', index=False)
    console.print(f"[green]✓[/green] All trials saved to winning_v2_all_trials.csv")
    
    # Save best params
    best_params_df = pd.DataFrame([best_trial.params])
    best_params_df['score'] = best_trial.value
    best_params_df['return_pct'] = return_pct
    best_params_df['alpha'] = alpha
    best_params_df['total_trades'] = total_trades
    best_params_df['win_rate'] = win_rate
    best_params_df['sharpe'] = sharpe
    best_params_df['max_dd'] = max_dd
    
    best_params_df.to_csv('winning_v2_best_params.csv', index=False)
    console.print(f"[green]✓[/green] Best params saved to winning_v2_best_params.csv")
    
    # Show top 5 params
    console.print("\n[bold cyan]Top 5 Important Parameters:[/bold cyan]")
    
    importance = optuna.importance.get_param_importances(study)
    for i, (param, imp) in enumerate(list(importance.items())[:5], 1):
        value = best_trial.params.get(param)
        console.print(f"  {i}. {param}: [yellow]{value}[/yellow] (importance: {imp:.3f})")
    
    console.print("\n[bold green]Done! 🎉[/bold green]\n")


if __name__ == '__main__':
    main()
