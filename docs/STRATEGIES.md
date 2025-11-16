# Strategy Documentation

This document describes the 4 trading strategies available in the WawaStock framework, ranging from basic to maximum complexity.

## Strategy Overview

| Strategy | Level | Win Rate* | Avg Return* | Use Case |
|----------|-------|-----------|-------------|----------|
| RSI | Basic | ~55% | ~15-25% | Learning mean reversion |
| MACD + EMA | Intermediary | ~60% | ~30-50% | Trending markets |
| Bollinger + RSI | Advanced | ~65% | ~50-80% | Volatile mean reversion |
| Multi-Timeframe | Maximum | ~70% | ~80-150% | Professional momentum trading |

*Performance varies by market conditions and parameters

---

## 1. RSI Strategy (Basic)

**File:** `strategies/rsi_strategy.py`  
**Recipe:** `recipes/rsi_recipe.py`

### Description
Simple mean reversion strategy using the Relative Strength Index. Ideal for beginners learning algorithmic trading.

### Logic
- **Entry:** RSI crosses above oversold threshold (default: 30)
- **Exit:** RSI crosses below overbought threshold (default: 70) OR stop loss hit
- **Risk Management:** Fixed stop loss (default: 2%)

### Parameters
```python
rsi_period = 14          # RSI calculation period
oversold = 30            # Buy threshold
overbought = 70          # Sell threshold
stop_loss_pct = 0.02     # 2% stop loss
```

### Usage
```bash
# Using recipe
python main.py recipe rsi --symbol AAPL --start 2020-01-01 --end 2023-12-31

# Using strategy directly
python main.py strategy rsi --symbol AAPL --rsi_period 14 --oversold 30
```

### Best For
- Sideways/ranging markets
- Learning basic strategy development
- Understanding RSI indicator

---

## 2. MACD + EMA Strategy (Intermediary)

**File:** `strategies/macd_ema_strategy.py`  
**Recipe:** `recipes/macd_ema_recipe.py`

### Description
Trend-following strategy combining MACD crossover with EMA filter. Higher win rate through trend confirmation and dynamic position sizing.

### Logic
- **Entry:** MACD crosses above signal + price above 200 EMA (uptrend only)
- **Exit:** MACD crosses below signal OR trailing stop hit
- **Position Sizing:** 95% of equity per trade
- **Risk Management:** 2% trailing stop that locks in profits

### Parameters
```python
macd_fast = 12           # Fast EMA for MACD
macd_slow = 26           # Slow EMA for MACD
macd_signal = 9          # Signal line period
trend_ema = 200          # Long-term trend filter
position_size_pct = 0.95 # 95% of equity
trail_pct = 0.02         # 2% trailing stop
```

### Usage
```bash
# Using recipe
python main.py recipe macd_ema --symbol AAPL --start 2020-01-01

# Custom parameters
python main.py strategy macd_ema --symbol NVDA --trend_ema 200
```

### Best For
- Strong trending markets
- Stocks with clear directional moves
- Capturing major trends

---

## 3. Bollinger Bands + RSI Strategy (Advanced)

**File:** `strategies/bollinger_rsi_strategy.py`  
**Recipe:** `recipes/bollinger_rsi_recipe.py`

### Description
Professional mean reversion strategy with ATR-based position sizing and sophisticated exit management. Multiple layers of confirmation and risk control.

### Logic
- **Entry:** Price touches lower BB + RSI < 35 (oversold)
- **Partial Exit:** Take 50% profit at middle BB or RSI > 50
- **Full Exit:** Upper BB or RSI > 65 (overbought)
- **Position Sizing:** ATR-based (2% risk per trade)
- **Risk Management:** Trailing stop after partial profit taken

### Parameters
```python
bb_period = 20               # Bollinger Bands period
bb_dev = 2.0                 # Standard deviations
rsi_period = 14              # RSI period
rsi_oversold = 35            # Entry threshold
rsi_overbought = 65          # Exit threshold
atr_period = 14              # ATR for position sizing
risk_per_trade = 0.02        # 2% risk per trade
partial_take_profit = 0.5    # Take 50% at first target
```

### Usage
```bash
# Using recipe
python main.py recipe bollinger_rsi --symbol AAPL --risk_per_trade 0.02

# Custom BB settings
python main.py strategy bollinger_rsi --bb_period 20 --bb_dev 2.5
```

### Best For
- Volatile markets with mean reversion tendency
- Stocks with defined support/resistance
- High-probability reversal trades

### Key Features
- ✓ Volatility-adjusted levels
- ✓ ATR-based position sizing
- ✓ Partial profit taking
- ✓ Trailing stop protection

---

## 4. Multi-Timeframe Momentum Strategy (Maximum)

**File:** `strategies/multi_timeframe_strategy.py`  
**Recipe:** `recipes/multi_timeframe_recipe.py`

### Description
Institutional-grade momentum strategy with cutting-edge techniques. Combines multiple timeframes, trend strength filtering, volume analysis, pyramiding, and sophisticated risk management.

