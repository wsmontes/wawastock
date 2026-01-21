# Metodologia de Treino/Teste para Estratégias SMA em BTC

## 📊 Resumo da Análise

Após extensiva validação walk-forward com múltiplos períodos de SMA, chegamos às seguintes conclusões:

### Resultados por Regime de Mercado

| Regime | % Tempo | Alpha SMA vs B&H | DD Reduction |
|--------|---------|------------------|--------------|
| **BULL** | ~57% | -33.3% ⛔ | +6.5% |
| **SIDEWAYS** | ~20% | +3.5% ✅ | +10.6% |
| **BEAR** | ~23% | +27.8% ✅ | +34.5% |

### Conclusão Principal

**SMA NÃO funciona como estratégia primária para BTC** porque:
1. BTC passa ~57% do tempo em bull markets onde SMA prejudica
2. O ganho em bears não compensa a perda em bulls
3. Alpha médio geral: **-12.4%**

### O que o SMA FAZ bem:
- ✅ Protege em bear markets (+27.8% vs B&H)
- ✅ Reduz drawdown significativamente (-34.5% em bears)
- ✅ Funciona como "stop defensivo"

### O que o SMA NÃO faz bem:
- ⛔ Perde muito em bull markets (-33.3% vs B&H)
- ⛔ Gera muitos sinais falsos (whipsaws)
- ⛔ Não supera B&H no longo prazo

---

## 🎯 Recomendações

### Opção 1: Buy & Hold Puro
Para quem tem horizonte longo e suporta volatilidade:
- Simplemente comprar e segurar
- BTC historicamente retorna ~100% ao ano
- Drawdowns de até 80% são normais

### Opção 2: SMA como Hedge/Seguro (Recomendado)
Usar SMA apenas em condições específicas:
```
SE regime == BEAR:
    Usar SMA-100 como stop defensivo
SENÃO:
    Ficar comprado (B&H)
```

Como detectar BEAR:
- Preço 10%+ abaixo da SMA-200
- OU retorno de 60 dias < -20%

### Opção 3: Estratégia Híbrida Adaptativa
```python
def decidir():
    trend = (preco - SMA200) / SMA200 * 100
    ret_60d = retorno_60_dias
    
    if trend > 5 and ret_60d > 10:
        # BULL -> ficar comprado sempre
        return "HOLD"
    elif trend < -10 or ret_60d < -20:
        # BEAR -> usar SMA como proteção
        if preco > SMA100:
            return "HOLD"
        else:
            return "SELL"
    else:
        # SIDEWAYS -> SMA conservador
        if preco > SMA130:
            return "HOLD"
        else:
            return "SELL"
```

---

## 📐 Metodologia de Validação Recomendada

### 1. Walk-Forward Expanding Window
```
Split 1: Treino [2018-2020] → Teste [2020H1]
Split 2: Treino [2018-2020H1] → Teste [2020H2]
Split 3: Treino [2018-2021] → Teste [2021H1]
...
```

### 2. Configuração Recomendada
- **Min treino**: 2 anos (730 dias)
- **Período teste**: 6 meses (180 dias)
- **Embargo**: 5 dias (evitar leakage)
- **Step**: 3 meses (90 dias)

### 3. Métricas a Avaliar
| Métrica | Threshold Mínimo |
|---------|------------------|
| Win Rate | ≥ 50% |
| Alpha Médio | > 0% |
| Degradação Train→Test | < 50% |
| Sharpe Test | > 0.5 |

### 4. Análise por Regime
SEMPRE separar resultados por regime:
- Performance em BULL
- Performance em BEAR
- Performance em SIDEWAYS

Uma estratégia que funciona em todos é muito difícil de encontrar!

---

## 🔬 Scripts de Validação

```bash
# Validação científica completa
python scripts/scientific_sma_validation.py

# Validação final com regimes
python scripts/final_sma_validation.py

# Resultados salvos em:
# - sma_walkforward_full_results.csv
# - sma_walkforward_summary.csv
# - final_sma_validation.csv
```

---

## 📈 Performance Esperada

### Se usar B&H puro:
- Retorno esperado: ~50-100% ao ano (volátil)
- Max drawdown esperado: até 80%
- Sem esforço de gestão

### Se usar SMA Defensivo:
- Retorno esperado: ~30-70% ao ano
- Max drawdown esperado: até 40%
- Requer monitoramento de regime

### Trade-off:
- SMA troca parte do retorno por proteção
- Funciona melhor em bear markets
- Não é "alpha positivo" consistente

---

## ⚠️ Disclaimer

Esta análise é baseada em dados históricos de 2018-2025. 
Performance passada não garante resultados futuros.
O mercado de cripto é altamente volátil e imprevisível.
