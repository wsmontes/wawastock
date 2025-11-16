# Strategy Playbook

Every trading strategy in WawaStock inherits from `BaseStrategy` (`strategies/base_strategy.py`) and is orchestrated through a matching recipe that wires the `DataEngine`, `IndicatorsEngine`, `BacktestEngine`, and `ReportEngine`. Use this document as your field guide for choosing, tuning, and extending the built-in playbook.

## Strategy Atlas

| Strategy | Complexity | Style | Best Market Context | Key Levers | Recipe / Files |
|----------|------------|-------|---------------------|------------|----------------|
| **Sample SMA** | Tutorial | Trend crossover | Education, smoke tests | `fast_period`, `slow_period` | `recipes/sample_recipe.py`, `strategies/sample_sma_strategy.py` |
| **RSI Mean Reversion** | ⭐ Basic | Oscillator bounce | Ranging equities / meme names | `rsi_period`, `oversold`, `overbought`, `stop_loss_pct` | `recipes/rsi_recipe.py`, `strategies/rsi_strategy.py` |
| **MACD + EMA Trend** | ⭐⭐ Intermediate | Momentum trend follow | Strong single-direction moves | `trend_ema`, `position_size_pct`, `trail_pct` | `recipes/macd_ema_recipe.py`, `strategies/macd_ema_strategy.py` |
| **Bollinger + RSI Pro** | ⭐⭐⭐ Advanced | Volatility mean reversion | Choppy/volatile, defined ranges | `bb_period`, `bb_dev`, `risk_per_trade`, `partial_take_profit` | `recipes/bollinger_rsi_recipe.py`, `strategies/bollinger_rsi_strategy.py` |
| **Multi-Timeframe Momentum** | ⭐⭐⭐⭐ Maximum | Institutional momentum | High-conviction trends (stocks/crypto) | `allow_pyramid`, `adx_threshold`, `profit_target_atr`, `trail_pct` | `recipes/multi_timeframe_recipe.py`, `strategies/multi_timeframe_strategy.py` |

> All recipes return Rich-formatted reports with analyzer stats (Sharpe, Max Drawdown, Win Rate, Total Trades) courtesy of `ReportEngine`.

---

## Shared Contract

- **Inputs**: OHLCV data from `DataEngine` (with optional indicator columns), optional CLI flags or Streamlit form values.
- **Outputs**: `BacktestEngine.run_backtest()` dictionary containing portfolio values, analyzer metrics, trade logs, and equity curve; automatically handed to `ReportEngine` for printouts and also surfaced to Streamlit via `run_recipe_programmatic()`.
- **Analyzers attached**: Sharpe Ratio, Max Drawdown, Annualized Return, Trade Analyzer (total/won/lost), Drawdown timeline. Extend analyzers in `engines/backtest_engine.py` if you need custom stats.

---

## Sample SMA Strategy (Onboarding)

- **Files**: `strategies/sample_sma_strategy.py`, `recipes/sample_recipe.py`
- **Concept**: Classic two SMA crossover (fast vs. slow) for smoke testing data ingestion and verifying CLI/UI wiring.

