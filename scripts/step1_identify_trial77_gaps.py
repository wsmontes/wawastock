"""
ANÁLISE SISTEMÁTICA: Identificar onde Trial 77 perde oportunidades vs Buy & Hold

Método: Comparação de Capital ao longo do tempo
- Calcular patrimônio Trial 77 dia a dia
- Calcular patrimônio Buy & Hold dia a dia
- Identificar QUANDO e QUANTO a diferença cresce
- Classificar períodos por tipo de gap (exposure, timing, risk)
"""

import pandas as pd
import numpy as np
from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy

print("="*80)
print("MÉTODO 1: ANÁLISE DE GAPS TEMPORAIS")
print("="*80)
print()
print("Objetivo: Identificar QUANDO Trial 77 perde vs Buy & Hold")
print("Abordagem: Comparar evolução de capital dia a dia")
print()

# Carregar dados
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

print(f"✓ Dados carregados: {len(df)} dias")
print(f"  Período: {df.index[0].date()} a {df.index[-1].date()}")
print()

# Parâmetros Trial 77 (corrigidos para nomes da estratégia)
trial77_params = {
    'rsi_period': 11,
    'rsi_oversold': 33,
    'rsi_overbought': 76,
    'bb_period': 19,
    'bb_dev': 2.35,  # Corrigido: bb_std -> bb_dev
    'volume_period': 18,  # Corrigido: volume_ma_period -> volume_period
    'volume_threshold': 1.15,
    'macd_fast': 11,
    'macd_slow': 25,
    'macd_signal': 8,
    'ema_fast': 8,  # Corrigido: ema_short -> ema_fast
    'ema_slow': 19,  # Corrigido: ema_long -> ema_slow
    'atr_period': 13,
    'atr_multiplier': 1.69,  # Corrigido: stop_loss_atr_mult -> atr_multiplier
    'take_profit_pct': 15.83,
    'trailing_stop_pct': 9.23,
    'position_size': 0.88,
    'min_signals_buy': 2,
    'min_signals_sell': 2
}

print("🔄 Executando Trial 77...")
backtest_engine = BacktestEngine(initial_cash=100000, commission=0.001)
results = backtest_engine.run_backtest(
    strategy_cls=BTCAdaptiveStrategy,
    data_df=df,
    symbol='BTC-USD',
    **trial77_params
)

print(f"✓ Trial 77: +{results['return_pct']:.2f}% ({results['trades_total']} trades)")
print()

# Simular Buy & Hold
initial_price = df['close'].iloc[0]
final_price = df['close'].iloc[-1]
bh_return = ((final_price - initial_price) / initial_price) * 100
shares_bh = 100000 / initial_price
bh_final = shares_bh * final_price

print(f"✓ Buy & Hold: +{bh_return:.2f}%")
print()

# Reconstruir histórico de capital Trial 77
print("🔍 Reconstruindo histórico de trades...")

# Extrair trades do resultado
trades_data = []
if hasattr(backtest_engine.cerebro.strats[0][0][0], 'trades_log'):
    trades_log = backtest_engine.cerebro.strats[0][0][0].trades_log
    for trade in trades_log:
        trades_data.append({
            'date': trade['exit_date'],
            'type': trade['type'],
            'entry_price': trade['entry_price'],
            'exit_price': trade['exit_price'],
            'pnl': trade['pnl'],
            'pnl_pct': trade['pnl_pct']
        })

# Criar série temporal de capital
capital_series = []
current_capital = 100000
in_position = False
shares = 0
entry_price = 0

for idx, row in df.iterrows():
    # Verificar se há trade neste dia
    trade_today = [t for t in trades_data if t['date'].date() == idx.date()]
    
    if trade_today:
        for trade in trade_today:
            if trade['type'] == 'BUY':
                in_position = True
                shares = (current_capital * 0.88) / trade['entry_price']  # position_size
                entry_price = trade['entry_price']
            elif trade['type'] == 'SELL':
                current_capital = shares * trade['exit_price']
                in_position = False
                shares = 0
    
    # Calcular capital do dia
    if in_position:
        capital = shares * row['close']
    else:
        capital = current_capital
    
    # Buy & Hold
    bh_capital = shares_bh * row['close']
    
    capital_series.append({
        'date': idx,
        'price': row['close'],
        'trial77_capital': capital,
        'bh_capital': bh_capital,
        'gap': bh_capital - capital,
        'gap_pct': ((bh_capital - capital) / capital) * 100 if capital > 0 else 0,
        'in_position': in_position
    })

