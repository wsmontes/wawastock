# Sistema de Cache Local-First

## 📦 Visão Geral

O framework implementa um sistema de **cache local-first** que gerencia automaticamente seus dados de mercado:

### Como Funciona

1. **Você solicita dados** (ex: BTCUSDT de 01/01 a 31/01)
2. **Sistema verifica o cache local** (DuckDB + Parquet)
3. **Identifica gaps** (ex: já tem 01-10, falta 11-31)
4. **Busca apenas o que falta** da API
5. **Salva tudo em Parquet** organizados por dia
6. **Retorna dados completos** do cache local

### Benefícios

✅ **Zero requisições desnecessárias** - API chamada só para dados faltantes  
✅ **Queries ultra-rápidas** - DuckDB lê direto dos Parquets  
✅ **Crescimento incremental** - Cache se constrói conforme você usa  
✅ **Organização automática** - Estrutura de pastas por source/symbol/timeframe  
✅ **Rastreamento completo** - Sabe exatamente o que tem em cache

## 🚀 Uso Básico

### 1. Buscar dados com cache inteligente

```bash
# Primeira vez: busca tudo da API e salva
python main.py get-cached --source yahoo --symbol AAPL \
  --start 2020-01-01 --end 2023-12-31

# Segunda vez: 100% local, sem API
python main.py get-cached --source yahoo --symbol AAPL \
  --start 2020-01-01 --end 2023-12-31

# Extender período: busca só 2024, já tem 2020-2023
python main.py get-cached --source yahoo --symbol AAPL \
  --start 2020-01-01 --end 2024-12-31
```

### 2. Ver informações do cache

```bash
# Ver tudo
python main.py cache-info

# Filtrar por source
python main.py cache-info --source YAHOO
python main.py cache-info --source BINANCE
```

Saída exemplo:
```
================================================================================
CACHE COVERAGE INFORMATION
================================================================================

source   symbol    timeframe  days  first_date  last_date   total_rows
YAHOO    AAPL      1d         1008  2020-01-01  2023-12-31  1008
BINANCE  BTCUSDT   1h         720   2024-01-01  2024-01-30  17280
CCXT_KRAKEN BTC/USD 1d        365   2023-01-01  2023-12-31  365

Total datasets: 3
Total days cached: 2093
Total rows: 18,653
================================================================================
```

### 3. Limpar cache

```bash
# Limpar tudo (pede confirmação)
python main.py cache-clear

# Limpar só uma source
python main.py cache-clear --source BINANCE

# Limpar só um símbolo
python main.py cache-clear --symbol BTCUSDT
```

## 📂 Estrutura de Armazenamento

```
data/
├── trader.duckdb              # Catálogo e índices
└── parquet/
    └── candles/
        ├── YAHOO/
        │   ├── AAPL/
        │   │   └── 1d/
        │   │       └── 2024/
        │   │           ├── 2024-01-01.parquet
        │   │           ├── 2024-01-02.parquet
        │   │           └── ...
        │   └── TSLA/
        │       └── 1h/
        │           └── 2024/
        │               └── ...
        ├── BINANCE/
        │   └── BTCUSDT/
        │       ├── 15m/
        │       ├── 1h/
        │       └── 1d/
        └── CCXT_KRAKEN/
            └── BTC_USD/
                └── 1d/
```

### Tabelas DuckDB

**parquet_files**: Catálogo de todos os arquivos Parquet
```sql
id        | kind    | source  | symbol  | timeframe | date       | path
----------|---------|---------|---------|-----------|------------|-------------
12345     | candles | YAHOO   | AAPL    | 1d        | 2024-01-01 | data/...
67890     | candles | BINANCE | BTCUSDT | 1h        | 2024-01-15 | data/...
```

**data_coverage**: Rastreamento de cobertura (quais dias estão completos)
```sql
source  | symbol  | timeframe | date       | complete | row_count
--------|---------|-----------|------------|----------|----------
YAHOO   | AAPL    | 1d        | 2024-01-01 | TRUE     | 1
BINANCE | BTCUSDT | 1h        | 2024-01-15 | TRUE     | 24
```

