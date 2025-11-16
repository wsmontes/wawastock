"""
Tests for LocalDataStore V2.
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime

from engines.local_data_store_v2 import LocalDataStoreV2


class TestLocalDataStoreV2:
    """Test cases for LocalDataStoreV2."""
    
    def test_init(self, temp_dir):
        """Test initialization."""
        store = LocalDataStoreV2(
            duckdb_path=str(Path(temp_dir) / "test.duckdb"),
            base_dir=str(Path(temp_dir) / "parquet")
        )
        
        assert store.conn is not None
        assert Path(temp_dir, "parquet").exists()
    
    def test_get_file_path_high_frequency(self, temp_dir):
        """Test file path generation for high frequency data."""
        store = LocalDataStoreV2(
            duckdb_path=str(Path(temp_dir) / "test.duckdb"),
            base_dir=str(Path(temp_dir) / "parquet")
        )
        
        # High frequency (1m) should include year
        path = store._get_file_path('binance/spot', 'BTCUSDT', '1m', 2023)
        
        assert '1m' in str(path)
        assert 'BTCUSDT' in str(path)
        assert '2023.parquet' in str(path)
    
    def test_get_file_path_low_frequency(self, temp_dir):
        """Test file path generation for low frequency data."""
        store = LocalDataStoreV2(
            duckdb_path=str(Path(temp_dir) / "test.duckdb"),
            base_dir=str(Path(temp_dir) / "parquet")
        )
        
        # Low frequency (1d) should NOT include year
        path = store._get_file_path('stocks/us', 'AAPL', '1d')
        
        assert '1d' in str(path)
        assert 'AAPL.parquet' in str(path)
    
    def test_save_and_get_data(self, temp_dir, sample_ohlcv_data):
        """Test saving and retrieving data."""
        store = LocalDataStoreV2(
            duckdb_path=str(Path(temp_dir) / "test.duckdb"),
            base_dir=str(Path(temp_dir) / "parquet")
        )
        
        # Save data
        store.save_data(
            sample_ohlcv_data.copy(),
            source='stocks/us',
            symbol='TEST',
            timeframe='1d'
        )
        
        # Retrieve data
        df = store.get_data(
            source='stocks/us',
            symbol='TEST',
            timeframe='1d',
            start='2023-01-01',
            end='2023-04-30'
        )
        
        assert not df.empty
        assert len(df) == 100
        assert 'close' in df.columns
    
    def test_has_data(self, temp_dir, sample_ohlcv_data):
        """Test data existence check."""
        store = LocalDataStoreV2(
            duckdb_path=str(Path(temp_dir) / "test.duckdb"),
            base_dir=str(Path(temp_dir) / "parquet")
        )
        
        # Should not have data initially
        assert not store.has_data(
            'stocks/us', 'TEST', '1d', '2023-01-01', '2023-12-31'
        )
        
        # Save data
        store.save_data(
            sample_ohlcv_data.copy(),
            source='stocks/us',
            symbol='TEST',
            timeframe='1d'
        )
        
        # Should have data now
        assert store.has_data(
            'stocks/us', 'TEST', '1d', '2023-01-01', '2023-12-31'
        )
    
    def test_merge_duplicate_data(self, temp_dir, sample_ohlcv_data):
        """Test that duplicate data is merged correctly."""
        store = LocalDataStoreV2(
            duckdb_path=str(Path(temp_dir) / "test.duckdb"),
            base_dir=str(Path(temp_dir) / "parquet")
        )
        
        # Save data twice
        store.save_data(
            sample_ohlcv_data.copy(),
            source='stocks/us',
            symbol='TEST',
            timeframe='1d'
        )
        
        store.save_data(
            sample_ohlcv_data.copy(),
            source='stocks/us',
            symbol='TEST',
            timeframe='1d'
        )
        
        # Should still have 100 bars (no duplicates)
        df = store.get_data(
            source='stocks/us',
            symbol='TEST',
            timeframe='1d',
            start='2023-01-01',
            end='2023-12-31'
        )
        
        assert len(df) == 100
    
    def test_catalog_update(self, temp_dir, sample_ohlcv_data):
        """Test that catalog is updated correctly."""
        store = LocalDataStoreV2(
            duckdb_path=str(Path(temp_dir) / "test.duckdb"),
            base_dir=str(Path(temp_dir) / "parquet")
        )
        
        # Save data
        store.save_data(
            sample_ohlcv_data.copy(),
            source='stocks/us',
            symbol='TEST',
            timeframe='1d'
        )
        
        # Check catalog
        result = store.conn.execute(
            "SELECT * FROM data_files WHERE symbol = 'TEST'"
        ).fetchall()
        
        assert len(result) == 1
        assert result[0][1] == 'TEST'  # symbol (index 1)
        assert result[0][6] == 100      # row_count (index 6)
