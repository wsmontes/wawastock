"""
WawaStock Backtest - Trading Strategy Backtesting
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamlit_components.bridge import StreamlitBridge
from streamlit_components.charts import plot_price_chart

# Page config - keep it simple
st.set_page_config(
    page_title="WawaStock Backtest",
    page_icon="📊",
    layout="wide"
)

# Initialize bridge
bridge = StreamlitBridge()

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("Configuration")
    
    # Recipe selection
    recipes = bridge.get_recipe_registry()
    recipe = st.selectbox("Strategy", list(recipes.keys()))
    
    # Symbol search
    st.subheader("Symbol")
    
    # Track which tab is being used
    search = st.text_input("Company name or ticker", placeholder="e.g. Apple, TSLA", key="symbol_search")
    
    if search and len(search) >= 2:
        try:
            from yfinance import Search
            results = Search(search, max_results=5, enable_fuzzy_query=True)
            if results.quotes:
                options = []
                for q in results.quotes:
                    name = q.get('shortname', q.get('longname', ''))
                    sym = q.get('symbol', '')
                    options.append(f"{sym} - {name}")
                
                selected = st.selectbox("Select from results", options, key="search_results")
                if selected:
                    symbol = selected.split(' - ')[0]
                    # Check if symbol changed
                    if st.session_state.get('selected_symbol') != symbol:
                        if 'results' in st.session_state:
                            del st.session_state['results']
                    st.session_state['selected_symbol'] = symbol
                    st.session_state['symbol_source'] = 'search'
            else:
                st.warning("No results found")
        except Exception as e:
            st.error(f"Search error: {e}")
    else:
        # Show database selector when not searching
        st.caption("Or select from database:")
        available = bridge.get_available_symbols()
        db_symbol = st.selectbox("Available symbols", available or ["AAPL"], key="db_symbols")
        if db_symbol:
            # Only update if not currently using search results
            if st.session_state.get('symbol_source') != 'search' or not search:
                if st.session_state.get('selected_symbol') != db_symbol:
                    if 'results' in st.session_state:
                        del st.session_state['results']
                st.session_state['selected_symbol'] = db_symbol
                st.session_state['symbol_source'] = 'database'
    
    # Get final symbol from session state
    symbol = st.session_state.get('selected_symbol', 'AAPL')
    
    # Date range
    st.subheader("Period")
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Start", value=datetime(2020, 1, 1))
    with col2:
        end = st.date_input("End", value=datetime.now())
    
    # Capital & Commission
    st.subheader("Trading")
    capital = st.number_input("Initial Capital ($)", value=10000, step=1000)
    commission = st.number_input("Commission (%)", value=0.1, step=0.05, format="%.2f")
    
    # Strategy parameters
    st.subheader("Parameters")
    strategy_params = {}
    params = bridge.get_strategy_params(recipe)
    
    for name, info in params.items():
        if isinstance(info['default'], bool):
            strategy_params[name] = st.checkbox(name.replace('_', ' ').title(), value=info['default'])
        elif isinstance(info['default'], int):
            strategy_params[name] = st.number_input(
                name.replace('_', ' ').title(),
                value=info['default'],
                step=1
            )
        elif isinstance(info['default'], float):
            strategy_params[name] = st.number_input(
                name.replace('_', ' ').title(),
                value=info['default'],
                step=0.1,
                format="%.2f"
            )
    
    st.divider()
    run_btn = st.button("▶ RUN BACKTEST", type="primary", width="stretch")

# ========== MAIN AREA ==========

# Run backtest
if run_btn:
    with st.spinner(f"Running backtest for {symbol}..."):
        try:
            results = bridge.run_recipe(
                recipe_name=recipe,
                symbol=symbol,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                initial_cash=capital,
                commission=commission / 100,
                **strategy_params
            )
            
            st.session_state['results'] = results
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.exception(e)

# Display results
if 'results' in st.session_state:
    results = st.session_state['results']
    
    # Symbol header with information
    st.markdown(f"""
    **{symbol}** · {results.get('period', 'N/A')} · Strategy: {recipe}
    """)
    st.caption(f"Initial Capital: ${capital:,.0f} · Commission: {commission}% · Total Bars: {len(results.get('data', [])) if results.get('data') is not None else 0}")
    st.divider()
    
    # Metrics row
    st.subheader("Results")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Return", f"{results.get('total_return', 0) or 0:.2f}%")
    with col2:
        st.metric("P&L", f"${results.get('total_pnl', 0) or 0:,.2f}")
    with col3:
        sharpe = results.get('sharpe_ratio', 0)
        st.metric("Sharpe", f"{sharpe if sharpe is not None else 0:.2f}")
    with col4:
        max_dd = results.get('max_drawdown', 0)
        st.metric("Max Drawdown", f"{max_dd if max_dd is not None else 0:.2f}%")
    with col5:
        st.metric("Total Trades", results.get('total_trades', 0) or 0)
    with col6:
        total = results.get('total_trades', 0) or 0
        won = results.get('won_trades', 0) or 0
        win_rate = (won / total * 100) if total > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    # Chart
    st.subheader("Price Chart")
    if 'data' in results and results['data'] is not None:
        fig = plot_price_chart(results['data'], symbol)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No chart data available")
    
    # Details in expander
    with st.expander("📊 Full Results"):
        st.json(results)

else:
    # Welcome message
    st.info("👈 Configure parameters in the sidebar and click RUN to start")
    
    # Example configuration
    st.subheader("Example Configuration")
    st.code(f"""
Symbol: {symbol}
Strategy: {recipe}
Period: {start} to {end}
Capital: ${capital:,.0f}
Commission: {commission}%
    """, language="text")
