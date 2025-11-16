"""
Base data source module - Abstract interface for all data providers.

All data sources should inherit from this class and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from datetime import datetime


class ExchangeClient(ABC):
    """
    Abstract interface for exchange clients compatible with LocalDataStore.
    
    This is a simplified interface focused on OHLCV data fetching.
    All exchange implementations should provide this interface.
    """
    
    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a specific time range.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            start: Start datetime (ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end: End datetime (ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            - timestamp should be datetime type
            - all price/volume columns should be numeric
        """
        pass


class BaseDataSource(ExchangeClient):
    """
    Abstract base class for all market data sources.
    
    Provides a common interface for fetching OHLCV data from different providers
    (Yahoo Finance, Binance, Alpaca, CCXT, etc.).
    """
    
    def __init__(self, name: str):
        """
        Initialize the data source.
        
        Args:
            name: Name identifier for this data source
        """
        self.name = name
    
    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data (implements ExchangeClient interface).
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            start: Start datetime (ISO format)
            end: End datetime (ISO format)
            
        Returns:
            DataFrame with: timestamp, open, high, low, close, volume
        """
        # Delegate to the original method with different signature
        return self._fetch_ohlcv_internal(symbol, start, end, timeframe)
    
    @abstractmethod
    def _fetch_ohlcv_internal(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Internal method for fetching OHLCV data (original signature).
        
        This exists for backward compatibility with existing code.
        """
        pass
    
    def fetch_ohlcv_legacy(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Legacy fetch method (for backward compatibility).
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL', 'BTCUSDT')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            interval: Timeframe (e.g., '1m', '5m', '1h', '1d')
        
        Returns:
            DataFrame with columns: datetime (index), open, high, low, close, volume
        """
        df = self._fetch_ohlcv_internal(symbol, start_date, end_date, interval)
        
        # Ensure timestamp column for new interface
        if 'timestamp' not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                df.rename(columns={'datetime': 'timestamp'}, inplace=True)
            else:
                df['timestamp'] = pd.to_datetime(df.index)
        
        return df
    
    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists/is available.
        
        Args:
            symbol: Trading symbol to validate
            
        Returns:
            True if symbol is valid, False otherwise
        """
        pass
    
    def save_to_parquet(
        self,
        df: pd.DataFrame,
        symbol: str,
        output_dir: str = 'data/processed'
    ):
        """
        Save DataFrame to Parquet file.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Symbol name (used for filename)
            output_dir: Directory to save the file
        """
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filepath = output_path / f"{symbol}.parquet"
        df.to_parquet(filepath)
        
        print(f"✓ Saved {len(df)} bars to {filepath}")
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame to standard format.
        
        Ensures columns are named consistently and datetime is the index.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Normalized DataFrame
        """
        # Ensure lowercase column names
        df.columns = df.columns.str.lower()
        
        # Ensure datetime column is datetime type
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
        elif not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Sort by datetime
        df.sort_index(inplace=True)
        
        return df
