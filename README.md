# Backtesting Framework

Mini framework de backtesting em Python usando `backtrader`, `duckdb` e Parquet para análise de estratégias de trading.

## 📁 Estrutura do Projeto

```
wawastock/
├── main.py                           # CLI principal
├── engines/                          # Motores do framework
│   ├── __init__.py
│   ├── base_engine.py               # Classe base para engines
│   ├── data_engine.py               # Carregamento de dados (Parquet + DuckDB)
│   └── backtest_engine.py           # Execução de backtests (Backtrader)
├── strategies/                       # Estratégias de trading
│   ├── __init__.py
│   ├── base_strategy.py             # Classe base para strategies
│   └── sample_sma_strategy.py       # Exemplo: SMA Crossover
├── recipes/                          # Workflows de backtesting
│   ├── __init__.py
│   ├── base_recipe.py               # Classe base para recipes
│   └── sample_recipe.py             # Exemplo de recipe
└── data/                             # Dados de mercado
    ├── raw/                          # Dados brutos
    └── processed/                    # Dados processados (Parquet)
```

## 🚀 Instalação

### 1. Ativar o ambiente virtual

```bash
source venv/bin/activate
```

### 2. Instalar dependências

**Dependências mínimas (backtest local):**
```bash
pip install backtrader pandas pyarrow duckdb
```

**Todas as dependências (incluindo fontes de dados):**
```bash
pip install -r requirements.txt
```

**Ou instalar fontes de dados específicas:**
```bash
# Yahoo Finance (ações, ETFs, índices, forex, crypto)
pip install yfinance

# Binance (cryptocurrency)
pip install python-binance

# Alpaca (ações US)
pip install alpaca-py

# CCXT (100+ exchanges)
pip install ccxt
```

## 📡 Fontes de Dados

O framework suporta múltiplas fontes de dados:

### Yahoo Finance
- **Tipos**: Ações, ETFs, Índices, Forex, Crypto
- **Exemplos**: AAPL, SPY, ^GSPC, EURUSD=X, BTC-USD
- **API Key**: Não requerida
- **Intervalos**: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo

### Binance
- **Tipos**: Cryptocurrency (spot)
- **Exemplos**: BTCUSDT, ETHUSDT, BNBUSDT
- **API Key**: Opcional (pública para dados históricos)
- **Intervalos**: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M

### Alpaca
- **Tipos**: Ações US
- **Exemplos**: AAPL, TSLA, SPY
- **API Key**: Requerida (tier gratuito disponível)
- **Intervalos**: 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M
- **Registro**: https://alpaca.markets

### CCXT
- **Tipos**: 100+ exchanges de crypto
- **Exchanges**: Binance, Coinbase, Kraken, Bybit, KuCoin, etc.
- **Exemplos**: BTC/USDT, ETH/USD, BNB/BTC
- **API Key**: Opcional (pública para dados históricos)
- **Intervalos**: Variam por exchange

## 📊 Formato dos Dados

Os arquivos Parquet devem conter as seguintes colunas:

- `datetime`: timestamp (índice)
- `open`: preço de abertura (float)
- `high`: preço máximo (float)
- `low`: preço mínimo (float)
- `close`: preço de fechamento (float)
- `volume`: volume negociado (numeric)

Exemplo de estrutura:
```
data/
├── raw/
│   └── binance/
│       └── BTCUSDT/
│           └── data.parquet
└── processed/
    ├── TEST.parquet
    ├── AAPL.parquet
    └── BTCUSDT.parquet
```

## 💻 Uso da CLI

### Buscar dados de fontes externas

```bash
# Yahoo Finance - Ações
python main.py fetch-data --source yahoo --symbol AAPL --start 2020-01-01 --end 2023-12-31

# Yahoo Finance - Crypto
python main.py fetch-data --source yahoo --symbol BTC-USD --start 2022-01-01 --interval 1d

# Binance - Crypto
python main.py fetch-data --source binance --symbol BTCUSDT --start 2023-01-01 --interval 1h

# CCXT - Qualquer exchange
python main.py fetch-data --source ccxt --exchange kraken --symbol BTC/USD --start 2023-01-01

# CCXT - Binance via CCXT
python main.py fetch-data --source ccxt --exchange binance --symbol ETH/USDT --interval 4h

# Alpaca - Ações US (requer API key)
python main.py fetch-data --source alpaca --symbol TSLA \
  --api-key YOUR_API_KEY \
  --api-secret YOUR_API_SECRET \
  --start 2023-01-01 --end 2023-12-31
```

### Listar comandos disponíveis

```bash
python main.py --help
```

### Executar uma recipe

```bash
# Recipe padrão
python main.py run-recipe --name sample

# Recipe com parâmetros customizados
python main.py run-recipe --name sample --symbol AAPL --start 2020-01-01 --end 2020-12-31

# Recipe com capital e comissão customizados
python main.py run-recipe --name sample --symbol TEST --cash 50000 --commission 0.002
```

