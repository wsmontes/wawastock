# Technical Indicators Integration - pandas-ta

## Overview

Implementação limpa e organizada de indicadores técnicos usando `pandas-ta`, com separação clara entre lógica de coleta de dados e cálculo de indicadores.

## Arquitetura

### 1. IndicatorsEngine (`engines/indicators_engine.py`)
- **Responsabilidade**: Calcular indicadores técnicos
- **Operação**: Nível de banco de dados (após coleta, antes de salvar)
- **Independente**: Não depende de fontes de dados específicas

### 2. DataEngine Integration
- **Parâmetro `auto_indicators`**: Ativa/desativa cálculo automático (default: `False`)
- **Parâmetro `indicator_set`**: Define quais indicadores calcular
  - `'minimal'`: SMA 20/50, RSI 14
  - `'standard'`: SMAs, EMAs, RSI, MACD, Bollinger Bands, ATR, OBV (default)
  - `'full'`: Todos os indicadores + ADX, Stochastic, VWAP, etc.

## Uso

### Básico - Com Indicadores
```python
from engines import DataEngine

# Inicializar com indicadores (standard)
engine = DataEngine(auto_indicators=True)

# Carregar dados - indicadores são calculados automaticamente
df = engine.load_prices('AAPL', start='2023-01-01', end='2023-12-31')

# DataFrame terá: OHLCV + indicadores técnicos
print(df.columns)
# ['open', 'high', 'low', 'close', 'volume', 'SMA_20', 'SMA_50', 'RSI_14', ...]
```

### Sem Indicadores (Legacy)
```python
# Desativar indicadores para compatibilidade com código antigo
engine = DataEngine(auto_indicators=False)
df = engine.load_prices('AAPL')

# DataFrame terá apenas: OHLCV
print(df.columns)
# ['open', 'high', 'low', 'close', 'volume']
```

### Diferentes Conjuntos de Indicadores
```python
# Minimal - apenas indicadores básicos
engine = DataEngine(auto_indicators=True, indicator_set='minimal')

# Full - todos os indicadores disponíveis
engine = DataEngine(auto_indicators=True, indicator_set='full')
```

## Indicadores Disponíveis

### Standard Set (22 indicadores)
- **Trend**: SMA 20/50/200, EMA 12/26
- **Momentum**: RSI 14, MACD, Stochastic
- **Volatility**: Bollinger Bands, ATR 14
- **Volume**: OBV

### Full Set (30+ indicadores)
- Todos do standard +
- EMA 9/21/55
- ADX (trend strength)
- VWAP

## Storage

- **Parquet Files**: Indicadores são salvos junto com dados OHLCV
- **DuckDB**: Queries podem usar indicadores diretamente
- **Cache-aware**: Detecta indicadores existentes e não recalcula

## Detecção de Duplicatas

O sistema automaticamente:
1. Verifica se indicadores já existem no DataFrame
2. Pula cálculo se já estiverem presentes
3. Evita colunas duplicadas

## Performance

- **Cálculo único**: Indicadores calculados uma vez e salvos
- **Loads subsequentes**: Carrega indicadores do disco (sem recálculo)
- **Lazy evaluation**: Só calcula quando `auto_indicators=True`

## Exemplo Completo

```python
from engines import DataEngine

# Setup com indicadores
engine = DataEngine(
    auto_indicators=True,
    indicator_set='standard'
)

# Primeira vez: calcula e salva indicadores
df = engine.load_prices('AAPL', start='2023-01-01', end='2023-12-31')
print(f"Colunas: {len(df.columns)}")  # 27 (5 OHLCV + 22 indicadores)

# Próximas vezes: carrega do disco (rápido)
df = engine.load_prices('AAPL', start='2023-01-01', end='2023-12-31')

# Usar indicadores em estratégias
latest = df.iloc[-1]
print(f"RSI: {latest['RSI_14']:.2f}")
print(f"MACD: {latest['MACD_12_26_9']:.2f}")
print(f"SMA 50: {latest['SMA_50']:.2f}")

engine.close()
```

## Compatibilidade

- **Backward Compatible**: Código antigo funciona sem mudanças (auto_indicators=False por padrão)
- **Recipes**: Funcionam normalmente (indicadores não interferem com backtrader)
- **Strategies**: Podem usar indicadores pré-calculados ou calcular próprios

## Próximos Passos

1. ✅ Implementação básica do IndicatorsEngine
2. ✅ Integração com DataEngine
3. ✅ Detecção de duplicatas
4. ⏳ Documentar uso em estratégias
5. ⏳ Adicionar indicadores customizados

## Files Modified

- `requirements.txt` - Added pandas-ta
- `engines/indicators_engine.py` - NEW: Engine de cálculo de indicadores
- `engines/data_engine.py` - Added auto_indicators support
- `engines/__init__.py` - Export IndicatorsEngine
- `scripts/example_indicators.py` - NEW: Exemplo de uso
