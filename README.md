# WawaStock Backtesting Framework

Professional-grade Python backtesting toolkit powered by `backtrader`, `duckdb`, `pandas`, and Streamlit. WawaStock bundles data ingestion, indicator enrichment, rich CLI reporting, and a multi-page UI so you can go from raw candles to strategy insights in minutes.

## Why WawaStock?

- **Composable engines** – `DataEngine`, `BacktestEngine`, `IndicatorsEngine`, and `ReportEngine` keep responsibilities separated and easy to extend.
- **Strategy library** – Five tiered strategies (RSI → Multi-Timeframe momentum) with ready-made recipes and parameter presets.
- **Local-first storage** – Parquet + DuckDB cache, optional DuckDB-backed indicators, and scripts to download equities or crypto from Yahoo, Binance, CCXT, and Alpaca.
- **Rich DX** – Loguru + Rich for structured logs, colorized CLI panels, and progress bars.
- **Modern UI** – Streamlit dashboards (`start.sh`) with metrics, charts, trade logs, and recipe controls.

## Architecture at a Glance

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| Engines | Execution primitives | `engines/base_engine.py`, `data_engine.py`, `backtest_engine.py`, `indicators_engine.py`, `report_engine.py` |
| Strategies | Trading logic (inherits `BaseStrategy`) | `strategies/*.py` |
| Recipes | Orchestrated workflows combining engines + strategies | `recipes/*.py` |
| CLI & Scripts | `main.py`, `scripts/*.py` for data download and summaries | |
| UI | Streamlit app + components under `streamlit_pages/` and `streamlit_components/` | |

## Installation & Environment

### 1. Automated setup (recommended)

```bash
./setup.sh        # macOS / Linux
setup.bat         # Windows
```

The script checks Python ≥3.8, creates `venv/`, installs `requirements.txt`, seeds data folders, and validates backtrader/DuckDB availability.

### 2. Manual steps (if you prefer)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
mkdir -p data/processed data/parquet logs
```

> Need extra data sources? Install targeted packages (e.g., `pip install yfinance ccxt python-binance alpaca-py`).

## Quickstart Workflow

1. **Activate the virtual environment** (see above).
2. **Run the sample recipe** to confirm everything works:
   ```bash
   python main.py run-recipe --name sample --symbol AAPL --start 2022-01-01 --end 2022-12-31
   ```
3. **Launch the Streamlit UI** for dashboards:
   ```bash
   ./start.sh      # or start.bat
   ```
4. **Download data** via CLI or scripts (see “Data ingestion”).

Troubleshooting tip: DuckDB allows a single writer. Close the Streamlit app before launching long CLI jobs, or use the OS scripts to avoid overlapping processes.

## Running Recipes vs. Strategies

Recipes wrap a full workflow (data load → indicators → backtest → report). Strategies give direct control over parameters. All commands share these global flags: `--symbol`, `--start`, `--end`, `--cash`, `--commission`.

```bash
# List help
python main.py --help
python main.py run-recipe --help
python main.py run-strategy --help

# Recipes
python main.py run-recipe --name rsi --symbol AAPL
python main.py run-recipe --name macd_ema --symbol MSFT --start 2020-01-01 --end 2023-12-31

# Strategies directly
python main.py run-strategy --strategy bollinger_rsi --symbol NVDA --rsi_period 10 --risk_per_trade 0.03
python main.py run-strategy --strategy multi_timeframe --symbol TSLA --cash 250000 --commission 0.0005
```

Backtest output is standardized by `ReportEngine` using Rich panels, tables, and analyzers (Sharpe, Drawdown, Total Return, trade stats). Logs are written to `logs/wawastock.log` via Loguru with rotation and compression.

## Streamlit Interface

- **Start**: `./start.sh` (macOS/Linux) or `start.bat` (Windows).
- **Pages**: Backtest runner, Data Explorer, Strategy Builder roadmap, Performance Analysis, Data Manager (see `docs/STREAMLIT_PLAN.md`).
- **Bridge**: Streamlit calls `run_recipe_programmatic()` in `main.py`, ensuring the same engines run behind the scenes.
- **Features**: parameter forms, live metrics cards, Plotly charts (equity, price + indicators, drawdown), trade tables, CSV export.

## Data Ingestion & Indicators

```bash
# Yahoo Finance
python main.py fetch-data --source yahoo --symbol AAPL --start 2020-01-01 --end 2024-01-01 --interval 1d