### Executar uma estratégia diretamente

```bash
# Estratégia básica
python main.py run-strategy --strategy sample_sma --symbol TEST --start 2020-01-01 --end 2020-12-31

# Estratégia com parâmetros customizados
python main.py run-strategy --strategy sample_sma --symbol AAPL --fast 5 --slow 15

# Estratégia com capital e comissão customizados
python main.py run-strategy --strategy sample_sma --symbol TEST --cash 200000 --commission 0.0005
```

## 🔧 Componentes

### Engines

**DataEngine**: Carrega e consulta dados de arquivos Parquet usando DuckDB
- `load_prices(symbol, start, end)`: Carrega dados OHLCV para um símbolo
- `load_parquet_table(path)`: Carrega arquivo Parquet como relação DuckDB

**BacktestEngine**: Executa backtests usando Backtrader
- `run_backtest(strategy_cls, data_df, **params)`: Executa backtest de uma estratégia
- Inclui analyzers: Sharpe Ratio, Drawdown, Returns

### Strategies

**BaseStrategy**: Classe base com funcionalidades comuns
- Logging de eventos
- Notificações de ordens e trades

**SampleSMAStrategy**: Estratégia de crossover de médias móveis
- Parâmetros: `fast_period` (padrão: 10), `slow_period` (padrão: 20)
- Compra: quando SMA rápida cruza acima da lenta
- Vende: quando SMA rápida cruza abaixo da lenta

### Recipes

**BaseRecipe**: Classe base para coordenar workflows
- Recebe DataEngine e BacktestEngine
- Define método abstrato `run()`

**SampleRecipe**: Exemplo de workflow completo
- Carrega dados para um símbolo
- Executa SampleSMAStrategy
- Exibe resultados formatados

## 🎯 Criando Novas Estratégias

```python
from strategies.base_strategy import BaseStrategy
import backtrader as bt

class MinhaEstrategia(BaseStrategy):
    params = (
        ('periodo', 14),
    )
    
    def __init__(self):
        self.indicador = bt.indicators.RSI(period=self.params.periodo)
    
    def next(self):
        if not self.position:
            if self.indicador < 30:  # Sobrevenda
                self.buy()
        else:
            if self.indicador > 70:  # Sobrecompra
                self.sell()
```

Depois, registre em `main.py`:

```python
STRATEGY_REGISTRY = {
    'sample_sma': SampleSMAStrategy,
    'minha_estrategia': MinhaEstrategia,  # Adicionar aqui
}
```

## 🎯 Criando Novas Recipes

```python
from recipes.base_recipe import BaseRecipe
from strategies.minha_estrategia import MinhaEstrategia

class MinhaRecipe(BaseRecipe):
    def run(self, symbol='TEST', start='2020-01-01', end='2020-12-31'):
        print(f"Executando backtest para {symbol}...")
        
        # Carregar dados
        data = self.data_engine.load_prices(symbol, start, end)
        
        # Executar backtest
        results = self.backtest_engine.run_backtest(
            MinhaEstrategia,
            data,
            periodo=14
        )
        
        # Exibir resultados
        print(f"Retorno: {results['return_pct']:.2f}%")
```

Registre em `main.py`:

```python
RECIPE_REGISTRY = {
    'sample': SampleRecipe,
    'minha_recipe': MinhaRecipe,  # Adicionar aqui
}
```

## 📈 Exemplo de Saída

```
================================================================================
SAMPLE RECIPE: SMA Crossover Strategy
================================================================================
Symbol: TEST
Period: 2020-01-01 to 2020-12-31
Strategy: SMA Crossover (Fast: 10, Slow: 20)
================================================================================

Loading data for TEST...
Loaded 252 bars of data

Running backtest...

Starting Portfolio Value: $100,000.00
2020-03-15 BUY SIGNAL, Fast SMA: 245.32, Slow SMA: 243.10
2020-03-15 BUY EXECUTED, Price: 246.50, Cost: 24650.00, Comm: 24.65
...
Final Portfolio Value: $112,450.00
PnL: $12,450.00 (12.45%)

================================================================================
BACKTEST RESULTS
================================================================================
Initial Portfolio Value: $100,000.00
Final Portfolio Value:   $112,450.00
Profit/Loss:             $12,450.00
Return:                  12.45%

Performance Metrics:
--------------------------------------------------------------------------------
Sharpe Ratio:            1.234
Max Drawdown:            -8.50%
Total Return:            12.45%
================================================================================
```

## 📚 Próximos Passos

1. Adicionar mais estratégias (RSI, Bollinger Bands, etc.)
2. Criar recipes para otimização de parâmetros
3. Adicionar suporte para múltiplos símbolos
4. Implementar walk-forward analysis
5. Adicionar visualizações (gráficos)

## 📝 Licença

Projeto educacional - use como base para seus próprios backtests.
