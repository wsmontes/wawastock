"""
Yahoo Finance data source - Fetch data using yfinance library.

Supports stocks, ETFs, indices, forex, and cryptocurrencies.
"""

from typing import Optional
import pandas as pd
from .base_data_source import BaseDataSource

try:
    import yfinance as yf
except ImportError:
    yf = None


class YahooDataSource(BaseDataSource):
    """
    Data source for Yahoo Finance.
    
    Provides access to historical price data for:
    - Stocks (e.g., 'AAPL', 'GOOGL')
    - ETFs (e.g., 'SPY', 'QQQ')
    - Indices (e.g., '^GSPC', '^DJI')
    - Forex (e.g., 'EURUSD=X')
    - Crypto (e.g., 'BTC-USD', 'ETH-USD')
    
    Intervals supported: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    
    def __init__(self):
        """Initialize Yahoo Finance data source."""
        super().__init__('Yahoo Finance')
        
        if yf is None:
            raise ImportError(
                "yfinance is required for YahooDataSource. "
                "Install it with: pip install yfinance"
            )
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data (ExchangeClient interface).
        
        Args:
            symbol: Yahoo Finance ticker symbol
            timeframe: Timeframe (1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo)
            start: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        
        Returns:
            DataFrame with: timestamp, open, high, low, close, volume
        """
        df = self._fetch_ohlcv_internal(symbol, start, end, timeframe)
        
        # Return empty DataFrame if no data
        if df.empty:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert to ExchangeClient format (timestamp column, not index)
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            if 'datetime' in df.columns:
                df.rename(columns={'datetime': 'timestamp'}, inplace=True)
            else:
                df['timestamp'] = df.index
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    def _fetch_ohlcv_internal(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance (internal method).
        
        Args:
            symbol: Yahoo Finance ticker symbol
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            interval: Timeframe (1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo)
        
        Returns:
            DataFrame with OHLCV data (datetime as index)
        """
        # Convert datetime strings to date-only if they contain time
        if start_date and 'T' in start_date:
            start_date = start_date.split('T')[0]
        if end_date and 'T' in end_date:
            end_date = end_date.split('T')[0]
        
        print(f"Fetching {symbol} from Yahoo Finance...")
        print(f"  Period: {start_date or 'max'} to {end_date or 'now'}")
        print(f"  Interval: {interval}")
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Fetch data
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True  # Use adjusted close
            )
            
            if df.empty:
                print(f"⚠️  No data returned for symbol {symbol}")
                return pd.DataFrame()
            
            # Yahoo Finance returns: Open, High, Low, Close, Volume, Dividends, Stock Splits
            # We only need OHLCV
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            
            # Rename columns to lowercase
            df.columns = ['open', 'high', 'low', 'close', 'volume']
        except Exception as e:
            print(f"⚠️  Error fetching {symbol}: {e}")
            return pd.DataFrame()
        
        # Ensure index is named 'datetime'
        df.index.name = 'datetime'
        
        print(f"✓ Fetched {len(df)} bars")
        
        return self.normalize_dataframe(df)
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists on Yahoo Finance.
        
        Args:
            symbol: Yahoo Finance ticker symbol
            
        Returns:
            True if symbol is valid
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid info
            return 'symbol' in info or 'shortName' in info
        except Exception:
            return False
    
    def get_info(self, symbol: str) -> dict:
        """
        Get additional information about a symbol.
        
        Args:
            symbol: Yahoo Finance ticker symbol
            
        Returns:
            Dictionary with symbol information
        """
        ticker = yf.Ticker(symbol)
        return ticker.info
