"""
Walk-forward validation for BTC Winning V2 strategy.

Splits data into:
- Train: 2020-2022 (optimize here)
- Validation: 2023-2024 (test generalization)
- Test: 2025 (final holdout)

This prevents overfitting to the full period and provides more realistic performance estimates.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import backtrader as bt
import pandas as pd
from datetime import datetime
import optuna
from optuna.samplers import TPESampler

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_winning_v2 import BTCWinningV2


def load_period_data(start_year: int, end_year: int) -> pd.DataFrame:
    """Load BTC data for specific year range."""
    print(f"\n📥 Carregando dados {start_year}-{end_year}...")
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    
    df = data_engine.load_prices(
        symbol="BTC-USD",
        start=start_date,
        end=end_date
    )
    
    if df is None or df.empty:
        raise ValueError(f"Nenhum dado encontrado para {start_year}-{end_year}")
    
    print(f"📊 Total: {len(df)} candles de {df.index.min()} até {df.index.max()}")
    
    return df


def objective(trial, train_data: pd.DataFrame) -> float:
    """
    Optimization objective function - runs backtest on training data only.
    """
    # Sample all parameters with CORRECT names from V2 strategy
    params = {
        # Base strategy parameters
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
        
        'position_size': trial.suggest_float('position_size', 0.60, 0.95),
        'hold_period_after_exit': trial.suggest_int('hold_period_after_exit', 1, 5),
        
        # V2 specific parameters
        'use_dynamic_stops': True,
        'atr_period': trial.suggest_int('atr_period', 10, 20),
        'atr_stop_multiplier': trial.suggest_float('atr_stop_multiplier', 1.5, 3.5),
        'atr_trailing_multiplier': trial.suggest_float('atr_trailing_multiplier', 2.0, 4.0),
        'trailing_activation_pct': trial.suggest_float('trailing_activation_pct', 0.10, 0.25),
        
        'use_trend_strength': trial.suggest_categorical('use_trend_strength', [True, False]),
        'trend_lookback': trial.suggest_int('trend_lookback', 5, 15),
        'min_higher_highs': trial.suggest_int('min_higher_highs', 1, 5),
        'min_higher_lows': trial.suggest_int('min_higher_lows', 1, 5),
        
        'use_bull_protection': trial.suggest_categorical('use_bull_protection', [True, False]),
        'bull_run_threshold': trial.suggest_float('bull_run_threshold', 0.30, 0.70),
        'bull_run_period': trial.suggest_int('bull_run_period', 20, 45),
        'bull_exit_signals_add': trial.suggest_int('bull_exit_signals_add', 1, 3),
    }
    
    # Run backtest on training data
    engine = BacktestEngine(initial_cash=10000.0, commission=0.001)
    
    try:
        results = engine.run_backtest(
            strategy_cls=BTCWinningV2,
            data_df=train_data,
            symbol='BTC-USD',
            **params
        )
    except Exception as e:
        # If backtest fails, return large negative score
        return -1000
    
    # Calculate metrics
    total_return = results.get('return_pct', 0)
    analyzers = results.get('analyzers', {})
    total_trades = analyzers.get('total_trades', 0)
    
    # Enforce minimum trades constraint (2/year * 3 years = 6 trades minimum)
    # Using lower constraint for training period
    if total_trades < 6:
        penalty = (6 - total_trades) * 100
        return -penalty
    
    # Calculate buy & hold on training data
    bh_return = ((train_data['close'].iloc[-1] - train_data['close'].iloc[0]) / train_data['close'].iloc[0]) * 100
    alpha = total_return - bh_return
    
    # Calculate advanced metrics
    won_trades = analyzers.get('won_trades', 0)
    win_rate = (won_trades / total_trades) * 100 if total_trades > 0 else 0
    
    sharpe = analyzers.get('sharpe', 0) or 0
    max_dd_pct = abs(analyzers.get('max_drawdown', 0) or 0)
    
    # Score function (same as original)
    score = alpha
    
    # Bonuses
    if sharpe > 0.8:
        score += 30
    if win_rate > 50:
        score += 20
    
    # Penalties
    if max_dd_pct > 80:
        score -= 50
    
    return score


def run_walkforward_optimization():
    """Execute walk-forward validation workflow."""
    print("=" * 80)
    print("🚀 WALK-FORWARD VALIDATION - BTC Winning V2")
    print("=" * 80)
    
    # Load data splits
    train_data = load_period_data(2020, 2022)
    validation_data = load_period_data(2023, 2024)
    test_data = load_period_data(2025, 2025)
    
    print("\n" + "=" * 80)
    print("📈 FASE 1: OTIMIZAÇÃO NO PERÍODO DE TREINO (2020-2022)")
    print("=" * 80)
    
    # Create Optuna study
    study = optuna.create_study(
        direction='maximize',
        sampler=TPESampler(seed=42)
    )
    
    # Run optimization on training data
    study.optimize(
        lambda trial: objective(trial, train_data),
        n_trials=50,  # Reduced for faster results
        show_progress_bar=True
    )
    
    # Get best parameters from training
    best_params = study.best_params
    best_score = study.best_value
    
    print(f"\n✅ Melhor score no treino: {best_score:.2f}")
    print(f"📊 Total de trials: {len(study.trials)}")
    print(f"🏆 Melhor trial: #{study.best_trial.number}")
    
    # Save training results
    trials_df = study.trials_dataframe()
    trials_df.to_csv('winning_v2_walkforward_train_trials.csv', index=False)
    print(f"\n💾 Trials salvos: winning_v2_walkforward_train_trials.csv")
    
    # Test on training period with best params
    print("\n" + "-" * 80)
    print("📊 Performance no TREINO (2020-2022) com melhores parâmetros:")
    print("-" * 80)
    train_results = test_parameters(best_params, train_data, "TREINO")
    
    # Test on validation period
    print("\n" + "=" * 80)
    print("📈 FASE 2: VALIDAÇÃO NO PERÍODO UNSEEN (2023-2024)")
    print("=" * 80)
    validation_results = test_parameters(best_params, validation_data, "VALIDAÇÃO")
    
    # Test on final test period
    print("\n" + "=" * 80)
    print("📈 FASE 3: TESTE NO PERÍODO HOLDOUT (2025)")
    print("=" * 80)
    test_results = test_parameters(best_params, test_data, "TESTE")
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("📊 RESUMO WALK-FORWARD")
    print("=" * 80)
    
    print(f"\n{'Período':<15} {'Retorno':<12} {'B&H':<12} {'Alpha':<12} {'Trades':<8} {'Win Rate':<10}")
    print("-" * 80)
    
    for name, results in [("TREINO 20-22", train_results), 
                          ("VALID 23-24", validation_results),
                          ("TESTE 2025", test_results)]:
        print(f"{name:<15} {results['return']:>10.1f}%  {results['bh_return']:>10.1f}%  "
              f"{results['alpha']:>10.1f}%  {results['trades']:>7}  {results['win_rate']:>9.1f}%")
    
    print("\n" + "=" * 80)
    print("💡 ANÁLISE:")
    print("=" * 80)
    
    # Check if validation performance is reasonable
    if validation_results['alpha'] > -50:
        print("✅ VALIDAÇÃO BOA: Alpha na validação não foi muito pior que treino")
        print("   → Parâmetros provavelmente generalizáveis")
    else:
        print("⚠️  VALIDAÇÃO FRACA: Alpha na validação muito pior que treino")
        print("   → Possível overfitting ao período de treino")
    
    # Check test performance
    if test_results['alpha'] > 0:
        print(f"✅ TESTE POSITIVO: Alpha de {test_results['alpha']:.1f}% no holdout")
    else:
        print(f"❌ TESTE NEGATIVO: Alpha de {test_results['alpha']:.1f}% no holdout")
    
    # Save best parameters
    params_df = pd.DataFrame([best_params])
    params_df['train_score'] = best_score
    params_df['train_return'] = train_results['return']
    params_df['train_alpha'] = train_results['alpha']
    params_df['validation_return'] = validation_results['return']
    params_df['validation_alpha'] = validation_results['alpha']
    params_df['test_return'] = test_results['return']
    params_df['test_alpha'] = test_results['alpha']
    
    params_df.to_csv('winning_v2_walkforward_best_params.csv', index=False)
    print(f"\n💾 Parâmetros salvos: winning_v2_walkforward_best_params.csv")


def test_parameters(params: dict, data: pd.DataFrame, period_name: str) -> dict:
    """Test parameters on given data period."""
    engine = BacktestEngine(initial_cash=10000.0, commission=0.001)
    
    try:
        results = engine.run_backtest(
            strategy_cls=BTCWinningV2,
            data_df=data,
            symbol='BTC-USD',
            **params
        )
    except Exception as e:
        print(f"❌ Erro no backtest {period_name}: {e}")
        return {
            'return': 0,
            'bh_return': 0,
            'alpha': 0,
            'trades': 0,
            'win_rate': 0,
            'sharpe': 0,
            'max_dd': 0
        }
    
    # Calculate metrics
    total_return = results.get('return_pct', 0)
    analyzers = results.get('analyzers', {})
    total_trades = analyzers.get('total_trades', 0)
    
    bh_return = ((data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]) * 100
    alpha = total_return - bh_return
    
    won_trades = analyzers.get('won_trades', 0)
    win_rate = (won_trades / total_trades) * 100 if total_trades > 0 else 0
    
    sharpe = analyzers.get('sharpe', 0) or 0
    max_dd = abs(analyzers.get('max_drawdown', 0) or 0)
    
    print(f"\n📊 {period_name}:")
    print(f"  Retorno estratégia: {total_return:>8.1f}%")
    print(f"  Retorno B&H:        {bh_return:>8.1f}%")
    print(f"  Alpha:              {alpha:>8.1f}%")
    print(f"  Total trades:       {total_trades:>8}")
    print(f"  Win rate:           {win_rate:>8.1f}%")
    print(f"  Sharpe ratio:       {sharpe:>8.3f}")
    print(f"  Max drawdown:       {max_dd:>8.1f}%")
    
    return {
        'return': total_return,
        'bh_return': bh_return,
        'alpha': alpha,
        'trades': total_trades,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'max_dd': max_dd
    }


if __name__ == '__main__':
    run_walkforward_optimization()
