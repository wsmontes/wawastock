"""
Backtest Terminal
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamlit_components.bridge import StreamlitBridge
from streamlit_components.charts import plot_price_chart

# Page config
st.set_page_config(
    page_title="Backtest",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - VSCode inspired
st.markdown("""
<style>
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* VSCode dark theme */
    .stApp {
        background-color: #1e1e1e;
        color: #cccccc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Compact spacing */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 20px;
        font-weight: 600;
        color: #4ec9b0;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 11px;
        color: #858585;
        text-transform: none;
    }
    
    /* Input styling */
    .stTextInput input, .stNumberInput input {
        background-color: #2d2d30;
        color: #cccccc;
        border: 1px solid #3e3e42;
        font-size: 13px;
        padding: 0.5rem;
        border-radius: 2px;
    }
    
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #007acc;
        outline: none;
    }
    
    /* Button styling */
    .stButton button {
        background-color: #007acc;
        color: #ffffff;
        border: none;
        font-weight: 500;
        width: 100%;
        font-size: 14px;
        padding: 0.6rem;
        border-radius: 2px;
    }
    
    .stButton button:hover {
        background-color: #005a9e;
    }
    
    /* Selectbox styling */
    .stSelectbox [data-baseweb="select"] {
        background-color: #2d2d30;
        border-color: #3e3e42;
        font-size: 13px;
    }
    
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #2d2d30;
        border-color: #3e3e42;
    }
    
    /* Date input */
    .stDateInput input {
        background-color: #2d2d30;
        color: #cccccc;
        border: 1px solid #3e3e42;
        font-size: 13px;
    }
    
    .stDateInput > div > div {
        background-color: #2d2d30;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #cccccc;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 0.5rem;
        margin-top: 1rem;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #252526;
        border-right: 1px solid #3e3e42;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #cccccc;
    }
    
    /* Labels */
    label {
        color: #cccccc;
        font-size: 13px;
    }
    
    /* Dividers */
    hr {
        border-color: #3e3e42;
        margin: 0.8rem 0;
    }
    
    /* Info messages */
    .stInfo {
        background-color: #2d2d30;
        color: #cccccc;
        border-left: 4px solid #007acc;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: #1e3a1e;
        color: #4ec9b0;
        border-left: 4px solid #4ec9b0;
    }
    
    /* Error messages */
    .stError {
        background-color: #3a1e1e;
        color: #f48771;
        border-left: 4px solid #f48771;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #007acc;
    }
</style>
""", unsafe_allow_html=True)

# Initialize bridge
if 'bridge' not in st.session_state:
    st.session_state.bridge = StreamlitBridge()

bridge = st.session_state.bridge

# SIDEBAR - PARAMETERS
with st.sidebar:
    # RUN BUTTON AT TOP
    run_backtest = st.button("▶ Run Backtest", use_container_width=True, type="primary")
    
    st.markdown("---")
    
    st.markdown("### Strategy")
    
    recipes = bridge.get_recipe_registry()
    recipe_names = list(recipes.keys())
    
    selected_recipe = st.selectbox(
        "Recipe",
        options=recipe_names,
        label_visibility="collapsed"
    )
    
    st.markdown("### Instrument")
    symbol = st.text_input(
        "Symbol",
        value="AAPL",
        label_visibility="collapsed"
    ).upper()
    
    st.markdown("### Timeframe")
    start_date = st.date_input(
        "Start date",
        value=datetime(2020, 1, 1),
        label_visibility="collapsed"
    )
    end_date = st.date_input(
        "End date",
        value=datetime(2023, 12, 31),
        label_visibility="collapsed"
    )
    
    st.markdown("### Capital")
    initial_cash = st.number_input(
        "Initial cash",
        min_value=1000.0,
        value=100000.0,
        step=10000.0,
        format="%.0f",
        label_visibility="collapsed"
    )
    
    commission = st.number_input(
        "Commission %",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.01,
        format="%.2f"
    ) / 100
    
    st.markdown("---")
    
    # Strategy parameters
    strategy_params = {}
    strategy_map = {
        'sample': 'sample_sma',
        'rsi': 'rsi',
        'macd_ema': 'macd_ema',
        'bollinger_rsi': 'bollinger_rsi',
        'multi_timeframe': 'multi_timeframe',
    }
    
    if selected_recipe:
        strategy_name = strategy_map.get(selected_recipe)
        if strategy_name:
            params_dict = bridge.get_strategy_params(strategy_name)
            
            if params_dict:
                st.markdown("### Parameters")
                for param_name, default_value in params_dict.items():
                    if isinstance(default_value, (int, float)):
                        value = st.number_input(
                            param_name.replace('_', ' ').title(),
                            value=float(default_value),
                            key=f"param_{param_name}"
                        )
                        strategy_params[param_name] = value
                    elif isinstance(default_value, str):
                        value = st.text_input(
                            param_name.replace('_', ' ').title(),
                            value=default_value,
                            key=f"param_{param_name}"
                        )
                        strategy_params[param_name] = value

# MAIN CONTENT
if run_backtest:
    with st.spinner("Running backtest..."):
        try:
            # Run backtest
            results = bridge.run_recipe(
                recipe_name=selected_recipe,
                symbol=symbol,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                initial_cash=initial_cash,
                commission=commission,
                **strategy_params
            )
            
            # Store results in session state
            st.session_state.results = results
            st.success("✓ Backtest completed")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.session_state.results = None

st.markdown("---")

# Main layout - 2 columns: chart and metrics
col_chart, col_metrics = st.columns([5, 2])

# Get results from session state
results = st.session_state.get('results')

# CHART PANEL
with col_chart:
    if results and 'data' in results:
        df = results['data']
        fig = plot_price_chart(df, symbol)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Run backtest to see chart")

# METRICS PANEL
with col_metrics:
    if results:
        st.markdown("### Performance")
        
        # Total return
        total_ret = results.get('total_return', 0)
        total_val = total_ret if total_ret else 0
        st.metric("Return", f"{total_val:.2f}%")
        
        # P&L
        pnl = results.get('total_pnl', 0)
        pnl_val = pnl if pnl else 0
        st.metric("P&L", f"${pnl_val:,.2f}")
        
        # Sharpe
        sharpe = results.get('sharpe_ratio', 0)
        sharpe_val = sharpe if sharpe else 0
        st.metric("Sharpe Ratio", f"{sharpe_val:.3f}")
        
        # Max DD
        dd = results.get('max_drawdown', 0)
        dd_val = dd if dd else 0
        st.metric("Max Drawdown", f"{dd_val:.2f}%")
        
        # Annual return
        ann = results.get('total_return_ann', 0)
        ann_val = ann if ann else 0
        st.metric("Annual Return", f"{ann_val:.2f}%")
        
        st.markdown("---")
        st.markdown("### Portfolio")
        
        # Final value
        final = results.get('final_value', 0)
        final_val = final if final else 0
        st.metric("Final Value", f"${final_val:,.0f}")
        
        # Starting value
        st.metric("Starting Value", f"${initial_cash:,.0f}")
        
        st.markdown("---")
        st.markdown("### Trades")
        
        # Total trades
        trades = results.get('total_trades', 0)
        st.metric("Total", f"{trades}")
        
        # Won trades
        won = results.get('won_trades', 0)
        st.metric("Won", f"{won}")
        
        # Lost trades
        lost = results.get('lost_trades', 0)
        st.metric("Lost", f"{lost}")
        
        # Win rate
        if trades > 0:
            win_rate = (won / trades) * 100
            st.metric("Win Rate", f"{win_rate:.1f}%")
        
    else:
        st.info("Run backtest to see metrics")
