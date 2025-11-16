"""
Alpaca data source - Fetch stock market data from Alpaca Markets.

Supports US stocks with commission-free trading data.
Requires API credentials (free tier available).
"""

from typing import Optional
import pandas as pd
from datetime import datetime
from .base_data_source import BaseDataSource

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
except ImportError:
    StockHistoricalDataClient = None
    StockBarsRequest = None
    TimeFrame = None
    TimeFrameUnit = None


class AlpacaDataSource(BaseDataSource):
    """
    Data source for Alpaca Markets.
    
    Provides access to US stock market data.
    Free tier available with registration at alpaca.markets
    
    Supported symbols: US stocks (e.g., 'AAPL', 'TSLA', 'SPY')
    
    Intervals: 1Min, 5Min, 15Min, 30Min, 1Hour, 1Day, 1Week, 1Month
    """
    
    # Interval mapping
    INTERVAL_MAP = {
        '1m': ('1', TimeFrameUnit.Minute) if TimeFrameUnit else None,
        '5m': ('5', TimeFrameUnit.Minute) if TimeFrameUnit else None,
        '15m': ('15', TimeFrameUnit.Minute) if TimeFrameUnit else None,
        '30m': ('30', TimeFrameUnit.Minute) if TimeFrameUnit else None,
        '1h': ('1', TimeFrameUnit.Hour) if TimeFrameUnit else None,
        '1d': ('1', TimeFrameUnit.Day) if TimeFrameUnit else None,
        '1w': ('1', TimeFrameUnit.Week) if TimeFrameUnit else None,
        '1M': ('1', TimeFrameUnit.Month) if TimeFrameUnit else None,
    }
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Alpaca data source.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            
        Note:
            Get free credentials at https://alpaca.markets
        """
        super().__init__('Alpaca')
        
        if StockHistoricalDataClient is None:
            raise ImportError(
                "alpaca-py is required for AlpacaDataSource. "
                "Install it with: pip install alpaca-py"
            )
        
        if not api_key or not api_secret:
            raise ValueError("Alpaca API credentials are required")
        
        # Initialize client
        self.client = StockHistoricalDataClient(api_key, api_secret)
    
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
            symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
            timeframe: Timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M)
            start: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        
        Returns:
            DataFrame with: timestamp, open, high, low, close, volume
        """
        df = self._fetch_ohlcv_internal(symbol, start, end, timeframe)
        
        # Convert to ExchangeClient format
        if 'datetime' in df.columns:
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    def _fetch_ohlcv_internal(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Alpaca (internal method).
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            interval: Timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M)
        
        Returns:
            DataFrame with OHLCV data (datetime column)
        """
        print(f"Fetching {symbol} from Alpaca...")
        print(f"  Period: {start_date or 'default start'} to {end_date or 'now'}")
        print(f"  Interval: {interval}")
        
        # Get Alpaca timeframe
        if interval not in self.INTERVAL_MAP:
            raise ValueError(
                f"Invalid interval: {interval}. "
                f"Supported: {', '.join(self.INTERVAL_MAP.keys())}"
            )
        
        amount, unit = self.INTERVAL_MAP[interval]
        timeframe = TimeFrame(int(amount), unit)
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        
        # Create request
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=start_dt,
            end=end_dt
        )
        
        try:
            # Fetch bars
            bars = self.client.get_stock_bars(request_params)
            
            # Convert to DataFrame
            df = bars.df
            
            if df.empty:
                raise ValueError(f"No data returned for symbol {symbol}")
            
            # Alpaca returns multi-index (symbol, timestamp)
            # Reset index to get timestamp as column
            df = df.reset_index()
            
            # Rename columns
            df = df.rename(columns={
                'timestamp': 'datetime',
                'trade_count': 'trades',
                'vwap': 'vwap'
            })
            
            # Keep only OHLCV columns
            df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
            
            print(f"✓ Fetched {len(df)} bars")
            
            return self.normalize_dataframe(df)
            
        except Exception as e:
            raise ValueError(f"Alpaca API error: {e}")
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists on Alpaca.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            True if symbol is valid
        """
        try:
            # Try to fetch 1 bar to validate
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame(1, TimeFrameUnit.Day),
                limit=1
            )
            bars = self.client.get_stock_bars(request)
            return not bars.df.empty
        except Exception:
            return False
