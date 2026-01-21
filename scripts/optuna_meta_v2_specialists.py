"""
Optuna Optimization for MetaStrategyV2 - PHASE 2: Specialist Behavior

FILOSOFIA:
- Trial 77 params são SAGRADOS - FIXOS
- Regime thresholds são OTIMIZADOS (Fase 1) - FIXOS agora
- Fase 2: Otimizar comportamento dos especialistas em regimes extremos

PARÂMETROS OTIMIZADOS (4):
1. bull_run_position_size: Tamanho da posição em STRONG_BULL_RUN
2. bull_run_trailing: Trailing stop % em STRONG_BULL_RUN (mais largo)
3. recovery_position_size: Tamanho da posição em RECOVERY
4. recovery_stop_loss: Stop loss % em RECOVERY
"""

import sys
from pathlib import Path
import optuna
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.meta_strategy_v2 import MetaStrategyV2

# Trial 77 params FIXOS (não otimizamos)
TRIAL77_PARAMS = {
    'rsi_period': 11,
    'rsi_oversold': 33,
    'rsi_overbought': 76,
    'bb_period': 19,
    'bb_dev': 2.35,
    'volume_period': 18,
    'volume_threshold': 1.15,
    'macd_fast': 11,
    'macd_slow': 25,
    'macd_signal': 8,
    'ema_fast': 8,
    'ema_slow': 19,
    'atr_period': 13,
    'atr_multiplier': 1.69,
    'take_profit_pct': 15.83,
    'trailing_stop_pct': 9.23,
    'position_size': 0.88,
    'min_signals_buy': 2,
    'min_signals_sell': 2,
}

# Regime thresholds OTIMIZADOS NA FASE 1 - FIXOS agora
REGIME_PARAMS = {
    'strong_bull_ret20': 14.539695475288168,
    'strong_bull_ret60': 37.81999665934651,
    'crash_threshold': -17.38819486836427,
    'recovery_ret20': 14.546212697785293,
}


def objective(trial):
    """Objetivo: Otimizar comportamento dos especialistas"""
    
    # FASE 2: Otimizar apenas parâmetros dos especialistas
    specialist_params = {
        'bull_run_position_size': trial.suggest_float('bull_run_position_size', 0.85, 1.0),
        'bull_run_trailing': trial.suggest_float('bull_run_trailing', 15.0, 30.0),
        'recovery_position_size': trial.suggest_float('recovery_position_size', 0.7, 0.95),
        'recovery_stop_loss': trial.suggest_float('recovery_stop_loss', 5.0, 12.0),
    }
    
    # Combinar todos os params
    strategy_params = {
        **TRIAL77_PARAMS,  # FIXOS
        **REGIME_PARAMS,  # FIXOS (otimizados Fase 1)
        **specialist_params,  # OTIMIZANDO
    }
    
    try:
        # Load data (mesmo método que funcionou)
        data_engine = DataEngine(use_cache=True, auto_indicators=True)
        df = data_engine.load_prices(
            symbol='BTC-USD',
            start='2020-01-01',
            end='2025-11-24'
        )
        
        if df is None or len(df) < 100:
            print(f"Trial {trial.number}: Dados insuficientes")
            return -1000
        
        # Run backtest (mesmo método que funcionou)
        backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
        
        results = backtest_engine.run_backtest(
            strategy_cls=MetaStrategyV2,
            data_df=df,
            symbol='BTC-USD',
            **strategy_params
        )
        
        if results is None:
            print(f"Trial {trial.number}: Backtest falhou")
            return -1000
        
        # Extrair métricas (estrutura correta)
        return_pct = results.get('return_pct', 0)
        analyzers = results.get('analyzers', {})
        sharpe = analyzers.get('sharpe', 0) or 0
        max_dd = abs(analyzers.get('max_drawdown', 100))
        total_trades = analyzers.get('total_trades', 0)
        
        # Validação básica
        if total_trades < 10:
            print(f"Trial {trial.number}: Poucos trades ({total_trades})")
            return -1000
        
        if return_pct <= 0:
            print(f"Trial {trial.number}: Retorno negativo ({return_pct:.2f}%)")
            return -1000
        
        # OBJETIVO: Maximizar retorno, penalizar DD alto
        # Baseline: Fase 1 = +638.44%, Sharpe=0.9889, DD=40.71%
        # Queremos > +638% com DD < 41%
        
        score = return_pct
        
        # Bonus por Sharpe alto
        if sharpe > 0.95:
            score += sharpe * 50
        
        # Penalidade por DD alto
        if max_dd > 42:
            dd_penalty = (max_dd - 42) * 5
            score -= dd_penalty
        
        # Penalidade por overtrading (> 150 trades)
        if total_trades > 150:
            score -= (total_trades - 150) * 0.5
        
        # Penalidade por undertrading (< 100 trades)
        if total_trades < 100:
            score -= (100 - total_trades) * 0.5
        
        print(f"Trial {trial.number}: Return={return_pct:.2f}%, Sharpe={sharpe:.4f}, "
              f"DD={max_dd:.2f}%, Trades={total_trades}, Score={score:.2f}")
        
        return score
        
    except Exception as e:
        print(f"Trial {trial.number} falhou: {e}")
        import traceback
        traceback.print_exc()
        return -1000


