"""
Teste Simples das Estratégias Complementares

Extrai APENAS os números essenciais da tabela de resultados
"""

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from strategies.strong_bull_rider_strategy import StrongBullRiderStrategy
from strategies.bear_market_avoider_strategy import BearMarketAvoiderStrategy

# Carregar dados
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)

print("="*80)
print("TESTE COMPARATIVO: TRIAL 77 vs ESTRATÉGIAS COMPLEMENTARES")
print("="*80)
print()

# B&H
initial_price = df['close'].iloc[0]
final_price = df['close'].iloc[-1]
bh_return = ((final_price - initial_price) / initial_price) * 100

print(f"Benchmark - Buy & Hold: +{bh_return:.2f}%")
print()

# Trial 77
trial77_params = {
    'rsi_period': 11, 'rsi_oversold': 33, 'rsi_overbought': 76,
    'bb_period': 19, 'bb_dev': 2.35, 'volume_period': 18,
    'volume_threshold': 1.15, 'macd_fast': 11, 'macd_slow': 25,
    'macd_signal': 8, 'ema_fast': 8, 'ema_slow': 19,
    'atr_period': 13, 'atr_multiplier': 1.69,
    'take_profit_pct': 15.83, 'trailing_stop_pct': 9.23,
    'position_size': 0.88, 'min_signals_buy': 2, 'min_signals_sell': 2
}

print("1. Trial 77 (BTCAdaptiveStrategy)")
print("   Foco: Multi-signal timing, 19 parâmetros")
print()
backtest_engine.run_backtest(
    strategy_cls=BTCAdaptiveStrategy,
    data_df=df,
    symbol='BTC-USD',
    **trial77_params
)
print()

print("2. Strong Bull Rider")
print("   Foco: Capturar bull runs fortes (return_20d > 15%)")
print()
backtest_engine.run_backtest(
    strategy_cls=StrongBullRiderStrategy,
    data_df=df,
    symbol='BTC-USD'
)
print()

print("3. Bear Market Avoider")
print("   Foco: Evitar quedas (return_20d < -10%)")
print()
backtest_engine.run_backtest(
    strategy_cls=BearMarketAvoiderStrategy,
    data_df=df,
    symbol='BTC-USD'
)
print()

print("="*80)
print("ANÁLISE")
print("="*80)
print()
print("Da tabela acima, identifique:")
print("1. Qual estratégia teve MAIOR retorno total?")
print("2. Qual teve MENOR drawdown?")
print("3. Qual teve MELHOR Sharpe Ratio?")
print("4. Quantos trades cada uma fez?")
print()
print("HIPÓTESE:")
print("  • Strong Bull Rider deve ter MENOS trades mas MAIOR retorno médio/trade")
print("  • Bear Avoider deve ter MENOR drawdown")
print("  • Trial 77 deve ter MAIS trades por ser timing-based")
print()