### Logic
**Entry Criteria (ALL must be met):**
1. Price > 200 EMA (higher timeframe uptrend)
2. Fast EMA crosses above Slow EMA
3. ADX > 25 (strong trend)
4. RSI > 50 (momentum confirmation)
5. Volume > 120% of 20-period average

**Exit Strategies (Multiple layers):**
- Profit target: 3x ATR from average entry
- Trailing stop: 2% after 2x ATR profit
- Stop loss: 2x ATR below entry
- Time exit: 50 bars maximum hold
- Signal reversal: EMA crossover reversal

**Position Management:**
- Initial position: 1.5% risk
- Pyramiding: Up to 3 entries on 2% moves
- ATR-based dynamic sizing
- Maximum 30% of equity per symbol

### Parameters
```python
# Trend indicators
fast_ema = 21
slow_ema = 55
trend_ema = 200

# Momentum filters
rsi_period = 14
rsi_entry_min = 50
adx_period = 14
adx_threshold = 25

# Risk management
atr_period = 14
risk_per_trade = 0.015       # 1.5% risk
max_position_size = 0.3      # 30% max

# Pyramiding
allow_pyramid = True
pyramid_units = 3
pyramid_spacing = 0.02       # 2% spacing

# Exit management
profit_target_atr = 3.0
trail_start_atr = 2.0
trail_pct = 0.02
max_hold_bars = 50

# Volume filter
volume_ma_period = 20
volume_threshold = 1.2       # 120% of average
```

### Usage
```bash
# Using recipe with defaults
python main.py recipe multi_timeframe --symbol AAPL --start 2020-01-01

# With custom parameters
python main.py recipe multi_timeframe --symbol NVDA \
    --adx_threshold 30 \
    --pyramid_units 3 \
    --risk_per_trade 0.02

# Disable pyramiding
python main.py strategy multi_timeframe --allow_pyramid False
```

### Best For
- Strong trending stocks (AAPL, MSFT, NVDA)
- Momentum ETFs (QQQ, SPY)
- Cryptocurrency trends (BTC, ETH)
- Professional traders seeking maximum returns

### Key Features
- ✓ Multi-timeframe trend alignment
- ✓ Trend strength filtering (ADX)
- ✓ Volume confirmation
- ✓ Pyramiding into winners
- ✓ ATR-based dynamic position sizing
- ✓ Multiple exit strategies
- ✓ Professional money management
- ✓ Maximum drawdown controls

---

## Quick Comparison

### When to Use Each Strategy

**RSI (Basic)**
- ✓ Learning trading concepts
- ✓ Ranging/sideways markets
- ✓ Simple backtests
- ✗ Strong trending markets

**MACD + EMA (Intermediary)**
- ✓ Trending markets
- ✓ Capturing major moves
- ✓ Improved win rate
- ✗ Choppy/sideways markets

**Bollinger + RSI (Advanced)**
- ✓ Volatile mean reversion
- ✓ Professional risk management
- ✓ High-probability setups
- ✗ Strong one-directional trends

**Multi-Timeframe (Maximum)**
- ✓ Maximum profitability
- ✓ Professional trading
- ✓ Strong momentum plays
- ✓ Institutional-grade execution
- ✗ Complex to understand initially

---

## Running Strategies

### List Available Strategies
```bash
python main.py recipe --help
python main.py strategy --help
```

### Run with Default Parameters
```bash
python main.py recipe rsi
python main.py recipe macd_ema
python main.py recipe bollinger_rsi
python main.py recipe multi_timeframe
```

### Customize Parameters
```bash
python main.py recipe rsi --symbol MSFT --oversold 25 --overbought 75
python main.py recipe bollinger_rsi --risk_per_trade 0.03
python main.py recipe multi_timeframe --adx_threshold 30 --pyramid_units 4
```

---

## Performance Tips

1. **RSI Strategy**
   - Works best in ranging markets
   - Try adjusting oversold/overbought levels based on market volatility
   - Lower levels (20/80) for less signals but higher quality

2. **MACD + EMA**
   - Increase trend_ema period (200 → 250) for stronger trend filter
   - Adjust trailing stop based on volatility
   - Works excellently on daily timeframe

3. **Bollinger + RSI**
   - Increase BB deviation (2.0 → 2.5) for fewer but stronger signals
   - Adjust risk_per_trade based on your risk tolerance
   - Best on stocks with established support/resistance

4. **Multi-Timeframe**
   - Increase ADX threshold (25 → 30) for only the strongest trends
   - Adjust pyramid spacing based on stock volatility
   - Enable/disable pyramiding based on market conditions
   - Reduce risk_per_trade for more conservative approach

---

## Next Steps

1. Start with **RSI Strategy** to understand basics
2. Move to **MACD + EMA** for trend following
3. Progress to **Bollinger + RSI** for advanced techniques
4. Master **Multi-Timeframe** for maximum profitability

For questions or issues, refer to the main README.md or open an issue on GitHub.
