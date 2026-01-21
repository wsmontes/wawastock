"""
ARQUITETURA DE META-MODELO: Orquestrador de Especialistas

INSIGHT FUNDAMENTAL:
Não criar um modelo que "faz tudo bem"
Criar modelos ESPECIALISTAS + um ORQUESTRADOR que escolhe qual usar

ANÁLISE: Quando Trial 77 falha?

Vou identificar os REGIMES onde Trial 77 perde ou ganha pouco,
e criar ESPECIALISTAS para cada regime.
"""

import pandas as pd
from engines.data_engine import DataEngine

print("="*80)
print("ANÁLISE: IDENTIFICAR REGIMES DE FALHA DO TRIAL 77")
print("="*80)
print()

# Carregar dados
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

# Classificar regimes de mercado
df['return_5d'] = df['close'].pct_change(5) * 100
df['return_20d'] = df['close'].pct_change(20) * 100
df['return_60d'] = df['close'].pct_change(60) * 100
df['vol_20d'] = df['close'].pct_change().rolling(20).std() * 100

df['sma20'] = df['close'].rolling(20).mean()
df['sma50'] = df['close'].rolling(50).mean()
df['sma200'] = df['close'].rolling(200).mean()

# Classificação de regime mais sofisticada
def classify_market_regime(row):
    """
    Classificar regime baseado em múltiplos fatores.
    Não apenas return, mas estrutura de mercado.
    """
    if pd.isna(row['return_20d']) or pd.isna(row['sma200']):
        return 'UNKNOWN'
    
    ret_20d = row['return_20d']
    ret_60d = row['return_60d']
    vol = row['vol_20d']
    price = row['close']
    sma20 = row['sma20']
    sma50 = row['sma50']
    sma200 = row['sma200']
    
    # Estrutura de tendência
    trend_up = sma20 > sma50 > sma200
    trend_down = sma20 < sma50 < sma200
    
    # REGIME 1: Bull Run Forte (Trial 77 pode perder por sair cedo)
    if ret_20d > 15 and ret_60d > 30 and trend_up:
        return 'STRONG_BULL_RUN'
    
    # REGIME 2: Bull Market com correções (Trial 77 toma stops)
    elif ret_60d > 20 and ret_20d < 5 and trend_up:
        return 'BULL_CORRECTION'
    
    # REGIME 3: Tendência de alta estável (Trial 77 pode funcionar bem)
    elif ret_20d > 5 and ret_60d > 10 and trend_up:
        return 'STEADY_BULL'
    
    # REGIME 4: Recuperação pós-queda (Trial 77 pode entrar tarde)
    elif ret_20d > 10 and ret_60d < 0 and price > sma50:
        return 'RECOVERY'
    
    # REGIME 5: Lateral de alta volatilidade (Trial 77 overtrading)
    elif abs(ret_20d) < 10 and vol > 4:
        return 'CHOPPY_SIDEWAYS'
    
    # REGIME 6: Lateral de baixa volatilidade (Trial 77 pode funcionar)
    elif abs(ret_20d) < 10 and vol <= 4:
        return 'CALM_SIDEWAYS'
    
    # REGIME 7: Queda rápida (Trial 77 toma perdas)
    elif ret_20d < -15 and trend_down:
        return 'CRASH'
    
    # REGIME 8: Bear market gradual (Trial 77 fica entrando e saindo)
    elif ret_20d < -5 and ret_60d < -10 and trend_down:
        return 'BEAR_MARKET'
    
    # REGIME 9: Fraqueza em tendência de alta (Trial 77 confuso)
    elif ret_20d < 0 and ret_60d > 10 and not trend_down:
        return 'WEAKENING_BULL'
    
    else:
        return 'UNDEFINED'

df['regime'] = df.apply(classify_market_regime, axis=1)

print("PASSO 1: DISTRIBUIÇÃO DE REGIMES")
print("="*80)
print()

regime_counts = df['regime'].value_counts()
total_days = len(df)

for regime, count in regime_counts.items():
    pct = (count / total_days) * 100
    print(f"{regime:25s}: {count:4d} dias ({pct:5.1f}%)")

print()

print("PASSO 2: PERFORMANCE B&H POR REGIME")
print("="*80)
print()

