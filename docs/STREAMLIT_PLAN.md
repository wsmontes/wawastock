# WawaStock Streamlit Interface - Plano Completo

## Objetivo
Criar uma interface web moderna e interativa usando Streamlit para o WawaStock, mantendo **100% das funcionalidades CLI** intactas e funcionais.

---

## Arquitetura da Solução

### Estrutura de Arquivos
```
wawastock/
├── streamlit_app.py          # Aplicação principal Streamlit
├── streamlit_pages/          # Páginas multi-page app
│   ├── 1_📊_Backtest.py
│   ├── 2_📈_Data_Explorer.py
│   ├── 3_⚙️_Strategy_Builder.py
│   ├── 4_📉_Performance_Analysis.py
│   └── 5_💾_Data_Manager.py
├── streamlit_components/     # Componentes reutilizáveis
│   ├── __init__.py
│   ├── charts.py            # Gráficos com Plotly/Altair
│   ├── metrics.py           # Cards de métricas
│   ├── tables.py            # Tabelas de dados
│   └── forms.py             # Formulários de configuração
└── main.py                   # CLI mantido intacto
```

---

## Páginas da Aplicação

### 📊 Página 1: Backtest Runner (Principal)
**Objetivo**: Interface principal para executar backtests de forma visual e interativa

#### Layout
```
┌─────────────────────────────────────────────────────────┐
│ 🎯 WawaStock - Backtesting Framework                   │
├─────────────────────────────────────────────────────────┤
│ SIDEBAR                  │ MAIN CONTENT                 │
│                          │                              │
│ [Recipe Selection]       │ ┌─ Configuration ─────────┐ │
│ ○ Sample SMA             │ │ Symbol: [AAPL     ▼]    │ │
│ ○ RSI                    │ │ Period: [2020-2023]     │ │
│ ● MACD+EMA               │ │ Initial Cash: $100,000  │ │
│ ○ Bollinger+RSI          │ └─────────────────────────┘ │
│ ○ Multi-Timeframe        │                              │
│                          │ ┌─ Strategy Parameters ───┐ │
│ [Symbol Input]           │ │ MACD Fast: [12]         │ │
│ [Date Range Picker]      │ │ MACD Slow: [26]         │ │
│ [Advanced Options]       │ │ EMA Period: [200]       │ │
│                          │ │ Position Size: [95%]    │ │
│ [🚀 Run Backtest]        │ └─────────────────────────┘ │
│                          │                              │
│                          │ [Run Backtest Button]        │
└──────────────────────────┴──────────────────────────────┘
```

#### Funcionalidades
1. **Seleção de Strategy/Recipe**
   - Radio buttons ou selectbox para escolher recipe
   - Descrição dinâmica de cada estratégia
   - Preview dos parâmetros disponíveis

2. **Configuração de Parâmetros**
   - Símbolo: Autocomplete com sugestões (AAPL, MSFT, BTC-USD, ETH-USD)
   - Date range picker para período
   - Sliders para initial_cash, commission
   - Parâmetros específicos da estratégia (dinâmicos)

3. **Execução do Backtest**
   - Progress bar durante execução
   - Spinner com status (Loading data → Calculating indicators → Running backtest)
   - Integração direta com BacktestEngine

4. **Visualização de Resultados**
   - **Métricas principais** (cards grandes):
     - Initial Value vs Final Value
     - Total Return (%)
     - Profit/Loss ($)
   - **Métricas secundárias** (cards menores):
     - Sharpe Ratio
     - Max Drawdown
     - Total Trades
     - Win Rate
   
5. **Gráficos Interativos**
   - **Equity Curve**: Evolução do portfólio ao longo do tempo
   - **Price Chart**: Preço + Indicadores + Pontos de entrada/saída
   - **Drawdown Chart**: Visualização de drawdowns
   - **Returns Distribution**: Histograma de retornos

6. **Tabela de Trades**
   - Lista de todas as operações
   - Colunas: Date, Type (Buy/Sell), Price, Size, PnL, %
   - Filtros e ordenação
   - Export para CSV

---

### 📈 Página 2: Data Explorer
**Objetivo**: Explorar e visualizar dados OHLCV com indicadores

