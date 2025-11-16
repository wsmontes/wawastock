"""
Tests for data sources.
"""

import pytest
from datetime import datetime

from engines.data_sources.yahoo_data_source import YahooDataSource


class TestYahooDataSource:
    """Test cases for Yahoo Finance data source."""
    
    def test_initialization(self):
        """Test data source initialization."""
        source = YahooDataSource()
        assert source is not None
    
    @pytest.mark.skip(reason="Requires network connection")
    def test_fetch_ohlcv_real_data(self):
        """Test fetching real data from Yahoo Finance."""
        source = YahooDataSource()
        
        df = source.fetch_ohlcv(
            symbol='AAPL',
            timeframe='1d',
            start='2023-01-01',
            end='2023-01-31'
        )
        
        assert not df.empty
        assert 'timestamp' in df.columns
        assert 'close' in df.columns
        assert len(df) > 0
    
    def test_invalid_symbol(self):
        """Test handling of invalid symbol."""
        source = YahooDataSource()
        
        # Should handle gracefully and return empty DataFrame
        df = source.fetch_ohlcv(
            symbol='INVALID_SYMBOL_XYZ',
            timeframe='1d',
            start='2023-01-01',
            end='2023-01-31'
        )
        
        # Should return empty DataFrame
        assert df.empty
    
    def test_invalid_date_range(self):
        """Test handling of invalid date range."""
        source = YahooDataSource()
        
        # End before start
        df = source.fetch_ohlcv(
            symbol='AAPL',
            timeframe='1d',
            start='2023-12-31',
            end='2023-01-01'
        )
        
        # Should return empty DataFrame
        assert df.empty


class TestDataSourceIntegration:
    """Integration tests for data sources."""
    
    @pytest.mark.skip(reason="Requires network connection")
    def test_fetch_multiple_symbols(self):
        """Test fetching data for multiple symbols."""
        source = YahooDataSource()
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        results = {}
        for symbol in symbols:
            df = source.fetch_ohlcv(
                symbol=symbol,
                timeframe='1d',
                start='2023-01-01',
                end='2023-01-31'
            )
            results[symbol] = df
        
        assert len(results) == 3
        for symbol, df in results.items():
            assert not df.empty
    
    @pytest.mark.skip(reason="Requires network connection")
    def test_different_timeframes(self):
        """Test fetching different timeframes."""
        source = YahooDataSource()
        timeframes = ['1d', '1wk', '1mo']
        
        results = {}
        for tf in timeframes:
            df = source.fetch_ohlcv(
                symbol='AAPL',
                timeframe=tf,
                start='2023-01-01',
                end='2023-12-31'
            )
            results[tf] = df
        
        # Daily should have more bars than weekly
        assert len(results['1d']) > len(results['1wk'])
        # Weekly should have more bars than monthly
        assert len(results['1wk']) > len(results['1mo'])
