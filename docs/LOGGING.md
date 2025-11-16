# Logging, ReportEngine, and Rich UI

WawaStock layers **Loguru** (structured logging) with **Rich** (colorized terminal UX) to deliver consistent CLI output, Streamlit-friendly status updates, and rotating log files. `ReportEngine` ties everything together so every recipe emits the same professional presentation.

## Stack Overview

| Component | Purpose | Location |
|-----------|---------|----------|
| Loguru | Central logging with rotation/compression | `utils/logger.py` |
| Rich | Panels, tables, progress bars, colorized console | `engines/report_engine.py`, `main.py`, Streamlit helpers |
| ReportEngine | High-level presenter wrapping Rich + analyzers | `engines/report_engine.py` |

All dependencies ship via `requirements.txt`, so `./setup.sh` installs them automatically.

## Loguru Configuration

```python
from utils.logger import setup_logger, get_logger

setup_logger(
    level="INFO",
    log_file="logs/wawastock.log",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    colorize=True,
)

logger = get_logger(__name__)
```

- Log files live in `logs/wawastock.log` with automatic rotation every 10 MB and 7-day retention.
- Console output inherits Rich colorization for better readability.
- Every engine/strategy inherits `self.logger` from `BaseEngine` / `BaseStrategy`, so logging is available without boilerplate.

### Usage snapshots

```python
class DataEngine(BaseEngine):
    def load_prices(...):
        self.logger.info("Loading data for %s", symbol)
```

```python
class MyStrategy(BaseStrategy):
    def next(self):
        if self.data.close[0] > self.sma_fast[0]:
            self.logger.debug("Bullish crossover at %.2f", self.data.close[0])
            self.buy()
```

### Changing verbosity

```python
setup_logger(level="DEBUG")   # verbose dev mode
setup_logger(level="WARNING") # quieter production mode
```

## ReportEngine + Rich

`ReportEngine` standardizes CLI output for every recipe:

```python
from engines.report_engine import ReportEngine

report = ReportEngine()
report.print_strategy_header(
    strategy_name="MACD + EMA",
    symbol="MSFT",
    start="2020-01-01",
    end="2023-12-31",
    params={"trend_ema": 200, "trail_pct": 0.02}
)
report.print_step("Loading data...", status="info")
report.print_backtest_results(results_dict)
```

### Built-in helpers

| Method | Description |
|--------|-------------|
| `print_strategy_header` | Panel with symbol, period, cash, commission, parameters |
| `print_step(message, status)` | Status banner with icons (`info`, `success`, `warning`, `error`) |
| `print_data_summary(rows, start_date, end_date)` | Table summarizing loaded candles |
| `print_backtest_results(results)` | Two Rich tables: portfolio metrics + analyzer metrics |
| `print_error(title, message)` | Red panel used for exceptions |
| `create_progress_context(description)` | Context manager for Rich progress bars |

Any new recipe should instantiate `ReportEngine` inside `__init__` and replace raw `print()` calls with these helpers.

## Console & Streamlit Flow

1. **CLI (`main.py`)** uses Rich to display headers and parameter tables even before `ReportEngine` kicks in (e.g., direct strategy runs).
2. **Recipes** rely on `ReportEngine`, which internally logs to Loguru and prints to the console simultaneously.
3. **Streamlit** reuses `run_recipe_programmatic()`—log messages still go to `logs/wawastock.log`, while the UI shows progress spinners and metrics cards.

## Example CLI Session

```
╭──────────────────────────────╮
│ MACD + EMA TREND STRATEGY    │
╰──────────────────────────────╯

Symbol:        MSFT
Period:        2020-01-01 to 2023-12-31
Initial Cash:  $100,000.00
Commission:    0.100%

ℹ️  Loading data for MSFT...
✓   Loaded 756 bars (2020-01-02 → 2023-12-29)
ℹ️  Running backtest...

┌───────────────────────┬─────────────────┐
│ Initial Portfolio     │ $100,000.00     │
│ Final Portfolio       │ $143,552.14     │
│ Profit / Loss         │ $ 43,552.14     │
│ Total Return          │ 43.55%          │
└───────────────────────┴─────────────────┘

┌──────────────────┬───────────┐
│ Sharpe Ratio     │ 1.31      │
│ Max Drawdown     │ -8.4%     │
│ Total Trades     │ 18        │
│ Win Rate         │ 61%       │
└──────────────────┴───────────┘
```

All lines above are colored/styled automatically and simultaneously logged via Loguru.

## Customizing the Look & Feel

- **Disable color**: `setup_logger(colorize=False)` for plain console output (useful for CI).
- **Change format**: edit the `logger.add` call in `utils/logger.py` to customize timestamps, levels, or message templates.
- **New panels/tables**: extend `ReportEngine` with helper methods so every recipe benefits. Keep styling consistent (Rich `Panel`, `Table`, `box.ROUNDED`).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: loguru` | Re-run `./setup.sh` or `pip install -r requirements.txt`. |
| No logs written to file | Confirm the `logs/` directory exists (setup scripts create it) and that the process has write permissions. |
| Duplicate log lines | Ensure `setup_logger` is only called once at app start (already handled in `utils/logger.py`). |
| Garbled colors in CI | Set `colorize=False` or use `TERM=dumb`. |

## References

- [Loguru docs](https://loguru.readthedocs.io/)
- [Rich docs](https://rich.readthedocs.io/)
- `engines/report_engine.py` for concrete usage patterns

Leverage this stack to keep CLI runs, tests, and Streamlit jobs aligned with the same high-quality output.
