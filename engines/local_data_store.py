"""
Local data store with automatic cache management.

This module implements a "local-first" caching system that:
1. Checks what data exists locally (DuckDB + Parquet)
2. Identifies missing data gaps
3. Fetches only missing data from APIs
4. Stores everything in organized Parquet files
5. Returns complete dataset from local cache

Data organization:
    data/parquet/
      candles/
        BINANCE/
          BTCUSDT/
            15m/
              2024/
                2024-01-01.parquet
                2024-01-02.parquet
                ...
"""

from pathlib import Path
from typing import Optional, List, Set
from datetime import date, datetime, timedelta
import pandas as pd
import duckdb


class LocalDataStore:
    """
    Local-first data store with automatic cache management.
    
    Automatically manages data caching:
    - Tracks what data is already stored locally
    - Identifies gaps in requested date ranges
    - Fetches only missing data from remote sources
    - Organizes data in Parquet files by day
    - Provides fast queries via DuckDB
    """
    
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
    
    def _init_schema(self):
        """Create database schema for tracking Parquet files and coverage."""
        
        # Table to track all Parquet files
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS parquet_files (
                id        BIGINT PRIMARY KEY,
                kind      VARCHAR,      -- 'candles', 'trades', 'features', etc.
                source    VARCHAR,      -- 'BINANCE', 'YAHOO', 'ALPACA', etc.
                symbol    VARCHAR,
                timeframe VARCHAR,      -- '1m', '5m', '15m', '1h', '1d', etc.
                date      DATE,         -- date covered by this file
                path      VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table to track data coverage (which days are complete)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS data_coverage (
                source    VARCHAR,
                symbol    VARCHAR,
                timeframe VARCHAR,
                date      DATE,
                complete  BOOLEAN DEFAULT TRUE,
                row_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source, symbol, timeframe, date)
            )
        """)
        
        # Create indexes for faster queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_parquet_lookup 
            ON parquet_files(kind, source, symbol, timeframe, date)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_lookup
            ON data_coverage(source, symbol, timeframe, date)
        """)
    
    def _date_range(self, start: str, end: str) -> List[date]:
        """
        Generate list of dates between start and end (inclusive).
        
        Args:
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            
        Returns:
            List of date objects
        """
        start_dt = pd.to_datetime(start).date()
        end_dt = pd.to_datetime(end).date()
        
        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        return [d.date() for d in dates]
    
    def _get_existing_dates(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        start: date,
        end: date
    ) -> Set[date]:
        """
        Get dates that are already stored locally.
        
        Args:
            source: Data source name
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 1h, 1d, etc.)
            start: Start date
            end: End date
            
        Returns:
            Set of dates with complete data
        """
        query = """
            SELECT date
            FROM data_coverage
            WHERE source = ?
              AND symbol = ?
              AND timeframe = ?
              AND date BETWEEN ? AND ?
              AND complete = TRUE
        """
        
        df = self.conn.execute(query, [
            source, symbol, timeframe, start, end
        ]).df()
        
        if df.empty:
            return set()
        
        return set(df['date'].tolist())
    
    def _get_missing_dates(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> List[date]:
        """
        Identify missing dates that need to be fetched.
        
        Args:
            source: Data source name
            symbol: Trading symbol
            timeframe: Timeframe
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            
        Returns:
            List of missing dates
        """
        requested_dates = set(self._date_range(start, end))
        
        if not requested_dates:
            return []
        
        start_date = min(requested_dates)
        end_date = max(requested_dates)
        
        existing_dates = self._get_existing_dates(
            source, symbol, timeframe, start_date, end_date
        )
        
        missing = requested_dates - existing_dates
        return sorted(missing)
    
    def _save_daily_data(
        self,
        df: pd.DataFrame,
        source: str,
        symbol: str,
        timeframe: str,
        day: date
    ):
        """
        Save data for a single day to Parquet and update catalog.
        
        Args:
            df: DataFrame with OHLCV data
            source: Data source name
            symbol: Trading symbol
            timeframe: Timeframe
            day: Date for this data
        """
        if df.empty:
            return
        
        # Build file path
        year = day.year
        date_str = day.isoformat()
        
        file_path = (
            self.base_dir
            / "candles"
            / source
            / symbol.replace('/', '_')
            / timeframe
            / str(year)
            / f"{date_str}.parquet"
        )
        
        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add metadata columns
        df_save = df.copy()
        df_save['source'] = source
        df_save['symbol'] = symbol
        df_save['timeframe'] = timeframe
        
        # Save to Parquet
        df_save.to_parquet(file_path, index=False)
        
        # Update parquet_files catalog
        file_id = hash(str(file_path))
        
        self.conn.execute("""
            INSERT OR REPLACE INTO parquet_files
            (id, kind, source, symbol, timeframe, date, path)
            VALUES (?, 'candles', ?, ?, ?, ?, ?)
        """, [file_id, source, symbol, timeframe, day, str(file_path)])
        
        # Update data_coverage
        self.conn.execute("""
            INSERT OR REPLACE INTO data_coverage
            (source, symbol, timeframe, date, complete, row_count)
            VALUES (?, ?, ?, ?, TRUE, ?)
        """, [source, symbol, timeframe, day, len(df_save)])
        
        print(f"  ✓ Saved {len(df_save)} rows to {file_path.name}")
    
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
        
        This method:
        1. Checks what data exists locally
        2. Identifies missing date ranges
        3. Fetches missing data from client (if provided)
        4. Saves new data to local cache
        5. Returns complete dataset from local storage
        
        Args:
            source: Data source ('BINANCE', 'YAHOO', 'ALPACA', 'CCXT')
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            start: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            client: Optional exchange client for fetching missing data
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        print(f"Requesting {source}:{symbol}:{timeframe} from {start} to {end}")
        
        # Find missing dates
        missing_dates = self._get_missing_dates(source, symbol, timeframe, start, end)
        
        # Fetch missing data if client provided
        if missing_dates and client:
            print(f"Missing {len(missing_dates)} days, fetching from {source}...")
            
            for day in missing_dates:
                try:
                    # Fetch data for this day
                    day_start = datetime.combine(day, datetime.min.time())
                    day_end = day_start + timedelta(days=1)
                    
                    df_day = client.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        start=day_start.isoformat(),
                        end=day_end.isoformat()
                    )
                    
                    if df_day is not None and not df_day.empty:
                        self._save_daily_data(df_day, source, symbol, timeframe, day)
                    
                except Exception as e:
                    print(f"  ✗ Error fetching {day}: {e}")
        
        elif missing_dates and not client:
            print(f"⚠ Missing {len(missing_dates)} days but no client provided for fetching")
        
        # Read from local cache
        # First, get list of files for this source/symbol/timeframe
        files_query = """
            SELECT path
            FROM parquet_files
            WHERE kind = 'candles'
              AND source = ?
              AND symbol = ?
              AND timeframe = ?
        """
        
        files_df = self.conn.execute(files_query, [
            source, symbol, timeframe
        ]).df()
        
        if files_df.empty:
            print("⚠ No data found in cache")
            return pd.DataFrame()
        
        # Get list of file paths
        file_paths = files_df['path'].tolist()
        
        # Read all files and filter by date
        query = """
            SELECT 
                timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM read_parquet(?)
            WHERE timestamp >= ?
              AND timestamp < ?
            ORDER BY timestamp
        """
        
        try:
            df = self.conn.execute(query, [
                file_paths, start, end
            ]).df()
            
            if df.empty:
                print("⚠ No data found in cache")
            else:
                print(f"✓ Loaded {len(df)} rows from cache")
            
            return df
            
        except Exception as e:
            print(f"⚠ Error reading from cache: {e}")
            return pd.DataFrame()
    
    def get_coverage_info(
        self,
        source: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get information about data coverage in cache.
        
        Args:
            source: Filter by source (optional)
            symbol: Filter by symbol (optional)
            timeframe: Filter by timeframe (optional)
            
        Returns:
            DataFrame with coverage statistics
        """
        query = """
            SELECT 
                source,
                symbol,
                timeframe,
                COUNT(*) as days,
                MIN(date) as first_date,
                MAX(date) as last_date,
                SUM(row_count) as total_rows
            FROM data_coverage
            WHERE 1=1
        """
        
        params = []
        if source:
            query += " AND source = ?"
            params.append(source)
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        
        query += """
            GROUP BY source, symbol, timeframe
            ORDER BY source, symbol, timeframe
        """
        
        return self.conn.execute(query, params).df()
    
    def clear_cache(
        self,
        source: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ):
        """
        Clear cached data (optionally filtered).
        
        Args:
            source: Clear only this source (optional)
            symbol: Clear only this symbol (optional)
            timeframe: Clear only this timeframe (optional)
        """
        # Build WHERE clause
        where_parts = []
        params = []
        
        if source:
            where_parts.append("source = ?")
            params.append(source)
        if symbol:
            where_parts.append("symbol = ?")
            params.append(symbol)
        if timeframe:
            where_parts.append("timeframe = ?")
            params.append(timeframe)
        
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        # Delete from tables
        self.conn.execute(f"DELETE FROM data_coverage WHERE {where_clause}", params)
        self.conn.execute(f"DELETE FROM parquet_files WHERE {where_clause}", params)
        
        print("✓ Cache cleared")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