regime_performance = {}
for regime in df['regime'].unique():
    if regime == 'UNKNOWN':
        continue
    
    regime_df = df[df['regime'] == regime]
    
    if len(regime_df) < 5:
        continue
    
    # Retorno acumulado
    total_return = regime_df['close'].pct_change().sum() * 100
    
    # Retorno médio por dia
    avg_return = regime_df['close'].pct_change().mean() * 100
    
    # Volatilidade
    volatility = regime_df['close'].pct_change().std() * 100
    
    # Sharpe (aproximado)
    sharpe = (avg_return / volatility) if volatility > 0 else 0
    
    regime_performance[regime] = {
        'days': len(regime_df),
        'total_return': total_return,
        'avg_return': avg_return,
        'volatility': volatility,
        'sharpe': sharpe
    }

# Ordenar por total return
sorted_regimes = sorted(regime_performance.items(), key=lambda x: x[1]['total_return'], reverse=True)

print(f"{'Regime':<25} | {'Dias':>5} | {'Ret Total':>10} | {'Ret/dia':>8} | {'Vol':>6} | {'Sharpe':>7}")
print("-" * 85)
for regime, stats in sorted_regimes:
    print(f"{regime:<25} | {stats['days']:>5} | {stats['total_return']:>9.2f}% | {stats['avg_return']:>7.3f}% | {stats['volatility']:>5.2f}% | {stats['sharpe']:>7.3f}")

print()

print("PASSO 3: IDENTIFICAR REGIMES DE OPORTUNIDADE")
print("="*80)
print()

# Regimes onde há MUITO ganho potencial (B&H ganha muito)
high_opportunity = [r for r, s in sorted_regimes if s['total_return'] > 100 and s['days'] > 50]
print("🎯 REGIMES DE ALTA OPORTUNIDADE (B&H ganha muito):")
for regime in high_opportunity:
    stats = regime_performance[regime]
    print(f"   • {regime}: +{stats['total_return']:.2f}% em {stats['days']} dias")
print()
print("   → Criar ESPECIALISTA para maximizar ganhos nesses regimes")
print()

# Regimes onde há MUITO risco (B&H perde muito)
high_risk = [r for r, s in sorted_regimes if s['total_return'] < -50]
print("⚠️  REGIMES DE ALTO RISCO (B&H perde muito):")
for regime in high_risk:
    stats = regime_performance[regime]
    print(f"   • {regime}: {stats['total_return']:.2f}% em {stats['days']} dias")
print()
print("   → Criar ESPECIALISTA para evitar/proteger capital nesses regimes")
print()

# Regimes choppy (baixo return, alta volatilidade)
choppy_regimes = [r for r, s in sorted_regimes if abs(s['total_return']) < 50 and s['volatility'] > 3]
print("🌊 REGIMES CHOPPY (lateral com volatilidade):")
for regime in choppy_regimes:
    stats = regime_performance[regime]
    print(f"   • {regime}: {stats['total_return']:+.2f}% em {stats['days']} dias (vol {stats['volatility']:.2f}%)")
print()
print("   → Criar ESPECIALISTA de range trading OU ficar fora")
print()

print("PASSO 4: ESTRATÉGIA DE ESPECIALISTAS")
print("="*80)
print()

specialists_needed = []

# Especialista 1: Bull Run Rider
if 'STRONG_BULL_RUN' in [r[0] for r in sorted_regimes]:
    stats = regime_performance['STRONG_BULL_RUN']
    specialists_needed.append({
        'name': 'BullRunRider',
        'regime': 'STRONG_BULL_RUN',
        'objective': 'Maximizar ganhos em bull runs fortes',
        'strategy': 'Buy-and-hold com trailing stop amplo',
        'entry': 'return_20d > 15% E trend_up confirmado',
        'exit': 'Apenas trailing stop (-20%) ou quebra de estrutura',
        'potential': stats['total_return'],
        'days': stats['days']
    })

# Especialista 2: Crash Avoider
if 'CRASH' in regime_performance:
    stats = regime_performance['CRASH']
    specialists_needed.append({
        'name': 'CrashAvoider',
        'regime': 'CRASH',
        'objective': 'Evitar perdas em crashes',
        'strategy': 'Ficar 100% em cash',
        'entry': 'NUNCA',
        'exit': 'Sair imediatamente se detectar crash',
        'potential': abs(stats['total_return']),  # Ganho = perda evitada
        'days': stats['days']
    })

