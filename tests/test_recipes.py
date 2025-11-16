"""Tests for recipe metadata and programmatic execution mapping."""

from __future__ import annotations

from typing import Any, Dict, Type

import pandas as pd
import pytest

import main
from strategies.bollinger_rsi_strategy import BollingerRSIStrategy
from strategies.macd_ema_strategy import MACDEMAStrategy
from strategies.multi_timeframe_strategy import MultiTimeframeMomentumStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.sample_sma_strategy import SampleSMAStrategy


@pytest.mark.parametrize(
    "recipe_name,expected_cls",
    [
        ("sample", SampleSMAStrategy),
        ("rsi", RSIStrategy),
        ("macd_ema", MACDEMAStrategy),
        ("bollinger_rsi", BollingerRSIStrategy),
        ("multi_timeframe", MultiTimeframeMomentumStrategy),
    ],
)
def test_recipes_expose_strategy_cls(recipe_name: str, expected_cls: Type):
    """All recipes should declare the strategy they orchestrate."""
    recipe_cls = main.RECIPE_REGISTRY[recipe_name]
    assert getattr(recipe_cls, "strategy_cls", None) is expected_cls


@pytest.mark.parametrize(
    "recipe_name,strategy_cls,extra_params",
    [
        (
            "bollinger_rsi",
            BollingerRSIStrategy,
            {
                "bb_period": 25,
                "bb_dev": 2.5,
            },
        ),
        (
            "multi_timeframe",
            MultiTimeframeMomentumStrategy,
            {
                "rsi_period": 10,
                "rsi_entry_min": 55,
                "adx_period": 10,
                "adx_threshold": 30,
                "atr_period": 12,
                "risk_per_trade": 0.02,
                "max_position_size": 0.4,
                "allow_pyramid": 0,  # UI may send ints; recipe should coerce to bool
                "pyramid_units": 2,
                "pyramid_spacing": 0.03,
                "profit_target_atr": 2.5,
                "trail_start_atr": 1.5,
                "trail_pct": 0.015,
                "max_hold_bars": 40,
                "volume_ma_period": 15,
                "volume_threshold": 1.3,
            },
        ),
    ],
)
def test_run_recipe_programmatic_uses_recipe_strategy(monkeypatch, sample_ohlcv_data, recipe_name, strategy_cls, extra_params):
    """Programmatic recipe execution should use the recipe's declared strategy class."""
    price_df = (
        sample_ohlcv_data
        .copy()
        .set_index("timestamp")
        [["open", "high", "low", "close", "volume"]]
    )

    class FakeDataEngine:
        def __init__(self, *args, **kwargs):
            pass

        def load_prices(self, *args, **kwargs):
            return price_df

    captured: Dict[str, Any] = {}

    class FakeBacktestEngine:
        def __init__(self, *args, **kwargs):
            pass

        def run_backtest(self, strategy_cls, data_df, symbol=None, **strategy_params):
            captured["strategy_cls"] = strategy_cls
            captured["strategy_params"] = strategy_params
            captured["symbol"] = symbol
            return {
                "initial_value": 100000.0,
                "final_value": 105000.0,
                "pnl": 5000.0,
                "return_pct": 5.0,
                "analyzers": {
                    "sharpe": 1.2,
                    "max_drawdown": 7.5,
                    "total_trades": 2,
                    "won_trades": 1,
                    "lost_trades": 1,
                },
                "strategy": strategy_cls,
            }

    monkeypatch.setattr(main, "DataEngine", FakeDataEngine)
    monkeypatch.setattr(main, "BacktestEngine", FakeBacktestEngine)

    result = main.run_recipe_programmatic(
        recipe_name=recipe_name,
        symbol="AAPL",
        start="2020-01-01",
        end="2021-01-01",
        **extra_params,
    )

    assert captured["strategy_cls"] is strategy_cls
    assert captured["symbol"] == "AAPL"
    for key, value in extra_params.items():
        expected = bool(value) if key == "allow_pyramid" else value
        assert captured["strategy_params"][key] == expected
    assert result["symbol"] == "AAPL"
    assert result["strategy"] is strategy_cls