#### Funcionalidades
1. **Seleção de Dados**
   - Dropdown com símbolos disponíveis no banco
   - Upload de novos dados
   - Date range selection

2. **Visualização**
   - Candlestick chart interativo (Plotly)
   - Sobreposição de indicadores (toggle on/off):
     - Moving Averages (SMA, EMA)
     - Bollinger Bands
     - Volume bars
   - Subgráficos:
     - RSI
     - MACD
     - Stochastic
     - OBV

3. **Estatísticas Descritivas**
   - Summary statistics (mean, std, min, max)
   - Correlation matrix dos indicadores
   - Missing data analysis

4. **Comparação Multi-Symbol**
   - Selecionar múltiplos símbolos
   - Normalized price comparison
   - Correlation heatmap

---

### ⚙️ Página 3: Strategy Builder
**Objetivo**: Criar e testar estratégias customizadas (futuro)

#### Funcionalidades (Roadmap)
1. **Visual Strategy Builder**
   - Drag-and-drop conditions
   - Logic builder (IF/AND/OR)
   - Indicator selector

2. **Code Editor**
   - Monaco editor para editar código Python
   - Syntax highlighting
   - Auto-completion

3. **Quick Test**
   - Fast backtest com período curto
   - Validation de estratégia

---

### 📉 Página 4: Performance Analysis
**Objetivo**: Análise detalhada de performance e comparação

#### Funcionalidades
1. **Compare Strategies**
   - Selecionar múltiplas estratégias
   - Comparar side-by-side:
     - Returns
     - Sharpe Ratio
     - Max Drawdown
     - Win Rate
   - Gráfico comparativo de equity curves

2. **Monte Carlo Simulation**
   - Simular múltiplos cenários
   - Distribution of outcomes
   - Confidence intervals

3. **Risk Analysis**
   - Value at Risk (VaR)
   - Conditional VaR
   - Beta vs market
   - Volatility analysis

4. **Trade Analysis**
   - Average win/loss
   - Profit factor
   - Expectancy
   - Best/worst trades

---

### 💾 Página 5: Data Manager
**Objetivo**: Gerenciar dados, cache e downloads

#### Funcionalidades
1. **Data Inventory**
   - Tabela com todos os símbolos no banco
   - Info: Symbol, Rows, Date Range, Size, Indicators
   - Actions: View, Download, Delete

2. **Bulk Download**
   - Upload CSV com lista de símbolos
   - Download de múltiplos símbolos
   - Progress tracking

3. **Cache Management**
   - View cache info
   - Clear cache by symbol/date
   - Cache statistics

4. **Data Quality**
   - Check missing data
   - Validate indicator calculations
   - Re-calculate indicators button

---

## Componentes Técnicos

### 1. `streamlit_app.py` - Aplicação Principal
```python
import streamlit as st
from streamlit_pages import backtest, data_explorer, strategy_builder

st.set_page_config(
    page_title="WawaStock",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None

# Main page
st.title("🎯 WawaStock Backtesting Framework")
st.markdown("Professional-grade backtesting for trading strategies")

# Navigation handled by streamlit multi-page
```

### 2. `streamlit_components/charts.py`
```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def plot_equity_curve(results: dict) -> go.Figure:
    """Plot portfolio equity curve"""
    
def plot_candlestick_with_indicators(df: pd.DataFrame, indicators: list) -> go.Figure:
    """Interactive candlestick chart with indicators"""
    
def plot_drawdown(equity_curve: pd.Series) -> go.Figure:
    """Drawdown chart"""
    
def plot_returns_distribution(returns: pd.Series) -> go.Figure:
    """Histogram of returns"""
```

### 3. `streamlit_components/metrics.py`
```python
def display_performance_metrics(results: dict):
    """Display key performance metrics in cards"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Return",
            f"{results['total_return']:.2f}%",
            delta=f"${results['profit_loss']:,.2f}"
        )
```

