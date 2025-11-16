"""
Professional Backtest Analysis Page
Advanced metrics, comparisons, and insights from all backtest runs
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime
import json
import duckdb

def load_all_backtest_results(bridge):
    """Load all backtest results from logs"""
    results_list = []
    
    log_path = Path("logs/wawastock.log")
    if not log_path.exists():
        return []
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    # Parse structured log entries
    current_test = {}
    in_results_block = False
    
    for line in lines:
        # Start of results block
        if "BACKTEST RESULTS - COMPLETE METRICS" in line:
            in_results_block = True
            current_test = {}
            continue
        
        # End of results block
        if in_results_block and "=" * 60 in line and current_test:
            # Save if we have minimum data
            if 'final_value' in current_test:
                results_list.append(current_test.copy())
            current_test = {}
            in_results_block = False
            continue
        
        # Parse fields inside results block
        if in_results_block:
            if "Symbol:" in line:
                try:
                    current_test['symbol'] = line.split("Symbol:")[1].strip()
                except:
                    pass
            elif "Strategy:" in line:
                try:
                    current_test['strategy'] = line.split("Strategy:")[1].strip()
                except:
                    pass
            elif "Initial Capital:" in line:
                try:
                    val = line.split("$")[1].replace(',', '').strip()
                    current_test['initial_value'] = float(val)
                except:
                    pass
            elif "Final Value:" in line:
                try:
                    val = line.split("$")[1].replace(',', '').strip()
                    current_test['final_value'] = float(val)
                except:
                    pass
            elif "Total P&L:" in line:
                try:
                    val = line.split("$")[1].replace(',', '').strip()
                    current_test['pnl'] = float(val)
                except:
                    pass
            elif "Total Return:" in line:
                try:
                    val = line.split(":")[1].replace('%', '').strip()
                    current_test['return'] = float(val)
                except:
                    pass
            elif "Sharpe Ratio:" in line:
                try:
                    val = line.split(":")[1].strip()
                    current_test['sharpe'] = float(val)
                except:
                    pass
            elif "Max Drawdown:" in line:
                try:
                    val = line.split(":")[1].replace('%', '').strip()
                    current_test['max_drawdown'] = float(val)
                except:
                    pass
            elif "Total Trades:" in line:
                try:
                    val = line.split(":")[1].strip()
                    current_test['total_trades'] = int(val)
                except:
                    pass
            elif "Won Trades:" in line:
                try:
                    val = line.split(":")[1].strip()
                    current_test['won_trades'] = int(val)
                except:
                    pass
            elif "Lost Trades:" in line:
                try:
                    val = line.split(":")[1].strip()
                    current_test['lost_trades'] = int(val)
                except:
                    pass
            elif "Win Rate:" in line:
                try:
                    val = line.split(":")[1].replace('%', '').strip()
                    current_test['win_rate'] = float(val)
                except:
                    pass
            elif "Average Trade:" in line:
                try:
                    val = line.split("$")[1].replace(',', '').strip()
                    current_test['avg_trade'] = float(val)
                except:
                    pass
    
    return results_list

def render_performance_overview(results_list):
    """Render overall performance statistics"""
    st.subheader("📊 Performance Overview")
    
    if not results_list:
        return
    
    df = pd.DataFrame(results_list)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Tests", len(results_list))
    with col2:
        avg_return = df['return'].mean() if 'return' in df else 0
        st.metric("Avg Return", f"{avg_return:.2f}%", delta=f"{avg_return:.2f}%")
    with col3:
        best_return = df['return'].max() if 'return' in df else 0
        st.metric("Best Return", f"{best_return:.2f}%")
    with col4:
        avg_sharpe = df['sharpe'].mean() if 'sharpe' in df else 0
        st.metric("Avg Sharpe", f"{avg_sharpe:.2f}")
    with col5:
        if 'win_rate' in df:
            avg_win_rate = df['win_rate'].mean()
            st.metric("Avg Win Rate", f"{avg_win_rate:.1f}%")
        else:
            st.metric("Avg Win Rate", "N/A")
    
    # Recent tests table
    st.subheader("Recent Tests")
    if len(df) > 0:
        # Select relevant columns
        display_cols = []
        for col in ['symbol', 'strategy', 'return', 'pnl', 'sharpe', 'max_drawdown', 'total_trades', 'win_rate']:
            if col in df.columns:
                display_cols.append(col)
        
        if display_cols:
            recent_df = df[display_cols].tail(10).iloc[::-1]  # Last 10, reversed
            
            # Format columns
            if 'return' in recent_df:
                recent_df['return'] = recent_df['return'].apply(lambda x: f"{x:.2f}%")
            if 'pnl' in recent_df:
                recent_df['pnl'] = recent_df['pnl'].apply(lambda x: f"${x:,.2f}")
            if 'sharpe' in recent_df:
                recent_df['sharpe'] = recent_df['sharpe'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            if 'max_drawdown' in recent_df:
                recent_df['max_drawdown'] = recent_df['max_drawdown'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
            if 'win_rate' in recent_df:
                recent_df['win_rate'] = recent_df['win_rate'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
            
            st.dataframe(recent_df, use_container_width=True, hide_index=True)

def render_comparison_charts(results_list):
    """Render comparison charts across all backtests"""
    st.subheader("📈 Performance Comparisons")
    
    if not results_list or len(results_list) < 2:
        return
    
    df = pd.DataFrame(results_list)
    
    # Returns distribution
    if 'return' in df:
        fig = px.histogram(
            df, 
            x='return',
            nbins=20,
            title="Returns Distribution",
            labels={'return': 'Return (%)'},
            color_discrete_sequence=['#636EFA']
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Sharpe vs Return scatter
    if 'return' in df and 'sharpe' in df:
        fig = px.scatter(
            df,
            x='sharpe',
            y='return',
            title="Risk-Adjusted Performance",
            labels={'sharpe': 'Sharpe Ratio', 'return': 'Return (%)'},
            color='return',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)

def render_detailed_metrics():
    """Render detailed metrics from session state results"""
    st.subheader("🔍 Detailed Analysis")
    
    if 'results' not in st.session_state:
        return
    
    results = st.session_state['results']
    
    # Create tabs for different analysis sections
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Returns", "⚖️ Risk", "💼 Trades", "📉 Drawdown"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Return", f"{results.get('total_return', 0) or 0:.2f}%")
            st.metric("Absolute P&L", f"${results.get('total_pnl', 0) or 0:,.2f}")
        with col2:
            initial = results.get('initial_value', 10000)
            final = results.get('final_value', 10000)
            st.metric("Initial Capital", f"${initial:,.2f}")
            st.metric("Final Value", f"${final:,.2f}")
    
    with tab2:
        col1, col2, col3 = st.columns(3)
        with col1:
            sharpe = results.get('sharpe_ratio', 0)
            st.metric("Sharpe Ratio", f"{sharpe if sharpe is not None else 0:.3f}")
        with col2:
            max_dd = results.get('max_drawdown', 0)
            st.metric("Max Drawdown", f"{max_dd if max_dd is not None else 0:.2f}%")
        with col3:
            volatility = results.get('volatility', 0)
            st.metric("Volatility", f"{volatility if volatility is not None else 0:.2f}%")
    
    with tab3:
        col1, col2, col3, col4 = st.columns(4)
        
        total_trades = results.get('total_trades', 0) or 0
        won_trades = results.get('won_trades', 0) or 0
        lost_trades = results.get('lost_trades', 0) or 0
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        with col1:
            st.metric("Total Trades", total_trades)
        with col2:
            st.metric("Won Trades", won_trades, delta=f"{win_rate:.1f}%")
        with col3:
            st.metric("Lost Trades", lost_trades)
        with col4:
            avg_trade = results.get('total_pnl', 0) / total_trades if total_trades > 0 else 0
            st.metric("Avg Trade", f"${avg_trade:,.2f}")
        
        # Trade distribution
        if total_trades > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Won', 'Lost'],
                values=[won_trades, lost_trades],
                marker=dict(colors=['#00cc96', '#ef553b']),
                hole=0.4
            )])
            fig.update_layout(title="Trade Distribution", height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.info("Drawdown analysis requires time-series data")
        max_dd = results.get('max_drawdown', 0)
        if max_dd:
            st.metric("Maximum Drawdown", f"{max_dd:.2f}%")
            
            # Visual representation
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=abs(max_dd) if max_dd else 0,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Max Drawdown (%)"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkred"},
                    'steps': [
                        {'range': [0, 10], 'color': "lightgreen"},
                        {'range': [10, 25], 'color': "lightyellow"},
                        {'range': [25, 100], 'color': "lightcoral"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': abs(max_dd) if max_dd else 0
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

def render_log_viewer():
    """Render log file viewer"""
    st.subheader("📋 System Logs")
    
    log_path = Path("logs/wawastock.log")
    if not log_path.exists():
        return
    
    # Filter options
    col1, col2 = st.columns([2, 1])
    with col1:
        filter_text = st.text_input("Filter logs", placeholder="e.g. ERROR, backtest, symbol")
    with col2:
        lines_to_show = st.number_input("Lines to display", value=100, min_value=10, max_value=1000, step=50)
    
    # Read and display logs
    with open(log_path, 'r') as f:
        all_lines = f.readlines()
    
    # Apply filter
    if filter_text:
        filtered_lines = [line for line in all_lines if filter_text.lower() in line.lower()]
    else:
        filtered_lines = all_lines
    
    # Show last N lines
    recent_lines = filtered_lines[-lines_to_show:]
    
    st.text_area(
        f"Showing last {len(recent_lines)} lines",
        value=''.join(recent_lines),
        height=400,
        disabled=True
    )
    
    # Download button
    log_content = ''.join(all_lines)
    st.download_button(
        label="📥 Download Full Log",
        data=log_content,
        file_name=f"wawastock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        mime="text/plain"
    )

def render(bridge):
    """Main render function for analysis page"""
    
    # Load all results (silently, no warnings)
    results_list = []
    try:
        results_list = load_all_backtest_results(bridge)
    except:
        pass
    
    # Render sections
    render_performance_overview(results_list)
    st.divider()
    
    render_comparison_charts(results_list)
    st.divider()
    
    render_detailed_metrics()
    st.divider()
    
    render_log_viewer()
