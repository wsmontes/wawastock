"""
Optuna Multi-Level Optimization for MetaStrategy

Otimiza TODOS os níveis da arquitetura:
1. Parâmetros do RegimeDetector (thresholds de classificação)
2. Parâmetros dos Especialistas (position sizing, stops)
3. Parâmetros do Trial77 (fallback)

ESTRATÉGIA:
- Otimizar de forma hierárquica
- RegimeDetector é crítico (afeta tudo)
- Especialistas devem ser coordenados
- Trial77 já está otimizado, ajustar pouco
"""

import optuna
from optuna.samplers import TPESampler
from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.meta_strategy import MetaStrategy
import warnings
warnings.filterwarnings('ignore')


def objective(trial):
    """
    Função objetivo para otimização multi-nível.
    
    Otimiza:
    - RegimeDetector thresholds
    - Especialistas parameters
    - Trial77 fallback parameters
    """
    
    # === NÍVEL 1: REGIME DETECTOR ===
    # Thresholds para classificação (CRÍTICO)
    
    regime_params = {
        # Bull run detection
        'strong_bull_ret20': trial.suggest_float('strong_bull_ret20', 10.0, 25.0),
        'strong_bull_ret60': trial.suggest_float('strong_bull_ret60', 20.0, 50.0),
        
        # Bull correction
        'bull_correction_ret60': trial.suggest_float('bull_correction_ret60', 10.0, 30.0),
        'bull_correction_ret20_max': trial.suggest_float('bull_correction_ret20_max', 0.0, 10.0),
        
        # Steady bull
        'steady_bull_ret20': trial.suggest_float('steady_bull_ret20', 3.0, 10.0),
        'steady_bull_ret60': trial.suggest_float('steady_bull_ret60', 5.0, 20.0),
        
        # Recovery
        'recovery_ret20': trial.suggest_float('recovery_ret20', 5.0, 15.0),
        
        # Sideways
        'sideways_threshold': trial.suggest_float('sideways_threshold', 5.0, 15.0),
        'sideways_vol_threshold': trial.suggest_float('sideways_vol_threshold', 2.5, 6.0),
        
        # Crash
        'crash_threshold': trial.suggest_float('crash_threshold', -20.0, -10.0),
        
        # Bear market
        'bear_ret20': trial.suggest_float('bear_ret20', -10.0, -3.0),
        'bear_ret60': trial.suggest_float('bear_ret60', -20.0, -5.0),
    }
    
    # === NÍVEL 2: ESPECIALISTAS ===
    
    # BullRunRider
    bull_run_params = {
        'bull_run_position_size': trial.suggest_float('bull_run_position_size', 0.85, 0.99),
        'bull_run_trailing': trial.suggest_float('bull_run_trailing', 15.0, 30.0),
        'bull_run_profit_threshold': trial.suggest_float('bull_run_profit_threshold', 15.0, 35.0),
    }
    
    # RecoveryHunter
    recovery_params = {
        'recovery_position_size': trial.suggest_float('recovery_position_size', 0.70, 0.95),
        'recovery_stop_loss': trial.suggest_float('recovery_stop_loss', 7.0, 15.0),
        'recovery_take_profit': trial.suggest_float('recovery_take_profit', 10.0, 25.0),
    }
    
    # CrashAvoider (não tem parâmetros - só sai)
    
    # === NÍVEL 3: TRIAL77 FALLBACK ===
    # Usar parâmetros já otimizados, mas permitir pequenos ajustes
    
    trial77_params = {
        'rsi_period': 11,  # Fixo
        'rsi_oversold': trial.suggest_int('rsi_oversold', 28, 38),
        'rsi_overbought': trial.suggest_int('rsi_overbought', 70, 80),
        'bb_period': 19,  # Fixo
        'bb_dev': trial.suggest_float('bb_dev', 2.0, 2.7),
        'volume_period': 18,  # Fixo
        'volume_threshold': trial.suggest_float('volume_threshold', 1.1, 1.3),
        'macd_fast': 11,  # Fixo
        'macd_slow': 25,  # Fixo
        'macd_signal': 8,  # Fixo
        'ema_fast': 8,  # Fixo
        'ema_slow': 19,  # Fixo
        'atr_period': 13,  # Fixo
        'atr_multiplier': trial.suggest_float('atr_multiplier', 1.3, 2.0),
        'take_profit_pct': trial.suggest_float('take_profit_pct', 12.0, 20.0),
        'trailing_stop_pct': trial.suggest_float('trailing_stop_pct', 7.0, 12.0),
        'position_size': trial.suggest_float('position_size', 0.80, 0.92),
        'min_signals_buy': trial.suggest_int('min_signals_buy', 1, 3),
        'min_signals_sell': trial.suggest_int('min_signals_sell', 1, 3),
    }
    
    # Combinar todos os parâmetros
    all_params = {**regime_params, **bull_run_params, **recovery_params, **trial77_params}
    
    # Executar backtest
    try:
        data_engine = DataEngine(use_cache=True, auto_indicators=True)
        df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
        
        backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
        
        # Passar TODOS os parâmetros incluindo regime_params
        results = backtest_engine.run_backtest(
            strategy_cls=MetaStrategy,
            data_df=df,
            symbol='BTC-USD',
            **all_params  # Usar all_params ao invés de passar separado
        )
        
        # Extrair métricas com valores padrão seguros
        analyzers = results.get('analyzers', {})
        return_pct = results.get('return_pct', 0)
        total_trades = analyzers.get('total_trades', 0)
        
        # OBJETIVO PRINCIPAL: MAXIMIZAR RETORNO TOTAL
        score = return_pct * 2  # Peso 2x no retorno
        
        # PENALIZAR PERDAS CONSECUTIVAS (critical)
        # Analisar trades da estratégia para detectar streaks de perdas
        strategy = results.get('strategy')
        if strategy and hasattr(strategy, 'trade_log') and len(strategy.trade_log) > 0:
            consecutive_losses = 0
            max_consecutive_losses = 0
            
            for trade in strategy.trade_log:
                if trade.get('pnl', 0) < 0:
                    consecutive_losses += 1
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                else:
                    consecutive_losses = 0
            
            # Penalidade severa para perdas consecutivas
            if max_consecutive_losses >= 5:
                score -= (max_consecutive_losses - 4) * 50  # -50 pontos por perda acima de 4
            elif max_consecutive_losses >= 3:
                score -= (max_consecutive_losses - 2) * 20  # -20 pontos por perda acima de 2
        
        # Penalizar undertrading severo (menos que 20 trades em 5 anos)
        if total_trades < 20:
            score -= (20 - total_trades) * 10
        
        # Penalizar overtrading extremo
        if total_trades > 200:
            score -= (total_trades - 200) * 2
        
        # Bônus para win rate alto
        won_trades = analyzers.get('won_trades', 0)
        if total_trades > 0:
            win_rate = won_trades / total_trades
            if win_rate > 0.6:
                score += (win_rate - 0.6) * 100  # Bônus para win rate > 60%
        
        return score
        
    except Exception as e:
        print(f"Trial falhou: {str(e)}")
        return -1000


