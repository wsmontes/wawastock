# Technical Indicators & `IndicatorsEngine`

WawaStock ships with automatic indicator enrichment powered by `pandas-ta`. The `IndicatorsEngine` sits between raw data ingestion and storage so every strategy (CLI or Streamlit) can rely on precomputed features without rewriting indicator math.

## Architecture

1. **`IndicatorsEngine` (`engines/indicators_engine.py`)**
   - Builds indicator columns on a pandas DataFrame using curated presets.
   - Runs immediately after new candles are fetched or before they are saved back to Parquet/DuckDB.
   - Decoupled from any specific data source—works with Yahoo, Binance, CCXT, Alpaca, or custom imports.

2. **`DataEngine` Integration (`engines/data_engine.py`)**
   - `auto_indicators` (bool, default `False`): toggles automatic calculations on every `load_prices`/fetch.
   - `indicator_set` (str): chooses the preset (`minimal`, `standard`, `full`, or a custom list).
   - When enabled, indicator columns are persisted to Parquet so future loads are instantaneous.

## Configuration Examples

```python
from engines.data_engine import DataEngine

# Standard preset (recommended)
engine = DataEngine(auto_indicators=True)
df = engine.load_prices('AAPL', start='2023-01-01', end='2023-12-31')

# Minimal indicators only
engine = DataEngine(auto_indicators=True, indicator_set='minimal')

# Full preset or custom list
engine = DataEngine(
  auto_indicators=True,
  indicator_set='full',
)

# Manual override
engine = DataEngine(auto_indicators=True, indicator_set=['SMA_20', 'EMA_55', 'RSI_14'])
```

Disable enrichment at any time to keep legacy workflows untouched:

```python
engine = DataEngine(auto_indicators=False)
df = engine.load_prices('MSFT')  # Only OHLCV columns
```

## Preset Catalog

| Preset | Contents |
|--------|----------|
| `minimal` | `SMA_20`, `SMA_50`, `RSI_14` |
| `standard` *(default)* | All minimal indicators plus `EMA_12/26`, MACD set, Bollinger Bands, `ATR_14`, Stochastic (`STOCH_kd`), `OBV` |
| `full` | Standard set plus EMA 9/21/55, `ADX_14`, `VWAP`, `CCI`, `Williams %R`, more exotic pandas-ta signals |

Add or edit presets inside `engines/indicators_engine.py` by updating the registry dictionary.

## Persistence & Performance

- **Parquet-first**: Indicator columns are stored alongside OHLCV data (`data/processed/<SYMBOL>.parquet`). Subsequent calls to `load_prices` simply read from disk.
- **DuckDB-ready**: Since all columns live inside the same Parquet files, DuckDB queries (e.g., in Streamlit Data Explorer) can use `SMA_50`, `RSI_14`, etc. directly.
- **Duplicate detection**: The engine checks columns before computing new features, avoiding recalculations and duplicate names.
- **One-time compute**: Most presets finish within milliseconds per symbol thanks to pandas-ta vectorization.

## Using Indicators in Strategies

```python
import backtrader as bt
from strategies.base_strategy import BaseStrategy

class MyIndicatorStrategy(BaseStrategy):
  def __init__(self):
    # Data columns already include indicators
    self.sma_fast = self.datas[0].SMA_20
    self.sma_slow = self.datas[0].SMA_50
    self.rsi = self.datas[0].RSI_14

  def next(self):
    if not self.position and self.sma_fast[0] > self.sma_slow[0] and self.rsi[0] > 55:
      self.buy()
```

Backtrader automatically exposes DataFrame columns as attributes when `BacktestEngine` feeds data into Cerebro. No need to instantiate indicators inside each strategy unless you want intrabar calculations.

## Streamlit & Indicators

- **Data Explorer page** toggles show/hide controls for SMA, EMA, Bollinger, RSI, MACD, etc., all sourced from the same Parquet columns.
- **Backtest Runner** forms respect preset choices by passing flags through `run_recipe_programmatic` → `DataEngine`.
- Clearing/recomputing indicators can be done via a future “Data Manager” action; for now rerun `python main.py fetch-data ...` with `auto_indicators=True` or manually delete the symbol’s Parquet file.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Indicator columns missing | `auto_indicators=False` or preset not set | Recreate `DataEngine` with `auto_indicators=True` and reload data |
| Columns duplicated (e.g., two `SMA_20`) | Custom scripts appended indicators manually | Delete Parquet file or drop duplicate columns before saving |
| pandas-ta import error | Dependency not installed in env | Run `pip install pandas-ta` (already in `requirements.txt`) |
| Unexpected NaNs | Not enough rows for lookback | Ensure your dataset spans at least `max_lookback` bars (e.g., 200 candles for SMA_200) |

## Extending the Engine

1. Open `engines/indicators_engine.py` and add a new entry to `INDICATOR_SETS` or create a helper function for custom logic.
2. Reference pandas-ta docs for function names (e.g., `ta.vortex`, `ta.kama`).
3. When adding indicators that require parameters, pass them via the helper (see existing ATR/MACD usage).
4. Update this document’s catalog plus README/Streamlit forms if the indicator should be user-toggleable.

## Example End-to-end Flow

```python
from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.rsi_strategy import RSIStrategy

data_engine = DataEngine(auto_indicators=True, indicator_set='standard')
backtest_engine = BacktestEngine()

df = data_engine.load_prices('NVDA', start='2022-01-01', end='2023-12-31')

results = backtest_engine.run_backtest(RSIStrategy, df, symbol='NVDA')
print(results['analyzers']['sharpe'])
```

Indicators are baked into `df`, consumed by the strategy, and summarized by `ReportEngine` without extra ceremony.