### Logic
- **Entry**: Fast SMA crosses above slow SMA and portfolio is flat.
- **Exit**: Fast SMA crosses below slow SMA or trailing stop from Backtrader hits.
- **Risk**: Uses `BacktestEngine` cash management & commission only; no ATR sizing.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fast_period` | 10 | Window for fast SMA |
| `slow_period` | 20 | Window for slow SMA |

### How to run

```bash
python main.py run-recipe --name sample --symbol TEST
python main.py run-strategy --strategy sample_sma --symbol AAPL --fast 5 --slow 30
```

> Streamlit: Choose “Sample SMA” from the recipe selector on the Backtest Runner page.

---

## RSI Mean Reversion (Basic)

- **Files**: `strategies/rsi_strategy.py`, `recipes/rsi_recipe.py`
- **Use case**: Learn oscillator-based entries, test meme or sideways tickers, or benchmark mean reversion logic.

### Logic & Risk
- **Entry**: RSI crosses up through `oversold`.
- **Exit**: RSI crosses down through `overbought` or stop loss hits.
- **Risk**: Fixed percentage stop per trade (`stop_loss_pct`). Position sizing uses available cash (no ATR sizing).

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `rsi_period` | 14 | Length for RSI calculation |
| `oversold` | 30 | Buy trigger level |
| `overbought` | 70 | Sell trigger level |
| `stop_loss_pct` | 0.02 | 2% fixed stop from entry |

### CLI / Streamlit

```bash
python main.py run-recipe --name rsi --symbol AAPL --start 2021-01-01 --end 2023-12-31
python main.py run-strategy --strategy rsi --symbol GME --oversold 25 --overbought 75
```

### Analyzer callouts
- Focus on Win Rate and Max Drawdown for sideways regimes.
- Sharpe remains modest; tune oversold/overbought to control trade frequency.

---

## MACD + EMA Trend (Intermediate)

- **Files**: `strategies/macd_ema_strategy.py`, `recipes/macd_ema_recipe.py`
- **Use case**: Catch larger moves in trending equities/ETFs with a strong long-term bias.

### Logic
1. Require price above `trend_ema` (default 200) for bullish bias.
2. Trigger entry when MACD line crosses above signal.
3. Exit on MACD cross-under or trailing stop hit (`trail_pct`). Position sizing uses a percentage of equity (`position_size_pct`).

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `macd_fast` / `macd_slow` / `macd_signal` | 12 / 26 / 9 | Standard MACD settings |
| `trend_ema` | 200 | Long-term trend filter |
| `position_size_pct` | 0.95 | Percent of cash per trade |
| `trail_pct` | 0.02 | Trailing stop once in profit |

### CLI / Streamlit

```bash
python main.py run-recipe --name macd_ema --symbol MSFT --start 2020-01-01 --end 2023-12-31
python main.py run-strategy --strategy macd_ema --symbol NVDA --trend_ema 250 --trail_pct 0.015
```

### Analyzer callouts
- Expect higher Sharpe and smoother equity curves in trending periods.
- Total trades stay low; inspect Trade Analyzer to ensure position sizing fits your risk tolerance.

---

## Bollinger + RSI Pro (Advanced)

- **Files**: `strategies/bollinger_rsi_strategy.py`, `recipes/bollinger_rsi_recipe.py`
- **Use case**: Professional-grade mean reversion with ATR-based sizing, partial exits, and multi-confirmation signals.

### Logic
- **Entry**: Price touches lower Bollinger Band (`bb_period`, `bb_dev`) AND RSI < `rsi_oversold`.
- **Partial Exit**: 50% position at middle band or RSI > 50.
- **Full Exit**: Upper band or RSI > `rsi_overbought`.
- **Risk/Sizing**: Use ATR (`atr_period`) to compute position size respecting `risk_per_trade`.
- **Protection**: Trailing stop engages after partial profits, ensuring downside containment.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `bb_period` / `bb_dev` | 20 / 2.0 | Bollinger lookback & standard deviations |
| `rsi_period` | 14 | RSI confirmation |
| `rsi_oversold` / `rsi_overbought` | 35 / 65 | Entry & exit gates |
| `atr_period` | 14 | ATR sizing window |
| `risk_per_trade` | 0.02 | 2% of equity per setup |
| `partial_take_profit` | 0.5 | 50% trim at first target |

### CLI / Streamlit

```bash
python main.py run-recipe --name bollinger_rsi --symbol TSLA --risk_per_trade 0.015
python main.py run-strategy --strategy bollinger_rsi --symbol NVDA --bb_dev 2.5 --partial_take_profit 0.3
```

### Analyzer callouts
- Watch Drawdown vs. Sharpe to ensure volatility is controlled.
- Trade Analyzer highlights win/loss asymmetry created by partial exits.

---

## Multi-Timeframe Momentum (Maximum)

- **Files**: `strategies/multi_timeframe_strategy.py`, `recipes/multi_timeframe_recipe.py`
- **Use case**: Institutional-style momentum with pyramiding, multi-filter confirmation, and strict risk governance; works well for top tech/ETF trends and crypto bull runs.

### Logic
1. Trend alignment: price above `trend_ema`, fast EMA > slow EMA.
2. Momentum confirmation: `RSI > rsi_entry_min`, `ADX > adx_threshold`, and volume above `volume_threshold` × 20-period average.
3. Entries staged with pyramiding (`pyramid_units`, `pyramid_spacing`).
4. Exit stack: ATR profit target, trailing stop after `trail_start_atr`, hard stop at `risk_per_trade`, max holding window (`max_hold_bars`).

### Parameters (highlights)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fast_ema` / `slow_ema` / `trend_ema` | 21 / 55 / 200 | Multi-timeframe EMAs |
| `adx_threshold` | 25 | Trend strength filter |
| `risk_per_trade` | 0.015 | 1.5% risk per leg |
| `allow_pyramid` / `pyramid_units` | True / 3 | Adds up to 3 positions |
| `profit_target_atr` / `trail_pct` | 3.0 / 0.02 | Exit matrix |
| `max_position_size` | 0.3 | Cap at 30% of equity |