# Binance spot
python main.py fetch-data --source binance --symbol BTCUSDT --interval 1h --start 2023-01-01

# CCXT (any exchange)
python main.py fetch-data --source ccxt --exchange kraken --symbol ETH/USD --interval 4h

# Alpaca (US equities, requires keys)
python main.py fetch-data --source alpaca --symbol TSLA --api-key $ALPACA_KEY --api-secret $ALPACA_SECRET
```

`DataEngine` stores candles as Parquet and exposes them via DuckDB. Enable automatic indicator enrichment when instantiating the engine (`auto_indicators=True`, `indicator_set='minimal|standard|full'`) to persist SMA/EMA/RSI/MACD/Bollinger/ATR/VWAP/etc. See `docs/INDICATORS.md` for the full catalog.

## Strategy Library Snapshot

| Strategy | Recipe | Level | Ideal Market | Highlights |
|----------|--------|-------|--------------|------------|
| `rsi_strategy.py` | `recipes/rsi_recipe.py` | ⭐ Basic | Range-bound equities | RSI 14 mean reversion, fixed stop loss |
| `macd_ema_strategy.py` | `recipes/macd_ema_recipe.py` | ⭐⭐ Intermediate | Trending stocks | MACD crossover + 200 EMA filter, trailing stop |
| `bollinger_rsi_strategy.py` | `recipes/bollinger_rsi_recipe.py` | ⭐⭐⭐ Advanced | Volatile names | ATR position sizing, partial exits, BB + RSI filter |
| `multi_timeframe_strategy.py` | `recipes/multi_timeframe_recipe.py` | ⭐⭐⭐⭐ Maximum | Pro momentum | Multi-timeframe EMA alignment, ADX/RSI/volume filters, pyramiding |
| `sample_sma_strategy.py` | `recipes/sample_recipe.py` | Tutorial | Learning | Simple SMA crossover baseline |

Detailed playbooks live in `docs/STRATEGIES.md` (parameters, analyzer metrics, tuning tips).

## Logging & Reporting

- `utils/logger.py` centralizes Loguru configuration (rotation every 10 MB, 7-day retention, Rich colorization).
- `ReportEngine` handles CLI UX: headers, status badges, data summaries, analyzer tables, and error panels. All recipes are migrated—any new workflow should instantiate `ReportEngine` for consistent output (see `docs/REPORT_ENGINE_MIGRATION.md`).

## Documentation Map

| Guide | Purpose |
|-------|---------|
| `QUICKSTART_SETUP.md` | First-time setup scripts, environment troubleshooting |
| `QUICKSTART.md` | How to run and compare the five bundled strategies |
| `docs/STRATEGIES.md` | Deep dive into logic, parameters, performance tips |
| `docs/INDICATORS.md` | Using `IndicatorsEngine` + pandas-ta integration |
| `docs/LOGGING.md` | Loguru/Rich integration details |
| `docs/IMPLEMENTATION_SUMMARY.md` | Platform internals & recent upgrades |
| `docs/STREAMLIT_PLAN.md` | Streamlit roadmap and page breakdown |
| `docs/REPORT_ENGINE_MIGRATION.md` | How CLI output became standardized |

## Next Steps & Ideas

- Add walk-forward analysis recipes and optimization loops.
- Expand Streamlit “Strategy Builder” with drag-and-drop and embedded code editor.
- Support multi-symbol portfolios and blended recipes.
- Ship report exports (PDF/HTML) via `ReportEngine` and Streamlit download buttons.

## License

Educational use only—adapt freely for your own research and backtests.
