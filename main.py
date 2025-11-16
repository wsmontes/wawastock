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


def run_recipe(args):
    """
    Execute a recipe by name.
    
    Args:
        args: Parsed command-line arguments
    """
    recipe_name = args.name
    
    if recipe_name not in RECIPE_REGISTRY:
        print(f"ERROR: Recipe '{recipe_name}' not found.")
        print(f"Available recipes: {', '.join(RECIPE_REGISTRY.keys())}")
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
        print(f"ERROR: Strategy '{strategy_name}' not found.")
        print(f"Available strategies: {', '.join(STRATEGY_REGISTRY.keys())}")
        sys.exit(1)
    
    # Initialize engines
    data_engine = DataEngine()
    backtest_engine = BacktestEngine(
        initial_cash=args.cash,
        commission=args.commission
    )
    
    print("=" * 80)
    print(f"RUNNING STRATEGY: {strategy_name}")
    print("=" * 80)
    print(f"Symbol: {args.symbol}")
    print(f"Period: {args.start} to {args.end}")
    print("=" * 80)
    print()
    
    # Load data
    print(f"Loading data for {args.symbol}...")
    try:
        data_df = data_engine.load_prices(
            symbol=args.symbol,
            start=args.start,
            end=args.end
        )
        print(f"Loaded {len(data_df)} bars of data")
        print()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print(f"Please create a data file at: data/processed/{args.symbol}.parquet")
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
        
        print(f"Strategy Parameters:")
        print(f"  Fast Period: {strategy_params.get('fast_period', 10)}")
        print(f"  Slow Period: {strategy_params.get('slow_period', 20)}")
        print()
    
    # Run backtest
    print("Running backtest...")
    print()
    results = backtest_engine.run_backtest(
        strategy_cls=strategy_cls,
        data_df=data_df,
        **strategy_params
    )
    
    # Display results
    print()
    print("=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(f"Initial Portfolio Value: ${results['initial_value']:,.2f}")
    print(f"Final Portfolio Value:   ${results['final_value']:,.2f}")
    print(f"Profit/Loss:             ${results['pnl']:,.2f}")
    print(f"Return:                  {results['return_pct']:.2f}%")
    
    if results['analyzers']:
        print()
        print("Performance Metrics:")
        print("-" * 80)
        
        analyzers = results['analyzers']
        
        if 'sharpe' in analyzers and analyzers['sharpe']:
            print(f"Sharpe Ratio:            {analyzers['sharpe']:.3f}")
        
        if 'max_drawdown' in analyzers and analyzers['max_drawdown']:
            print(f"Max Drawdown:            {analyzers['max_drawdown']:.2f}%")
        
        if 'total_return' in analyzers and analyzers['total_return']:
            print(f"Total Return:            {analyzers['total_return']:.2f}%")
    
    print("=" * 80)


def fetch_data(args):
    """
    Fetch data from external sources and save to Parquet.
    
    Args:
        args: Parsed command-line arguments
    """
    data_engine = DataEngine()
    
    print("=" * 80)
    print(f"FETCHING DATA FROM: {args.source.upper()}")
    print("=" * 80)
    
    # Prepare source parameters
    source_params = {}
    
    if args.source.lower() == 'alpaca':
        if not args.api_key or not args.api_secret:
            print("ERROR: Alpaca requires --api-key and --api-secret")
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
        
        print()
        print("=" * 80)
        print("DATA SUMMARY")
        print("=" * 80)
        print(f"Rows: {len(df)}")
        print(f"Date Range: {df.index[0]} to {df.index[-1]}")
        print(f"Columns: {', '.join(df.columns)}")
        print()
        print("First few rows:")
        print(df.head())
        print("=" * 80)
        
    except Exception as e:
        print(f"ERROR: {e}")
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
    
    print("=" * 80)
    print(f"FETCHING WITH LOCAL-FIRST CACHE: {args.source.upper()}")
    print("=" * 80)
    
    # Prepare source parameters
    source_params = {}
    
    if args.source.lower() == 'alpaca':
        if not args.api_key or not args.api_secret:
            print("ERROR: Alpaca requires --api-key and --api-secret")
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
        
        print()
        print("=" * 80)
        print("DATA SUMMARY")
        print("=" * 80)
        print(f"Rows: {len(df)}")
        if not df.empty:
            print(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"Columns: {', '.join(df.columns)}")
            print()
            print("First few rows:")
            print(df.head())
            print()
            print("Last few rows:")
            print(df.tail())
        print("=" * 80)
        
    except Exception as e:
        print(f"ERROR: {e}")
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
    
    print("=" * 80)
    print("CACHE COVERAGE INFORMATION")
    print("=" * 80)
    print()
    
    df = data_engine.get_coverage_info(source=args.source)
    
    if df.empty:
        print("No cached data found.")
    else:
        print(df.to_string(index=False))
        print()
        print(f"Total datasets: {len(df)}")
        print(f"Total days cached: {df['days'].sum()}")
        print(f"Total rows: {df['total_rows'].sum():,.0f}")
    
    print("=" * 80)


def cache_clear(args):
    """
    Clear cached data.
    
    Args:
        args: Parsed command-line arguments
    """
    data_engine = DataEngine(use_cache=True)
    
    print("=" * 80)
    print("CLEARING CACHE")
    print("=" * 80)
    
    if not args.source and not args.symbol:
        confirm = input("Clear ALL cached data? This cannot be undone. (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
    
    data_engine.clear_cache(source=args.source, symbol=args.symbol)
    print("=" * 80)


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
