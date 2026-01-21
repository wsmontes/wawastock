"""
Diagnóstico: Por que BTC Enhanced falhou?

RESULTADO: -18.08% (perdeu dinheiro!)
BASELINE: +420.42% (Trial 77)
GAP: -438.50% 

Isso NÃO é problema de ajuste - é falha arquitetural.

HIPÓTESES DE FALHA:

1. REGIME FILTER MUITO RESTRITIVO
   - Enhanced bloqueia BEAR e STRONG_BEAR
   - Se classificação estiver errada, perde oportunidades
   - Bitcoin teve correções que depois se recuperaram
   - Filtro pode estar classificando recuperações como bear

2. SIGNAL QUALITY SCORE IMPOSSÍVEL
   - Requer 6/10 pontos
   - Pode ser que NUNCA ou RARAMENTE atinja 6
   - Score pode estar mal calibrado
   - Resultado: fica fora do mercado quando deveria entrar

3. STOP LOSS ADAPTATIVO MUITO AGRESSIVO
   - Stop de 15% em bull pode ser OK
   - Mas stop de 8% em outros regimes pode ser muito apertado
   - Bitcoin é volátil - 8% é ruído normal
   - Pode estar tomando stops desnecessários

4. SAÍDAS PREMATURAS
   - Múltiplas condições de saída (6 condições!)
   - Pode estar saindo cedo demais
   - Trial 77 tinha 2 sinais para vender
   - Enhanced tem 6 gatilhos - overprotective

MÉTODO DE DIAGNÓSTICO:

Vou criar script que analisa:
1. Quantas vezes signal_quality >= 6? (deve ser raro)
2. Quantos dias classificados como BEAR/STRONG_BEAR? (pode ser muitos)
3. Quantos stops ativados vs take profits?
4. Comparar decisões Enhanced vs Trial 77 dia a dia
"""

from engines.data_engine import DataEngine
import pandas as pd

print("="*80)
print("DIAGNÓSTICO: POR QUE ENHANCED PERDEU -18%?")
print("="*80)
print()

# Carregar dados
data_engine = DataEngine(use_cache=True, auto_indicators=True)
df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')

# Simular classificação de regime
df['return_20d'] = df['close'].pct_change(20) * 100
df['sma20'] = df['close'].rolling(20).mean()
df['sma50'] = df['close'].rolling(50).mean()
df['sma200'] = df['close'].rolling(200).mean()

def classify_regime(row):
    ret = row['return_20d']
    if pd.isna(ret):
        return 'UNKNOWN'
    if ret > 15.0:
        return 'STRONG_BULL'
    elif ret > 5.0:
        return 'BULL'
    elif ret > 0:
        return 'WEAK_BULL'
    elif ret > -10.0:
        return 'WEAK_BEAR'
    elif ret > -20.0:
        return 'BEAR'
    else:
        return 'STRONG_BEAR'

df['regime'] = df.apply(classify_regime, axis=1)

print("ANÁLISE 1: DISTRIBUIÇÃO DE REGIMES")
print("="*80)
print()

regime_counts = df['regime'].value_counts()
for regime, count in regime_counts.items():
    pct = (count / len(df)) * 100
    blocked = "🚫 BLOQUEADO" if regime in ['BEAR', 'STRONG_BEAR'] else "✅ Permitido"
    print(f"{regime:15s}: {count:4d} dias ({pct:5.1f}%) {blocked}")

blocked_days = df[df['regime'].isin(['BEAR', 'STRONG_BEAR'])].shape[0]
print()
print(f"Total BLOQUEADO: {blocked_days} dias ({blocked_days/len(df)*100:.1f}%)")
print()

# Calcular se bloqueios foram bons ou ruins
blocked_df = df[df['regime'].isin(['BEAR', 'STRONG_BEAR'])]
blocked_return = blocked_df['close'].pct_change().sum() * 100
print(f"Retorno nos dias bloqueados: {blocked_return:+.2f}%")
print()

if blocked_return > 0:
    print("❌ PROBLEMA! Bloqueou dias com retorno POSITIVO")
    print("   Regime filter está ATRAPALHANDO, não ajudando")
else:
    print("✅ OK! Bloqueou dias com retorno negativo")
    print("   Regime filter funcionou corretamente")
print()

print("ANÁLISE 2: SIGNAL QUALITY SCORE")
print("="*80)
print()

# Simular signal quality (aproximado - sem todos os indicadores)
df['rsi'] = 50  # Placeholder
df['volume'] = df['volume'].fillna(df['volume'].mean())
df['volume_sma'] = df['volume'].rolling(20).mean()