## 💻 Uso Programático

### Python API

```python
from engines.data_engine import DataEngine

# Inicializar com cache habilitado
engine = DataEngine(use_cache=True)

# Buscar dados (cache automático)
df = engine.get_ohlcv_cached(
    source='yahoo',
    symbol='AAPL',
    timeframe='1d',
    start='2020-01-01',
    end='2023-12-31'
)

# Ver informações do cache
coverage = engine.get_coverage_info()
print(coverage)

# Limpar cache
engine.clear_cache(source='YAHOO', symbol='AAPL')
```

### Exemplo Completo

```python
from engines.data_engine import DataEngine

# Setup
engine = DataEngine(use_cache=True)

# Primeira chamada: busca da API
print("Primeira chamada (API)...")
df1 = engine.get_ohlcv_cached(
    source='binance',
    symbol='BTCUSDT',
    timeframe='1h',
    start='2024-01-01',
    end='2024-01-10'
)
# Output: Fetching... ✓ Saved 240 rows

# Segunda chamada: 100% local
print("\nSegunda chamada (cache)...")
df2 = engine.get_ohlcv_cached(
    source='binance',
    symbol='BTCUSDT',
    timeframe='1h',
    start='2024-01-01',
    end='2024-01-10'
)
# Output: ✓ Loaded 240 rows from cache

# Extender período: busca só o que falta
print("\nTerceira chamada (parcial)...")
df3 = engine.get_ohlcv_cached(
    source='binance',
    symbol='BTCUSDT',
    timeframe='1h',
    start='2024-01-01',
    end='2024-01-20'
)
# Output: Missing 10 days, fetching...
#         ✓ Loaded 480 rows from cache
```

## 🎯 Casos de Uso

### Backtesting com Múltiplos Símbolos

```python
symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
engine = DataEngine(use_cache=True)

for symbol in symbols:
    df = engine.get_ohlcv_cached(
        source='yahoo',
        symbol=symbol,
        timeframe='1d',
        start='2020-01-01',
        end='2023-12-31'
    )
    # Primeira rodada: busca tudo
    # Rodadas seguintes: tudo do cache!
```

### Análise Multi-Timeframe

```python
symbol = 'BTCUSDT'
timeframes = ['5m', '15m', '1h', '4h', '1d']

for tf in timeframes:
    df = engine.get_ohlcv_cached(
        source='binance',
        symbol=symbol,
        timeframe=tf,
        start='2024-01-01',
        end='2024-01-31'
    )
    # Cada timeframe em cache separado
```

### Atualização Diária

```bash
# Cron job para atualizar dados diariamente
0 0 * * * cd /path/to/wawastock && python main.py get-cached --source yahoo --symbol AAPL --start 2020-01-01
```

Quando rodar, só busca o dia atual (se faltar).

## ⚙️ Configuração Avançada

### Personalizar Localização do Banco

```python
engine = DataEngine(
    db_path="meu_trader.duckdb",  # Customizar caminho
    use_cache=True
)
```

### Desabilitar Cache (modo legacy)

```python
# Para usar métodos antigos sem cache
engine = DataEngine(use_cache=False)
df = engine.fetch_from_source('yahoo', 'AAPL', ...)
```

### LocalDataStore Direto

```python
from engines.local_data_store import LocalDataStore
from engines.data_sources import YahooDataSource

# Usar store diretamente
store = LocalDataStore(
    duckdb_path="meu_banco.duckdb",
    base_dir="meus_dados"
)

client = YahooDataSource()

df = store.get_ohlcv(
    source='YAHOO',
    symbol='AAPL',
    timeframe='1d',
    start='2020-01-01',
    end='2023-12-31',
    client=client
)
```

## 📊 Performance

### Comparação: API vs Cache

