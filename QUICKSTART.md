# Strategy Quick Start

This guide assumes you have already completed the environment setup in `QUICKSTART_SETUP.md`. Below is everything you need to start running, comparing, and iterating on the five bundled strategies.

## 1. Prep Checklist

1. Activate the virtual environment (`source venv/bin/activate` on macOS/Linux or `venv\Scripts\activate` on Windows).
2. Ensure you have at least one processed Parquet file under `data/processed/` (use `python main.py fetch-data ...` or the scripts in `scripts/`).
3. Decide whether you want the CLI or Streamlit UI:
   - CLI → `python main.py run-recipe ...`
   - UI → `./start.sh` (launches Streamlit with backtest pages)

## 2. Recipe-first (Recommended)

Recipes encapsulate data loading, indicator enrichment, backtesting, analyzers, and reporting. Run any recipe with just a symbol (defaults cover the rest):

```bash
python main.py run-recipe --name rsi --symbol AAPL
python main.py run-recipe --name macd_ema --symbol MSFT --start 2021-01-01 --end 2023-12-31
python main.py run-recipe --name bollinger_rsi --symbol NVDA --risk_per_trade 0.03
python main.py run-recipe --name multi_timeframe --symbol TSLA --cash 150000 --commission 0.0005
python main.py run-recipe --name sample --symbol TEST
```

Each run prints a Rich-formatted report (header, parameters, data summary, analyzer metrics). Results are also logged to `logs/wawastock.log`.

## 3. Strategy-only Runs

Need bespoke parameters or want to iterate quickly? Call strategies directly:

```bash
python main.py run-strategy --strategy rsi --symbol AAPL --start 2020-01-01 --end 2023-12-31 --rsi_period 10 --oversold 25 --overbought 75
python main.py run-strategy --strategy bollinger_rsi --symbol TSLA --bb_period 30 --bb_dev 2.5 --risk_per_trade 0.015
python main.py run-strategy --strategy multi_timeframe --symbol NVDA --allow_pyramid False --adx_threshold 30
```

Strategy runs share the same analyzers as recipes; you simply control the parameter map yourself.

## 4. Strategy Matrix

| Recipe / Strategy | Level | Ideal Use Case | Key Parameters | Files |
|-------------------|-------|----------------|----------------|-------|
| `rsi` | ⭐ Basic | Mean reversion learners | `rsi_period`, `oversold`, `overbought`, `stop_loss_pct` | `recipes/rsi_recipe.py`, `strategies/rsi_strategy.py` |
| `macd_ema` | ⭐⭐ Intermediate | Trending stocks / ETFs | `trend_ema`, `position_size_pct`, `trail_pct` | `recipes/macd_ema_recipe.py`, `strategies/macd_ema_strategy.py` |
| `bollinger_rsi` | ⭐⭐⭐ Advanced | Volatile names needing ATR position sizing | `bb_period`, `bb_dev`, `risk_per_trade`, `partial_take_profit` | `recipes/bollinger_rsi_recipe.py`, `strategies/bollinger_rsi_strategy.py` |
| `multi_timeframe` | ⭐⭐⭐⭐ Maximum | Professional momentum + pyramiding | `allow_pyramid`, `pyramid_units`, `adx_threshold`, `profit_target_atr`, `trail_pct` | `recipes/multi_timeframe_recipe.py`, `strategies/multi_timeframe_strategy.py` |
| `sample` | Tutorial | SMA crossover baseline / onboarding | `fast_period`, `slow_period` | `recipes/sample_recipe.py`, `strategies/sample_sma_strategy.py` |

For deeper indicator logic and tuning tips, see `docs/STRATEGIES.md`.

## 5. Battle-tested Workflows

### Compare strategies on the same symbol

```bash
python main.py run-recipe --name rsi --symbol AAPL --start 2022-01-01 --end 2023-12-31
python main.py run-recipe --name macd_ema --symbol AAPL --start 2022-01-01 --end 2023-12-31
python main.py run-recipe --name bollinger_rsi --symbol AAPL --start 2022-01-01 --end 2023-12-31
python main.py run-recipe --name multi_timeframe --symbol AAPL --start 2022-01-01 --end 2023-12-31
```

### Regime testing

```bash
# Pandemic rally vs. post-inflation period
python main.py run-recipe --name multi_timeframe --symbol NVDA --start 2020-03-01 --end 2021-12-31
python main.py run-recipe --name multi_timeframe --symbol NVDA --start 2022-01-01 --end 2023-12-31
```

### Asset-type rotation

```bash
# Trending tech
python main.py run-recipe --name macd_ema --symbol MSFT

# Volatile meme stock
python main.py run-recipe --name rsi --symbol GME

# Crypto momentum
python main.py run-recipe --name multi_timeframe --symbol BTCUSDT --start 2021-01-01 --end 2023-12-31
```

## 6. Streamlit Shortcut

Prefer point-and-click? Launch Streamlit and use the Backtest Runner page:

```bash
./start.sh     # Opens http://localhost:8502 with prebuilt forms, metrics, and charts
```

Each Streamlit run internally calls the same engines through `run_recipe_programmatic`, so results match the CLI.

## 7. Helpful Commands & Tips

- `python main.py list-recipes` *(if you add a helper command)* or inspect `main.py` → `RECIPE_REGISTRY` for names.
- `python main.py fetch-data --help` to view all data-source flags.
- Close Streamlit before running long CLI jobs to avoid DuckDB locks.
- Use processed symbols like `AAPL`, `MSFT`, or `BTCUSDT` first; they have complete sample data.
- Logs live at `logs/wawastock.log`; tail them when iterating on strategy code.

## 8. Where to Go Next

- Dive into `docs/STRATEGIES.md` for equations, indicator combos, and tuning heuristics.
- Skim `docs/LOGGING.md` to extend ReportEngine/Loguru output.
- Use `scripts/show_data_summary.py` to inspect processed data before testing.

Happy backtesting! 🚀
