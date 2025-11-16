"""
Chart components for Streamlit UI.

Provides interactive charts using Plotly for visualizing backtest results.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st
from typing import Optional, List, Dict, Any


def plot_equity_curve(results: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Plot portfolio equity curve over time.
    
    Args:
        results: Dictionary with backtest results
        
    Returns:
        Plotly figure or None
    """
    # TODO: Extract equity curve data from backtest results
    # For now, return a placeholder
    st.info("Equity curve visualization coming soon!")
    return None


def plot_price_chart(
    df: pd.DataFrame,
    symbol: str,
    indicators: Optional[List[str]] = None
) -> go.Figure:
    """
    Plot candlestick chart with optional indicators.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol name
        indicators: List of indicator columns to plot
        
    Returns:
        Plotly figure
    """
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{symbol} Price', 'Volume'),
        row_heights=[0.7, 0.3]
    )
    
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC'
        ),
        row=1, col=1
    )
    
    # Add indicators if specified
    if indicators:
        for indicator in indicators:
            if indicator in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[indicator],
                        name=indicator,
                        line=dict(width=1)
                    ),
                    row=1, col=1
                )
    
    # Volume bars
    colors = ['red' if close < open else 'green' 
              for close, open in zip(df['close'], df['open'])]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title=f'{symbol} - Price Chart',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        height=600,
        hovermode='x unified'
    )
    
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig


def plot_returns_distribution(returns: pd.Series) -> go.Figure:
    """
    Plot histogram of returns distribution.
    
    Args:
        returns: Series of returns
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    fig.add_trace(
        go.Histogram(
            x=returns,
            nbinsx=50,
            name='Returns',
            marker_color='lightblue',
            opacity=0.75
        )
    )
    
    fig.update_layout(
        title='Returns Distribution',
        xaxis_title='Return (%)',
        yaxis_title='Frequency',
        height=400,
        showlegend=False
    )
    
    return fig


def plot_drawdown(equity_curve: pd.Series) -> go.Figure:
    """
    Plot drawdown chart.
    
    Args:
        equity_curve: Series with portfolio values over time
        
    Returns:
        Plotly figure
    """
    # Calculate drawdown
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax * 100
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown,
            fill='tozeroy',
            name='Drawdown',
            line=dict(color='red', width=1),
            fillcolor='rgba(255, 0, 0, 0.2)'
        )
    )
    
    fig.update_layout(
        title='Drawdown Over Time',
        xaxis_title='Date',
        yaxis_title='Drawdown (%)',
        height=400,
        hovermode='x unified'
    )
    
    return fig


def plot_trades_timeline(trades: List[Dict[str, Any]], df: pd.DataFrame) -> go.Figure:
    """
    Plot trades on price chart.
    
    Args:
        trades: List of trade dictionaries
        df: DataFrame with price data
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Price line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['close'],
            name='Price',
            line=dict(color='lightgray', width=1)
        )
    )
    
    # TODO: Add buy/sell markers when trade data structure is available
    # For now, just show the price
    
    fig.update_layout(
        title='Trades Timeline',
        xaxis_title='Date',
        yaxis_title='Price',
        height=400,
        hovermode='x unified'
    )
    
    return fig


def create_indicator_selector(df: pd.DataFrame) -> List[str]:
    """
    Create a multiselect widget for choosing indicators to display.
    
    Args:
        df: DataFrame with indicator columns
        
    Returns:
        List of selected indicator column names
    """
    # Find indicator columns
    indicator_cols = []
    indicator_prefixes = ['SMA_', 'EMA_', 'BB', 'RSI', 'MACD', 'ATR', 'OBV', 'STOCH', 'VWAP']
    
    for col in df.columns:
        if any(col.startswith(prefix) for prefix in indicator_prefixes):
            indicator_cols.append(col)
    
    if not indicator_cols:
        return []
    
    # Create multiselect
    selected = st.multiselect(
        "Select indicators to display",
        options=indicator_cols,
        default=indicator_cols[:3] if len(indicator_cols) >= 3 else indicator_cols,
        help="Choose which technical indicators to overlay on the price chart"
    )
    
    return selected
