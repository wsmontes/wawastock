"""
Teste das Estratégias Complementares ao Trial 77

Baseado na análise sistemática que identificou:
1. Strong Bull Rider - Capturar bull runs (+337.26% potencial, 267 dias)
2. Bear Market Avoider - Evitar quedas (+308.12% potencial evitado, 296 dias)
3. Moderate Trend Follower - (próximo)

Objetivo: Verificar se as estratégias capturam as oportunidades identificadas
"""

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from strategies.strong_bull_rider_strategy import StrongBullRiderStrategy
from strategies.bear_market_avoider_strategy import BearMarketAvoiderStrategy

print("="*80)
print("TESTE: ESTRATÉGIAS COMPLEMENTARES AO TRIAL 77")
print("="*80)
print()
print("Baseline:")
print("  • Trial 77 (BTCAdaptiveStrategy): +825.72%, 109 trades, 10.2% exposição")
print("  • Buy & Hold: +1,142.65%, 100% exposição")
print("  • Gap: -316.93%")
print()
print("Hipótese:")
print("  • Strong Bull Rider captura bull runs que Trial 77 perdeu")
print("  • Bear Avoider preserva capital que Trial 77 perdeu em quedas")
print()

# Carregar dados
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

print(f"✓ Dados: {len(df)} dias (2020-01-01 a 2025-11-22)")
print()

# Buy & Hold para referência
initial_price = df['close'].iloc[0]
final_price = df['close'].iloc[-1]
bh_return = ((final_price - initial_price) / initial_price) * 100
shares_bh = 100000 / initial_price
bh_final = shares_bh * final_price

print("="*80)
print("TESTE 1: STRONG BULL RIDER")
print("="*80)
print()
print("Objetivo: Capturar +337.26% de retorno em 267 dias de STRONG_BULL")
print("Lógica: return_20d > 15%, close > sma20 > sma50, manter até enfraquecer")
print()

backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
results_bull = backtest_engine.run_backtest(
    strategy_cls=StrongBullRiderStrategy,
    data_df=df,
    symbol='BTC-USD'
)

print()
print("Resultado:")
print(f"  Retorno: +{results_bull.get('total_return_pct', 0):.2f}%")
print(f"  Trades: {results_bull.get('total_trades', 0)}")
print(f"  Win Rate: {results_bull.get('win_rate', 0):.2f}%")
print(f"  Max DD: {results_bull.get('max_drawdown_pct', 0):.2f}%")
print(f"  Sharpe: {results_bull.get('sharpe_ratio', 0):.4f}")
print()

if results_bull.get('total_return_pct', 0) > 0:
    vs_trial77 = results_bull.get('total_return_pct', 0) - 825.72
    vs_bh = results_bull.get('total_return_pct', 0) - bh_return
    print(f"  vs Trial 77: {vs_trial77:+.2f}%")
    print(f"  vs Buy & Hold: {vs_bh:+.2f}%")
    print()
    
    if results_bull.get('total_return_pct', 0) > 825.72:
        print("  ✅ SUCESSO! Supera Trial 77")
    else:
        print("  ⚠️  Não supera Trial 77, mas pode ser complementar")
print()

print("="*80)
print("TESTE 2: BEAR MARKET AVOIDER")
print("="*80)
print()
print("Objetivo: Evitar -308.12% de perdas em 296 dias de BEAR markets")
print("Lógica: Detectar bear (return_20d < -10%), ficar em cash, entrar em recuperação")
print()

results_bear = backtest_engine.run_backtest(
    strategy_cls=BearMarketAvoiderStrategy,
    data_df=df,
    symbol='BTC-USD'
)

print()
print("Resultado:")
print(f"  Retorno: +{results_bear.get('total_return_pct', 0):.2f}%")
print(f"  Trades: {results_bear.get('total_trades', 0)}")
print(f"  Win Rate: {results_bear.get('win_rate', 0):.2f}%")
print(f"  Max DD: {results_bear.get('max_drawdown_pct', 0):.2f}%")
print(f"  Sharpe: {results_bear.get('sharpe_ratio', 0):.4f}")
print()

