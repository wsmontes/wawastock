# Analysis Page Features

## Overview
Professional-grade backtest analysis dashboard with comprehensive metrics and insights.

## Features

### 1. Performance Overview
- Total backtests counter
- Average return across all tests
- Best performing strategy
- Average Sharpe ratio

### 2. Comparison Charts
- **Returns Distribution**: Histogram of all backtest returns
- **Risk-Adjusted Performance**: Scatter plot (Sharpe vs Return)
- Color-coded by performance level

### 3. Detailed Metrics Tabs

#### Returns Tab
- Total return percentage
- Absolute P&L in dollars
- Initial vs Final capital comparison

#### Risk Tab
- **Sharpe Ratio**: Risk-adjusted return metric
- **Max Drawdown**: Largest peak-to-trough decline
- **Volatility**: Standard deviation of returns

#### Trades Tab
- Total, won, and lost trades count
- Win rate percentage
- Average trade P&L
- Visual pie chart of trade distribution

#### Drawdown Tab
- Maximum drawdown visualization
- Gauge chart with color-coded risk levels:
  - Green (0-10%): Low risk
  - Yellow (10-25%): Medium risk
  - Red (25%+): High risk

### 4. System Logs Viewer
- Real-time log file reading
- Text filtering capability
- Adjustable display lines (10-1000)
- Download full log file button
- Timestamped export filename

## Data Sources

1. **DuckDB Database**: `data/trader.duckdb`
   - Trades table
   - Results history

2. **Log Files**: `logs/wawastock.log`
   - Backtest execution logs
   - Performance metrics
   - Error tracking

3. **Session State**: Current backtest in memory

## Technical Implementation

- **Framework**: Streamlit with multi-page navigation
- **Charts**: Plotly for interactive visualizations
- **Data**: Pandas for analysis, DuckDB for persistence
- **Styling**: Professional color schemes (RdYlGn, custom palettes)

## Usage

1. Run backtests from the Backtest page
2. Switch to Analysis page using top navigation
3. View aggregated performance across all tests
4. Drill down into specific metrics
5. Filter and download logs for debugging
