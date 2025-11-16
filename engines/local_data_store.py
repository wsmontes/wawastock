"""
Wrapper to integrate LocalDataStoreV2 with existing DataEngine.

This provides backward compatibility while using the new clean structure.
"""

from engines.local_data_store_v2 import LocalDataStoreV2
import pandas as pd


class LocalDataStore:
    """
    Wrapper around LocalDataStoreV2 for backward compatibility.
    
    Maps old API to new implementation.
    """
    
    # Source mapping
    SOURCE_MAP = {
        'YAHOO': 'stocks/us',
        'ALPACA': 'stocks/us',
        'BINANCE': 'binance/spot',
        'CCXT': 'binance/spot',
    }
    
    def __init__(
        self,
        duckdb_path: str = "data/trader.duckdb",
        base_dir: str = "data/parquet"
    ):
        """Initialize with V2 store."""
        self.store = LocalDataStoreV2(duckdb_path, base_dir)
        self.conn = self.store.conn
    
    def close(self):
        """Close connection."""
        if hasattr(self, 'store'):
            self.store.conn.commit()
            self.store.conn.close()
    
    def get_ohlcv(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        client=None
    ) -> pd.DataFrame:
        """
        Get OHLCV data with automatic cache management.
        
        Args:
            source: Data source ('YAHOO', 'BINANCE', etc.)
            symbol: Trading symbol
            timeframe: Timeframe
            start: Start date
            end: End date
            client: Optional client for fetching missing data
            
        Returns:
            DataFrame with timestamp index
        """
        # Map source to path
        source_path = self.SOURCE_MAP.get(source, source)
        
        print(f"Requesting {source}:{symbol}:{timeframe} from {start} to {end}")
        
        # Check if we have data
        has_data = self.store.has_data(source_path, symbol, timeframe, start, end)
        
        if not has_data and client:
            # Fetch missing data
            print(f"Fetching {symbol} from {source}...")
            
            df = client.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end
            )
            
            if df is not None and not df.empty:
                print(f"✓ Fetched {len(df)} bars")
                self.store.save_data(df, source_path, symbol, timeframe)
            else:
                print("✗ No data returned")
                return pd.DataFrame()
        
        # Load from cache
        df = self.store.get_data(source_path, symbol, timeframe, start, end)
        
        if not df.empty:
            print(f"✓ Loaded {len(df)} rows from cache")
        else:
            print("⚠ No data found in cache")
        
        return df
