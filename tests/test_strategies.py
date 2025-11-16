"""
Tests for strategies.
"""

import pytest
import pandas as pd
import backtrader as bt
from datetime import datetime, timedelta
from typing import Any, cast

bt = cast(Any, bt)

from strategies.rsi_strategy import RSIStrategy
from strategies.sample_sma_strategy import SampleSMAStrategy
from strategies.multi_timeframe_strategy import MultiTimeframeMomentumStrategy


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
        data = bt.feeds.PandasData(dataname=df)  # type: ignore[arg-type]
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
        data = bt.feeds.PandasData(dataname=df)  # type: ignore[arg-type]
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
            
            data = bt.feeds.PandasData(dataname=df)  # type: ignore[arg-type]
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


class TestMultiTimeframeStrategy:
    """Tests for advanced multi-timeframe strategy."""

    def test_initialization(self):
        """Strategy should register without errors."""
        cerebro = bt.Cerebro()
        cerebro.addstrategy(MultiTimeframeMomentumStrategy)
        assert len(cerebro.strats) == 1

    def test_runs_on_sample_data(self, sample_ohlcv_data):
        """Strategy should run on sample data without attribute errors."""
        cerebro = bt.Cerebro()
        cerebro.addstrategy(
            MultiTimeframeMomentumStrategy,
            allow_pyramid=False,
            volume_threshold=0.0,
            risk_per_trade=0.005,
            fast_ema=8,
            slow_ema=21,
            trend_ema=55,
            volume_ma_period=10,
            adx_period=10,
            atr_period=10,
        )

        df = sample_ohlcv_data.copy().set_index('timestamp')
        data = bt.feeds.PandasData(dataname=df)  # type: ignore[arg-type]
        cerebro.adddata(data)
        cerebro.broker.setcash(50000)
        cerebro.run()
        assert cerebro.broker.getvalue() > 0

class TestMultiTimeframeHelpers:
    """Unit tests for MultiTimeframeMomentumStrategy helper methods."""

    def test_safe_divide_handles_zero_denominator(self):
        """_safe_divide should fallback to default when denominator is zero."""
        helper = MultiTimeframeMomentumStrategy._safe_divide
        assert helper(10, 2) == 5
        assert helper(10, 0) == 0
        assert helper(10, 0, default=1.5) == 1.5

    def test_average_entry_handles_empty_list(self):
        """_average_entry should use fallback when prices list empty."""
        helper = MultiTimeframeMomentumStrategy._average_entry
        assert helper([100, 110], 90) == 105
        assert helper([], 95) == 95