### CLI / Streamlit

```bash
python main.py run-recipe --name multi_timeframe --symbol NVDA --start 2020-01-01 --end 2023-12-31
python main.py run-strategy --strategy multi_timeframe --symbol BTCUSDT --allow_pyramid False --risk_per_trade 0.01
```

### Analyzer callouts
- Expect higher Total Return but larger drawdown swings—monitor Sharpe vs. Max Drawdown.
- Trade Analyzer exposes the impact of pyramiding (won/lost counts, average win size).

---

## Using the Strategies

### CLI

```bash
python main.py run-recipe --name <recipe> --symbol <SYMBOL> [--start YYYY-MM-DD --end YYYY-MM-DD]
python main.py run-strategy --strategy <strategy> --symbol <SYMBOL> [--param value ...]
```

### Streamlit

Launch `./start.sh` and navigate to **📊 Backtest Runner** to:

1. Select a recipe from the sidebar list.
2. Fill symbol, timeframe, and advanced parameter sliders/forms.
3. Observe metrics cards, Plotly charts (price + indicators, equity, drawdown), and trade tables.
4. Download trades/equity as CSV for further analysis.

`StreamlitBridge` (`streamlit_components/bridge.py`) simply calls `run_recipe_programmatic`, so CLI and UI share identical engine behavior.

---

## Analyzer Reference

`BacktestEngine` registers the following analyzers by default:

| Analyzer | Meaning | Where it appears |
|----------|---------|------------------|
| Sharpe Ratio | Risk-adjusted return (`btanalyzers.SharpeRatio_A`) | ReportEngine tables, Streamlit metrics |
| Max Drawdown | Worst peak-to-trough decline | ReportEngine, Streamlit drawdown chart |
| Returns Analyzer | Total and annualized return percentages | ReportEngine, Streamlit cards |
| Trade Analyzer | Total trades, win/loss counts, streaks | CLI table + Streamlit trade summary |

Add more in `engines/backtest_engine.py` if your strategy demands additional stats (e.g., Sortino, Calmar).

---

## Tuning Checklist

1. **Data sanity** – use `scripts/show_data_summary.py` or the Streamlit Data Explorer to confirm there are no gaps/outliers.
2. **Indicator alignment** – if using precomputed indicators via `IndicatorsEngine`, confirm column names match your strategy (e.g., `SMA_20`).
3. **Parameter sweeps** – create lightweight scripts or Streamlit forms to loop through parameter grids; log outputs via `ReportEngine` for consistent comparison.
4. **Regime tests** – run each strategy across contrasting periods (bull/bear/sideways) to see stability.
5. **Risk sizing** – adjust `risk_per_trade`, `position_size_pct`, or `max_position_size` before touching entry logic; the analyzers will quickly show improved drawdowns.

---

## Extending the Library

1. Implement a new strategy in `strategies/` inheriting from `BaseStrategy`.
2. Build a recipe in `recipes/` that wires `DataEngine`, `BacktestEngine`, `ReportEngine`.
3. Register the recipe/strategy in `main.py` (`RECIPE_REGISTRY`, `STRATEGY_REGISTRY`).
4. Update this document’s Strategy Atlas and parameter table.
5. Optionally expose controls in Streamlit (form inputs + bridging layer).

With these guidelines, you can expand WawaStock’s playbook while keeping documentation, CLI, and Streamlit in sync.
