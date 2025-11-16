# ReportEngine Migration & Usage Guide

The `ReportEngine` now owns every piece of CLI output inside WawaStock. This document explains what changed, how to adopt the new pattern in future recipes, and how to customize the presentation.

## What Changed

### New Component
**`engines/report_engine.py`** centralizes:
- Rich-formatted tables, panels, and progress indicators
- Automatic Loguru logging (console + rotating file)
- Consistent status badges (info/success/warning/error)
- Analyzer rendering (Sharpe, drawdown, trade stats)

### Migrated Recipes
All shipping recipes call `ReportEngine`:

1. ✅ **rsi_recipe.py** - RSI Mean Reversion
2. ✅ **macd_ema_recipe.py** - MACD + EMA Trend Following  
3. ✅ **bollinger_rsi_recipe.py** - Bollinger Bands + RSI Mean Reversion
4. ✅ **multi_timeframe_recipe.py** - Multi-Timeframe Momentum with Pyramiding
5. ✅ **sample_recipe.py** - SMA Crossover Strategy

### Migration Pattern

**Before:**
```python
class MyRecipe(BaseRecipe):
    def run(self, ...):
        print("=" * 80)
        print("STRATEGY NAME")
        print("=" * 80)
        print(f"Symbol: {symbol}")
        # ... lots of print statements
```

**After:**
```python
from engines.report_engine import ReportEngine

class MyRecipe(BaseRecipe):
    def __init__(self, data_engine, backtest_engine):
        super().__init__(data_engine, backtest_engine)
        self.report = ReportEngine()
    
    def run(self, ...):
        # Professional formatted header with Rich panels
        self.report.print_strategy_header(
            strategy_name="Strategy Name",
            symbol=symbol,
            start=start,
            end=end,
            params={'key': 'value'}
        )
        
        # Status updates with icons and colors
        self.report.print_step("Loading data...", "info")
        
        # Data summary
        self.report.print_data_summary(rows=len(data), start_date=..., end_date=...)
        
        # Error handling with Rich panels
        self.report.print_error("Error title", "Error message")
        
        # Results table with color-coded values
        self.report.print_backtest_results(results)
```

## ReportEngine API

| Method | What it does |
|--------|---------------|
| `print_strategy_header(strategy_name, symbol, start, end, params)` | Panel with metadata + params table |
| `print_step(message, status="info")` | Status badge (`info`, `success`, `warning`, `error`) |
| `print_data_summary(rows, start_date, end_date)` | Summarizes candles loaded |
| `print_backtest_results(results)` | Two tables: portfolio metrics + analyzer metrics |
| `print_error(title, message)` | Red bordered panel for fatal errors |
| `create_progress_context(description)` | Rich Progress context manager |

## Benefits

1. **Consistency** – One style across CLI, CI logs, and demos.
2. **Maintainability** – Update `ReportEngine` once to change styling globally.
3. **Logging** – Every panel/table mirrors into `logs/wawastock.log` via Loguru.
4. **Streamlit parity** – `run_recipe_programmatic()` consumes the same results dict produced right after `print_backtest_results`.
5. **Extensibility** – Add new helper methods (e.g., trade breakdown tables) and adopt them across recipes without touching each file.

## Example Output

```
╭────────────────────╮
│ RSI Mean Reversion │
╰────────────────────╯

   Symbol            AAPL
   Period            2020-01-01 to 2023-12-31
   Rsi Period        14
   Oversold          30
   Overbought        70
   Stop Loss Pct     2.0%

ℹ️ Loading data for AAPL...
✓ Loaded 1,006 bars of data (2020-01-02 to 2023-12-29)

ℹ️ Running backtest...

╭──────────────────╮
│ BACKTEST RESULTS │
╰──────────────────╯
╭─────────────────┬─────────────────╮
│  Initial Value  │  $  100,000.00  │
│  Final Value    │  $  100,051.55  │
│  Profit/Loss    │  $       51.55  │
│  Total Return   │          0.05%  │
╰─────────────────┴─────────────────╯

╭───────────────────────┬────────────────╮
│  Sharpe Ratio         │       -74.677  │
│  Max Drawdown         │         0.03%  │
│  Total Return (Ann.)  │         0.00%  │
╰───────────────────────┴────────────────╯
```

## Adoption Checklist

1. **Import & initialize**: `from engines.report_engine import ReportEngine` and set `self.report = ReportEngine()` inside the recipe’s `__init__`.
2. **Replace prints**: Swap `print()` calls for the appropriate helper (header, step updates, summaries, results, errors).
3. **Wrap long tasks**: Use `create_progress_context` for loops (e.g., optimization runs).
4. **Bubble errors**: Instead of `print("error")`, raise exceptions or call `print_error` then `raise`—both the console and log file capture the details.
5. **Return results**: Recipes should still return/propagate the `BacktestEngine` results dict so Streamlit and scripts can consume it.

## Customization Tips

- Need new analyzer fields? Extend `ReportEngine._format_results_table()` (or similar) with additional rows (e.g., Sortino, exposure time).
- Localization or theming can be centralized by editing the palette/border styles in `ReportEngine`.
- Want CSV/HTML export? Add methods that accept the same results dict and write to disk; call them from recipes after printing tables.

## Testing

```bash
python main.py run-recipe --name rsi --symbol AAPL
python main.py run-recipe --name multi_timeframe --symbol NVDA --start 2021-01-01 --end 2023-12-31
```

Confirm that headers, steps, and analyzer tables appear, and that `logs/wawastock.log` mirrors the output.

## Future Enhancements

- Export Rich tables to Markdown/HTML for reports.
- Add a `print_trades_table` helper fed by the trade analyzer.
- Surface warnings (e.g., missing indicators, short datasets) consistently via `print_step(..., status="warning")`.

Following this guide keeps every new recipe aligned with the rest of the platform and minimizes copy/paste formatting code.
