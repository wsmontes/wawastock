"""
Local data store V2 - Clean structure with smart file organization.

Structure:
  data/parquet/
    stocks/us/
      1d/
        AAPL.parquet
        MSFT.parquet
      1h/
        AAPL.parquet
    binance/spot/
      1d/
        BTCUSDT.parquet
      1m/
        BTCUSDT/
          2023.parquet
          2024.parquet
        ETHUSDT/
          2023.parquet

Logic:
- High timeframes (1d, 1h, 4h): Single file per symbol
- Low timeframes (1m, 5m, 15m, 30m): One file per year per symbol
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
import pandas as pd
import duckdb


class LocalDataStoreV2:
    """
    Clean local data store with smart file organization.
    
    - High frequency data (1m, 5m): Organized by year
    - Low frequency data (1h, 1d): Single file per symbol
    - No per-day fragmentation
    - Fast queries with DuckDB
    """
    
    # Timeframes that need year-based splitting (high frequency)
    SPLIT_BY_YEAR = {'1m', '5m', '15m', '30m'}
    
    def __init__(
        self,
        duckdb_path: str = "data/trader.duckdb",
        base_dir: str = "data/parquet"
    ):
        """
        Initialize the local data store.
        
        Args:
            duckdb_path: Path to DuckDB database file
            base_dir: Base directory for Parquet files
        """
        self.duckdb_path = duckdb_path
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize DuckDB connection
        self.conn = duckdb.connect(duckdb_path)
        self._init_schema()
    
    def __del__(self):
        """Cleanup: ensure changes are committed."""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.commit()
                self.conn.close()
        except:
            pass
    
    def _init_schema(self):
        """Create database schema for tracking files."""
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS data_files (
                source    VARCHAR,      -- 'stocks/us', 'binance/spot'
                symbol    VARCHAR,      -- 'AAPL', 'BTCUSDT'
                timeframe VARCHAR,      -- '1m', '1h', '1d'
                file_path VARCHAR,      -- Full path to parquet file
                min_date  DATE,         -- First date in file
                max_date  DATE,         -- Last date in file
                row_count INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source, symbol, timeframe, file_path)
            )
        """)
        
        self.conn.commit()
    
    def _get_file_path(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        year: Optional[int] = None
    ) -> Path:
        """
        Get file path based on timeframe logic.
        
        Args:
            source: Data source path (e.g., 'stocks/us', 'binance/spot')
            symbol: Trading symbol
            timeframe: Timeframe
            year: Year (only for high-frequency timeframes)
            
        Returns:
            Path to parquet file
        """
        base = self.base_dir / source / timeframe
        
        if timeframe in self.SPLIT_BY_YEAR:
            # High frequency: symbol folder with year files
            if year is None:
                raise ValueError(f"Year required for timeframe {timeframe}")
            return base / symbol / f"{year}.parquet"
        else:
            # Low frequency: single file per symbol
            return base / f"{symbol}.parquet"
    
    def save_data(
        self,
        df: pd.DataFrame,
        source: str,
        symbol: str,
        timeframe: str
    ):
        """
        Save data to parquet file(s) based on timeframe.
        
        Args:
            df: DataFrame with columns: timestamp, open, high, low, close, volume
            source: Data source path (e.g., 'stocks/us')
            symbol: Trading symbol
            timeframe: Timeframe
        """
        if df.empty:
            return
        
        # Ensure required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Convert timestamp to datetime
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        
        # Add metadata
        df = df.copy()
        df['source'] = source
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        # Get date range
        min_date = df['timestamp'].min().date()
        max_date = df['timestamp'].max().date()
        
        if timeframe in self.SPLIT_BY_YEAR:
            # Split by year for high-frequency data
            df['year'] = df['timestamp'].dt.year
            
            for year, df_year in df.groupby('year'):
                file_path = self._get_file_path(source, symbol, timeframe, year)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Merge with existing data if file exists
                if file_path.exists():
                    df_existing = pd.read_parquet(file_path)
                    df_combined = pd.concat([df_existing, df_year], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
                    df_combined = df_combined.sort_values('timestamp')
                    df_combined.to_parquet(file_path, index=False)
                else:
                    df_year.drop('year', axis=1).to_parquet(file_path, index=False)
                
                # Update catalog
                self._update_catalog(file_path, source, symbol, timeframe)
        
        else:
            # Single file for low-frequency data
            file_path = self._get_file_path(source, symbol, timeframe)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Merge with existing data if file exists
            if file_path.exists():
                df_existing = pd.read_parquet(file_path)
                df_combined = pd.concat([df_existing, df], ignore_index=True)
                df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
                df_combined = df_combined.sort_values('timestamp')
                df_combined.to_parquet(file_path, index=False)
            else:
                df.to_parquet(file_path, index=False)
            
            # Update catalog
            self._update_catalog(file_path, source, symbol, timeframe)
        
        print(f"  ✓ Saved {len(df)} rows to {source}/{symbol}/{timeframe}")
        self.conn.commit()
    
    def _update_catalog(
        self,
        file_path: Path,
        source: str,
        symbol: str,
        timeframe: str
    ):
        """Update catalog with file metadata."""
        
        # Read file to get stats
        df = pd.read_parquet(file_path)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            min_date = df['timestamp'].min().date()
            max_date = df['timestamp'].max().date()
            row_count = len(df)
            
            self.conn.execute("""
                INSERT OR REPLACE INTO data_files
                (source, symbol, timeframe, file_path, min_date, max_date, row_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [source, symbol, timeframe, str(file_path), min_date, max_date, row_count])
    
    def get_data(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> pd.DataFrame:
        """
        Get data from cache.
        
        Args:
            source: Data source path
            symbol: Trading symbol
            timeframe: Timeframe
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with timestamp index
        """
        # Get relevant files
        query = """
            SELECT file_path, min_date, max_date
            FROM data_files
            WHERE source = ?
              AND symbol = ?
              AND timeframe = ?
              AND max_date >= ?
              AND min_date <= ?
        """
        
        result = self.conn.execute(query, [
            source, symbol, timeframe, start, end
        ]).fetchall()
        
        if not result:
            return pd.DataFrame()
        
        # Read all relevant files
        dfs = []
        for file_path, _, _ in result:
            if Path(file_path).exists():
                df = pd.read_parquet(file_path)
                dfs.append(df)
        
        if not dfs:
            return pd.DataFrame()
        
        # Combine and filter
        df = pd.concat(dfs, ignore_index=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        # Filter by date range
        df = df[
            (df['timestamp'] >= pd.to_datetime(start, utc=True)) &
            (df['timestamp'] < pd.to_datetime(end, utc=True))
        ]
        
        # Sort and set index
        df = df.sort_values('timestamp')
        df = df.set_index('timestamp')
        
        # Return only OHLCV columns
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def has_data(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> bool:
        """
        Check if we have data covering the range.
        
        Note: We check for ANY overlap, not exact coverage.
        This is because start date might be a weekend/holiday.
        """
        
        query = """
            SELECT COUNT(*) as count
            FROM data_files
            WHERE source = ?
              AND symbol = ?
              AND timeframe = ?
              AND NOT (max_date < ? OR min_date > ?)
        """
        
        result = self.conn.execute(query, [
            source, symbol, timeframe, start, end
        ]).fetchone()
        
        return result[0] > 0 if result else False