def run_optimization(n_trials=200):
    """
    Executar otimização multi-nível.
    
    Args:
        n_trials: Número de trials
    """
    print("="*80)
    print("OPTUNA MULTI-LEVEL OPTIMIZATION: MetaStrategy")
    print("="*80)
    print()
    print("Otimizando 3 níveis:")
    print("  1. RegimeDetector thresholds (classificação de regimes)")
    print("  2. Especialistas parameters (BullRunRider, RecoveryHunter)")
    print("  3. Trial77 fallback parameters")
    print()
    print(f"Trials: {n_trials}")
    print()
    
    # Criar estudo
    study = optuna.create_study(
        direction='maximize',
        sampler=TPESampler(seed=42)
    )
    
    # Otimizar
    print("Iniciando otimização...")
    print()
    
    study.optimize(
        objective,
        n_trials=n_trials,
        show_progress_bar=True,
        n_jobs=1  # Backtrader não é thread-safe
    )
    
    # Resultados
    print()
    print("="*80)
    print("RESULTADOS DA OTIMIZAÇÃO")
    print("="*80)
    print()
    
    print(f"Melhor score: {study.best_value:.2f}")
    print()
    
    print("Melhores parâmetros:")
    print()
    
    # Agrupar por nível
    regime_params = {}
    specialist_params = {}
    trial77_params = {}
    
    for key, value in study.best_params.items():
        if 'bull_run' in key or 'recovery' in key or 'crash' in key:
            specialist_params[key] = value
        elif any(x in key for x in ['strong_bull', 'bull_correction', 'steady_bull', 
                                      'sideways', 'bear', 'regime']):
            regime_params[key] = value
        else:
            trial77_params[key] = value
    
    print("NÍVEL 1: RegimeDetector")
    for key, value in sorted(regime_params.items()):
        print(f"  {key:30s}: {value}")
    print()
    
    print("NÍVEL 2: Especialistas")
    for key, value in sorted(specialist_params.items()):
        print(f"  {key:30s}: {value}")
    print()
    
    print("NÍVEL 3: Trial77 Fallback")
    for key, value in sorted(trial77_params.items()):
        print(f"  {key:30s}: {value}")
    print()
    
    # Top 10 trials
    print("="*80)
    print("TOP 10 TRIALS")
    print("="*80)
    print()
    
    trials_df = study.trials_dataframe()
    trials_df = trials_df.sort_values('value', ascending=False).head(10)
    
    print(f"{'Trial':>6} | {'Score':>10} | {'State':>10}")
    print("-" * 32)
    
    for idx, row in trials_df.iterrows():
        trial_num = row['number']
        score = row['value']
        state = row['state']
        print(f"{trial_num:>6} | {score:>10.2f} | {state:>10}")
    
    print()
    
    # Salvar resultados
    import pandas as pd
    
    best_params_df = pd.DataFrame([study.best_params])
    best_params_df.to_csv('data/processed/meta_strategy_best_params.csv', index=False)
    
    trials_df.to_csv('data/processed/meta_strategy_all_trials.csv', index=False)
    
    print("✓ Resultados salvos:")
    print("  - data/processed/meta_strategy_best_params.csv")
    print("  - data/processed/meta_strategy_all_trials.csv")
    print()
    
    # Teste final com melhores parâmetros
    print("="*80)
    print("TESTE FINAL COM MELHORES PARÂMETROS")
    print("="*80)
    print()
    
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
    
    backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
    
    # Usar TODOS os melhores parâmetros (incluindo regime_params)
    print("Executando backtest final...")
    results = backtest_engine.run_backtest(
        strategy_cls=MetaStrategy,
        data_df=df,
        symbol='BTC-USD',
        **study.best_params  # Passar todos os parâmetros direto do study
    )
    
    print()
    print("="*80)
    print("COMPARAÇÃO")
    print("="*80)
    print()
    
    print("Trial 77 original:")
    print("  Retorno: +420.42%")
    print("  Sharpe: 0.8038")
    print("  Max DD: 51.72%")
    print("  Trades: 132")
    print()
    
    print("MetaStrategy otimizada:")
    print(f"  Retorno: +{results.get('total_return_pct', 0):.2f}%")
    print(f"  Sharpe: {results.get('sharpe_ratio', 0):.4f}")
    print(f"  Max DD: {results.get('max_drawdown_pct', 0):.2f}%")
    print(f"  Trades: {results.get('total_trades', 0)}")
    print()
    
    improvement = results.get('total_return_pct', 0) - 420.42
    print(f"Melhoria: {improvement:+.2f}%")
    print()


if __name__ == '__main__':
    import sys
    
    # Permitir passar número de trials via argumento
    n_trials = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    
    run_optimization(n_trials=n_trials)
