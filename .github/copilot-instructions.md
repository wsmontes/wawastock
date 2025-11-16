# Copilot Instructions - WawaStock Backtesting Framework

## Project Overview
Python backtesting framework using `backtrader`, `duckdb`, and Parquet for trading strategy analysis.

## Architecture Patterns

### Core Components
- **Engines**: Task-specific components (data loading, backtest execution)
  - All engines inherit from `BaseEngine` and implement `run()`
  - `DataEngine`: Parquet/DuckDB data operations
  - `BacktestEngine`: Backtrader execution wrapper

- **Strategies**: Trading logic implementations
  - Inherit from `BaseStrategy` (extends `backtrader.Strategy`)
  - Implement `__init__` for indicators, `next()` for trading logic
  - Use `self.log()` for consistent logging

- **Recipes**: Complete backtest workflows
  - Inherit from `BaseRecipe` and implement `run()`
  - Combine DataEngine, BacktestEngine, and Strategies
  - Register in `main.py` RECIPE_REGISTRY

### Data Storage
- Raw data: `data/parquet/candles/{SOURCE}/{SYMBOL}/{TIMEFRAME}/{YEAR}/`
- Processed data: `data/processed/`
- Database: `data/trader.duckdb`

## Code Style

### General
- Use type hints for function parameters and returns
- Docstrings: Google style with Args/Returns sections
- Keep abstractions simple and focused

### Strategy Development
```python
class MyStrategy(BaseStrategy):
    params = (('period', 20),)  # Use params tuple
    
    def __init__(self):
        self.indicator = bt.indicators.SMA(self.data.close, period=self.params.period)
    
    def next(self):
        # Trading logic here
        if self.indicator > self.data.close:
            self.buy()
```

### Engine Development
- Engines manage single responsibilities (data, backtest, optimization)
- Always inherit from `BaseEngine`
- Implement `run()` method for execution

### Recipe Development
- Recipes orchestrate engines and strategies
- Initialize engines in `__init__`, execute in `run()`
- Register new recipes in `main.py`

## CLI Usage
- `python main.py recipe <name>` - Run predefined recipe
- `python main.py strategy <name>` - Run strategy directly
- All strategies/recipes must be registered in `main.py`

## Dependencies
- Core: `backtrader`, `pandas`, `pyarrow`, `duckdb`
- Data sources: `yfinance`, `alpaca-py`, `ccxt`, `binance`

## File Organization
- New strategies → `strategies/`
- New engines → `engines/`
- New recipes → `recipes/`
- Data sources → `engines/data_sources/`
