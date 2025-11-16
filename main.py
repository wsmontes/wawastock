#!/usr/bin/env python3
"""
Main CLI entry point for the backtesting framework.

This script provides command-line interface to:
- Run predefined recipes
- Run strategies directly with custom parameters
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from utils.logger import get_logger, setup_logger

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine

# Import recipes
from recipes.sample_recipe import SampleRecipe
from recipes.rsi_recipe import RSIRecipe
from recipes.macd_ema_recipe import MACDEMARecipe
from recipes.bollinger_rsi_recipe import BollingerRSIRecipe
from recipes.multi_timeframe_recipe import MultiTimeframeRecipe

# Import strategies
from strategies.sample_sma_strategy import SampleSMAStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_ema_strategy import MACDEMAStrategy
from strategies.bollinger_rsi_strategy import BollingerRSIStrategy
from strategies.multi_timeframe_strategy import MultiTimeframeMomentumStrategy

# Initialize console and logger
console = Console()
logger = get_logger(__name__)


# Registry mapping names to classes
RECIPE_REGISTRY = {
    'sample': SampleRecipe,
    'rsi': RSIRecipe,
    'macd_ema': MACDEMARecipe,
    'bollinger_rsi': BollingerRSIRecipe,
    'multi_timeframe': MultiTimeframeRecipe,
}

STRATEGY_REGISTRY = {
    'sample_sma': SampleSMAStrategy,
    'rsi': RSIStrategy,
    'macd_ema': MACDEMAStrategy,
    'bollinger_rsi': BollingerRSIStrategy,
    'multi_timeframe': MultiTimeframeMomentumStrategy,
}


def run_recipe_programmatic(
    recipe_name: str,
    symbol: str = None,
    start: str = None,
    end: str = None,
    cash: float = 100000.0,
    commission: float = 0.001,
    **kwargs
):
    """
    Execute a recipe programmatically (for Streamlit/API usage).
    
    Args:
        recipe_name: Name of the recipe to run
        symbol: Stock/crypto symbol
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        cash: Initial capital
        commission: Commission rate
        **kwargs: Additional parameters passed to recipe
    
    Returns:
        Dictionary with backtest results
    """
    if recipe_name not in RECIPE_REGISTRY:
        raise ValueError(f"Recipe '{recipe_name}' not found. Available: {', '.join(RECIPE_REGISTRY.keys())}")
    
    # Initialize engines
    data_engine = DataEngine()
    backtest_engine = BacktestEngine(
        initial_cash=cash,
        commission=commission
    )
    
    # Get recipe class and instantiate
    recipe_cls = RECIPE_REGISTRY[recipe_name]
    recipe = recipe_cls(data_engine, backtest_engine)
    
    # Run recipe with parameters
    run_kwargs = {}
    if symbol:
        run_kwargs['symbol'] = symbol
    if start:
        run_kwargs['start'] = start
    if end:
        run_kwargs['end'] = end
    run_kwargs.update(kwargs)
    
    # Run recipe - this calls backtest_engine.run_backtest() internally
    # which returns results dict
    recipe.run(**run_kwargs)
    
    # The recipe.run() doesn't return anything, but backtest_engine.run_backtest() 
    # was called internally. We need to capture those results.
    # Let's check if recipe has a results attribute or we need to run differently
    
    # Actually, recipes don't store results. Let me look at how they work...
    # For now, let's load the data and run the backtest manually to get results
    
    # Load data
    df = data_engine.load_prices(
        symbol=symbol,
        start=start,
        end=end
    )
    
    if df is None or df.empty:
        raise ValueError(f"No data available for {symbol}")
    
    # Get the strategy class from the recipe
    # This is a bit hacky but necessary since recipes don't return results
    strategy_cls = None
    for name, strat_cls in STRATEGY_REGISTRY.items():
        if name in recipe_name or recipe_cls.__name__.replace('Recipe', '').lower() in name:
            strategy_cls = strat_cls
            break
    
    if strategy_cls is None:
        # Try to get from recipe mapping
        recipe_strategy_map = {
            'sample': SampleSMAStrategy,
            'rsi': RSIStrategy,
            'macd_ema': MACDEMAStrategy,
            'bollinger_rsi': BollingerRSIStrategy,
            'multi_timeframe': MultiTimeframeMomentumStrategy,
        }
        strategy_cls = recipe_strategy_map.get(recipe_name)
    
    if strategy_cls is None:
        raise ValueError(f"Could not determine strategy for recipe '{recipe_name}'")
    
    # Run backtest and get results
    results = backtest_engine.run_backtest(
        strategy_cls=strategy_cls,
        data_df=df,
        symbol=symbol,
        **kwargs
    )
    
    # Add data for chart
    results['data'] = df
    
    return results


def run_recipe(args):
    """
    Execute a recipe by name.
    
    Args:
        args: Parsed command-line arguments
    """
    recipe_name = args.name
    
    if recipe_name not in RECIPE_REGISTRY:
        console.print(f"[red]ERROR: Recipe '{recipe_name}' not found.[/red]")
        console.print(f"Available recipes: {', '.join(RECIPE_REGISTRY.keys())}")
        sys.exit(1)
    
    # Initialize engines
    data_engine = DataEngine()
    backtest_engine = BacktestEngine(
        initial_cash=args.cash,
        commission=args.commission
    )
    
    # Get recipe class and instantiate
    recipe_cls = RECIPE_REGISTRY[recipe_name]
    recipe = recipe_cls(data_engine, backtest_engine)
    
    # Run recipe with optional parameters
    kwargs = {}
    if args.symbol:
        kwargs['symbol'] = args.symbol
    if args.start:
        kwargs['start'] = args.start
    if args.end:
        kwargs['end'] = args.end
    
    recipe.run(**kwargs)


def run_strategy(args):
    """
    Execute a strategy directly with custom parameters.
    
    Args:
        args: Parsed command-line arguments
    """
    strategy_name = args.strategy
    
    if strategy_name not in STRATEGY_REGISTRY:
        console.print(f"[red]ERROR: Strategy '{strategy_name}' not found.[/red]")
        console.print(f"Available strategies: {', '.join(STRATEGY_REGISTRY.keys())}")
        sys.exit(1)
    
    # Initialize engines
    data_engine = DataEngine()
    backtest_engine = BacktestEngine(
        initial_cash=args.cash,
        commission=args.commission
    )
    
    # Display header
    console.print(Panel.fit(
        f"[bold cyan]RUNNING STRATEGY: {strategy_name}[/bold cyan]",
        border_style="cyan"
    ))
    
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_row("[cyan]Symbol:[/cyan]", args.symbol)
    table.add_row("[cyan]Period:[/cyan]", f"{args.start} to {args.end}")
    table.add_row("[cyan]Initial Cash:[/cyan]", f"${args.cash:,.2f}")
    table.add_row("[cyan]Commission:[/cyan]", f"{args.commission:.3%}")
    console.print(table)
    console.print()
    
    # Load data
    logger.info(f"Loading data for {args.symbol}...")
    try:
        data_df = data_engine.load_prices(
            symbol=args.symbol,
            start=args.start,
            end=args.end
        )
        console.print(f"[green]✓[/green] Loaded {len(data_df)} bars of data")
        console.print()
    except FileNotFoundError as e:
        console.print(f"[red]ERROR: {e}[/red]")
        console.print(f"[yellow]Please create a data file at: data/processed/{args.symbol}.parquet[/yellow]")
        sys.exit(1)
    
    # Prepare strategy parameters
    strategy_cls = STRATEGY_REGISTRY[strategy_name]
    strategy_params = {}
    
    # Add strategy-specific parameters
    if strategy_name == 'sample_sma':
        if args.fast:
            strategy_params['fast_period'] = args.fast
        if args.slow:
            strategy_params['slow_period'] = args.slow
        
        param_table = Table(title="Strategy Parameters", box=box.ROUNDED)
        param_table.add_column("Parameter", style="cyan")
        param_table.add_column("Value", style="green")
        param_table.add_row("Fast Period", str(strategy_params.get('fast_period', 10)))
        param_table.add_row("Slow Period", str(strategy_params.get('slow_period', 20)))
        console.print(param_table)
        console.print()
    
    # Run backtest
    logger.info("Running backtest...")
    results = backtest_engine.run_backtest(
        strategy_cls=strategy_cls,
        data_df=data_df,
        symbol=args.symbol,
        **strategy_params
    )
    
    # Results are already displayed by BacktestEngine
    console.print()


def fetch_data(args):
    """
    Fetch data from external sources and save to Parquet.
    
    Args:
        args: Parsed command-line arguments
    """
    data_engine = DataEngine()
    
    console.print(Panel.fit(
        f"[bold cyan]FETCHING DATA FROM: {args.source.upper()}[/bold cyan]",
        border_style="cyan"
    ))
    
    # Prepare source parameters
    source_params = {}
    
    if args.source.lower() == 'alpaca':
        if not args.api_key or not args.api_secret:
            console.print("[red]ERROR: Alpaca requires --api-key and --api-secret[/red]")
            sys.exit(1)
        source_params['api_key'] = args.api_key
        source_params['api_secret'] = args.api_secret
    
    elif args.source.lower() == 'ccxt':
        source_params['exchange_id'] = args.exchange or 'binance'
        if args.api_key:
            source_params['api_key'] = args.api_key
        if args.api_secret:
            source_params['api_secret'] = args.api_secret
    
    elif args.source.lower() == 'binance':
        if args.api_key:
            source_params['api_key'] = args.api_key
        if args.api_secret:
            source_params['api_secret'] = args.api_secret
    
    try:
        df = data_engine.fetch_from_source(
            source=args.source,
            symbol=args.symbol,
            start=args.start,
            end=args.end,
            interval=args.interval,
            save=not args.no_save,
            **source_params
        )
        
        console.print()
        console.print(Panel.fit(
            "[bold green]DATA SUMMARY[/bold green]",
            border_style="green"
        ))
        
        summary_table = Table(box=box.ROUNDED, show_header=False)
        summary_table.add_column("Property", style="cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Rows", f"{len(df):,}")
        summary_table.add_row("Date Range", f"{df.index[0]} to {df.index[-1]}")
        summary_table.add_row("Columns", ", ".join(df.columns))
        
        console.print(summary_table)
        console.print()
        console.print("[cyan]First few rows:[/cyan]")
        console.print(df.head())
        
    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def get_cached(args):
    """
    Get OHLCV data with automatic local-first caching.
    
    Args:
        args: Parsed command-line arguments
    """
    data_engine = DataEngine(use_cache=True)
    
    console.print(Panel.fit(
        f"[bold cyan]FETCHING WITH LOCAL-FIRST CACHE: {args.source.upper()}[/bold cyan]",
        border_style="cyan"
    ))
    
    # Prepare source parameters
    source_params = {}
    
    if args.source.lower() == 'alpaca':
        if not args.api_key or not args.api_secret:
            console.print("[red]ERROR: Alpaca requires --api-key and --api-secret[/red]")
            sys.exit(1)
        source_params['api_key'] = args.api_key
        source_params['api_secret'] = args.api_secret
    
    elif args.source.lower() == 'ccxt':
        source_params['exchange_id'] = args.exchange or 'binance'
        if args.api_key:
            source_params['api_key'] = args.api_key
        if args.api_secret:
            source_params['api_secret'] = args.api_secret
    
    elif args.source.lower() == 'binance':
        if args.api_key:
            source_params['api_key'] = args.api_key
        if args.api_secret:
            source_params['api_secret'] = args.api_secret
    
    try:
        df = data_engine.get_ohlcv_cached(
            source=args.source,
            symbol=args.symbol,
            timeframe=args.interval,
            start=args.start,
            end=args.end,
            **source_params
        )
        
        console.print()
        console.print(Panel.fit(
            "[bold green]DATA SUMMARY[/bold green]",
            border_style="green"
        ))
        
        summary_table = Table(box=box.ROUNDED, show_header=False)
        summary_table.add_column("Property", style="cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Rows", f"{len(df):,}")
        
        if not df.empty:
            summary_table.add_row("Date Range", f"{df['timestamp'].min()} to {df['timestamp'].max()}")
            summary_table.add_row("Columns", ", ".join(df.columns))
        
        console.print(summary_table)
        
        if not df.empty:
            console.print()
            console.print("[cyan]First few rows:[/cyan]")
            console.print(df.head())
            console.print()
            console.print("[cyan]Last few rows:[/cyan]")
            console.print(df.tail())
        
    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cache_info(args):
    """
    Show information about cached data.
    
    Args:
        args: Parsed command-line arguments
    """
    data_engine = DataEngine(use_cache=True)
    
    console.print(Panel.fit(
        "[bold cyan]CACHE COVERAGE INFORMATION[/bold cyan]",
        border_style="cyan"
    ))
    console.print()
    
    df = data_engine.get_coverage_info(source=args.source)
    
    if df.empty:
        console.print("[yellow]No cached data found.[/yellow]")
    else:
        # Create rich table from dataframe
        table = Table(box=box.ROUNDED)
        for col in df.columns:
            table.add_column(col, style="cyan")
        
        for _, row in df.iterrows():
            table.add_row(*[str(v) for v in row])
        
        console.print(table)
        console.print()
        
        summary_table = Table(show_header=False, box=box.SIMPLE)
        summary_table.add_row("[cyan]Total datasets:[/cyan]", str(len(df)))
        summary_table.add_row("[cyan]Total days cached:[/cyan]", str(df['days'].sum()))
        summary_table.add_row("[cyan]Total rows:[/cyan]", f"{df['total_rows'].sum():,.0f}")
        console.print(summary_table)


def cache_clear(args):
    """
    Clear cached data.
    
    Args:
        args: Parsed command-line arguments
    """
    data_engine = DataEngine(use_cache=True)
    
    console.print(Panel.fit(
        "[bold yellow]CLEARING CACHE[/bold yellow]",
        border_style="yellow"
    ))
    
    if not args.source and not args.symbol:
        from rich.prompt import Confirm
        if not Confirm.ask("[bold red]Clear ALL cached data? This cannot be undone.[/bold red]"):
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    data_engine.clear_cache(source=args.source, symbol=args.symbol)
    console.print("[green]✓ Cache cleared successfully[/green]")


def main():
    """
    Main entry point - parse arguments and dispatch to appropriate handler.
    """
    parser = argparse.ArgumentParser(
        description='Backtesting Framework CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch data from Yahoo Finance
  python main.py fetch-data --source yahoo --symbol AAPL --start 2020-01-01 --end 2023-12-31
  
  # Fetch crypto from Binance
  python main.py fetch-data --source binance --symbol BTCUSDT --interval 1h
  
  # Fetch from CCXT (specify exchange)
  python main.py fetch-data --source ccxt --exchange kraken --symbol BTC/USD --interval 1d
  
  # Fetch from Alpaca (requires API keys)
  python main.py fetch-data --source alpaca --symbol TSLA --api-key YOUR_KEY --api-secret YOUR_SECRET
  
  # Run a recipe
  python main.py run-recipe --name sample
  
  # Run a recipe with custom parameters
  python main.py run-recipe --name sample --symbol AAPL --start 2020-01-01 --end 2020-12-31
  
  # Run a strategy directly
  python main.py run-strategy --strategy sample_sma --symbol TEST --start 2020-01-01 --end 2020-12-31
  
  # Run a strategy with custom parameters
  python main.py run-strategy --strategy sample_sma --symbol TEST --fast 5 --slow 15
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Subcommand: get-cached (smart caching)
    get_cached_parser = subparsers.add_parser(
        'get-cached',
        help='Get data with automatic local-first caching'
    )
    get_cached_parser.add_argument(
        '--source',
        required=True,
        choices=['yahoo', 'binance', 'alpaca', 'ccxt'],
        help='Data source to use'
    )
    get_cached_parser.add_argument(
        '--symbol',
        required=True,
        help='Symbol to fetch'
    )
    get_cached_parser.add_argument(
        '--start',
        help='Start date (YYYY-MM-DD), default: 30 days ago'
    )
    get_cached_parser.add_argument(
        '--end',
        help='End date (YYYY-MM-DD), default: today'
    )
    get_cached_parser.add_argument(
        '--interval',
        default='1d',
        help='Timeframe (1m, 5m, 15m, 1h, 1d, etc., default: 1d)'
    )
    get_cached_parser.add_argument(
        '--exchange',
        help='Exchange ID for CCXT (e.g., binance, kraken, coinbase)'
    )
    get_cached_parser.add_argument(
        '--api-key',
        help='API key (required for Alpaca)'
    )
    get_cached_parser.add_argument(
        '--api-secret',
        help='API secret (required for Alpaca)'
    )
    
    # Subcommand: cache-info
    cache_info_parser = subparsers.add_parser(
        'cache-info',
        help='Show cache coverage information'
    )
    cache_info_parser.add_argument(
        '--source',
        help='Filter by source (optional)'
    )
    
    # Subcommand: cache-clear
    cache_clear_parser = subparsers.add_parser(
        'cache-clear',
        help='Clear cached data'
    )
    cache_clear_parser.add_argument(
        '--source',
        help='Clear only this source (optional)'
    )
    cache_clear_parser.add_argument(
        '--symbol',
        help='Clear only this symbol (optional)'
    )
    
    # Subcommand: fetch-data
    fetch_parser = subparsers.add_parser(
        'fetch-data',
        help='Fetch data from external sources'
    )
    fetch_parser.add_argument(
        '--source',
        required=True,
        choices=['yahoo', 'binance', 'alpaca', 'ccxt'],
        help='Data source to use'
    )
    fetch_parser.add_argument(
        '--symbol',
        required=True,
        help='Symbol to fetch (e.g., AAPL, BTCUSDT, BTC/USD)'
    )
    fetch_parser.add_argument(
        '--start',
        help='Start date (YYYY-MM-DD)'
    )
    fetch_parser.add_argument(
        '--end',
        help='End date (YYYY-MM-DD)'
    )
    fetch_parser.add_argument(
        '--interval',
        default='1d',
        help='Timeframe (1m, 5m, 15m, 1h, 1d, etc., default: 1d)'
    )
    fetch_parser.add_argument(
        '--exchange',
        help='Exchange ID for CCXT (e.g., binance, kraken, coinbase)'
    )
    fetch_parser.add_argument(
        '--api-key',
        help='API key (required for Alpaca, optional for others)'
    )
    fetch_parser.add_argument(
        '--api-secret',
        help='API secret (required for Alpaca, optional for others)'
    )
    fetch_parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save data to Parquet file'
    )
    
    # Subcommand: run-recipe
    recipe_parser = subparsers.add_parser(
        'run-recipe',
        help='Run a predefined recipe'
    )
    recipe_parser.add_argument(
        '--name',
        required=True,
        help='Name of the recipe to run'
    )
    recipe_parser.add_argument(
        '--symbol',
        help='Symbol to backtest (overrides recipe default)'
    )
    recipe_parser.add_argument(
        '--start',
        help='Start date (YYYY-MM-DD)'
    )
    recipe_parser.add_argument(
        '--end',
        help='End date (YYYY-MM-DD)'
    )
    recipe_parser.add_argument(
        '--cash',
        type=float,
        default=100000.0,
        help='Initial cash (default: 100000.0)'
    )
    recipe_parser.add_argument(
        '--commission',
        type=float,
        default=0.001,
        help='Commission rate (default: 0.001 = 0.1%%)'
    )
    
    # Subcommand: run-strategy
    strategy_parser = subparsers.add_parser(
        'run-strategy',
        help='Run a strategy directly'
    )
    strategy_parser.add_argument(
        '--strategy',
        required=True,
        help='Name of the strategy to run'
    )
    strategy_parser.add_argument(
        '--symbol',
        required=True,
        help='Symbol to backtest'
    )
    strategy_parser.add_argument(
        '--start',
        default='2020-01-01',
        help='Start date (YYYY-MM-DD, default: 2020-01-01)'
    )
    strategy_parser.add_argument(
        '--end',
        default='2020-12-31',
        help='End date (YYYY-MM-DD, default: 2020-12-31)'
    )
    strategy_parser.add_argument(
        '--cash',
        type=float,
        default=100000.0,
        help='Initial cash (default: 100000.0)'
    )
    strategy_parser.add_argument(
        '--commission',
        type=float,
        default=0.001,
        help='Commission rate (default: 0.001 = 0.1%%)'
    )
    
    # Strategy-specific parameters (for sample_sma)
    strategy_parser.add_argument(
        '--fast',
        type=int,
        help='Fast SMA period (for sample_sma strategy)'
    )
    strategy_parser.add_argument(
        '--slow',
        type=int,
        help='Slow SMA period (for sample_sma strategy)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to appropriate handler
    if args.command == 'get-cached':
        get_cached(args)
    elif args.command == 'cache-info':
        cache_info(args)
    elif args.command == 'cache-clear':
        cache_clear(args)
    elif args.command == 'fetch-data':
        fetch_data(args)
    elif args.command == 'run-recipe':
        run_recipe(args)
    elif args.command == 'run-strategy':
        run_strategy(args)


if __name__ == '__main__':
    main()
