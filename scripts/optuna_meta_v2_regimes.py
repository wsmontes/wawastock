"""
Optuna Optimization for MetaStrategyV2 - PHASE 1: Regime Detection Thresholds

FILOSOFIA:
- Trial 77 params são SAGRADOS - não otimizamos
- Fase 1: Otimizar thresholds dos regimes (quando ativar especialistas)
- Fase 2: Depois otimizar comportamento dos especialistas

PARÂMETROS OTIMIZADOS (4):
1. strong_bull_ret20: Return 20d para detectar STRONG_BULL_RUN
2. strong_bull_ret60: Return 60d para detectar STRONG_BULL_RUN
3. crash_threshold: Return 20d para detectar CRASH
4. recovery_ret20: Return 20d para detectar RECOVERY
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

# Specialist params FIXOS (por enquanto, fase 2 otimiza)
SPECIALIST_PARAMS = {
    'bull_run_position_size': 0.95,
    'bull_run_trailing': 20.0,
    'recovery_position_size': 0.85,
    'recovery_stop_loss': 8.0,
}


def objective(trial):
    """Objetivo: Otimizar thresholds dos regimes"""
    
    # FASE 1: Otimizar apenas thresholds de detecção de regimes
    regime_params = {
        'strong_bull_ret20': trial.suggest_float('strong_bull_ret20', 10.0, 30.0),
        'strong_bull_ret60': trial.suggest_float('strong_bull_ret60', 30.0, 60.0),
        'crash_threshold': trial.suggest_float('crash_threshold', -30.0, -10.0),
        'recovery_ret20': trial.suggest_float('recovery_ret20', 10.0, 25.0),
    }
    
    # Combinar todos os params
    strategy_params = {
        **TRIAL77_PARAMS,  # FIXOS
        **SPECIALIST_PARAMS,  # FIXOS (por enquanto)
        **regime_params,  # OTIMIZANDO
    }
    
    try:
        # Load data (mesmo método que test_meta_v2.py que funcionou)
        data_engine = DataEngine(use_cache=True, auto_indicators=True)
        df = data_engine.load_prices(
            symbol='BTC-USD',
            start='2020-01-01',
            end='2025-11-24'
        )
        
        if df is None or len(df) < 100:
            print(f"Trial {trial.number}: Dados insuficientes")
            return -1000
        
        # Run backtest (mesmo método que test_meta_v2.py)
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
        # Baseline: Trial 77 = +420%, MetaV2 atual = +474%
        # Queremos > +474% com DD < 46%
        
        score = return_pct
        
        # Bonus por Sharpe alto
        if sharpe > 0.8:
            score += sharpe * 50
        
        # Penalidade por DD alto
        if max_dd > 50:
            dd_penalty = (max_dd - 50) * 5
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
    print("OPTUNA OPTIMIZATION - MetaStrategy V2 - PHASE 1: REGIME THRESHOLDS")
    print("=" * 80)
    print(f"\nTrial 77 params: FIXOS (não otimizados)")
    print(f"Specialist params: FIXOS (otimizados na Fase 2)")
    print(f"\nOtimizando 4 parâmetros de detecção de regimes:")
    print(f"  1. strong_bull_ret20: [10%, 30%]")
    print(f"  2. strong_bull_ret60: [30%, 60%]")
    print(f"  3. crash_threshold: [-30%, -10%]")
    print(f"  4. recovery_ret20: [10%, 25%]")
    print(f"\nBaseline: MetaV2 atual = +474.74%, Sharpe=0.8463, DD=45.92%")
    print(f"Objetivo: Maximizar retorno, minimizar DD")
    print(f"\nRodando {n_trials} trials...\n")
    
    # Create study
    study = optuna.create_study(
        direction='maximize',
        study_name='meta_v2_regimes',
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
    print(f"\nMelhores Parâmetros de Regime:")
    for key, value in best_trial.params.items():
        print(f"  {key}: {value}")
    
    # Save results
    output_dir = project_root / 'data' / 'processed'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save best params
    best_params_df = pd.DataFrame([best_trial.params])
    best_params_df['score'] = best_trial.value
    best_params_df['trial_number'] = best_trial.number
    best_params_file = output_dir / 'meta_v2_regimes_best_params.csv'
    best_params_df.to_csv(best_params_file, index=False)
    print(f"\n✅ Melhores parâmetros salvos: {best_params_file}")
    
    # Save all trials
    trials_df = study.trials_dataframe()
    all_trials_file = output_dir / 'meta_v2_regimes_all_trials.csv'
    trials_df.to_csv(all_trials_file, index=False)
    print(f"✅ Todos os trials salvos: {all_trials_file}")
    
    # Test best params
    print("\n" + "=" * 80)
    print("TESTANDO MELHORES PARÂMETROS")
    print("=" * 80)
    
    best_regime_params = best_trial.params
    strategy_params = {
        **TRIAL77_PARAMS,
        **SPECIALIST_PARAMS,
        **best_regime_params,
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
        
        # Compare with baseline
        print(f"\n📊 Comparação com MetaV2 atual:")
        print(f"  Retorno: {results['return_pct']:.2f}% vs 474.74% ({results['return_pct'] - 474.74:+.2f}%)")
        print(f"  Sharpe: {results['analyzers']['sharpe']:.4f} vs 0.8463 ({results['analyzers']['sharpe'] - 0.8463:+.4f})")
        print(f"  Max DD: {results['analyzers']['max_drawdown']:.2f}% vs 45.92% ({results['analyzers']['max_drawdown'] - 45.92:+.2f}%)")
    
    print("\n" + "=" * 80)
    print("PRÓXIMA FASE: Otimizar comportamento dos especialistas")
    print("  Execute: python scripts/optuna_meta_v2_specialists.py")
    print("=" * 80)


if __name__ == '__main__':
    main()
