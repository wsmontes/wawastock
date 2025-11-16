"""
Metrics display components for Streamlit UI.

Provides functions to display performance metrics in cards and tables.
"""

import streamlit as st
from typing import Dict, Any


def display_performance_metrics(results: Dict[str, Any]):
    """
    Display key performance metrics in metric cards.
    
    Args:
        results: Dictionary with backtest results
    """
    st.subheader("📊 Performance Metrics")
    
    # Top row - Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Initial Value",
            f"${results.get('initial_value', 0):,.2f}"
        )
    
    with col2:
        st.metric(
            "Final Value",
            f"${results.get('final_value', 0):,.2f}"
        )
    
    with col3:
        profit_loss = results.get('profit_loss', 0)
        st.metric(
            "Profit/Loss",
            f"${profit_loss:,.2f}",
            delta=f"{profit_loss:,.2f}",
            delta_color="normal" if profit_loss >= 0 else "inverse"
        )
    
    with col4:
        total_return = results.get('total_return', 0)
        st.metric(
            "Total Return",
            f"{total_return:.2f}%",
            delta=f"{total_return:.2f}%",
            delta_color="normal" if total_return >= 0 else "inverse"
        )
    
    # Bottom row - Risk metrics
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        sharpe = results.get('sharpe_ratio', 0)
        st.metric(
            "Sharpe Ratio",
            f"{sharpe:.3f}" if sharpe else "N/A"
        )
    
    with col6:
        max_dd = results.get('max_drawdown', 0)
        st.metric(
            "Max Drawdown",
            f"{max_dd:.2f}%" if max_dd else "N/A"
        )
    
    with col7:
        ann_return = results.get('total_return_ann', 0)
        st.metric(
            "Annualized Return",
            f"{ann_return:.2f}%" if ann_return else "N/A"
        )
    
    with col8:
        trades = results.get('trades', [])
        st.metric(
            "Total Trades",
            len(trades) if trades else 0
        )


def display_strategy_config(
    recipe_name: str,
    symbol: str,
    period: str,
    params: Dict[str, Any]
):
    """
    Display strategy configuration in a nice format.
    
    Args:
        recipe_name: Name of the recipe
        symbol: Symbol being backtested
        period: Period range
        params: Strategy parameters
    """
    st.subheader("⚙️ Strategy Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **Recipe**: {recipe_name}  
        **Symbol**: {symbol}  
        **Period**: {period}
        """)
    
    with col2:
        if params:
            st.markdown("**Parameters:**")
            for key, value in params.items():
                st.markdown(f"- {key}: `{value}`")
        else:
            st.markdown("*Using default parameters*")


def display_summary_card(results: Dict[str, Any]):
    """
    Display a summary card with key results.
    
    Args:
        results: Dictionary with backtest results
    """
    profit_loss = results.get('profit_loss', 0)
    total_return = results.get('total_return', 0)
    
    # Determine color based on performance
    if total_return > 10:
        emoji = "🚀"
        color = "green"
    elif total_return > 0:
        emoji = "📈"
        color = "blue"
    elif total_return > -10:
        emoji = "📉"
        color = "orange"
    else:
        emoji = "⚠️"
        color = "red"
    
    st.markdown(f"""
    <div style='padding: 1rem; border-radius: 0.5rem; background-color: rgba(0,0,0,0.05); border-left: 4px solid {color};'>
        <h3 style='margin: 0;'>{emoji} Backtest Summary</h3>
        <p style='margin: 0.5rem 0;'>
            <strong>Symbol:</strong> {results.get('symbol', 'N/A')}<br>
            <strong>Period:</strong> {results.get('period', 'N/A')}<br>
            <strong>Return:</strong> <span style='color: {color}; font-size: 1.2em; font-weight: bold;'>{total_return:.2f}%</span><br>
            <strong>P&L:</strong> ${profit_loss:,.2f}
        </p>
    </div>
    """, unsafe_allow_html=True)
