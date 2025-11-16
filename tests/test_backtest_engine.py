"""
Tests for BacktestEngine.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from engines.backtest_engine import BacktestEngine
from strategies.sample_sma_strategy import SampleSMAStrategy


class TestBacktestEngine:
    """Test cases for BacktestEngine."""
    
    def test_initialization(self):
        """Test engine initialization."""
        engine = BacktestEngine()
        
        assert engine.initial_cash == 100000
        assert engine.commission == 0.001
        assert engine.stake == 100
    
    def test_custom_initial_cash(self):
        """Test custom initial cash."""
        engine = BacktestEngine(initial_cash=50000)
        
        assert engine.initial_cash == 50000
    
    def test_create_cerebro(self):
        """Test cerebro creation."""
        engine = BacktestEngine()
        cerebro = engine.create_cerebro()
        
        assert cerebro is not None
        assert cerebro.broker.getvalue() == 100000
    
    def test_run_backtest_insufficient_data(self, sample_ohlcv_data):
        """Test backtest with insufficient data raises error."""
        engine = BacktestEngine()
        
        # Create small dataset (less than 50 bars)
        small_df = sample_ohlcv_data.head(30).copy()
        small_df = small_df.set_index('timestamp')
        
        with pytest.raises(ValueError, match="Insufficient data"):
            engine.run_backtest(SampleSMAStrategy, small_df)
    
    def test_run_backtest_valid_data(self, sample_ohlcv_data):
        """Test backtest with valid data."""
        engine = BacktestEngine()
        
        df = sample_ohlcv_data.copy()
        df = df.set_index('timestamp')
        
        results = engine.run_backtest(SampleSMAStrategy, df, fast_period=5, slow_period=20)
        
        assert results is not None
        assert 'initial_value' in results
        assert 'final_value' in results
        assert 'return_pct' in results
    
    def test_backtest_returns_metrics(self, sample_ohlcv_data):
        """Test backtest returns correct metrics."""
        engine = BacktestEngine()
        
        df = sample_ohlcv_data.copy()
        df = df.set_index('timestamp')
        
        results = engine.run_backtest(SampleSMAStrategy, df, fast_period=5, slow_period=20)
        
        assert results['initial_value'] == 100000
        assert results['final_value'] > 0
        assert isinstance(results['return_pct'], float)
        assert results['pnl'] == results['final_value'] - results['initial_value']
    
    def test_empty_dataframe(self):
        """Test backtest with empty dataframe."""
        engine = BacktestEngine()
        
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="empty"):
            engine.run_backtest(SampleSMAStrategy, empty_df)
    
    def test_dataframe_with_nan_values(self, sample_ohlcv_data):
        """Test backtest handles NaN values."""
        engine = BacktestEngine()
        
        df = sample_ohlcv_data.copy()
        # Add some NaN values
        df.loc[10:15, 'close'] = None
        df = df.set_index('timestamp')
        
        # Should handle NaN values (fill forward/backward)
        results = engine.run_backtest(SampleSMAStrategy, df, fast_period=5, slow_period=20)
        
        assert results is not None
        assert results['final_value'] > 0


class TestBacktestEngineIntegration:
    """Integration tests for BacktestEngine."""
    
    def test_multiple_strategies_same_data(self, sample_ohlcv_data):
        """Test running different strategies on same data."""
        from strategies.rsi_strategy import RSIStrategy
        
        df = sample_ohlcv_data.copy()
        df = df.set_index('timestamp')
        
        strategies = [RSIStrategy, SampleSMAStrategy]
        results_list = []
        
        for strat in strategies:
            engine = BacktestEngine()
            results = engine.run_backtest(strat, df)
            results_list.append(results)
        
        # All should complete
        assert len(results_list) == 2
        for result in results_list:
            assert result['final_value'] > 0
    
    def test_strategy_with_custom_params(self, sample_ohlcv_data):
        """Test strategy with custom parameters."""
        from strategies.rsi_strategy import RSIStrategy
        
        engine = BacktestEngine()
        
        df = sample_ohlcv_data.copy()
        df = df.set_index('timestamp')
        
        results = engine.run_backtest(
            RSIStrategy,
            df,
            rsi_period=21,
            oversold=25,
            overbought=75
        )
        
        assert results is not None
        assert results['final_value'] > 0
