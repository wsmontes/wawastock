"""
CCXT data source - Unified API for multiple cryptocurrency exchanges.

Supports 100+ exchanges through the CCXT library.
"""

from typing import Optional, List
import pandas as pd
from datetime import datetime, timedelta
from .base_data_source import BaseDataSource

try:
    import ccxt
except ImportError:
    ccxt = None


class CCXTDataSource(BaseDataSource):
    """
    Data source using CCXT unified exchange API.
    
    Supports 100+ cryptocurrency exchanges including:
    - Binance, Coinbase, Kraken, Bitfinex, Bybit
    - KuCoin, Gate.io, OKX, Huobi, and many more
    
    Common symbols format: BTC/USDT, ETH/USDT, etc.
    
    Intervals vary by exchange, common ones: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
    """
    
    def __init__(
        self, 
        exchange_id: str = 'binance',
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        **exchange_params
    ):
        """
        Initialize CCXT data source.
        
        Args:
            exchange_id: Exchange identifier (e.g., 'binance', 'coinbase', 'kraken')
            api_key: API key (optional for public data)
            api_secret: API secret (optional for public data)
            **exchange_params: Additional exchange-specific parameters
        """
        super().__init__(f'CCXT-{exchange_id}')
        
        if ccxt is None:
            raise ImportError(
                "ccxt is required for CCXTDataSource. "
                "Install it with: pip install ccxt"
            )
        
        # Check if exchange is supported
        if exchange_id not in ccxt.exchanges:
            raise ValueError(
                f"Exchange '{exchange_id}' not supported. "
                f"Available: {', '.join(ccxt.exchanges[:10])}... (and {len(ccxt.exchanges) - 10} more)"
            )
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # Respect rate limits
            **exchange_params
        }
        
        self.exchange = exchange_class(config)
        self.exchange_id = exchange_id
        
        # Load markets
        try:
            self.exchange.load_markets()
        except Exception as e:
            print(f"Warning: Could not load markets: {e}")
    
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
            symbol: Trading pair in CCXT format (e.g., 'BTC/USDT')
            timeframe: Timeframe (varies by exchange: 1m, 5m, 15m, 1h, 1d, etc.)
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
        Fetch OHLCV data from exchange via CCXT (internal method).
        
        Args:
            symbol: Trading pair in CCXT format (e.g., 'BTC/USDT', 'ETH/USD')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            interval: Timeframe (varies by exchange: 1m, 5m, 15m, 1h, 1d, etc.)
        
        Returns:
            DataFrame with OHLCV data (datetime column)
        """
        print(f"Fetching {symbol} from {self.exchange_id.upper()} via CCXT...")
        print(f"  Period: {start_date or 'recent'} to {end_date or 'now'}")
        print(f"  Interval: {interval}")
        
        # Check if exchange supports fetching OHLCV
        if not self.exchange.has['fetchOHLCV']:
            raise ValueError(f"Exchange {self.exchange_id} doesn't support OHLCV data")
        
        # Check if timeframe is supported
        if interval not in self.exchange.timeframes:
            raise ValueError(
                f"Timeframe '{interval}' not supported by {self.exchange_id}. "
                f"Available: {', '.join(self.exchange.timeframes.keys())}"
            )
        
        # Convert dates to timestamps (milliseconds)
        since = None
        if start_date:
            since = int(datetime.fromisoformat(start_date).timestamp() * 1000)
        
        limit = 1000  # Max bars per request (varies by exchange)
        all_ohlcv = []
        
        try:
            # Fetch data (may need multiple requests for large ranges)
            while True:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=interval,
                    since=since,
                    limit=limit
                )
                
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Check if we got all data or need more requests
                if len(ohlcv) < limit:
                    break
                
                # Update 'since' for next batch
                since = ohlcv[-1][0] + 1
                
                # Check if we've passed end_date
                if end_date:
                    end_ts = int(datetime.fromisoformat(end_date).timestamp() * 1000)
                    if since > end_ts:
                        break
            
            if not all_ohlcv:
                raise ValueError(f"No data returned for symbol {symbol}")
            
            # Convert to DataFrame
            df = pd.DataFrame(
                all_ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.drop('timestamp', axis=1, inplace=True)
            
            # Filter by end_date if provided
            if end_date:
                end_dt = pd.to_datetime(end_date)
                df = df[df['datetime'] <= end_dt]
            
            print(f"✓ Fetched {len(df)} bars")
            
            return self.normalize_dataframe(df)
            
        except ccxt.BaseError as e:
            raise ValueError(f"CCXT error: {e}")
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists on the exchange.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            
        Returns:
            True if symbol is valid
        """
        try:
            return symbol in self.exchange.markets
        except Exception:
            return False
    
    def get_markets(self) -> List[str]:
        """
        Get list of all available markets/symbols.
        
        Returns:
            List of trading pair symbols
        """
        return list(self.exchange.markets.keys())
    
    def get_timeframes(self) -> List[str]:
        """
        Get list of supported timeframes for this exchange.
        
        Returns:
            List of timeframe strings
        """
        return list(self.exchange.timeframes.keys())
    
    @staticmethod
    def get_supported_exchanges() -> List[str]:
        """
        Get list of all exchanges supported by CCXT.
        
        Returns:
            List of exchange IDs
        """
        if ccxt is None:
            return []
        return ccxt.exchanges