| Operação | Tempo (API) | Tempo (Cache) | Speedup |
|----------|-------------|---------------|---------|
| 1 ano, 1d | ~2-5s | ~50ms | 40-100x |
| 1 mês, 1h | ~3-8s | ~100ms | 30-80x |
| 1 semana, 5m | ~5-10s | ~150ms | 33-66x |

### Tamanho de Armazenamento

Exemplo: BTCUSDT, 1 ano de dados

| Timeframe | Rows | Parquet Size | DuckDB Overhead |
|-----------|------|--------------|-----------------|
| 1d | 365 | ~15 KB | ~50 KB |
| 1h | 8,760 | ~350 KB | ~100 KB |
| 15m | 35,040 | ~1.4 MB | ~200 KB |
| 5m | 105,120 | ~4.2 MB | ~400 KB |
| 1m | 525,600 | ~21 MB | ~1 MB |

**Compressão**: Parquet comprime muito bem, ~10x menor que CSV.

## 🔍 Troubleshooting

### "No data found in cache"

Primeira vez buscando esses dados. É esperado.

### "Missing X days but no client provided"

Você pediu dados que não estão em cache, mas não passou client para buscar.

```python
# Errado
df = store.get_ohlcv('YAHOO', 'AAPL', '1d', '2024-01-01', '2024-01-31')

# Certo
from engines.data_sources import YahooDataSource
client = YahooDataSource()
df = store.get_ohlcv('YAHOO', 'AAPL', '1d', '2024-01-01', '2024-01-31', client=client)
```

### Cache corrompido

```bash
# Limpar e recriar
python main.py cache-clear
rm -rf data/parquet data/trader.duckdb
```

### Ver dados brutos do DuckDB

```python
import duckdb
conn = duckdb.connect('data/trader.duckdb')

# Ver arquivos
print(conn.execute("SELECT * FROM parquet_files").df())

# Ver cobertura
print(conn.execute("SELECT * FROM data_coverage ORDER BY date DESC").df())

conn.close()
```

## 🎓 Conceitos

### Por que por dia?

Dividir dados por dia facilita:
- **Granularidade ideal**: não muito pequeno, não muito grande
- **Atualizações incrementais**: adicionar dias novos sem reprocessar tudo
- **Queries eficientes**: DuckDB pode pular dias inteiros se não necessários
- **Manutenção simples**: fácil deletar/reprocessar dias específicos

### Por que DuckDB?

- **Zero configuração**: arquivo único, sem servidor
- **Extremamente rápido**: lê Parquet nativamente
- **SQL completo**: queries complexas quando precisar
- **Integração pandas**: converte para DataFrame instantaneamente

### Por que Parquet?

- **Compressão excelente**: 10x menor que CSV
- **Leitura seletiva**: lê só colunas necessárias
- **Tipos preservados**: datetime, float mantém precisão
- **Padrão da indústria**: compatível com Spark, Arrow, etc.

## 🔄 Workflow Recomendado

1. **Desenvolvimento**: Use cache para iterar rápido
   ```python
   # Busca uma vez, testa 100 vezes
   df = engine.get_ohlcv_cached('yahoo', 'AAPL', '1d', '2020-01-01', '2023-12-31')
   ```

2. **Produção**: Atualize cache em schedule
   ```bash
   # Cron diário
   0 1 * * * python main.py get-cached --source yahoo --symbol AAPL
   ```

3. **Pesquisa**: Organize por projeto
   ```python
   # Projeto 1
   engine1 = DataEngine(db_path="projeto1.duckdb")
   
   # Projeto 2
   engine2 = DataEngine(db_path="projeto2.duckdb")
   ```

4. **Compartilhamento**: Commite o banco (pequeno!)
   ```bash
   # .gitignore: NÃO ignore .duckdb
   # É só índice, não dados crus
   git add data/trader.duckdb
   ```

---

**Próximos Passos**: Ver [README.md](README.md) para uso completo do framework.
