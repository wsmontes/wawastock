"""
Example: Using DataEngine with Technical Indicators

This demonstrates how the indicators are automatically calculated and stored
with the price data in the database.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines import DataEngine
from rich.console import Console
from rich.table import Table

console = Console()

def show_example():
    """Show how to use indicators with DataEngine."""
    
    console.print("\n[bold cyan]═══ DataEngine with Technical Indicators ═══[/bold cyan]\n")
    
    # Example 1: Load with standard indicators (default)
    console.print("[bold]Example 1: Standard indicators (auto_indicators=True)[/bold]")
    engine = DataEngine(auto_indicators=True, indicator_set='standard')
    
    df = engine.load_prices('AAPL', start='2023-01-01', end='2023-12-31')
    
    # Show available columns
    ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
    indicator_cols = [col for col in df.columns if col not in ohlcv_cols]
    
    table = Table(title="Data Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Bars", str(len(df)))
    table.add_row("OHLCV Columns", str(len(ohlcv_cols)))
    table.add_row("Indicator Columns", str(len(indicator_cols)))
    table.add_row("Total Columns", str(len(df.columns)))
    
    console.print(table)
    
    console.print(f"\n[bold]Available Indicators:[/bold]")
    for col in sorted(indicator_cols):
        console.print(f"  • {col}")
    
    console.print(f"\n[bold]Latest values (last row):[/bold]")
    last_row = df.iloc[-1]
    console.print(f"  Close: ${last_row['close']:.2f}")
    console.print(f"  RSI_14: {last_row['RSI_14']:.2f}")
    console.print(f"  SMA_20: ${last_row['SMA_20']:.2f}")
    console.print(f"  SMA_50: ${last_row['SMA_50']:.2f}")
    
    engine.close()
    
    # Example 2: Without indicators
    console.print(f"\n[bold]Example 2: Without indicators (auto_indicators=False)[/bold]")
    engine2 = DataEngine(auto_indicators=False)
    df2 = engine2.load_prices('AAPL', start='2023-01-01', end='2023-12-31')
    
    console.print(f"  Columns: {list(df2.columns)}")
    console.print(f"  Total: {len(df2.columns)} columns (OHLCV only)")
    
    engine2.close()
    
    console.print("\n[green]✓ Examples completed successfully![/green]\n")


if __name__ == '__main__':
    show_example()