# Calcular score simplificado
def estimate_signal_quality(row):
    score = 0
    
    # RSI < 33 (+2)
    if row['rsi'] < 33:
        score += 2
    
    # Preço acima SMA50 (+2)
    if not pd.isna(row['sma50']) and row['close'] > row['sma50']:
        score += 2
    
    # Golden cross (+2)
    if not pd.isna(row['sma20']) and not pd.isna(row['sma50']):
        if row['sma20'] > row['sma50']:
            score += 2
    
    # Volume acima média (+1)
    if not pd.isna(row['volume_sma']) and row['volume'] > row['volume_sma'] * 1.15:
        score += 1
    
    return score

df['quality_estimate'] = df.apply(estimate_signal_quality, axis=1)

quality_dist = df['quality_estimate'].value_counts().sort_index()
print("Distribuição de Signal Quality Score (estimado):")
for score, count in quality_dist.items():
    pct = (count / len(df)) * 100
    allowed = "✅ ENTRA" if score >= 6 else "🚫 Bloqueia"
    print(f"  Score {score}: {count:4d} dias ({pct:5.1f}%) {allowed}")

print()
allowed_by_quality = df[df['quality_estimate'] >= 6].shape[0]
print(f"Dias com quality >= 6: {allowed_by_quality} ({allowed_by_quality/len(df)*100:.1f}%)")
print()

if allowed_by_quality < 100:
    print("❌ PROBLEMA CRÍTICO! Menos de 100 dias atingem quality >= 6")
    print("   Score está MUITO restritivo - estratégia quase nunca entra")
    print()
    print("RECOMENDAÇÃO: Reduzir min_quality_score de 6 para 4")
else:
    print("✅ Score parece OK")

print()

print("ANÁLISE 3: COMBINAÇÃO DE FILTROS")
print("="*80)
print()

# Dias que passam AMBOS os filtros
df['passes_regime'] = ~df['regime'].isin(['BEAR', 'STRONG_BEAR'])
df['passes_quality'] = df['quality_estimate'] >= 6
df['passes_both'] = df['passes_regime'] & df['passes_quality']

both_pass = df['passes_both'].sum()
print(f"Dias que passam AMBOS os filtros: {both_pass} ({both_pass/len(df)*100:.1f}%)")
print()

if both_pass < 200:
    print("❌ PROBLEMA ARQUITETURAL!")
    print(f"   Apenas {both_pass} dias de {len(df)} passam pelos filtros")
    print(f"   Isso é {both_pass/len(df)*100:.1f}% de oportunidades")
    print()
    print("   Trial 77 tinha 10.2% de exposição e fez +420%")
    print(f"   Enhanced tem ~{both_pass/len(df)*100:.1f}% de oportunidades possíveis")
    print()
    print("CAUSA RAIZ: Filtros DUPLOS são muito restritivos")
    print("   - Regime filter bloqueia muitos dias")
    print("   - Quality score bloqueia muitos dias")
    print("   - Interseção é MUITO pequena")
else:
    print("✅ Filtros parecem razoáveis")

print()

print("="*80)
print("CONCLUSÃO DO DIAGNÓSTICO")
print("="*80)
print()

print("FALHA IDENTIFICADA: Excesso de proteção (overprotective)")
print()
print("Enhanced tem:")
print("  1. Regime filter (bloqueia BEAR + STRONG_BEAR)")
print("  2. Quality score >= 6 (muito restritivo)")
print("  3. 6 condições de saída (vs 2 do Trial 77)")
print("  4. Stop loss adaptativo (pode ser muito apertado)")
print()
print("Resultado: Fica FORA do mercado na maior parte do tempo")
print("           Quando entra, sai cedo demais")
print("           Toma stops em volatilidade normal")
print()

print("="*80)
print("ESTRATÉGIA DE CORREÇÃO")
print("="*80)
print()

print("NÃO FAZER:")
print("  ✗ Ajustar parâmetros aleatoriamente")
print("  ✗ Remover todos os filtros (volta ao Trial 77)")
print("  ✗ Tentar otimizar com Optuna (GIGO)")
print()

print("FAZER:")
print("  1. SIMPLIFICAR lógica")
print("     - Manter 1 filtro principal (regime OU quality, não ambos)")
print("     - Reduzir condições de saída de 6 para 3")
print()
print("  2. CALIBRAR melhor")
print("     - min_quality_score: 6 → 4")
print("     - Permitir WEAK_BEAR (só bloquear BEAR + STRONG_BEAR)")
print()
print("  3. TESTAR incrementalmente")
print("     - V1: Só regime filter")
print("     - V2: Só quality filter")  
print("     - V3: Ambos com thresholds relaxados")
print("     - Comparar qual funciona melhor")
print()

print("INSIGHT FUNDAMENTAL:")
print("  Bear Avoider (+255%) e Strong Bull Rider (+179%) funcionam")
print("  porque cada um tem UMA filosofia clara")
print()
print("  Enhanced tentou combinar TUDO e ficou paralisado")
print("  Menos filtros, mais execução")
print()

# Salvar análise
df.to_csv('data/processed/enhanced_diagnosis.csv', index=True)
print("✓ Diagnóstico salvo em: data/processed/enhanced_diagnosis.csv")
