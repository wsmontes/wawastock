"""
WawaStock Backtest - Home/Backtest Page
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from streamlit_components.bridge import StreamlitBridge
from streamlit_components.charts import plot_price_chart

# Page config
st.set_page_config(
    page_title="WawaStock Backtest",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize bridge
bridge = StreamlitBridge()

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("Configuration")
    
    # Run button at the top
    run_btn = st.button("▶ RUN BACKTEST", use_container_width=True)
    st.divider()
    
    # Recipe selection
    recipes = bridge.get_recipe_registry()
    recipe = st.selectbox("Strategy", list(recipes.keys()))
    
    # Symbol search
    st.subheader("Symbol")
    
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
                    if st.session_state.get('selected_symbol') != symbol:
                        if 'results' in st.session_state:
                            del st.session_state['results']
                    st.session_state['selected_symbol'] = symbol
            else:
                st.warning("No results found")
        except Exception as e:
            st.error(f"Search error: {e}")
    else:
        st.caption("Or select from database:")
        available = bridge.get_available_symbols()
        db_symbol = st.selectbox("Available symbols", available or ["AAPL"], key="db_symbols")
        if db_symbol:
            symbol = db_symbol
            if st.session_state.get('selected_symbol') != symbol:
                if 'results' in st.session_state:
                    del st.session_state['results']
            st.session_state['selected_symbol'] = symbol
    
    # Get final symbol
    symbol = st.session_state.get('selected_symbol', 'AAPL')
    st.info(f"Selected: **{symbol}**")
    
    # Date range
    st.subheader("Period")
    from datetime import datetime, timedelta
    default_end = datetime.now()
    default_start = datetime(2020, 1, 1)  # Fixed date with plenty of data
    
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Start", value=default_start)
    with col2:
        end = st.date_input("End", value=default_end)
    
    # Capital and commission
    st.subheader("Capital")
    capital = st.number_input("Initial Capital ($)", value=10000, step=1000)
    commission = st.number_input("Commission (%)", value=0.001, step=0.001, format="%.3f")
    
    # Strategy parameters
    st.subheader("Parameters")
    strategy_params = bridge.get_strategy_params(recipe)
    params = {}
    for name, default_value in strategy_params.items():
        params[name] = st.number_input(
            name.replace('_', ' ').title(),
            value=default_value,
            key=f"param_{name}"
        )

# ========== MAIN CONTENT ==========
if run_btn:
    with st.spinner("Running backtest..."):
        try:
            results = bridge.run_recipe(
                recipe_name=recipe,
                symbol=symbol,
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d'),
                initial_cash=capital,
                commission=commission,
                **params
            )
            if results:
                st.session_state['results'] = results
                st.session_state['last_symbol'] = symbol
            else:
                st.error("Backtest failed. Check the logs for details.")
        except Exception as e:
            st.error(f"Error running backtest: {str(e)}")

if 'results' in st.session_state and st.session_state['results']:
    results = st.session_state['results']
    symbol = st.session_state.get('last_symbol', symbol)
    
    # Metrics
    st.subheader("Results")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        final_value = results.get('final_value', 0)
        st.metric("Final Value", f"${final_value:,.2f}")
    
    with col2:
        total_return = results.get('total_return', 0)
        st.metric("Total Return", f"{total_return:.2f}%")
    
    with col3:
        sharpe = results.get('sharpe_ratio')
        st.metric("Sharpe Ratio", f"{sharpe:.3f}" if sharpe is not None else "N/A")
    
    with col4:
        trades = results.get('total_trades', 0)
        st.metric("Total Trades", trades)
    
    # Chart
    st.subheader("Price Chart")
    if 'data' in results and results['data'] is not None:
        fig = plot_price_chart(results['data'], symbol)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No chart data available")
    
    # Details in expander
    with st.expander("📊 Full Results"):
        st.json(results)

else:
    st.info("👈 Configure parameters in the sidebar and click RUN to start")
    
    st.subheader("Quick Start")
    st.markdown("""
    1. Select a **strategy** from the sidebar
    2. Choose a **symbol** (search or pick from database)
    3. Set **date range** and **capital**
    4. Adjust strategy **parameters** if needed
    5. Click **RUN BACKTEST**
    """)
