"""Debug: Ver estrutura do results dict"""

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.meta_strategy_v2 import MetaStrategyV2
import json

trial77_params = {
    'rsi_period': 11, 'rsi_oversold': 33, 'rsi_overbought': 76,
    'bb_period': 19, 'bb_dev': 2.35, 'volume_period': 18,
    'volume_threshold': 1.15, 'macd_fast': 11, 'macd_slow': 25,
    'macd_signal': 8, 'ema_fast': 8, 'ema_slow': 19,
    'atr_period': 13, 'atr_multiplier': 1.69,
    'take_profit_pct': 15.83, 'trailing_stop_pct': 9.23,
    'position_size': 0.88, 'min_signals_buy': 2, 'min_signals_sell': 2
}

specialist_params = {
    'bull_run_position_size': 0.95,
    'bull_run_trailing': 20.0,
    'recovery_position_size': 0.85,
    'recovery_stop_loss': 8.0,
}

regime_params = {
    'strong_bull_ret20': 20.0,
    'strong_bull_ret60': 40.0,
    'crash_threshold': -20.0,
    'recovery_ret20': 15.0,
}

strategy_params = {
    **trial77_params,
    **specialist_params,
    **regime_params,
}

data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)

results = backtest_engine.run_backtest(
    strategy_cls=MetaStrategyV2,
    data_df=df,
    symbol='BTC-USD',
    **strategy_params
)

print("\n" + "="*80)
print("ESTRUTURA DO RESULTS DICT:")
print("="*80)
print(json.dumps(results, indent=2, default=str))
