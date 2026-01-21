"""
Testar MetaStrategy com os melhores parâmetros do Optuna
"""

import pandas as pd
from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.meta_strategy import MetaStrategy


def main():
    # Carregar melhores parâmetros
    best_params_df = pd.read_csv('data/processed/meta_strategy_best_params.csv')
    best_params = best_params_df.iloc[0].to_dict()
    
    print("="*80)
    print("TESTE COM MELHORES PARÂMETROS DO OPTUNA")
    print("="*80)
    print()
    
    print("Parâmetros carregados:")
    print(f"  RegimeDetector: strong_bull_ret20={best_params['strong_bull_ret20']:.2f}")
    print(f"  BullRunRider: position_size={best_params['bull_run_position_size']:.2f}")
    print(f"  RecoveryHunter: position_size={best_params['recovery_position_size']:.2f}")
    print(f"  Trial77: position_size={best_params['position_size']:.2f}")
    print()
    
    # Carregar dados
    data_engine = DataEngine(use_cache=True, auto_indicators=True)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
    
    # Backtest
    backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
    
    print("Executando backtest com MetaStrategy otimizada...")
    print()
    
    results = backtest_engine.run_backtest(
        strategy_cls=MetaStrategy,
        data_df=df,
        symbol='BTC-USD',
        **best_params
    )
    
    # Extrair métricas (normalizar nomes)
    analyzers = results.get('analyzers', {})
    return_pct = results.get('return_pct', 0)
    sharpe = analyzers.get('sharpe', 0) or 0
    max_dd = abs(analyzers.get('max_drawdown', 0) or 0)
    total_trades = analyzers.get('total_trades', 0)
    won_trades = analyzers.get('won_trades', 0)
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
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
    print("  Win Rate: 44.70%")
    print()
    
    print("MetaStrategy otimizada:")
    print(f"  Retorno: +{return_pct:.2f}%")
    print(f"  Sharpe: {sharpe:.4f}")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Trades: {total_trades}")
    print(f"  Win Rate: {win_rate:.2f}%")
    print()
    
    # Análise
    ret_diff = return_pct - 420.42
    sharpe_diff = sharpe - 0.8038
    dd_diff = max_dd - 51.72
    
    print("Diferenças:")
    print(f"  Retorno: {ret_diff:+.2f}% ({ret_diff/420.42*100:+.1f}%)")
    print(f"  Sharpe: {sharpe_diff:+.4f} ({sharpe_diff/0.8038*100:+.1f}%)")
    print(f"  Max DD: {dd_diff:+.2f}% ({dd_diff/51.72*100:+.1f}%)")
    print()
    
    if ret_diff > 0:
        print("✓ MetaStrategy VENCEU!")
    elif ret_diff > -50:
        print("≈ Resultados similares")
    else:
        print("✗ Trial 77 ainda é melhor")


if __name__ == '__main__':
    main()
