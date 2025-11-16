"""
Analysis Page - View all backtest results
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Analysis - WawaStock",
    page_icon="📊",
    layout="wide"
)

# Load results function
def load_all_backtest_results():
    """Load all backtest results from logs"""
    results_list = []
    
    log_path = Path("logs/wawastock.log")
    if not log_path.exists():
        return []
    
    with open(log_path, 'r') as f:
        content = f.read()
    
    blocks = content.split("BACKTEST RESULTS - COMPLETE METRICS")
    
    for block in blocks[1:]:
        result = {}
        
        lines = block.split('\n')
        if lines and '|' in lines[0]:
            try:
                timestamp = lines[0].split('|')[0].strip()
                if timestamp:
                    result['timestamp'] = timestamp
            except:
                pass
        
        if "Symbol:" in block:
            try:
                result['symbol'] = block.split("Symbol:")[1].split('\n')[0].strip()
            except:
                pass
        
        if "Strategy:" in block:
            try:
                result['strategy'] = block.split("Strategy:")[1].split('\n')[0].strip()
            except:
                pass
        
        if "Initial Capital:" in block:
            try:
                val = block.split("Initial Capital:")[1].split('\n')[0].replace('$', '').replace(',', '').strip()
                result['initial_value'] = float(val)
            except:
                pass
        
        if "Final Value:" in block:
            try:
                val = block.split("Final Value:")[1].split('\n')[0].replace('$', '').replace(',', '').strip()
                result['final_value'] = float(val)
            except:
                pass
        
        if "Total P&L:" in block:
            try:
                val = block.split("Total P&L:")[1].split('\n')[0].replace('$', '').replace(',', '').strip()
                result['pnl'] = float(val)
            except:
                pass
        
        if "Total Return:" in block:
            try:
                val = block.split("Total Return:")[1].split('\n')[0].replace('%', '').strip()
                result['return'] = float(val)
            except:
                pass
        
        if "Sharpe Ratio:" in block:
            try:
                val = block.split("Sharpe Ratio:")[1].split('\n')[0].strip()
                result['sharpe'] = float(val)
            except:
                pass
        
        if "Max Drawdown:" in block:
            try:
                val = block.split("Max Drawdown:")[1].split('\n')[0].replace('%', '').strip()
                result['max_drawdown'] = float(val)
            except:
                pass
        
        if "Total Trades:" in block:
            try:
                val = block.split("Total Trades:")[1].split('\n')[0].strip()
                result['total_trades'] = int(val)
            except:
                pass
        
        if "Won Trades:" in block:
            try:
                val = block.split("Won Trades:")[1].split('\n')[0].strip()
                result['won_trades'] = int(val)
            except:
                pass
        
        if "Lost Trades:" in block:
            try:
                val = block.split("Lost Trades:")[1].split('\n')[0].strip()
                result['lost_trades'] = int(val)
            except:
                pass
        
        if "Win Rate:" in block:
            try:
                val = block.split("Win Rate:")[1].split('\n')[0].replace('%', '').strip()
                result['win_rate'] = float(val)
            except:
                pass
        
        if "Average Trade:" in block:
            try:
                val = block.split("Average Trade:")[1].split('\n')[0].replace('$', '').replace(',', '').strip()
                result['avg_trade'] = float(val)
            except:
                pass
        
        if 'symbol' in result and 'strategy' in result and 'final_value' in result:
            results_list.append(result)
    
    return results_list

# Load data
results_list = load_all_backtest_results()

if not results_list:
    st.info("No backtest results found. Run some backtests to see analysis here.")
    st.stop()

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Comparison", "Strategy Analysis", "Logs"])

with tab1:
    st.subheader("Performance Overview")
    
    df = pd.DataFrame(results_list)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Tests", len(results_list))
    with col2:
        avg_return = df['return'].mean()
        st.metric("Avg Return", f"{avg_return:.2f}%")
    with col3:
        best_return = df['return'].max()
        st.metric("Best Return", f"{best_return:.2f}%")
    with col4:
        avg_sharpe = df['sharpe'].mean()
        st.metric("Avg Sharpe", f"{avg_sharpe:.3f}")
    with col5:
        avg_win_rate = df['win_rate'].mean()
        st.metric("Avg Win Rate", f"{avg_win_rate:.1f}%")
    
    st.subheader("Recent Tests")
    recent_df = df.tail(20).copy()
    recent_df = recent_df[['timestamp', 'symbol', 'strategy', 'return', 'sharpe', 'total_trades', 'win_rate']]
    recent_df['timestamp'] = recent_df['timestamp'].apply(lambda x: x[11:19] if len(x) > 19 else x)
    recent_df['return'] = recent_df['return'].apply(lambda x: f"{x:.2f}%")
    recent_df['sharpe'] = recent_df['sharpe'].apply(lambda x: f"{x:.3f}")
    recent_df['win_rate'] = recent_df['win_rate'].apply(lambda x: f"{x:.1f}%")
    recent_df = recent_df.rename(columns={
        'timestamp': 'Time', 'symbol': 'Symbol', 'strategy': 'Strategy',
        'return': 'Return', 'sharpe': 'Sharpe', 'total_trades': 'Trades', 'win_rate': 'Win Rate'
    })
    st.dataframe(recent_df, use_container_width=True, hide_index=True, height=400)

with tab2:
    st.subheader("Performance Comparisons")
    
    if len(results_list) >= 2:
        df = pd.DataFrame(results_list)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=df['return'], nbinsx=20, marker_color='#636EFA'))
            fig.update_layout(
                title="Returns Distribution",
                xaxis_title="Return (%)",
                yaxis_title="Frequency",
                height=300,
                template="plotly_dark",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=df['win_rate'], nbinsx=20, marker_color='#00cc96'))
            fig.update_layout(
                title="Win Rate Distribution",
                xaxis_title="Win Rate (%)",
                yaxis_title="Frequency",
                height=300,
                template="plotly_dark",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['sharpe'],
            y=df['return'],
            mode='markers',
            marker=dict(
                size=10,
                color=df['return'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Return (%)")
            ),
            text=df.apply(lambda row: f"{row['symbol']} - {row['strategy']}", axis=1),
            hovertemplate='<b>%{text}</b><br>Sharpe: %{x:.3f}<br>Return: %{y:.2f}%<extra></extra>'
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            title="Sharpe Ratio vs Return",
            xaxis_title="Sharpe Ratio",
            yaxis_title="Return (%)",
            height=400,
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Strategy Comparison")
    
    if len(results_list) >= 2:
        df = pd.DataFrame(results_list)
        
        if 'strategy' in df and 'return' in df:
            strategy_stats = df.groupby('strategy').agg({
                'return': ['mean', 'std', 'min', 'max'],
                'sharpe': 'mean',
                'win_rate': 'mean',
                'total_trades': 'sum'
            }).round(2)
            
            strategy_stats.columns = ['Avg Return', 'Std Dev', 'Min', 'Max', 'Avg Sharpe', 'Avg Win Rate', 'Total Trades']
            st.dataframe(strategy_stats, use_container_width=True, height=200)
            
            strategy_avg = df.groupby('strategy')['return'].mean().sort_values(ascending=False)
            
            fig = go.Figure()
            colors = ['#00cc96' if x > 0 else '#ef553b' for x in strategy_avg.values]
            fig.add_trace(go.Bar(
                x=strategy_avg.index,
                y=strategy_avg.values,
                marker_color=colors,
                text=[f"{x:.2f}%" for x in strategy_avg.values],
                textposition='auto',
            ))
            fig.update_layout(
                title="Average Return by Strategy",
                xaxis_title="Strategy",
                yaxis_title="Average Return (%)",
                height=350,
                template="plotly_dark",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("System Logs")
    
    log_path = Path("logs/wawastock.log")
    if log_path.exists():
        col1, col2 = st.columns([2, 1])
        with col1:
            filter_text = st.text_input("Filter logs", placeholder="e.g. ERROR, backtest, symbol")
        with col2:
            lines_to_show = st.number_input("Lines to display", value=100, min_value=10, max_value=1000, step=50)
        
        with open(log_path, 'r') as f:
            all_lines = f.readlines()
        
        if filter_text:
            filtered_lines = [line for line in all_lines if filter_text.lower() in line.lower()]
        else:
            filtered_lines = all_lines
        
        recent_lines = filtered_lines[-lines_to_show:]
        
        st.text_area(
            f"Showing last {len(recent_lines)} lines",
            value=''.join(recent_lines),
            height=400,
            disabled=True
        )
        
        from datetime import datetime
        log_content = ''.join(all_lines)
        st.download_button(
            label="📥 Download Full Log",
            data=log_content,
            file_name=f"wawastock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            mime="text/plain"
        )
