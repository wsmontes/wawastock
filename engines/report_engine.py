"""
Report Engine - Centralized reporting and output formatting.

Handles all terminal output with Rich formatting and Loguru logging.
"""

from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .base_engine import BaseEngine


console = Console()


class ReportEngine(BaseEngine):
    """
    Engine responsible for all terminal output and reporting.
    
    Features:
    - Standardized output formatting with Rich
    - Automatic logging with Loguru
    - Progress tracking
    - Results presentation
    """
    
    def __init__(self):
        """Initialize the ReportEngine."""
        super().__init__()
    
    def run(self):
        """Not implemented for ReportEngine."""
        raise NotImplementedError("ReportEngine doesn't have a general run() method.")
    
    def print_strategy_header(
        self,
        strategy_name: str,
        symbol: str,
        start: str,
        end: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Print strategy header with configuration.
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            start: Start date
            end: End date
            params: Optional strategy parameters to display
        """
        self.logger.info(f"Starting backtest: {strategy_name} on {symbol}")
        
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]{strategy_name}[/bold cyan]",
            border_style="cyan"
        ))
        
        # Basic info table
        info_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Symbol", symbol)
        info_table.add_row("Period", f"{start} to {end}")
        
        # Add parameters if provided
        if params:
            for key, value in params.items():
                formatted_key = key.replace('_', ' ').title()
                info_table.add_row(formatted_key, str(value))
        
        console.print(info_table)
        console.print()
    
    def print_step(self, message: str, status: str = "info"):
        """
        Print a step message with appropriate styling.
        
        Args:
            message: Message to display
            status: Status type (info, success, warning, error)
        """
        icons = {
            "info": "ℹ️",
            "success": "✓",
            "warning": "⚠️",
            "error": "✗"
        }
        
        colors = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }
        
        icon = icons.get(status, "•")
        color = colors.get(status, "white")
        
        console.print(f"[{color}]{icon} {message}[/{color}]")
        
        # Log appropriately
        if status == "error":
            self.logger.error(message)
        elif status == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def print_data_summary(self, rows: int, start_date: str, end_date: str):
        """
        Print data loading summary.
        
        Args:
            rows: Number of data rows loaded
            start_date: First date in dataset
            end_date: Last date in dataset
        """
        self.print_step(f"Loaded {rows:,} bars of data ({start_date} to {end_date})", "success")
        console.print()
    
    def create_progress_context(self, description: str = "Running backtest..."):
        """
        Create a progress context for long-running operations.
        
        Args:
            description: Description of the operation
            
        Returns:
            Progress context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        )
    
    def print_backtest_results(self, results: Dict[str, Any]):
        """
        Print backtest results in a standardized format.
        
        Args:
            results: Dictionary containing backtest results
        """
        self.logger.info(f"Backtest completed - Return: {results['return_pct']:.2f}%")
        
        console.print()
        console.print(Panel.fit(
            "[bold]BACKTEST RESULTS[/bold]",
            border_style="green" if results['pnl'] >= 0 else "red"
        ))
        
        # Results table
        results_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
        results_table.add_column("Metric", style="cyan", no_wrap=True)
        results_table.add_column("Value", style="bold", justify="right")
        
        # Core metrics
        results_table.add_row("Initial Value", f"${results['initial_value']:>12,.2f}")
        results_table.add_row("Final Value", f"${results['final_value']:>12,.2f}")
        
        # P&L with color
        pnl_color = "green" if results['pnl'] >= 0 else "red"
        results_table.add_row(
            "Profit/Loss",
            f"[{pnl_color}]${results['pnl']:>12,.2f}[/{pnl_color}]"
        )
        
        # Return % with color
        return_color = "green" if results['return_pct'] >= 0 else "red"
        results_table.add_row(
            "Total Return",
            f"[{return_color}]{results['return_pct']:>11.2f}%[/{return_color}]"
        )
        
        console.print(results_table)
        
        # Analyzers (if available)
        if results.get('analyzers'):
            analyzers = results['analyzers']
            
            if any(analyzers.values()):
                console.print()
                
                analyzer_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
                analyzer_table.add_column("Metric", style="cyan", no_wrap=True)
                analyzer_table.add_column("Value", style="bold", justify="right")
                
                if 'sharpe' in analyzers and analyzers['sharpe'] is not None:
                    sharpe_color = "green" if analyzers['sharpe'] > 1 else "yellow" if analyzers['sharpe'] > 0 else "red"
                    analyzer_table.add_row(
                        "Sharpe Ratio",
                        f"[{sharpe_color}]{analyzers['sharpe']:>12.3f}[/{sharpe_color}]"
                    )
                
                if 'max_drawdown' in analyzers and analyzers['max_drawdown'] is not None:
                    dd_color = "green" if analyzers['max_drawdown'] < 10 else "yellow" if analyzers['max_drawdown'] < 20 else "red"
                    analyzer_table.add_row(
                        "Max Drawdown",
                        f"[{dd_color}]{analyzers['max_drawdown']:>11.2f}%[/{dd_color}]"
                    )
                
                if 'total_return' in analyzers and analyzers['total_return'] is not None:
                    ret_color = "green" if analyzers['total_return'] > 0 else "red"
                    analyzer_table.add_row(
                        "Total Return (Ann.)",
                        f"[{ret_color}]{analyzers['total_return']:>11.2f}%[/{ret_color}]"
                    )
                
                console.print(analyzer_table)
        
        console.print()
    
    def print_error(self, error: str, details: Optional[str] = None):
        """
        Print error message.
        
        Args:
            error: Error message
            details: Optional error details
        """
        self.logger.error(f"{error}{': ' + details if details else ''}")
        
        console.print()
        console.print(Panel.fit(
            f"[bold red]ERROR[/bold red]\n{error}",
            border_style="red"
        ))
        
        if details:
            console.print(f"[red]{details}[/red]")
        
        console.print()
    
    def print_section(self, title: str):
        """
        Print a section separator.
        
        Args:
            title: Section title
        """
        console.print()
        console.print(f"[bold cyan]{'─' * 20} {title} {'─' * 20}[/bold cyan]")
        console.print()
    
    def print_summary_table(self, data: Dict[str, Any], title: str = "Summary"):
        """
        Print a generic summary table.
        
        Args:
            data: Dictionary of key-value pairs
            title: Table title
        """
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()
            table.add_row(formatted_key, str(value))
        
        console.print(table)
        console.print()
