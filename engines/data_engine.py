"""
Data engine module - Handles data loading from multiple sources.

Supports:
- Local Parquet files (via DuckDB)
- Yahoo Finance (stocks, ETFs, crypto)
- Binance (cryptocurrency)
- Alpaca (US stocks)
- CCXT (100+ exchanges)

Expected Parquet structure:
- Columns: datetime, open, high, low, close, volume
- datetime should be parseable to timestamp
- price columns (open, high, low, close) should be float
- volume should be numeric

Directory structure:
- data/raw/{exchange}/{symbol}/...  - raw data files
- data/processed/{symbol}.parquet   - processed single-file data
"""

from typing import Optional, Dict, Any
import pandas as pd
import duckdb
from pathlib import Path
from rich.console import Console

from .base_engine import BaseEngine
from .local_data_store import LocalDataStore
from .data_sources import (
    YahooDataSource,
    BinanceDataSource,
    AlpacaDataSource,
    CCXTDataSource
)


console = Console()


class DataEngine(BaseEngine):
    """
    Engine responsible for loading and querying data from multiple sources.
    
    Features:
    - Local-first caching with automatic gap detection
    - Multiple data sources (Yahoo, Binance, Alpaca, CCXT)
    - Organized Parquet storage with DuckDB indexing
    - Automatic fetching of missing data
    """
    
    def __init__(
        self, 
        db_path: str = "data/trader.duckdb",
        use_cache: bool = True
    ):
        """
        Initialize the DataEngine.
        
        Args:
            db_path: Path to DuckDB database file
            use_cache: Enable local-first caching (recommended)
        """
        super().__init__()
        self.db_path = db_path
        self.use_cache = use_cache
        
        # Initialize local data store (cache)
        if use_cache:
            self.store = LocalDataStore(
                duckdb_path=db_path,
                base_dir="data/parquet"
            )
        else:
            # Legacy mode: simple DuckDB connection
            self.conn = duckdb.connect(db_path)
            self.store = None
        
        # Data source instances (lazy initialization)
        self._yahoo = None
        self._binance = None
        self._alpaca = None
        self._ccxt_sources: Dict[str, CCXTDataSource] = {}
        
    def run(self):
        """
        Not implemented for DataEngine - use specific load methods instead.
        """
        raise NotImplementedError("DataEngine doesn't have a general run() method. Use load_* methods.")
    
    def get_ohlcv_cached(
        self,
        source: str,
        symbol: str,
        timeframe: str = '1d',
        start: Optional[str] = None,
        end: Optional[str] = None,
        **source_params
    ) -> pd.DataFrame:
        """
        Get OHLCV data with automatic local-first caching.
        
        This method:
        1. Checks local cache for existing data
        2. Identifies missing date ranges
        3. Fetches only missing data from source
        4. Saves to cache automatically
        5. Returns complete dataset
        
        Args:
            source: Data source ('yahoo', 'binance', 'alpaca', 'ccxt')
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            start: Start date/datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end: End date/datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            **source_params: Additional parameters (api_key, api_secret, exchange_id)
        
        Returns:
            DataFrame with: timestamp, open, high, low, close, volume
        
        Examples:
            # Yahoo Finance (no API key needed)
            df = engine.get_ohlcv_cached('yahoo', 'AAPL', '1d', '2020-01-01', '2023-12-31')
            
            # Binance (public data)
            df = engine.get_ohlcv_cached('binance', 'BTCUSDT', '1h', '2024-01-01', '2024-01-31')
            
            # CCXT with specific exchange
            df = engine.get_ohlcv_cached('ccxt', 'BTC/USD', '1d', '2023-01-01', exchange_id='kraken')
        """
        if not self.use_cache:
            raise ValueError("Caching is disabled. Enable it in __init__ or use fetch_from_source()")
        
        # Get appropriate client
        client = self._get_client(source, **source_params)
        
        # Normalize source name for storage
        source_normalized = source.upper()
        if source.lower() == 'ccxt':
            exchange_id = source_params.get('exchange_id', 'binance')
            source_normalized = f"CCXT_{exchange_id.upper()}"
        
        # Use LocalDataStore to get data (with automatic caching)
        return self.store.get_ohlcv(
            source=source_normalized,
            symbol=symbol,
            timeframe=timeframe,
            start=start or '2020-01-01',
            end=end or pd.Timestamp.now().strftime('%Y-%m-%d'),
            client=client
        )
    
    def _get_client(self, source: str, **params):
        """Get or create client for a data source."""
        source_lower = source.lower()
        
        if source_lower == 'yahoo':
            if self._yahoo is None:
                self._yahoo = YahooDataSource()
            return self._yahoo
        
        elif source_lower == 'binance':
            if self._binance is None:
                self._binance = BinanceDataSource(
                    api_key=params.get('api_key'),
                    api_secret=params.get('api_secret')
                )
            return self._binance
        
        elif source_lower == 'alpaca':
            api_key = params.get('api_key')
            api_secret = params.get('api_secret')
            if not api_key or not api_secret:
                raise ValueError("Alpaca requires api_key and api_secret")
            return AlpacaDataSource(api_key, api_secret)
        
        elif source_lower == 'ccxt':
            exchange_id = params.get('exchange_id', 'binance')
            if exchange_id not in self._ccxt_sources:
                self._ccxt_sources[exchange_id] = CCXTDataSource(
                    exchange_id=exchange_id,
                    api_key=params.get('api_key'),
                    api_secret=params.get('api_secret')
                )
            return self._ccxt_sources[exchange_id]
        
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def get_coverage_info(self, source: Optional[str] = None) -> pd.DataFrame:
        """
        Get information about cached data coverage.
        
        Args:
            source: Filter by source (optional)
            
        Returns:
            DataFrame with coverage statistics
        """
        if not self.use_cache:
            raise ValueError("Caching is disabled")
        
        return self.store.get_coverage_info(source=source)
    
    def clear_cache(self, source: Optional[str] = None, symbol: Optional[str] = None):
        """
        Clear cached data.
        
        Args:
            source: Clear only this source (optional)
            symbol: Clear only this symbol (optional)
        """
        if not self.use_cache:
            raise ValueError("Caching is disabled")
        
        self.store.clear_cache(source=source, symbol=symbol)
    
    def load_parquet_table(self, path: str):
        """
        Load a Parquet file as a DuckDB relation (legacy method).
        
        Args:
            path: Path to the Parquet file
            
        Returns:
            DuckDB relation object for querying
        """
        conn = self.store.conn if self.use_cache else self.conn
        return conn.read_parquet(path)
    
    def load_prices(
        self, 
        symbol: str, 
        start: Optional[str] = None, 
        end: Optional[str] = None,
        data_dir: str = "data/processed"
    ) -> pd.DataFrame:
        """
        Load price data for a symbol from Parquet files (legacy method).
        
        For new code, use get_ohlcv_cached() instead.
        
        Args:
            symbol: Symbol to load (e.g., "AAPL", "TEST")
            start: Start date in YYYY-MM-DD format (optional)
            end: End date in YYYY-MM-DD format (optional)
            data_dir: Directory containing processed parquet files
            
        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume
        """
        conn = self.store.conn if self.use_cache else self.conn
        
        parquet_path = Path(data_dir) / f"{symbol}.parquet"
        
        if not parquet_path.exists():
            # Try to load from cache if available
            if self.use_cache:
                self.logger.info("Processed file not found. Attempting to load from cache...")
                try:
                    # Try Yahoo first (most common for stocks)
                    df = self.get_ohlcv_cached(
                        source='yahoo',
                        symbol=symbol,
                        timeframe='1d',
                        start=start,
                        end=end
                    )
                    if not df.empty:
                        console.print(f"[green]✓[/green] Loaded {len(df)} bars from cache")
                        
                        # Convert timestamp column to datetime index
                        if 'timestamp' in df.columns:
                            # Convert Unix timestamp (seconds or nanoseconds) to datetime
                            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                            df.set_index('datetime', inplace=True)
                            df.drop('timestamp', axis=1, inplace=True)
                        elif 'datetime' in df.columns:
                            df['datetime'] = pd.to_datetime(df['datetime'])
                            df.set_index('datetime', inplace=True)
                        elif df.index.name != 'datetime':
                            # If index is already datetime but not named
                            df.index = pd.to_datetime(df.index)
                            df.index.name = 'datetime'
                        
                        # Ensure we have the required columns
                        required_cols = ['open', 'high', 'low', 'close', 'volume']
                        for col in required_cols:
                            if col not in df.columns:
                                raise ValueError(f"Missing required column: {col}")
                        
                        return df
                except Exception as e:
                    self.logger.warning(f"Could not load from cache: {e}")
            
            raise FileNotFoundError(f"Data file not found: {parquet_path}")
        
        # Build query with optional date filters
        query = f"SELECT * FROM read_parquet('{parquet_path}')"
        
        # First, check which datetime column exists
        temp_df = conn.execute(f"SELECT * FROM read_parquet('{parquet_path}') LIMIT 1").df()
        datetime_col = 'datetime' if 'datetime' in temp_df.columns else 'timestamp'
        
        conditions = []
        if start:
            conditions.append(f"{datetime_col} >= '{start}'")
        if end:
            conditions.append(f"{datetime_col} <= '{end}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" ORDER BY {datetime_col}"
        
        # Execute query and return as pandas DataFrame
        df = conn.execute(query).df()
        
        # Ensure datetime is properly formatted and standardize column name
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'])
            df.drop('timestamp', axis=1, inplace=True)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
        
        return df
    
    def fetch_from_source(
        self,
        source: str,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = '1d',
        save: bool = True,
        **source_params
    ) -> pd.DataFrame:
        """
        Fetch data from external source (Yahoo, Binance, Alpaca, CCXT).
        
        Args:
            source: Data source ('yahoo', 'binance', 'alpaca', 'ccxt')
            symbol: Symbol to fetch
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format
            interval: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            save: Whether to save data to Parquet file
            **source_params: Additional source-specific parameters
                - For Alpaca: api_key, api_secret
                - For CCXT: exchange_id, api_key, api_secret
        
        Returns:
            DataFrame with OHLCV data
        """
        df = None
        
        if source.lower() == 'yahoo':
            if self._yahoo is None:
                self._yahoo = YahooDataSource()
            df = self._yahoo.fetch_ohlcv(symbol, start, end, interval)
        
        elif source.lower() == 'binance':
            if self._binance is None:
                api_key = source_params.get('api_key')
                api_secret = source_params.get('api_secret')
                self._binance = BinanceDataSource(api_key, api_secret)
            df = self._binance.fetch_ohlcv(symbol, interval, start, end)
        
        elif source.lower() == 'alpaca':
            api_key = source_params.get('api_key')
            api_secret = source_params.get('api_secret')
            
            if not api_key or not api_secret:
                raise ValueError("Alpaca requires api_key and api_secret")
            
            # Create new instance (credentials may change)
            alpaca = AlpacaDataSource(api_key, api_secret)
            df = alpaca.fetch_ohlcv(symbol, start, end, interval)
        
        elif source.lower() == 'ccxt':
            exchange_id = source_params.get('exchange_id', 'binance')
            api_key = source_params.get('api_key')
            api_secret = source_params.get('api_secret')
            
            # Get or create CCXT source for this exchange
            if exchange_id not in self._ccxt_sources:
                self._ccxt_sources[exchange_id] = CCXTDataSource(
                    exchange_id=exchange_id,
                    api_key=api_key,
                    api_secret=api_secret
                )
            
            df = self._ccxt_sources[exchange_id].fetch_ohlcv(symbol, start, end, interval)
        
        else:
            raise ValueError(
                f"Unknown source: {source}. "
                "Supported: yahoo, binance, alpaca, ccxt"
            )
        
        # Save to Parquet if requested
        if save and df is not None:
            output_dir = Path("data/processed")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = output_dir / f"{symbol.replace('/', '_')}.parquet"
            
            # Reset index for saving (datetime as column)
            df_save = df.reset_index()
            df_save.to_parquet(filepath, index=False)
            
            console.print(f"[green]✓[/green] Saved to {filepath}")
        
        return df
    
    def get_available_sources(self) -> list:
        """
        Get list of available data sources.
        
        Returns:
            List of source names
        """
        sources = ['yahoo', 'binance', 'alpaca', 'ccxt']
        return sources
    
    def close(self):
        """Close database connections."""
        if self.use_cache and self.store:
            self.store.close()
        elif hasattr(self, 'conn') and self.conn:
            self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
