# Quick Start Guide - New Strategies

## Available Strategies

You now have **4 trading strategies** with increasing complexity:

1. **rsi** - Basic RSI mean reversion (beginner-friendly)
2. **macd_ema** - Intermediary MACD + EMA trend following
3. **bollinger_rsi** - Advanced Bollinger Bands + RSI with ATR sizing
4. **multi_timeframe** - Maximum multi-timeframe momentum with pyramiding

## Running Strategies

### Option 1: Using Recipes (Recommended)

Recipes provide a complete workflow with defaults and formatted output:

```bash
# Activate virtual environment first
source venv/bin/activate

# Basic RSI Strategy
python main.py run-recipe --name rsi --symbol AAPL

# Intermediary MACD + EMA Strategy
python main.py run-recipe --name macd_ema --symbol AAPL

# Advanced Bollinger + RSI Strategy
python main.py run-recipe --name bollinger_rsi --symbol AAPL

# Maximum Multi-Timeframe Strategy
python main.py run-recipe --name multi_timeframe --symbol AAPL
```

### Option 2: Using Strategies Directly

For more control over parameters:

```bash
# RSI Strategy
python main.py run-strategy --strategy rsi \
    --symbol AAPL \
    --start 2020-01-01 \
    --end 2023-12-31

# MACD + EMA Strategy
python main.py run-strategy --strategy macd_ema \
    --symbol MSFT \
    --start 2021-01-01 \
    --end 2023-12-31

# Bollinger + RSI Strategy
python main.py run-strategy --strategy bollinger_rsi \
    --symbol NVDA \
    --start 2022-01-01 \
    --end 2023-12-31

# Multi-Timeframe Strategy
python main.py run-strategy --strategy multi_timeframe \
    --symbol TSLA \
    --start 2020-01-01 \
    --end 2023-12-31
```

## Strategy Comparison

| Strategy | Complexity | Ideal For | Key Feature |
|----------|-----------|-----------|-------------|
| **rsi** | ⭐ Basic | Learning | Simple mean reversion |
| **macd_ema** | ⭐⭐ Intermediary | Trending markets | EMA filter + trailing stop |
| **bollinger_rsi** | ⭐⭐⭐ Advanced | Volatile markets | ATR-based sizing + partial profits |
| **multi_timeframe** | ⭐⭐⭐⭐ Maximum | Professional trading | Pyramiding + multi-layer exits |

## Example Workflows

### 1. Test All Strategies on AAPL

```bash
source venv/bin/activate

# Run each strategy
python main.py run-recipe --name rsi --symbol AAPL
python main.py run-recipe --name macd_ema --symbol AAPL
python main.py run-recipe --name bollinger_rsi --symbol AAPL
python main.py run-recipe --name multi_timeframe --symbol AAPL
```

### 2. Compare Periods

```bash
# 2020-2021 (COVID recovery)
python main.py run-recipe --name multi_timeframe --symbol AAPL \
    --start 2020-01-01 --end 2021-12-31

# 2022-2023 (Bear to Bull)
python main.py run-recipe --name multi_timeframe --symbol AAPL \
    --start 2022-01-01 --end 2023-12-31
```

### 3. Test on Different Assets

```bash
# Tech stocks (trending)
python main.py run-recipe --name macd_ema --symbol NVDA
python main.py run-recipe --name multi_timeframe --symbol MSFT

# Volatile stocks (mean reversion)
python main.py run-recipe --name bollinger_rsi --symbol TSLA
python main.py run-recipe --name rsi --symbol GME
```

## Available Recipes

List all available recipes:
```bash
# These are the current recipes
- sample           # Original SMA example
- rsi              # NEW: Basic RSI strategy
- macd_ema         # NEW: Intermediary MACD strategy
- bollinger_rsi    # NEW: Advanced Bollinger strategy
- multi_timeframe  # NEW: Maximum momentum strategy
```

## Next Steps

1. **Start Simple**: Run the RSI recipe first
   ```bash
   python main.py run-recipe --name rsi --symbol AAPL
   ```

2. **Progress to Intermediary**: Test MACD + EMA
   ```bash
   python main.py run-recipe --name macd_ema --symbol AAPL
   ```

3. **Try Advanced**: Bollinger Bands + RSI
   ```bash
   python main.py run-recipe --name bollinger_rsi --symbol AAPL
   ```

4. **Master Maximum**: Multi-timeframe momentum
   ```bash
   python main.py run-recipe --name multi_timeframe --symbol AAPL
   ```

## Detailed Documentation

For complete strategy details, parameters, and optimization tips, see:
- **STRATEGIES.md** - Comprehensive strategy documentation
- **README.md** - General framework documentation

## Tips

- Always activate the virtual environment: `source venv/bin/activate`
- Start with AAPL as it has good data in most cases
- Compare strategies on the same symbol and period
- Each strategy level builds on concepts from the previous one
- The multi_timeframe strategy is production-ready for professional use

## Getting Help

```bash
# General help
python main.py --help

# Recipe help
python main.py run-recipe --help

# Strategy help
python main.py run-strategy --help
```

Enjoy backtesting! 🚀