capital_df = pd.DataFrame(capital_series)
capital_df.set_index('date', inplace=True)

print(f"✓ Histórico reconstruído: {len(capital_df)} dias")
print()

# ANÁLISE 1: Quando o gap cresce?
print("="*80)
print("ANÁLISE 1: PERÍODOS DE MAIOR DIVERGÊNCIA")
print("="*80)
print()

capital_df['gap_growth'] = capital_df['gap'].diff()
capital_df['gap_growth_pct'] = capital_df['gap_pct'].diff()

# Identificar períodos de crescimento acelerado do gap
threshold = capital_df['gap_growth'].quantile(0.90)  # Top 10% de crescimento
critical_periods = capital_df[capital_df['gap_growth'] > threshold].copy()

print(f"🎯 Períodos críticos (top 10% de divergência): {len(critical_periods)} dias")
print()

# Agrupar períodos consecutivos
critical_periods['period_id'] = (critical_periods.index.to_series().diff() > pd.Timedelta(days=7)).cumsum()

for period_id, group in critical_periods.groupby('period_id'):
    start_date = group.index[0]
    end_date = group.index[-1]
    days = len(group)
    gap_increase = group['gap'].iloc[-1] - group['gap'].iloc[0]
    price_change = ((group['price'].iloc[-1] - group['price'].iloc[0]) / group['price'].iloc[0]) * 100
    was_in_position = group['in_position'].mean()
    
    print(f"Período {period_id + 1}:")
    print(f"  Data: {start_date.date()} a {end_date.date()} ({days} dias)")
    print(f"  Gap cresceu: ${gap_increase:,.2f}")
    print(f"  Preço: {price_change:+.2f}%")
    print(f"  Exposição Trial 77: {was_in_position*100:.1f}%")
    print()

# ANÁLISE 2: Correlação gap com condições de mercado
print("="*80)
print("ANÁLISE 2: CONDIÇÕES QUE GERAM GAP")
print("="*80)
print()

# Calcular retornos de diferentes períodos
capital_df['return_1d'] = capital_df['price'].pct_change(1) * 100
capital_df['return_7d'] = capital_df['price'].pct_change(7) * 100
capital_df['return_30d'] = capital_df['price'].pct_change(30) * 100
capital_df['volatility_30d'] = capital_df['return_1d'].rolling(30).std()

# Correlação entre crescimento de gap e condições
correlations = {
    'Retorno 1 dia': capital_df['gap_growth'].corr(capital_df['return_1d']),
    'Retorno 7 dias': capital_df['gap_growth'].corr(capital_df['return_7d']),
    'Retorno 30 dias': capital_df['gap_growth'].corr(capital_df['return_30d']),
    'Volatilidade': capital_df['gap_growth'].corr(capital_df['volatility_30d']),
    'Fora posição': capital_df['gap_growth'].corr(~capital_df['in_position'])
}

print("Correlação entre crescimento do gap e:")
for factor, corr in sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True):
    print(f"  {factor:20s}: {corr:+.4f}")
print()

# ANÁLISE 3: Classificar períodos por tipo de problema
print("="*80)
print("ANÁLISE 3: CLASSIFICAÇÃO DE LACUNAS")
print("="*80)
print()

# Definir critérios
capital_df['strong_uptrend'] = capital_df['return_30d'] > 20  # Alta forte
capital_df['moderate_uptrend'] = (capital_df['return_30d'] > 5) & (capital_df['return_30d'] <= 20)
capital_df['sideways'] = (capital_df['return_30d'] >= -5) & (capital_df['return_30d'] <= 5)
capital_df['downtrend'] = capital_df['return_30d'] < -5

# Calcular gap médio por condição
gaps_by_condition = {
    'Alta forte (>20%)': capital_df[capital_df['strong_uptrend']]['gap_growth'].mean(),
    'Alta moderada (5-20%)': capital_df[capital_df['moderate_uptrend']]['gap_growth'].mean(),
    'Lateral (-5 a 5%)': capital_df[capital_df['sideways']]['gap_growth'].mean(),
    'Queda (<-5%)': capital_df[capital_df['downtrend']]['gap_growth'].mean()
}

print("Gap médio diário por condição de mercado:")
for condition, gap in sorted(gaps_by_condition.items(), key=lambda x: x[1], reverse=True):
    print(f"  {condition:25s}: ${gap:+,.2f}/dia")
print()

