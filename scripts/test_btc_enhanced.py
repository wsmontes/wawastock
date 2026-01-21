"""
Teste Sistemático: BTC Enhanced Strategy vs Trial 77

HIPÓTESE:
BTC Enhanced deve superar Trial 77 ao incorporar:
1. Regime Filter (Bear Avoider) - Reduzir drawdown
2. Signal Quality (Strong Bull Rider) - Reduzir overtrading
3. Dynamic Position Sizing - Ajustar exposição por contexto

EXPECTATIVA:
- Retorno: +500-600% (vs +420% Trial 77)
- Drawdown: <35% (vs 51.72% Trial 77)
- Sharpe: >0.90 (vs 0.8038 Trial 77)
- Trades: 80-100 (vs 132 Trial 77)
- Win Rate: >48% (vs 44.70% Trial 77)
"""

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from strategies.btc_enhanced_strategy import BTCEnhancedStrategy

# Carregar dados
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)

print("="*80)
print("TESTE SISTEMÁTICO: BTC ENHANCED vs TRIAL 77")
print("="*80)
print()

# B&H
initial_price = df['close'].iloc[0]
final_price = df['close'].iloc[-1]
bh_return = ((final_price - initial_price) / initial_price) * 100

print(f"🎯 Objetivo: Superar Trial 77 (+420.42%) e aproximar de B&H (+{bh_return:.2f}%)")
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
print("Características:")
print("  • Multi-signal timing")
print("  • 19 parâmetros otimizados")
print("  • Sem filtro de regime")
print("  • Position sizing fixo (88%)")
print()

results_trial77 = backtest_engine.run_backtest(
    strategy_cls=BTCAdaptiveStrategy,
    data_df=df,
    symbol='BTC-USD',
    **trial77_params
)
print()

print("="*80)
print("NOVA VERSÃO: BTC ENHANCED")
print("="*80)
print("Melhorias incorporadas:")
print("  1. Market Regime Filter - Bloqueia entradas em bear markets")
print("  2. Signal Quality Score - Requer 6/10 pontos para entrar")
print("  3. Dynamic Position Sizing - 95% em STRONG_BULL, 50% em SIDEWAYS")
print("  4. Adaptive Stop Loss - 15% em bull, 8% em outros regimes")
print()

results_enhanced = backtest_engine.run_backtest(
    strategy_cls=BTCEnhancedStrategy,
    data_df=df,
    symbol='BTC-USD'
)
print()

print("="*80)
print("COMPARAÇÃO DETALHADA")
print("="*80)
print()

# Extrair métricas das tabelas
print("Análise visual das tabelas acima:")
print()
print("Métricas para comparar:")
print("  1. Total Return - Enhanced deve ter +100-180% sobre Trial 77")
print("  2. Max Drawdown - Enhanced deve ter ~15-20% menos")
print("  3. Sharpe Ratio - Enhanced deve ser >0.90")
print("  4. Total Trades - Enhanced deve ter ~30-50 trades menos")
print("  5. Win Rate - Enhanced deve ser >48%")
print()

print("="*80)
print("VALIDAÇÃO DE HIPÓTESES")
print("="*80)
print()

print("HIPÓTESE 1: Regime Filter reduz drawdown")
print("  Trial 77 não evita bears → DD alto")
print("  Enhanced bloqueia entradas em bears → DD menor")
print("  ✓ Validar: Enhanced DD < Trial 77 DD * 0.68")
print()

print("HIPÓTESE 2: Signal Quality reduz overtrading")
print("  Trial 77 entra com min 2 sinais → 132 trades")
print("  Enhanced exige 6/10 pontos → menos trades")
print("  ✓ Validar: Enhanced trades < Trial 77 trades * 0.76")
print()

print("HIPÓTESE 3: Dynamic Sizing aumenta retorno")
print("  Trial 77 sempre usa 88% → exposição subótima")
print("  Enhanced usa 50-95% por regime → exposição otimizada")
print("  ✓ Validar: Enhanced return > Trial 77 return * 1.20")
print()

print("HIPÓTESE 4: Combinação bate Buy & Hold")
print("  Trial 77: +420.42% (gap de -722%)")
print("  Enhanced com todas melhorias → reduzir gap")
print("  ✓ Meta: Enhanced > +600% (gap < -540%)")
print()

print("="*80)
print("ANÁLISE DE MELHORIAS")
print("="*80)
print()

print("Se Enhanced NÃO superou Trial 77:")
print("  → Revisar Signal Quality Score (pode estar muito restritivo)")
print("  → Ajustar min_quality_score de 6 para 5")
print("  → Considerar relaxar regime filter em WEAK_BEAR")
print()

print("Se Enhanced superou mas não bateu B&H:")
print("  → Problema é filosófico, não de parâmetros")
print("  → Bitcoin 2020-2025 foi bull run histórico")
print("  → Trading ativo não consegue superar buy-and-hold em mercado unidirecional")
print("  → Considerar estratégia híbrida: hold em bull, trade em outros regimes")
print()

print("="*80)
print("PRÓXIMOS PASSOS")
print("="*80)
print()

print("1. Se Enhanced > Trial 77:")
print("   → Otimizar parâmetros com Optuna")
print("   → Testar em out-of-sample (2026 quando disponível)")
print("   → Documentar lições aprendidas")
print()

print("2. Se Enhanced ≈ Trial 77:")
print("   → Analisar logs para entender comportamento")
print("   → Verificar se regime filter está funcionando")
print("   → Ajustar thresholds de regime")
print()

print("3. Se Enhanced < Trial 77:")
print("   → Validar implementação da lógica")
print("   → Revisar calculate_signal_quality()")
print("   → Possivelmente signal quality muito restritivo")
print()
