"""
Tests for strategies.
"""

import pytest
import pandas as pd
import backtrader as bt
from datetime import datetime, timedelta

from strategies.rsi_strategy import RSIStrategy
from strategies.sample_sma_strategy import SampleSMAStrategy


class TestRSIStrategy:
    """Test cases for RSI Strategy."""
    
    def test_strategy_initialization(self):
        """Test strategy initializes with correct parameters."""
        cerebro = bt.Cerebro()
        
        cerebro.addstrategy(
            RSIStrategy,
            rsi_period=14,
            oversold=30,
            overbought=70
        )
        
        # Should not raise any errors
        assert len(cerebro.strats) == 1
    
    def test_strategy_params(self):
        """Test strategy parameters can be customized."""
        cerebro = bt.Cerebro()
        
        cerebro.addstrategy(
            RSIStrategy,
            rsi_period=21,
            oversold=25,
            overbought=75
        )
        
        assert len(cerebro.strats) == 1
    
    def test_strategy_on_sample_data(self, sample_ohlcv_data):
        """Test strategy runs on sample data without errors."""
        cerebro = bt.Cerebro()
        # Use shorter RSI period for 100 bars
        cerebro.addstrategy(RSIStrategy, rsi_period=10)
        
        # Prepare data
        df = sample_ohlcv_data.copy()
        df = df.set_index('timestamp')
        
        # Add to cerebro
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)
        
        # Run
        cerebro.broker.setcash(100000)
        start_value = cerebro.broker.getvalue()
        
        results = cerebro.run()
        
        end_value = cerebro.broker.getvalue()
        
        # Should complete without errors
        assert results is not None
        assert end_value > 0


class TestSampleSMAStrategy:
    """Test cases for Sample SMA Strategy."""
    
    def test_strategy_initialization(self):
        """Test strategy initializes correctly."""
        cerebro = bt.Cerebro()
        
        cerebro.addstrategy(
            SampleSMAStrategy,
            fast_period=10,
            slow_period=30
        )
        
        assert len(cerebro.strats) == 1
    
    def test_strategy_on_sample_data(self, sample_ohlcv_data):
        """Test strategy runs on sample data."""
        cerebro = bt.Cerebro()
        cerebro.addstrategy(SampleSMAStrategy)
        
        # Prepare data
        df = sample_ohlcv_data.copy()
        df = df.set_index('timestamp')
        
        # Add to cerebro
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)
        
        # Run
        cerebro.broker.setcash(100000)
        results = cerebro.run()
        
        assert results is not None


class TestStrategyIntegration:
    """Integration tests for strategies."""
    
    def test_multiple_strategies(self, sample_ohlcv_data):
        """Test running multiple strategies on same data."""
        # Use shorter periods for 100 bars
        strategies = [
            (RSIStrategy, {'rsi_period': 10}),
            (SampleSMAStrategy, {'fast_period': 5, 'slow_period': 20})
        ]
        
        results = {}
        
        for strat, params in strategies:
            cerebro = bt.Cerebro()
            cerebro.addstrategy(strat, **params)
            
            df = sample_ohlcv_data.copy()
            df = df.set_index('timestamp')
            
            data = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(data)
            
            cerebro.broker.setcash(100000)
            start_value = cerebro.broker.getvalue()
            
            cerebro.run()
            
            end_value = cerebro.broker.getvalue()
            results[strat.__name__] = {
                'start': start_value,
                'end': end_value,
                'return': (end_value - start_value) / start_value * 100
            }
        
        # All strategies should complete
        assert len(results) == 2
        for name, result in results.items():
            assert result['end'] > 0