# Exposição por condição
exposure_by_condition = {
    'Alta forte (>20%)': capital_df[capital_df['strong_uptrend']]['in_position'].mean() * 100,
    'Alta moderada (5-20%)': capital_df[capital_df['moderate_uptrend']]['in_position'].mean() * 100,
    'Lateral (-5 a 5%)': capital_df[capital_df['sideways']]['in_position'].mean() * 100,
    'Queda (<-5%)': capital_df[capital_df['downtrend']]['in_position'].mean() * 100
}

print("Exposição Trial 77 por condição de mercado:")
for condition, exposure in exposure_by_condition.items():
    print(f"  {condition:25s}: {exposure:.1f}%")
print()

# ANÁLISE 4: Identificar padrões de entrada/saída perdidos
print("="*80)
print("ANÁLISE 4: OPORTUNIDADES PERDIDAS")
print("="*80)
print()

# Períodos fora de posição durante alta
out_during_bull = capital_df[~capital_df['in_position'] & capital_df['strong_uptrend']]
print(f"🔴 Dias FORA durante alta forte: {len(out_during_bull)} ({len(out_during_bull)/len(capital_df)*100:.1f}%)")

if len(out_during_bull) > 0:
    missed_gain = (out_during_bull['price'].pct_change() * 100).sum()
    print(f"   Ganho perdido estimado: {missed_gain:.2f}%")
    print()

# Períodos dentro de posição durante queda
in_during_bear = capital_df[capital_df['in_position'] & capital_df['downtrend']]
print(f"🔴 Dias DENTRO durante queda: {len(in_during_bear)} ({len(in_during_bear)/len(capital_df)*100:.1f}%)")

if len(in_during_bear) > 0:
    loss_taken = (in_during_bear['price'].pct_change() * 100).sum()
    print(f"   Perda tomada estimada: {loss_taken:.2f}%")
    print()

# CONCLUSÕES E ESTRATÉGIAS COMPLEMENTARES
print("="*80)
print("ESTRATÉGIAS COMPLEMENTARES NECESSÁRIAS")
print("="*80)
print()

# Baseado nas análises, propor estratégias
strategies_needed = []

if gaps_by_condition['Alta forte (>20%)'] > gaps_by_condition['Lateral (-5 a 5%)']:
    strategies_needed.append({
        'name': 'Bull Trend Rider',
        'logic': 'Detectar e surfar tendências fortes (>20% em 30d)',
        'focus': 'Maximizar exposição em bull markets',
        'entry': 'Confirmação de tendência forte + momentum',
        'exit': 'Apenas em reversão confirmada ou stop amplo',
        'gap_addressed': gaps_by_condition['Alta forte (>20%)']
    })

if exposure_by_condition['Alta moderada (5-20%)'] < 50:
    strategies_needed.append({
        'name': 'Moderate Trend Follower',
        'logic': 'Capturar altas moderadas (5-20% em 30d)',
        'focus': 'Maior exposição em tendências moderadas',
        'entry': 'Pullback em tendência estabelecida',
        'exit': 'Stop trailing ou quebra de tendência',
        'gap_addressed': gaps_by_condition['Alta moderada (5-20%)']
    })

if len(out_during_bull) > 100:
    strategies_needed.append({
        'name': 'Early Bull Detector',
        'logic': 'Entrar ANTES de tendência forte se confirmar',
        'focus': 'Identificar início de bull markets',
        'entry': 'Divergências de momentum + volume',
        'exit': 'Transferir para Bull Trend Rider',
        'gap_addressed': missed_gain if len(out_during_bull) > 0 else 0
    })

# Salvar análise
capital_df.to_csv('data/processed/trial77_gap_analysis.csv')
print(f"✓ Análise salva em: data/processed/trial77_gap_analysis.csv")
print()

print(f"🎯 ESTRATÉGIAS COMPLEMENTARES IDENTIFICADAS: {len(strategies_needed)}")
print()

for i, strategy in enumerate(strategies_needed, 1):
    print(f"{i}. {strategy['name']}")
    print(f"   Lógica: {strategy['logic']}")
    print(f"   Foco: {strategy['focus']}")
    print(f"   Entrada: {strategy['entry']}")
    print(f"   Saída: {strategy['exit']}")
    print(f"   Gap endereçado: ${strategy['gap_addressed']:,.2f}/dia")
    print()

# Salvar recomendações
recommendations_df = pd.DataFrame(strategies_needed)
recommendations_df.to_csv('data/processed/complementary_strategies_needed.csv', index=False)
print(f"✓ Recomendações salvas em: data/processed/complementary_strategies_needed.csv")
print()

print("="*80)
print("PRÓXIMO PASSO: Implementar estratégias complementares")
print("="*80)