def main():
    """Run optimization"""
    import sys
    
    n_trials = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    
    print("=" * 80)
    print("OPTUNA OPTIMIZATION - MetaStrategy V2 - PHASE 2: SPECIALIST BEHAVIOR")
    print("=" * 80)
    print(f"\nTrial 77 params: FIXOS (não otimizados)")
    print(f"Regime thresholds: FIXOS (otimizados Fase 1)")
    print(f"  strong_bull_ret20: {REGIME_PARAMS['strong_bull_ret20']:.2f}%")
    print(f"  strong_bull_ret60: {REGIME_PARAMS['strong_bull_ret60']:.2f}%")
    print(f"  crash_threshold: {REGIME_PARAMS['crash_threshold']:.2f}%")
    print(f"  recovery_ret20: {REGIME_PARAMS['recovery_ret20']:.2f}%")
    print(f"\nOtimizando 4 parâmetros de comportamento dos especialistas:")
    print(f"  1. bull_run_position_size: [0.85, 1.0]")
    print(f"  2. bull_run_trailing: [15%, 30%]")
    print(f"  3. recovery_position_size: [0.7, 0.95]")
    print(f"  4. recovery_stop_loss: [5%, 12%]")
    print(f"\nBaseline: Fase 1 = +638.44%, Sharpe=0.9889, DD=40.71%")
    print(f"Objetivo: Maximizar retorno, minimizar DD")
    print(f"\nRodando {n_trials} trials...\n")
    
    # Create study
    study = optuna.create_study(
        direction='maximize',
        study_name='meta_v2_specialists',
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    
    # Optimize
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    
    # Results
    print("\n" + "=" * 80)
    print("OTIMIZAÇÃO COMPLETA")
    print("=" * 80)
    
    best_trial = study.best_trial
    print(f"\nMelhor Score: {best_trial.value:.2f}")
    print(f"\nMelhores Parâmetros de Especialistas:")
    for key, value in best_trial.params.items():
        print(f"  {key}: {value}")
    
    # Save results
    output_dir = project_root / 'data' / 'processed'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save best params
    best_params_df = pd.DataFrame([best_trial.params])
    best_params_df['score'] = best_trial.value
    best_params_df['trial_number'] = best_trial.number
    best_params_file = output_dir / 'meta_v2_specialists_best_params.csv'
    best_params_df.to_csv(best_params_file, index=False)
    print(f"\n✅ Melhores parâmetros salvos: {best_params_file}")
    
    # Save all trials
    trials_df = study.trials_dataframe()
    all_trials_file = output_dir / 'meta_v2_specialists_all_trials.csv'
    trials_df.to_csv(all_trials_file, index=False)
    print(f"✅ Todos os trials salvos: {all_trials_file}")
    
    # Test best params
    print("\n" + "=" * 80)
    print("TESTANDO MELHORES PARÂMETROS")
    print("=" * 80)
    
    best_specialist_params = best_trial.params
    strategy_params = {
        **TRIAL77_PARAMS,
        **REGIME_PARAMS,
        **best_specialist_params,
    }
    
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-11-24'
    )
    
    backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
    
    results = backtest_engine.run_backtest(
        strategy_cls=MetaStrategyV2,
        data_df=df,
        symbol='BTC-USD',
        **strategy_params
    )
    
    if results:
        print(f"\n✅ Teste Final:")
        print(f"  Retorno: {results['return_pct']:.2f}%")
        print(f"  Sharpe: {results['analyzers']['sharpe']:.4f}")
        print(f"  Max DD: {results['analyzers']['max_drawdown']:.2f}%")
        print(f"  Trades: {results['analyzers']['total_trades']}")
        print(f"  Win Rate: {results['analyzers']['won_trades'] / results['analyzers']['total_trades'] * 100:.2f}%")
        
        # Compare with Fase 1 baseline
        print(f"\n📊 Comparação com Fase 1 (regime otimizado):")
        print(f"  Retorno: {results['return_pct']:.2f}% vs 638.44% ({results['return_pct'] - 638.44:+.2f}%)")
        print(f"  Sharpe: {results['analyzers']['sharpe']:.4f} vs 0.9889 ({results['analyzers']['sharpe'] - 0.9889:+.4f})")
        print(f"  Max DD: {results['analyzers']['max_drawdown']:.2f}% vs 40.71% ({results['analyzers']['max_drawdown'] - 40.71:+.2f}%)")
        
        # Compare with original Trial 77
        print(f"\n📊 Comparação com Trial 77 original:")
        print(f"  Retorno: {results['return_pct']:.2f}% vs 420.42% ({results['return_pct'] - 420.42:+.2f}%)")
        print(f"  Sharpe: {results['analyzers']['sharpe']:.4f} vs 0.8038 ({results['analyzers']['sharpe'] - 0.8038:+.4f})")
        print(f"  Max DD: {results['analyzers']['max_drawdown']:.2f}% vs 51.72% ({results['analyzers']['max_drawdown'] - 51.72:+.2f}%)")
    
    print("\n" + "=" * 80)
    print("OTIMIZAÇÃO COMPLETA!")
    print("MetaStrategy V2 totalmente otimizado:")
    print("  - Trial 77: Parâmetros base (FIXOS)")
    print("  - Fase 1: Thresholds de regime otimizados")
    print("  - Fase 2: Comportamento dos especialistas otimizado")
    print("=" * 80)


if __name__ == '__main__':
    main()