# Especialista 3: Recovery Hunter
if 'RECOVERY' in regime_performance:
    stats = regime_performance['RECOVERY']
    specialists_needed.append({
        'name': 'RecoveryHunter',
        'regime': 'RECOVERY',
        'objective': 'Capturar recuperações pós-queda',
        'strategy': 'Entry agressivo em reversão confirmada',
        'entry': 'return_20d > 10% após período negativo',
        'exit': 'Transferir para BullRunRider ou stop loss',
        'potential': stats['total_return'],
        'days': stats['days']
    })

# Especialista 4: Sideways Sitter
if 'CHOPPY_SIDEWAYS' in regime_performance or 'CALM_SIDEWAYS' in regime_performance:
    specialists_needed.append({
        'name': 'SidewaysSitter',
        'regime': 'CHOPPY_SIDEWAYS, CALM_SIDEWAYS',
        'objective': 'Não overtrading em lateral',
        'strategy': 'Ficar fora OU range trading conservador',
        'entry': 'Apenas se suporte/resistência claros',
        'exit': 'Quick take profit ou stop apertado',
        'potential': 0,  # Objetivo é não perder
        'days': regime_performance.get('CHOPPY_SIDEWAYS', {}).get('days', 0)
    })

print(f"🎯 {len(specialists_needed)} ESPECIALISTAS IDENTIFICADOS:")
print()

for i, spec in enumerate(specialists_needed, 1):
    print(f"{i}. {spec['name']}")
    print(f"   Regime alvo: {spec['regime']}")
    print(f"   Objetivo: {spec['objective']}")
    print(f"   Estratégia: {spec['strategy']}")
    print(f"   Entrada: {spec['entry']}")
    print(f"   Saída: {spec['exit']}")
    print(f"   Potencial: +{spec['potential']:.2f}% em {spec['days']} dias")
    print()

print("PASSO 5: META-MODELO (ORQUESTRADOR)")
print("="*80)
print()

print("O Orquestrador decide QUAL especialista usar baseado no regime atual:")
print()
print("Lógica de decisão:")
print("  1. Classificar regime atual (usando última janela de dados)")
print("  2. Consultar qual especialista é responsável por esse regime")
print("  3. Delegar decisão de trading para esse especialista")
print("  4. Se nenhum especialista, usar Trial 77 como fallback")
print()

print("Exemplo de fluxo:")
print("  • Dia 100: Regime = STRONG_BULL_RUN → Ativar BullRunRider")
print("  • Dia 150: Regime = CRASH → Ativar CrashAvoider (sair imediatamente)")
print("  • Dia 200: Regime = RECOVERY → Ativar RecoveryHunter")
print("  • Dia 250: Regime = STEADY_BULL → Usar Trial 77 (regime conhecido)")
print()

print("="*80)
print("PRÓXIMO PASSO: IMPLEMENTAR ARQUITETURA")
print("="*80)
print()

print("1. Criar RegimeDetector")
print("   - Classe que classifica regime em tempo real")
print("   - Usa última janela de 60 dias")
print()

print("2. Criar Especialistas (1 classe por regime)")
print("   - BullRunRiderStrategy")
print("   - CrashAvoiderStrategy")
print("   - RecoveryHunterStrategy")
print("   - SidewaysSitterStrategy")
print()

print("3. Criar MetaStrategy (Orquestrador)")
print("   - next() chama RegimeDetector")
print("   - Seleciona especialista apropriado")
print("   - Delega decisão de trading")
print()

print("4. Testar incrementalmente")
print("   - Cada especialista individualmente")
print("   - MetaStrategy com todos especialistas")
print("   - Comparar vs Trial 77 e B&H")
print()

# Salvar análise
df.to_csv('data/processed/regime_analysis_for_specialists.csv')
specialists_df = pd.DataFrame(specialists_needed)
specialists_df.to_csv('data/processed/specialists_needed.csv', index=False)

print("✓ Análise salva:")
print("  - data/processed/regime_analysis_for_specialists.csv")
print("  - data/processed/specialists_needed.csv")
print()
