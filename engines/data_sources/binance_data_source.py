"""
Binance data source - Fetch cryptocurrency data from Binance.

Supports spot market data for all trading pairs available on Binance.
"""

from typing import Optional
import pandas as pd
from datetime import datetime, timedelta
from .base_data_source import BaseDataSource

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except ImportError:
    Client = None
    BinanceAPIException = None


class BinanceDataSource(BaseDataSource):
    """
    Data source for Binance cryptocurrency exchange.
    
    Provides access to historical OHLCV data for crypto pairs.
    No API key required for public market data.
    
    Common symbols: BTCUSDT, ETHUSDT, BNBUSDT, etc.
    
    Intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    """
    
    # Interval mapping to Binance format
    INTERVAL_MAP = {
        '1m': Client.KLINE_INTERVAL_1MINUTE if Client else None,
        '3m': Client.KLINE_INTERVAL_3MINUTE if Client else None,
        '5m': Client.KLINE_INTERVAL_5MINUTE if Client else None,
        '15m': Client.KLINE_INTERVAL_15MINUTE if Client else None,
        '30m': Client.KLINE_INTERVAL_30MINUTE if Client else None,
        '1h': Client.KLINE_INTERVAL_1HOUR if Client else None,
        '2h': Client.KLINE_INTERVAL_2HOUR if Client else None,
        '4h': Client.KLINE_INTERVAL_4HOUR if Client else None,
        '6h': Client.KLINE_INTERVAL_6HOUR if Client else None,
        '8h': Client.KLINE_INTERVAL_8HOUR if Client else None,
        '12h': Client.KLINE_INTERVAL_12HOUR if Client else None,
        '1d': Client.KLINE_INTERVAL_1DAY if Client else None,
        '3d': Client.KLINE_INTERVAL_3DAY if Client else None,
        '1w': Client.KLINE_INTERVAL_1WEEK if Client else None,
        '1M': Client.KLINE_INTERVAL_1MONTH if Client else None,
    }
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Binance data source.
        
        Args:
            api_key: Binance API key (optional for public data)
            api_secret: Binance API secret (optional for public data)
        """
        super().__init__('Binance')
        
        if Client is None:
            raise ImportError(
                "python-binance is required for BinanceDataSource. "
                "Install it with: pip install python-binance"
            )
        
        # Initialize client (works without credentials for public data)
        self.client = Client(api_key, api_secret)
    
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
            symbol: Binance trading pair (e.g., 'BTCUSDT')
            timeframe: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
            start: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        
        Returns:
            DataFrame with: timestamp, open, high, low, close, volume
        """
        df = self._fetch_ohlcv_internal(symbol, start, end, timeframe)
        
        # Convert to ExchangeClient format
        # normalize_dataframe sets datetime as index, so we need to reset it
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        elif 'datetime' in df.columns:
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
        Fetch OHLCV data from Binance (internal method).
        
        Args:
            symbol: Binance trading pair (e.g., 'BTCUSDT', 'ETHUSDT')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            interval: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
        
        Returns:
            DataFrame with OHLCV data (datetime column)
        """
        print(f"Fetching {symbol} from Binance...")
        print(f"  Period: {start_date or '500 periods ago'} to {end_date or 'now'}")
        print(f"  Interval: {interval}")
        
        # Get Binance interval format
        if interval not in self.INTERVAL_MAP:
            raise ValueError(
                f"Invalid interval: {interval}. "
                f"Supported: {', '.join(self.INTERVAL_MAP.keys())}"
            )
        
        binance_interval = self.INTERVAL_MAP[interval]
        
        try:
            # Fetch klines (candlestick data)
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=binance_interval,
                start_str=start_date,
                end_str=end_date
            )
            
            if not klines:
                raise ValueError(f"No data returned for symbol {symbol}")
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Keep only OHLCV columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            
            # Convert timestamp to datetime
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.drop('timestamp', axis=1, inplace=True)
            
            # Convert price/volume to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✓ Fetched {len(df)} bars")
            
            return self.normalize_dataframe(df)
            
        except BinanceAPIException as e:
            raise ValueError(f"Binance API error: {e}")
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists on Binance.
        
        Args:
            symbol: Binance trading pair (e.g., 'BTCUSDT')
            
        Returns:
            True if symbol is valid
        """
        try:
            info = self.client.get_symbol_info(symbol)
            return info is not None
        except Exception:
            return False
    
    def get_exchange_info(self, symbol: Optional[str] = None) -> dict:
        """
        Get exchange information.
        
        Args:
            symbol: Optional symbol to get specific info
            
        Returns:
            Dictionary with exchange/symbol information
        """
        if symbol:
            return self.client.get_symbol_info(symbol)
        return self.client.get_exchange_info()
    
    def get_all_symbols(self) -> list:
        """
        Get list of all available trading pairs.
        
        Returns:
            List of symbol names
        """
        info = self.client.get_exchange_info()
        return [s['symbol'] for s in info['symbols']]
