# Logging e Rich UI - WawaStock

## Overview

O framework agora usa **Loguru** para logging estruturado e **Rich** para interface de usuário aprimorada no terminal.

## Instalação

```bash
pip install loguru rich
```

Ou instale todas as dependências:

```bash
pip install -r requirements.txt
```

## Loguru - Logging Estruturado

### Configuração Centralizada

O módulo `utils/logger.py` fornece configuração centralizada do Loguru:

```python
from utils.logger import get_logger, setup_logger

# Configurar logger (opcional - já inicializado por padrão)
setup_logger(
    level="INFO",                    # Nível de logging
    log_file="logs/wawastock.log",   # Arquivo de log
    rotation="10 MB",                # Rotação de arquivo
    retention="7 days",              # Retenção de logs
    colorize=True                    # Cores no console
)

# Obter logger para uso
logger = get_logger(__name__)
```

### Uso em Engines

Todas as engines herdam de `BaseEngine` e têm acesso ao logger:

```python
class MyEngine(BaseEngine):
    def run(self):
        self.logger.info("Iniciando engine")
        self.logger.debug("Informação de debug")
        self.logger.warning("Aviso importante")
        self.logger.error("Erro ocorrido")
```

### Uso em Strategies

Estratégias herdam de `BaseStrategy` e também têm logger:

```python
class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.logger.info("Estratégia inicializada")
    
    def next(self):
        self.logger.debug(f"Preço atual: {self.data.close[0]}")
```

### Níveis de Logging

- **DEBUG**: Informações detalhadas para debugging
- **INFO**: Informações gerais sobre o funcionamento
- **WARNING**: Avisos sobre situações potencialmente problemáticas
- **ERROR**: Erros que não interrompem a execução
- **CRITICAL**: Erros críticos que podem interromper o sistema

### Arquivos de Log

Os logs são salvos em:
- **Console**: Output colorido com formatação Rich
- **Arquivo**: `logs/wawastock.log` (rotacionado a cada 10 MB)
- **Compressão**: Logs antigos são comprimidos em ZIP
- **Retenção**: Logs mantidos por 7 dias

## Rich - Interface de Usuário

### Console Output

O framework usa Rich para output visualmente aprimorado:

```python
from rich.console import Console

console = Console()

# Print colorido
console.print("[green]✓ Sucesso![/green]")
console.print("[red]✗ Erro![/red]")
console.print("[yellow]⚠️  Aviso[/yellow]")
console.print("[cyan]ℹ️  Informação[/cyan]")
```

### Tabelas

Resultados são exibidos em tabelas formatadas:

```python
from rich.table import Table

table = Table(title="Backtest Results")
table.add_column("Metric", style="cyan")
table.add_column("Value", style="green")

table.add_row("Initial Value", "$100,000.00")
table.add_row("Final Value", "$125,000.00")
table.add_row("Return", "25.00%")

console.print(table)
```

### Progress Bars

Operações longas exibem indicadores de progresso:

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("[cyan]Running backtest...", total=100)
    # ... operação ...
    progress.update(task, advance=10)
```

### Panels

Seções importantes são destacadas com painéis:

```python
from rich.panel import Panel

console.print(Panel.fit(
    "[bold green]BACKTEST RESULTS[/bold green]",
    border_style="green"
))
```

## Exemplos de Uso

### CLI com Rich

```bash
python main.py run-strategy --strategy rsi --symbol AAPL --start 2020-01-01 --end 2020-12-31
```

Output:
```
╭─────────────────────────────────────╮
│ RUNNING STRATEGY: rsi               │
╰─────────────────────────────────────╯

Symbol:        AAPL
Period:        2020-01-01 to 2020-12-31
Initial Cash:  $100,000.00
Commission:    0.100%

✓ Loaded 252 bars of data

╭─────────────────────────────────────╮
│ BACKTEST RESULTS                    │
╰─────────────────────────────────────╯

┌─────────────────────────┬──────────────┐
│ Metric                  │ Value        │
├─────────────────────────┼──────────────┤
│ Initial Portfolio Value │ $100,000.00  │
│ Final Portfolio Value   │ $125,000.00  │
│ Profit/Loss             │ $25,000.00   │
│ Return                  │ 25.00%       │
└─────────────────────────┴──────────────┘
```

### Engine com Logging

```python
from engines.data_engine import DataEngine

engine = DataEngine()

# Logs automáticos
df = engine.load_prices("AAPL", "2020-01-01", "2020-12-31")
# INFO: Loading data for AAPL...
# INFO: Loaded 252 bars
```

### Strategy com Logging

```python
class MyStrategy(BaseStrategy):
    def next(self):
        if self.data.close[0] > self.sma[0]:
            self.logger.info(f"Buy signal at {self.data.close[0]}")
            self.buy()
```

## Personalização

### Alterar Nível de Log

```python
from utils.logger import setup_logger

# Modo debug para desenvolvimento
setup_logger(level="DEBUG")

# Modo silencioso para produção
setup_logger(level="WARNING")
```

### Customizar Formato de Log

Edite `utils/logger.py`:

```python
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)
```

### Desabilitar Cores

```python
setup_logger(colorize=False)
```

## Benefícios

### Loguru
- ✅ Configuração simples e intuitiva
- ✅ Formatação colorida automática
- ✅ Rotação e compressão de logs
- ✅ Stack traces melhores
- ✅ Binding de contexto

### Rich
- ✅ Output visual atraente
- ✅ Tabelas formatadas automaticamente
- ✅ Progress bars elegantes
- ✅ Painéis e bordas
- ✅ Syntax highlighting
- ✅ Emojis e ícones

## Referências

- [Loguru Documentation](https://loguru.readthedocs.io/)
- [Rich Documentation](https://rich.readthedocs.io/)
