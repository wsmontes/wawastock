"""
Optuna para BTC Adaptive Hold - Encontrar parâmetros que superam Buy & Hold

OBJETIVO: Maximizar retorno ACIMA do buy & hold (+1,142%)

VARIÁVEIS OTIMIZADAS: 30+ parâmetros
- Exit signals: 8 indicadores com thresholds ajustáveis
- Entry signals: 10 indicadores com thresholds ajustáveis  
- Confirmações: min_exit_signals, min_entry_signals
- Períodos: lookbacks, EMAs, etc
"""

import sys
from pathlib import Path
import optuna
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_hold import BTCAdaptiveHold


def objective(trial):
    """
    Objetivo: Superar buy & hold (+1,142%)
    
    CONSTRAINT: Mínimo 5 trades por ano (5 anos = 25 trades)
    Penalizar: trades excessivos, DD muito alto
    Bonificar: retorno alto, Sharpe alto, trades moderados
    """
    
    # ==========================================
    # EXIT PARAMETERS
    # ==========================================
    params = {
        # RSI
        'rsi_period': trial.suggest_int('rsi_period', 10, 20),
        'rsi_exit_threshold': trial.suggest_int('rsi_exit_threshold', 15, 35),
        
        # MACD
        'macd_fast': trial.suggest_int('macd_fast', 8, 15),
        'macd_slow': trial.suggest_int('macd_slow', 20, 30),
        'macd_signal': trial.suggest_int('macd_signal', 7, 12),
        'macd_exit_threshold': trial.suggest_float('macd_exit_threshold', -100, -20),
        
        # Volume
        'volume_period': trial.suggest_int('volume_period', 10, 30),
        'volume_panic_multiplier': trial.suggest_float('volume_panic_multiplier', 1.5, 4.0),
        
        # Drawdown
        'lookback_dd': trial.suggest_int('lookback_dd', 10, 30),
        'drawdown_exit_threshold': trial.suggest_float('drawdown_exit_threshold', -35.0, -10.0),
        
        # Bollinger Bands
        'bb_period': trial.suggest_int('bb_period', 15, 30),
        'bb_std': trial.suggest_float('bb_std', 1.5, 3.0),
        'bb_exit_lower_mult': trial.suggest_float('bb_exit_lower_mult', 0.3, 1.0),
        
        # ATR
        'atr_period': trial.suggest_int('atr_period', 10, 20),
        'atr_exit_multiplier': trial.suggest_float('atr_exit_multiplier', 2.0, 4.0),
        
        # Momentum
        'momentum_period': trial.suggest_int('momentum_period', 5, 15),
        'momentum_exit_threshold': trial.suggest_float('momentum_exit_threshold', -0.25, -0.05),
        
        # EMA
        'ema_fast': trial.suggest_int('ema_fast', 10, 30),
        'ema_slow': trial.suggest_int('ema_slow', 40, 70),
        'use_ema_cross_exit': trial.suggest_categorical('use_ema_cross_exit', [True, False]),
        
        # Confirmação de saída
        'min_exit_signals': trial.suggest_int('min_exit_signals', 2, 6),
        
        # ==========================================
        # ENTRY PARAMETERS
        # ==========================================
        
        # RSI recovery
        'rsi_entry_threshold': trial.suggest_int('rsi_entry_threshold', 25, 45),
        
        # MACD
        'macd_entry_threshold': trial.suggest_float('macd_entry_threshold', -20, 20),
        'macd_entry_crossover': trial.suggest_categorical('macd_entry_crossover', [True, False]),
        
        # Volume
        'volume_entry_max': trial.suggest_float('volume_entry_max', 1.0, 2.5),
        
        # Recovery
        'lookback_recovery': trial.suggest_int('lookback_recovery', 5, 15),
        'recovery_threshold': trial.suggest_float('recovery_threshold', 0.0, 0.15),
        
        # Bollinger
        'bb_entry_position': trial.suggest_float('bb_entry_position', 0.2, 0.6),
        
        # ATR
        'atr_entry_multiplier': trial.suggest_float('atr_entry_multiplier', 1.0, 2.5),
        
        # Momentum
        'momentum_entry_threshold': trial.suggest_float('momentum_entry_threshold', -0.05, 0.05),
        
        # EMA
        'use_ema_cross_entry': trial.suggest_categorical('use_ema_cross_entry', [True, False]),
        
        # Higher lows
        'check_higher_lows': trial.suggest_categorical('check_higher_lows', [True, False]),
        'higher_lows_period': trial.suggest_int('higher_lows_period', 3, 10),
        
        # Confirmação de entrada
        'min_entry_signals': trial.suggest_int('min_entry_signals', 1, 5),
        
        # ==========================================
        # OUTROS
        # ==========================================
        'position_size': trial.suggest_float('position_size', 0.90, 0.99),
        'hold_period_after_exit': trial.suggest_int('hold_period_after_exit', 1, 7),
    }
    
    try:
        # Load data
        data_engine = DataEngine(use_cache=True, auto_indicators=True)
        df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
        
        if df is None or len(df) < 100:
            return -10000
        
        # Calcular buy & hold baseline
        buyhold_return = ((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']) * 100
        
        # Run backtest
        backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
        results = backtest_engine.run_backtest(
            strategy_cls=BTCAdaptiveHold,
            data_df=df,
            symbol='BTC-USD',
            **params
        )
        
        if results is None:
            return -10000
        
        # Extrair métricas
        return_pct = results.get('return_pct', 0)
        analyzers = results.get('analyzers', {})
        sharpe = analyzers.get('sharpe', 0) or 0
        max_dd = abs(analyzers.get('max_drawdown', 100))
        total_trades = analyzers.get('total_trades', 0)
        win_rate = analyzers.get('win_rate', 0)
        
        # ==========================================
        # VALIDAÇÃO - MÍNIMO 5 TRADES/ANO
        # ==========================================
        if total_trades == 0:
            return -10000
        
        # CONSTRAINT: Mínimo 25 trades em 5 anos (5 trades/ano)
        # Se fizer menos, retornar score negativo proporcional
        if total_trades < 25:
            penalty = (25 - total_trades) * 50  # 50 pontos por trade faltante
            print(f"Trial {trial.number}: REJECTED - Only {total_trades} trades (need 25+), penalty={penalty}")
            return -penalty
        
        # ==========================================
        # FUNÇÃO OBJETIVO
        # ==========================================
        
        # Base: Diferença vs buy & hold
        alpha = return_pct - buyhold_return
        score = alpha
        
        # BONUS: Superar buy & hold significativamente
        if alpha > 50:  # >50% acima do B&H
            score += 100
        elif alpha > 20:
            score += 50
        elif alpha > 0:
            score += 20
        
        # BONUS: Sharpe alto
        if sharpe > 0.9:
            score += 50
        elif sharpe > 0.8:
            score += 25
        
        # PENALTY: DD muito alto
        if max_dd > 60:
            score -= (max_dd - 60) * 5
        elif max_dd > 50:
            score -= (max_dd - 50) * 3
        
        # PENALTY: Overtrading (mas não muito severo)
        if total_trades > 100:
            score -= (total_trades - 100) * 3
        elif total_trades > 50:
            score -= (total_trades - 50) * 1
        
        # PENALTY: Retorno negativo (nunca deve acontecer)
        if return_pct < 0:
            score -= 500
        
        # PENALTY: Pior que buy & hold
        if return_pct < buyhold_return * 0.8:  # <80% do B&H
            score -= 200
        
        print(f"Trial {trial.number}: Return={return_pct:.1f}% (B&H={buyhold_return:.1f}%), "
              f"Alpha={alpha:+.1f}%, Sharpe={sharpe:.3f}, DD={max_dd:.1f}%, "
              f"Trades={total_trades}, WinRate={win_rate:.1f}%, Score={score:.1f}")
        
        return score
        
    except Exception as e:
        print(f"Trial {trial.number} ERROR: {e}")
        import traceback
        traceback.print_exc()
        return -10000


def main():
    n_trials = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    
    print("=" * 80)
    print("OPTUNA: BTC ADAPTIVE HOLD - BEAT BUY & HOLD V2")
    print("=" * 80)
    print(f"\n🎯 OBJETIVO: Superar buy & hold (+1,142%)")
    print(f"\n⚠️  CONSTRAINT: MÍNIMO 25 TRADES (5 trades/ano)")
    print(f"   → Força estratégia a fazer trading ativo")
    print(f"   → Elimina buy & hold disfarçado")
    print(f"\n📊 Otimizando 30+ parâmetros:")
    print(f"   • 8 exit signals com thresholds ajustáveis")
    print(f"   • 10 entry signals com thresholds ajustáveis")
    print(f"   • Confirmações múltiplas")
    print(f"   • Períodos variáveis")
    print(f"\n🔬 Rodando {n_trials} trials...\n")
    
    # Create study
    study = optuna.create_study(
        direction='maximize',
        study_name='btc_adaptive_hold',
        sampler=optuna.samplers.TPESampler(seed=42, n_startup_trials=20)
    )
    
    # Optimize
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    
    # Results
    print("\n" + "=" * 80)
    print("OTIMIZAÇÃO COMPLETA")
    print("=" * 80)
    
    best_trial = study.best_trial
    print(f"\n✨ Melhor Score: {best_trial.value:.2f}")
    
    # Save results
    output_dir = project_root / 'data' / 'processed'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    best_params_df = pd.DataFrame([best_trial.params])
    best_params_df['score'] = best_trial.value
    best_params_df['trial_number'] = best_trial.number
    best_params_file = output_dir / 'adaptive_hold_v2_best_params.csv'
    best_params_df.to_csv(best_params_file, index=False)
    
    trials_df = study.trials_dataframe()
    all_trials_file = output_dir / 'adaptive_hold_v2_all_trials.csv'
    trials_df.to_csv(all_trials_file, index=False)
    
    print(f"\n💾 Resultados salvos")
    print(f"   Best: {best_params_file}")
    print(f"   All: {all_trials_file}")
    
    print("\n" + "=" * 80)
    print("🏆 MELHORES PARÂMETROS ENCONTRADOS")
    print("=" * 80)
    for key, value in sorted(best_trial.params.items()):
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
