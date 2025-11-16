wawastock/
# WawaStock Streamlit Interface – Plan & Status

This roadmap keeps the Streamlit experience aligned with the CLI engines. The UI reuses `DataEngine`, `BacktestEngine`, and `ReportEngine` through the same registries exposed in `main.py`, so every run—scripted or visual—produces identical results.

## Current Status (Nov 2025)

| Page / Feature | Purpose | Status | Shipped Highlights | Next Up |
|----------------|---------|--------|--------------------|---------|
| **📊 Backtest Runner** (`pages/1_📊_Backtest.py`) | Primary interface to launch recipes | ✅ Done | Recipe selector, parameter form, metrics cards, equity + price charts, trade table download | Add parameter presets per strategy + caching for repeated runs |
| **📈 Data Explorer** (`pages/1_Analysis.py` placeholder) | Visualize OHLCV + indicators | 🚧 In progress | Basic dataframe preview + placeholder charts | Finish Plotly candlestick with indicator toggles, descriptive stats, multi-symbol compare |
| **⚙️ Strategy Builder** | Build custom logic visually/code editor | 💤 Not started | – | Drag-and-drop condition builder, Monaco editor, quick-test harness |
| **📉 Performance Analysis** | Compare strategies & risk metrics | 💤 Not started | – | Equity curve overlay, Monte Carlo sim, risk table |
| **💾 Data Manager** | Manage downloads/cache/inventory | 💤 Not started | – | Symbol inventory, cache clear, bulk download UI |

Legend: ✅ complete · 🚧 in progress · 💤 planned

## File Layout

```
4. **Responsive grids**: Adaptar colunas ao espaço disponível
├── streamlit_app.py        # Entry point (multipage redirect)
├── pages/                  # Native Streamlit pages (per filename prefix)
│   ├── 1_📊_Backtest.py    # Shipped page
│   └── 1_Analysis.py       # Placeholder for Data Explorer
├── streamlit_components/   # Shared widgets/helpers
│   ├── charts.py           # Plotly charts (equity, candlestick, drawdown)
│   ├── metrics.py          # KPI cards + delta logic
│   ├── tables.py           # Trade/position tables
│   └── bridge.py           # StreamlitBridge (DataEngine + BacktestEngine)
└── main.py                 # CLI/recipe definitions reused by the bridge
```

## Data Flow

1. User selects a recipe/strategy and parameters in Streamlit.
2. `StreamlitBridge` calls `run_recipe_programmatic()` from `main.py`, ensuring the same engines as the CLI.
3. `BacktestEngine` returns a results dict containing analyzers, equity curve, and trades.
4. Streamlit components render metrics, charts, and tables; optional exports stream from the same data.

No direct database writes occur from Streamlit—`DataEngine` handles caching/Parquet persistence, so CLI and UI remain in sync.

## Page Breakdown

### 📊 Backtest Runner (Shipped)

- **Controls**: recipe selector, symbol input, date pickers, advanced expanders for cash/commission/strategy params.
- **Status messaging**: spinners for “Loading data” → “Running backtest”, plus Rich/ReportEngine logs in the terminal.
- **Visuals**: KPI cards (`metrics.py`), Plotly equity and price+indicator charts (`charts.py`), drawdown tab, trade table with CSV download.
- **Next enhancements**: saved parameter presets per strategy, ability to pin multiple runs for side-by-side comparison, caching of last run per session.

### 📈 Data Explorer (In Progress)

- **Goal**: interactive OHLCV explorer with indicator toggles, descriptive stats, and multi-symbol correlation.
- **Current**: placeholder page referencing `DataEngine` to load data.
- **Planned**: Plotly candlestick with overlays (SMA, EMA, Bollinger, VWAP), RSI/MACD subplots, stats cards (min/max/avg), correlation heatmap, export controls.

### ⚙️ Strategy Builder (Planned)

- **Phase 1**: Form-based condition builder (IF/AND/OR), indicator selector pulled from `IndicatorsEngine` presets.
- **Phase 2**: Monaco editor to tweak Python strategy templates inline.
- **Phase 3**: Quick-test harness for short backtests with immediate results.

### 📉 Performance Analysis (Planned)

- Compare multiple strategies/runs via uploaded CSVs or session cache.
- Monte Carlo simulator (bootstrap trade returns) with confidence intervals.
- Advanced risk metrics (VaR/CVaR/Beta) and trade distribution visuals.

### 💾 Data Manager (Planned)

- Symbol inventory table (rows, date range, indicator columns, file size).
- Cache management (clear symbol, refresh indicators, rebuild DuckDB indexes).
- Bulk downloader leveraging existing `scripts/download_*` utilities.

