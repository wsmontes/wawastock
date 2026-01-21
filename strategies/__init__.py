"""
Strategies module - Trading strategies using backtrader.
"""

from .base_strategy import BaseStrategy
from .sample_sma_strategy import SampleSMAStrategy
from .rsi_strategy import RSIStrategy
from .macd_ema_strategy import MACDEMAStrategy
from .bollinger_rsi_strategy import BollingerRSIStrategy
from .multi_timeframe_strategy import MultiTimeframeMomentumStrategy
from .btc_adaptive_hold import BTCAdaptiveHold
from .btc_winning_v2 import BTCWinningV2

__all__ = [
    'BaseStrategy',
    'SampleSMAStrategy',
    'RSIStrategy',
    'MACDEMAStrategy',
    'BollingerRSIStrategy',
    'MultiTimeframeMomentumStrategy',
    'BTCAdaptiveHold',
    'BTCWinningV2',
]
