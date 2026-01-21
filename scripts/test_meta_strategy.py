"""
Teste: MetaStrategy (Orquestrador de Especialistas)

HIPÓTESE:
MetaStrategy deve superar Trial 77 ao usar especialistas por regime:
- BullRunRider em STRONG_BULL_RUN
- RecoveryHunter em RECOVERY
- CrashAvoider em CRASH/BEAR
- Trial77 como fallback

EXPECTATIVA:
- Retorno > Trial 77 (+420%)
- Drawdown < Trial 77 (51.72%)
- Sharpe > Trial 77 (0.8038)
"""

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from strategies.meta_strategy import MetaStrategy

# Carregar dados
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)

print("="*80)
print("TESTE: META STRATEGY (Orquestrador de Especialistas)")
print("="*80)
print()

# B&H
initial_price = df['close'].iloc[0]
final_price = df['close'].iloc[-1]
bh_return = ((final_price - initial_price) / initial_price) * 100

print(f"Benchmark - Buy & Hold: +{bh_return:.2f}%")
print()

# Trial 77 baseline
trial77_params = {
    'rsi_period': 11, 'rsi_oversold': 33, 'rsi_overbought': 76,
    'bb_period': 19, 'bb_dev': 2.35, 'volume_period': 18,
    'volume_threshold': 1.15, 'macd_fast': 11, 'macd_slow': 25,
    'macd_signal': 8, 'ema_fast': 8, 'ema_slow': 19,
    'atr_period': 13, 'atr_multiplier': 1.69,
    'take_profit_pct': 15.83, 'trailing_stop_pct': 9.23,
    'position_size': 0.88, 'min_signals_buy': 2, 'min_signals_sell': 2
}

print("="*80)
print("BASELINE: TRIAL 77")
print("="*80)
print("Abordagem: Multi-signal timing sem adaptação de regime")
print()

results_trial77 = backtest_engine.run_backtest(
    strategy_cls=BTCAdaptiveStrategy,
    data_df=df,
    symbol='BTC-USD',
    **trial77_params
)
print()

print("="*80)
print("NOVA ABORDAGEM: META STRATEGY")
print("="*80)
print("Arquitetura:")
print("  1. RegimeDetector classifica mercado")
print("  2. MetaStrategy seleciona especialista:")
print("     • STRONG_BULL_RUN → BullRunRider (98% capital, trailing 20%)")
print("     • RECOVERY → RecoveryHunter (90% capital, stop 10%)")
print("     • CRASH/BEAR → CrashAvoider (sair imediatamente)")
print("     • Outros → Trial77 (fallback)")
print()

results_meta = backtest_engine.run_backtest(
    strategy_cls=MetaStrategy,
    data_df=df,
    symbol='BTC-USD'
)
print()

print("="*80)
print("ANÁLISE COMPARATIVA")
print("="*80)
print()

print("Copie os valores das tabelas acima:")
print()
print("Trial 77:")
print("  - Total Return: _____%")
print("  - Max Drawdown: _____%")
print("  - Sharpe Ratio: ______")
print("  - Total Trades: ______")
print("  - Win Rate: _____%")
print()

print("MetaStrategy:")
print("  - Total Return: _____%")
print("  - Max Drawdown: _____%")
print("  - Sharpe Ratio: ______")
print("  - Total Trades: ______")
print("  - Win Rate: _____%")
print()

print("="*80)
print("VALIDAÇÃO")
print("="*80)
print()

print("✓ MetaStrategy deve SUPERAR Trial 77 se:")
print("  1. Retorno > +420% (especialistas capturam oportunidades)")
print("  2. Drawdown < 51.72% (CrashAvoider protege capital)")
print("  3. Sharpe > 0.8038 (melhor risk-adjusted return)")
print()

print("⚠️  MetaStrategy FALHOU se:")
print("  1. Retorno < +420% (especialistas não funcionaram)")
print("  2. Muitas transições entre especialistas (overhead)")
print("  3. RegimeDetector classificando mal")
print()

print("📊 Se MetaStrategy ≈ Trial 77:")
print("  → Especialistas não agregam valor")
print("  → Problema pode ser na detecção de regime")
print("  → Revisar thresholds do RegimeDetector")
print()

print("🎯 Se MetaStrategy >> Trial 77:")
print("  → Arquitetura de especialistas FUNCIONA")
print("  → Otimizar parâmetros dos especialistas")
print("  → Adicionar mais especialistas (ex: SidewaysSitter)")
print()