## Shared Components

- **`streamlit_components/bridge.py`** – wraps `DataEngine` + `BacktestEngine`; ensures the UI never directly instantiates recipes.
- **`charts.py`** – Plotly builders (`plot_equity_curve`, `plot_candlestick_with_indicators`, `plot_drawdown`, `plot_returns_distribution`).
- **`metrics.py`** – Reusable `st.metric` layouts, with helper functions for formatting currency/percent deltas.
- **`tables.py`** – DataFrame -> AgGrid/native tables + CSV download utilities.

## Tech Stack

- `streamlit` ≥ 1.30 (multipage support, native themes)
- `plotly` ≥ 5.18 for interactive charts
- `pandas`, `numpy` (already core dependencies)
- Optional: `streamlit-aggrid`, `streamlit-extras`, `altair` for advanced tables/visuals (install as needed)

## Delivery Phases

1. **Foundation (complete)** – Setup scripts (`start.sh`), base Backtest Runner, bridge module, metrics & charts components.
2. **Visual Enhancements (in progress)** – Enrich Backtest Runner visuals, finalize Data Explorer candlestick/drawdown charts.
3. **Analysis Suite (planned)** – Performance comparison, Monte Carlo, strategy builder MVP.
4. **Data Management (planned)** – Inventory, cache control, bulk download UI.
5. **Polish** – Theme toggles, responsive tweaks, tooltip docs, error boundary improvements.

## Design Notes

- **Layout**: Use `st.set_page_config(layout="wide")`, with sidebar for navigation and top-level controls.
- **Color palette**: reuse the Rich/CLI palette (`primary` blue `#1f77b4`, `success` green `#2ca02c`, `danger` red `#d62728`, `warning` orange `#ff7f0e`, `info` cyan `#17becf`).
- **Consistency**: Metric labels, icons, and table headers should match ReportEngine wording (Initial Value, Final Value, Profit/Loss, etc.).

## Next Steps Checklist

- [ ] Finish Data Explorer visuals + stats block.
- [ ] Add caching/preset support to Backtest Runner forms.
- [ ] Scaffold Strategy Builder page with placeholder controls.
- [ ] Define shared theme constants for colors/spacing across charts and cards.

This document will continue to track the Streamlit roadmap so contributors can see exactly what’s done versus what’s in flight.

---

## Integração com CLI

### Manter CLI Intacto
- `main.py` permanece **100% funcional**
- Streamlit é um **frontend adicional**
- Ambos usam os mesmos engines e strategies
- Zero duplicação de lógica

### Shared Code
```
wawastock/
├── engines/           # Compartilhado
├── strategies/        # Compartilhado
├── recipes/           # Compartilhado
├── main.py           # CLI (intacto)
└── streamlit_app.py  # Web UI (novo)
```

---

## Métricas de Sucesso

### Funcionalidade
- ✅ Todos os recipes executáveis via UI
- ✅ Todos os parâmetros configuráveis
- ✅ Resultados visualmente claros
- ✅ Performance similar ao CLI

### Usabilidade
- ✅ Interface intuitiva (não precisa manual)
- ✅ Feedback visual de ações
- ✅ Handling de erros user-friendly
- ✅ Tempo de resposta < 5s para backtests

### Manutenibilidade
- ✅ Código modular e reutilizável
- ✅ Separação clara UI/Logic
- ✅ Fácil adicionar novos recipes
- ✅ Testes unitários para componentes

---

## Próximos Passos

1. **Aprovação do plano** pelo usuário
2. **Fase 1**: Setup e estrutura básica
3. **Fase 2**: Implementar página principal de Backtest
4. **Testes e iteração**: Validar com usuário
5. **Fases seguintes**: Expandir funcionalidades

---

## Notas Técnicas

### Session State Management
```python
# Persistir dados entre interações
st.session_state.backtest_results = results
st.session_state.selected_symbol = "AAPL"
st.session_state.data_cache = {}
```

### Caching para Performance
```python
@st.cache_data
def load_symbol_data(symbol: str) -> pd.DataFrame:
    """Cache data loading"""
    
@st.cache_resource
def get_data_engine() -> DataEngine:
    """Cache engine initialization"""
```

### Error Handling
```python
try:
    results = bridge.run_recipe(recipe_name, **params)
    st.success("Backtest completed!")
except Exception as e:
    st.error(f"Error running backtest: {str(e)}")
    st.exception(e)  # Show traceback in expander
```

---

## Referências
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [Demo Stockpeers](https://github.com/streamlit/demo-stockpeers) - Inspiração para UI
- [Streamlit Gallery](https://streamlit.io/gallery) - Exemplos de dashboards
