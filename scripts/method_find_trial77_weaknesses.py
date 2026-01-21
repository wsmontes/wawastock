"""
MÉTODO SISTEMÁTICO: Identificar fraquezas do Trial 77

Abordagem de 3 níveis:
1. QUANDO Trial 77 perde vs B&H (análise temporal)
2. ONDE Trial 77 falha (condições de mercado)
3. POR QUÊ Trial 77 falha (lógica da estratégia)

Resultado: Estratégias complementares baseadas em evidências
"""

import pandas as pd
import numpy as np
from datetime import datetime
from engines.data_engine import DataEngine

print("="*80)
print("MÉTODO SISTEMÁTICO: ANÁLISE DE FRAQUEZAS DO TRIAL 77")
print("="*80)
print()
print("Objetivo: Identificar lacunas específicas para criar estratégias complementares")
print("Abordagem: Evidência empírica, não aleatoriedade")
print()

# Carregar dados usando DataEngine
data_engine = DataEngine(use_cache=True, auto_indicators=False)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
print(f"✓ Dados carregados: {len(df)} dias ({df.index[0].date()} a {df.index[-1].date()})")
print()

# Calcular métricas de mercado
df['return_1d'] = df['close'].pct_change() * 100
df['return_5d'] = df['close'].pct_change(5) * 100
df['return_20d'] = df['close'].pct_change(20) * 100
df['return_60d'] = df['close'].pct_change(60) * 100
df['vol_20d'] = df['return_1d'].rolling(20).std()

# SMA para tendência
df['sma20'] = df['close'].rolling(20).mean()
df['sma50'] = df['close'].rolling(50).mean()
df['sma200'] = df['close'].rolling(200).mean()

# Classificar regime de mercado
def classify_regime(row):
    if pd.isna(row['return_20d']) or pd.isna(row['sma200']):
        return 'UNKNOWN'
    
    if row['return_20d'] > 20:
        return 'STRONG_BULL'
    elif row['return_20d'] > 10:
        return 'MODERATE_BULL'
    elif row['return_20d'] > 0:
        return 'WEAK_BULL'
    elif row['return_20d'] > -10:
        return 'WEAK_BEAR'
    elif row['return_20d'] > -20:
        return 'MODERATE_BEAR'
    else:
        return 'STRONG_BEAR'

df['regime'] = df.apply(classify_regime, axis=1)

print("="*80)
print("ANÁLISE 1: DISTRIBUIÇÃO DE REGIMES DE MERCADO")
print("="*80)
print()

regime_counts = df['regime'].value_counts()
regime_pcts = (regime_counts / len(df) * 100).round(1)

for regime, pct in regime_pcts.items():
    days = regime_counts[regime]
    print(f"{regime:20s}: {days:4d} dias ({pct:5.1f}%)")

print()

# Calcular performance B&H por regime
print("="*80)
print("ANÁLISE 2: PERFORMANCE BUY & HOLD POR REGIME")
print("="*80)
print()

bh_performance_by_regime = {}
for regime in df['regime'].unique():
    if regime == 'UNKNOWN':
        continue
    regime_df = df[df['regime'] == regime]
    total_return = regime_df['return_1d'].sum()
    bh_performance_by_regime[regime] = total_return

print("Retorno acumulado Buy & Hold por regime:")
for regime, ret in sorted(bh_performance_by_regime.items(), key=lambda x: x[1], reverse=True):
    print(f"  {regime:20s}: {ret:+8.2f}%")

print()

# Trial 77: 10.2% de exposição, 109 trades, +825.72%
# Isso significa que ficou FORA do mercado 89.8% do tempo
trial77_exposure = 0.102
trial77_return = 825.72
trial77_trades = 109

# Estimar em quais regimes Trial 77 deveria estar DENTRO
print("="*80)
print("ANÁLISE 3: OPORTUNIDADE POR REGIME")
print("="*80)
print()

print(f"Trial 77 Performance: +{trial77_return:.2f}%")
print(f"Trial 77 Exposição: {trial77_exposure*100:.1f}%")
print(f"Trial 77 Trades: {trial77_trades}")
print()

# Buy & Hold performance
initial_price = df['close'].iloc[0]
final_price = df['close'].iloc[-1]
bh_return = ((final_price - initial_price) / initial_price) * 100

print(f"Buy & Hold Performance: +{bh_return:.2f}%")
print(f"Buy & Hold Exposição: 100.0%")
print()

print(f"Gap: {bh_return - trial77_return:.2f}%")
print()

# ANÁLISE 4: Identificar onde aumentar exposição
print("="*80)
print("ANÁLISE 4: ONDE AUMENTAR EXPOSIÇÃO")
print("="*80)
print()

# Se Trial 77 tem 10.2% de exposição e B&H tem 100%, faltam 89.8%
# A questão é: em qual regime aumentar?

# Calcular "eficiência" de cada regime (retorno / risco)
print("Análise de eficiência por regime (Retorno / Volatilidade):")
print()

regime_efficiency = {}
for regime in df['regime'].unique():
    if regime == 'UNKNOWN':
        continue
    regime_df = df[df['regime'] == regime]
    
    if len(regime_df) < 10:
        continue
    
    avg_return = regime_df['return_1d'].mean()
    avg_vol = regime_df['vol_20d'].mean()
    
    if avg_vol > 0:
        efficiency = avg_return / avg_vol
    else:
        efficiency = 0
    
    regime_efficiency[regime] = {
        'avg_return': avg_return,
        'avg_vol': avg_vol,
        'efficiency': efficiency,
        'days': len(regime_df),
        'total_return': regime_df['return_1d'].sum()
    }