if results_bear.get('total_return_pct', 0) > 0:
    vs_trial77 = results_bear.get('total_return_pct', 0) - 825.72
    vs_bh = results_bear.get('total_return_pct', 0) - bh_return
    print(f"  vs Trial 77: {vs_trial77:+.2f}%")
    print(f"  vs Buy & Hold: {vs_bh:+.2f}%")
    print()
    
    if results_bear.get('total_return_pct', 0) > 825.72:
        print("  ✅ SUCESSO! Supera Trial 77")
    else:
        print("  ⚠️  Não supera Trial 77")
        if results_bear.get('max_drawdown_pct', 0) < 36.78:
            print("  ✅ MAS tem drawdown menor (melhor proteção)")
print()

# Parâmetros Trial 77 para comparação
trial77_params = {
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
    'min_signals_sell': 2
}

print("="*80)
print("TESTE 3: TRIAL 77 (BASELINE)")
print("="*80)
print()
print("Objetivo: Confirmar performance baseline")
print()

results_trial77 = backtest_engine.run_backtest(
    strategy_cls=BTCAdaptiveStrategy,
    data_df=df,
    symbol='BTC-USD',
    **trial77_params
)

print()
print("Resultado:")
print(f"  Retorno: +{results_trial77.get('total_return_pct', 0):.2f}%")
print(f"  Trades: {results_trial77.get('total_trades', 0)}")
print(f"  Win Rate: {results_trial77.get('win_rate', 0):.2f}%")
print(f"  Max DD: {results_trial77.get('max_drawdown_pct', 0):.2f}%")
print(f"  Sharpe: {results_trial77.get('sharpe_ratio', 0):.4f}")
print()

# COMPARAÇÃO FINAL
print("="*80)
print("COMPARAÇÃO FINAL")
print("="*80)
print()

strategies_comparison = [
    {
        'name': 'Buy & Hold',
        'return': bh_return,
        'trades': 1,
        'dd': (df['close'].pct_change().cumsum().min()) * 100,
        'focus': 'Benchmark'
    },
    {
        'name': 'Trial 77 (Adaptive)',
        'return': results_trial77.get('total_return_pct', 0),
        'trades': results_trial77.get('total_trades', 0),
        'dd': results_trial77.get('max_drawdown_pct', 0),
        'focus': 'Multi-signal timing'
    },
    {
        'name': 'Strong Bull Rider',
        'return': results_bull.get('total_return_pct', 0),
        'trades': results_bull.get('total_trades', 0),
        'dd': results_bull.get('max_drawdown_pct', 0),
        'focus': 'Bull runs (267d, +337%)'
    },
    {
        'name': 'Bear Avoider',
        'return': results_bear.get('total_return_pct', 0),
        'trades': results_bear.get('total_trades', 0),
        'dd': results_bear.get('max_drawdown_pct', 0),
        'focus': 'Avoid bears (296d, -308%)'
    }
]

# Ordenar por retorno
strategies_comparison.sort(key=lambda x: x['return'], reverse=True)

print(f"{'Estratégia':<22} | {'Retorno':>10} | {'Trades':>7} | {'Max DD':>8} | {'Foco'}")
print("-" * 80)
for strat in strategies_comparison:
    print(f"{strat['name']:<22} | {strat['return']:>9.2f}% | {strat['trades']:>7} | {strat['dd']:>7.2f}% | {strat['focus']}")

print()
print("="*80)
print("ANÁLISE")
print("="*80)
print()

# Identificar melhor estratégia complementar
best_complement = max(
    [s for s in strategies_comparison if s['name'] not in ['Buy & Hold', 'Trial 77 (Adaptive)']],
    key=lambda x: x['return']
)

print(f"Melhor estratégia complementar: {best_complement['name']}")
print(f"  Retorno: +{best_complement['return']:.2f}%")
print(f"  Gap vs B&H: {best_complement['return'] - bh_return:.2f}%")
print()

if best_complement['return'] > results_trial77.get('total_return_pct', 0):
    print(f"✅ {best_complement['name']} SUPERA Trial 77 em {best_complement['return'] - results_trial77.get('total_return_pct', 0):.2f}%")
    print()
    print("Conclusão: Esta estratégia entende algo que Trial 77 não entende")
    print(f"Foco diferencial: {best_complement['focus']}")
else:
    print(f"⚠️  Nenhuma estratégia individual supera Trial 77")
    print()
    print("Próximo passo: Testar ENSEMBLE combinando estratégias")

print()
print("="*80)
