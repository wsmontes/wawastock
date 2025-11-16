"""
Bridge between Streamlit UI and WawaStock engines.

This module provides the interface layer that connects the Streamlit UI
with the core WawaStock engines (DataEngine, BacktestEngine) and registries.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from engines.report_engine import ReportEngine


class StreamlitBridge:
    """
    Bridge between Streamlit UI and WawaStock engines.
    
    Provides methods to:
    - Execute recipes and strategies
    - Load and manage data
    - Format results for Streamlit display
    - Access registries of recipes and strategies
    """
    
    def __init__(self):
        """Initialize the bridge with engines."""
        self.data_engine = DataEngine()
        self.backtest_engine = None  # Created per-backtest with custom params
        self.report_engine = ReportEngine()
    
    def get_recipe_registry(self) -> Dict[str, Any]:
        """Get the recipe registry from main.py"""
        from main import RECIPE_REGISTRY
        return RECIPE_REGISTRY
    
    def get_strategy_registry(self) -> Dict[str, Any]:
        """Get the strategy registry from main.py"""
        from main import STRATEGY_REGISTRY
        return STRATEGY_REGISTRY
    
    def get_recipe_info(self, recipe_name: str) -> Dict[str, Any]:
        """
        Get information about a recipe.
        
        Args:
            recipe_name: Name of the recipe
            
        Returns:
            Dictionary with recipe information (description, parameters, etc.)
        """
        registry = self.get_recipe_registry()
        if recipe_name not in registry:
            return {}
        
        recipe_cls = registry[recipe_name]
        return {
            'name': recipe_name,
            'class': recipe_cls.__name__,
            'doc': recipe_cls.__doc__ or "No description available",
        }
    
    def get_strategy_params(self, strategy_name: str) -> Dict[str, Any]:
        """
        Get parameters for a strategy.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Dictionary of parameter names and default values
        """
        registry = self.get_strategy_registry()
        if strategy_name not in registry:
            return {}
        
        strategy_cls = registry[strategy_name]
        params_dict = {}
        
        # Extract params from backtrader strategy
        if hasattr(strategy_cls, 'params'):
            params = strategy_cls.params
            # params can be a tuple of tuples or an instance
            if hasattr(params, '_getitems'):
                # It's a backtrader params object
                for param_name in params._getkeys():
                    default_value = getattr(params, param_name)
                    params_dict[param_name] = default_value
            elif isinstance(params, (tuple, list)):
                # It's a tuple/list of tuples
                for param_tuple in params:
                    if len(param_tuple) >= 2:
                        param_name = param_tuple[0]
                        default_value = param_tuple[1]
                        params_dict[param_name] = default_value
        
        return params_dict
    
    def load_data(
        self,
        symbol: str,
        start: str,
        end: str
    ) -> Optional[pd.DataFrame]:
        """
        Load price data for a symbol.
        
        Args:
            symbol: Stock/crypto symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with OHLCV data and indicators, or None if failed
        """
        try:
            df = self.data_engine.load_prices(
                symbol=symbol,
                start=start,
                end=end
            )
            return df
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return None
    
    def run_recipe(
        self,
        recipe_name: str,
        symbol: str,
        start: str,
        end: str,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        **strategy_params
    ) -> Optional[Dict[str, Any]]:
        """
        Run a recipe and return formatted results.
        
        Args:
            recipe_name: Name of the recipe to run
            symbol: Stock/crypto symbol
            start: Start date
            end: End date
            initial_cash: Initial capital
            commission: Commission rate
            **strategy_params: Additional strategy parameters
            
        Returns:
            Dictionary with backtest results or None if failed
        """
        try:
            # Create backtest engine with custom parameters
            self.backtest_engine = BacktestEngine(
                initial_cash=initial_cash,
                commission=commission
            )
            
            # Get recipe class
            registry = self.get_recipe_registry()
            if recipe_name not in registry:
                st.error(f"Recipe '{recipe_name}' not found")
                return None
            
            recipe_cls = registry[recipe_name]
            
            # Instantiate recipe
            recipe = recipe_cls(self.data_engine, self.backtest_engine)
            
            # Prepare kwargs
            kwargs = {
                'symbol': symbol,
                'start': start,
                'end': end,
            }
            kwargs.update(strategy_params)
            
            # Run recipe (captures results internally)
            # Note: Recipes don't return results directly, they run backtest
            # We'll need to capture the backtest results
            
            # Load data first
            df = self.load_data(symbol, start, end)
            if df is None or df.empty:
                st.error(f"No data available for {symbol}")
                return None
            
            # Get strategy from recipe
            # This is recipe-specific, we'll need to handle this
            # For now, let's run the backtest directly
            
            # Get the strategy class from the recipe
            strategy_cls = self._get_strategy_from_recipe(recipe_name)
            if strategy_cls is None:
                st.error("Could not determine strategy for recipe")
                return None
            
            # Convert float params to int if they are whole numbers (periods, etc)
            cleaned_params = {}
            for key, value in strategy_params.items():
                if isinstance(value, float) and value.is_integer():
                    cleaned_params[key] = int(value)
                else:
                    cleaned_params[key] = value
            
            # Run backtest
            results = self.backtest_engine.run_backtest(
                strategy_cls=strategy_cls,
                data_df=df,
                **cleaned_params
            )
            
            return self._format_results(results, symbol, start, end, df)
            
        except Exception as e:
            st.error(f"Error running backtest: {str(e)}")
            import traceback
            st.exception(e)
            return None
    
    def _get_strategy_from_recipe(self, recipe_name: str) -> Optional[Any]:
        """
        Get the strategy class associated with a recipe.
        
        This is a helper to map recipes to their strategies.
        """
        # Mapping of recipes to strategies
        recipe_strategy_map = {
            'sample': 'sample_sma',
            'rsi': 'rsi',
            'macd_ema': 'macd_ema',
            'bollinger_rsi': 'bollinger_rsi',
            'multi_timeframe': 'multi_timeframe',
        }
        
        strategy_name = recipe_strategy_map.get(recipe_name)
        if strategy_name:
            strategy_registry = self.get_strategy_registry()
            return strategy_registry.get(strategy_name)
        
        return None
    
    def _format_results(
        self,
        results: Dict[str, Any],
        symbol: str,
        start: str,
        end: str,
        data_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Format backtest results for Streamlit display.
        
        Args:
            results: Raw results from BacktestEngine
            symbol: Symbol that was backtested
            start: Start date
            end: End date
            data_df: Original DataFrame with price data
            
        Returns:
            Formatted results dictionary
        """
        formatted = {
            'symbol': symbol,
            'period': f"{start} to {end}",
            'initial_value': results.get('initial_value', 0),
            'final_value': results.get('final_value', 0),
            'total_pnl': results.get('pnl', 0),  # Changed from profit_loss to pnl
            'total_return': results.get('return_pct', 0),  # Changed from profit_loss to return_pct
            'analyzers': results.get('analyzers', {}),
            'trades': results.get('trades', []),
            'data': data_df,  # Add the DataFrame for charting
        }
        
        # Extract specific metrics
        analyzers = results.get('analyzers', {})
        formatted['sharpe_ratio'] = analyzers.get('sharpe', 0)
        formatted['max_drawdown'] = analyzers.get('max_drawdown', 0)
        formatted['total_return_ann'] = analyzers.get('total_return', 0)
        
        # Add trade statistics from analyzer
        formatted['total_trades'] = analyzers.get('total_trades', 0)
        formatted['won_trades'] = analyzers.get('won_trades', 0)
        formatted['lost_trades'] = analyzers.get('lost_trades', 0)
        
        return formatted
    
    def get_available_symbols(self) -> List[str]:
        """
        Get list of available symbols in the database, sorted intelligently.
        
        Priority:
        1. Common stocks (AAPL, MSFT, GOOGL, etc.)
        2. By recency of data (most recent first)
        3. Alphabetically
        
        Returns:
            List of symbol names sorted by relevance
        """
        try:
            processed_dir = Path(__file__).parent.parent / 'data' / 'processed'
            if not processed_dir.exists():
                return []
            
            # Common/popular symbols for prioritization
            popular = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'SPY', 'QQQ']
            
            symbol_info = []
            for file in processed_dir.glob('*.parquet'):
                symbol = file.stem
                # Get file modification time as proxy for data recency
                mtime = file.stat().st_mtime
                is_popular = symbol in popular
                
                symbol_info.append({
                    'symbol': symbol,
                    'mtime': mtime,
                    'is_popular': is_popular
                })
            
            # Sort: popular first, then by recency, then alphabetically
            sorted_symbols = sorted(
                symbol_info,
                key=lambda x: (
                    not x['is_popular'],  # Popular first (False < True)
                    -x['mtime'],          # Recent first (negative for descending)
                    x['symbol']           # Alphabetically
                )
            )
            
            return [s['symbol'] for s in sorted_symbols]
        except Exception:
            return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a symbol in the database.
        
        Args:
            symbol: Symbol name
            
        Returns:
            Dictionary with symbol info (rows, date range, size, etc.)
        """
        try:
            df = self.data_engine.load_prices(symbol, start='1900-01-01', end='2100-01-01')
            if df is None or df.empty:
                return None
            
            processed_path = Path(__file__).parent.parent / 'data' / 'processed' / f'{symbol}.parquet'
            file_size = processed_path.stat().st_size if processed_path.exists() else 0
            
            return {
                'symbol': symbol,
                'rows': len(df),
                'start_date': str(df.index[0].date()) if len(df) > 0 else 'N/A',
                'end_date': str(df.index[-1].date()) if len(df) > 0 else 'N/A',
                'columns': list(df.columns),
                'file_size': file_size,
                'has_indicators': any(col.startswith(('SMA_', 'EMA_', 'RSI_', 'MACD')) for col in df.columns),
            }
        except Exception:
            return None