for regime, stats in sorted(regime_efficiency.items(), key=lambda x: x[1]['efficiency'], reverse=True):
    print(f"{regime:20s}:")
    print(f"  Retorno médio/dia: {stats['avg_return']:+.3f}%")
    print(f"  Volatilidade:      {stats['avg_vol']:.3f}%")
    print(f"  Eficiência:        {stats['efficiency']:+.4f}")
    print(f"  Dias:              {stats['days']}")
    print(f"  Retorno total:     {stats['total_return']:+.2f}%")
    print()

# ANÁLISE 5: Propor estratégias complementares
print("="*80)
print("ANÁLISE 5: ESTRATÉGIAS COMPLEMENTARES NECESSÁRIAS")
print("="*80)
print()

strategies = []

# Estratégia 1: Capturar STRONG_BULL (onde B&H mais ganha)
if 'STRONG_BULL' in regime_efficiency:
    strong_bull = regime_efficiency['STRONG_BULL']
    strategies.append({
        'name': 'Strong Bull Rider',
        'target_regime': 'STRONG_BULL',
        'logic': 'Detectar início de bull run forte e manter posição',
        'entry_condition': 'return_20d > 15% E close > sma20 > sma50',
        'exit_condition': 'return_20d < 10% OU close < sma20',
        'expected_days': strong_bull['days'],
        'potential_gain': strong_bull['total_return'],
        'priority': 1
    })

# Estratégia 2: Capturar MODERATE_BULL (segundo maior ganho)
if 'MODERATE_BULL' in regime_efficiency:
    mod_bull = regime_efficiency['MODERATE_BULL']
    strategies.append({
        'name': 'Moderate Trend Follower',
        'target_regime': 'MODERATE_BULL',
        'logic': 'Surfar tendências moderadas com trailing stop',
        'entry_condition': 'return_20d entre 5-20% E close > sma50',
        'exit_condition': 'close < sma20 OU trailing stop',
        'expected_days': mod_bull['days'],
        'potential_gain': mod_bull['total_return'],
        'priority': 2
    })

# Estratégia 3: Evitar BEAR markets (onde B&H perde)
bear_regimes = ['STRONG_BEAR', 'MODERATE_BEAR']
total_bear_loss = sum(regime_efficiency.get(r, {}).get('total_return', 0) for r in bear_regimes)
if total_bear_loss < 0:
    strategies.append({
        'name': 'Bear Market Avoider',
        'target_regime': 'STRONG_BEAR, MODERATE_BEAR',
        'logic': 'Ficar em cash durante quedas confirmadas',
        'entry_condition': 'NUNCA (apenas saídas)',
        'exit_condition': 'return_20d < -10% E close < sma50',
        'expected_days': sum(regime_efficiency.get(r, {}).get('days', 0) for r in bear_regimes),
        'potential_gain': abs(total_bear_loss),  # Evitar perda
        'priority': 3
    })

# Estratégia 4: Capturar recuperações (WEAK_BULL após BEAR)
strategies.append({
    'name': 'Recovery Hunter',
    'target_regime': 'WEAK_BULL após BEAR',
    'logic': 'Entrar cedo em recuperações pós-correção',
    'entry_condition': 'close cruzou sma20 para cima após período bear',
    'exit_condition': 'Transferir para Strong Bull Rider OU stop loss',
    'expected_days': regime_efficiency.get('WEAK_BULL', {}).get('days', 0),
    'potential_gain': regime_efficiency.get('WEAK_BULL', {}).get('total_return', 0),
    'priority': 4
})

print(f"🎯 {len(strategies)} ESTRATÉGIAS COMPLEMENTARES IDENTIFICADAS")
print()

for i, strategy in enumerate(strategies, 1):
    print(f"{i}. {strategy['name']}")
    print(f"   Regime alvo:       {strategy['target_regime']}")
    print(f"   Lógica:            {strategy['logic']}")
    print(f"   Entrada:           {strategy['entry_condition']}")
    print(f"   Saída:             {strategy['exit_condition']}")
    print(f"   Dias esperados:    {strategy['expected_days']}")
    print(f"   Ganho potencial:   {strategy['potential_gain']:+.2f}%")
    print(f"   Prioridade:        {strategy['priority']}")
    print()

# Salvar recomendações
recommendations_df = pd.DataFrame(strategies)
recommendations_df.to_csv('data/processed/trial77_complementary_strategies.csv', index=False)
print(f"✓ Análise salva em: data/processed/trial77_complementary_strategies.csv")
print()

# ANÁLISE 6: Matriz de decisão
print("="*80)
print("ANÁLISE 6: MATRIZ DE DECISÃO PARA IMPLEMENTAÇÃO")
print("="*80)
print()

print("Ordem de implementação baseada em impacto:")
print()

# Calcular impacto potencial
for strategy in sorted(strategies, key=lambda x: x['priority']):
    days_pct = (strategy['expected_days'] / len(df)) * 100
    daily_avg = strategy['potential_gain'] / strategy['expected_days'] if strategy['expected_days'] > 0 else 0
    
    print(f"Prioridade {strategy['priority']}: {strategy['name']}")
    print(f"  • Cobertura: {days_pct:.1f}% dos dias ({strategy['expected_days']} dias)")
    print(f"  • Retorno médio: {daily_avg:+.3f}%/dia")
    print(f"  • Potencial total: {strategy['potential_gain']:+.2f}%")
    print()

print("="*80)
print("PRÓXIMOS PASSOS")
print("="*80)
print()
print("1. Implementar 'Strong Bull Rider' - Maior impacto potencial")
print("2. Implementar 'Bear Market Avoider' - Proteção de capital")
print("3. Implementar 'Moderate Trend Follower' - Complemento")
print("4. Testar ensemble combinando Trial 77 + novas estratégias")
print()