### 4. Bridge entre Streamlit e WawaStock
```python
# streamlit_components/bridge.py
from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from recipes import RECIPE_REGISTRY

class StreamlitBridge:
    """Bridge between Streamlit UI and WawaStock engines"""
    
    def __init__(self):
        self.data_engine = DataEngine()
        self.backtest_engine = BacktestEngine()
    
    def run_recipe(self, recipe_name: str, **kwargs) -> dict:
        """Run a recipe and return results in Streamlit-friendly format"""
        recipe_cls = RECIPE_REGISTRY[recipe_name]
        recipe = recipe_cls(self.data_engine, self.backtest_engine)
        results = recipe.run(**kwargs)
        return self._format_results(results)
    
    def _format_results(self, results: dict) -> dict:
        """Format results for Streamlit display"""
        # Convert to JSON-serializable format
        # Extract equity curve, trades list, metrics
        return formatted_results
```

---

## Tecnologias e Bibliotecas

### Core
- **streamlit**: ^1.30.0 - Framework principal
- **plotly**: ^5.18.0 - Gráficos interativos
- **altair**: ^5.2.0 - Gráficos declarativos (alternativa)

### Data Viz
- **pandas**: Already installed
- **numpy**: Already installed
- **matplotlib**: Backup para gráficos estáticos

### UI Components
- **streamlit-aggrid**: Tabelas avançadas com filtros
- **streamlit-option-menu**: Menu lateral customizado
- **streamlit-card**: Cards de métricas
- **streamlit-extras**: Componentes adicionais

### Optional Enhancements
- **streamlit-authenticator**: Login/autenticação (futuro)
- **streamlit-autorefresh**: Auto-refresh de dados
- **streamlit-pdf-viewer**: Export de relatórios

---

## Fluxo de Desenvolvimento

### Fase 1: Setup e Estrutura Básica (Prioridade 1)
1. ✅ Instalar Streamlit e dependências
2. ✅ Criar `streamlit_app.py` com página principal
3. ✅ Criar estrutura de pastas (`streamlit_pages/`, `streamlit_components/`)
4. ✅ Implementar `StreamlitBridge` para integração com engines
5. ✅ Criar página de Backtest básica

### Fase 2: Página Principal de Backtest (Prioridade 1)
1. ✅ Sidebar com seleção de recipe
2. ✅ Formulário de parâmetros dinâmico
3. ✅ Botão de execução com progress
4. ✅ Display de métricas principais
5. ✅ Gráfico de equity curve básico
6. ✅ Tabela de trades

### Fase 3: Visualizações Avançadas (Prioridade 2)
1. 📊 Candlestick chart com indicadores
2. 📊 Drawdown chart
3. 📊 Returns distribution
4. 📊 Trade markers no gráfico de preço

### Fase 4: Data Explorer (Prioridade 2)
1. 📈 Página de exploração de dados
2. 📈 Candlestick interativo
3. 📈 Toggles de indicadores
4. 📈 Multi-symbol comparison

### Fase 5: Performance Analysis (Prioridade 3)
1. 📉 Página de análise comparativa
2. 📉 Compare strategies
3. 📉 Risk metrics
4. 📉 Trade analysis

### Fase 6: Data Manager (Prioridade 3)
1. 💾 Página de gerenciamento
2. 💾 Data inventory
3. 💾 Bulk download
4. 💾 Cache management

### Fase 7: Polish e Otimizações (Prioridade 4)
1. 🎨 Tema customizado
2. 🎨 Responsividade mobile
3. 🎨 Dark mode
4. ⚡ Performance optimization (caching)
5. ⚡ Error handling
6. 📝 Help tooltips e documentação inline

---

## Design System

### Paleta de Cores
```python
COLORS = {
    'primary': '#1f77b4',      # Blue
    'success': '#2ca02c',      # Green (profit)
    'danger': '#d62728',       # Red (loss)
    'warning': '#ff7f0e',      # Orange
    'info': '#17becf',         # Cyan
    'neutral': '#7f7f7f',      # Gray
}
```

### Typography
- Headers: Bold, size hierarchy (H1, H2, H3)
- Metrics: Large, bold numbers
- Body text: Regular, readable size
- Code: Monospace for símbolos e valores técnicos

### Layout Principles
1. **Wide layout**: Aproveitar espaço horizontal
2. **Card-based**: Agrupar informações relacionadas em containers
3. **Progressive disclosure**: Detalhes em expanders/tabs
4. **Responsive grids**: Adaptar colunas ao espaço disponível

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
