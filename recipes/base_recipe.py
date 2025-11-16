"""
Base recipe module - Abstract base class for backtesting recipes.

Recipes are high-level workflows that coordinate:
- Data loading (via DataEngine)
- Strategy selection
- Backtest execution (via BacktestEngine)
"""

from abc import ABC, abstractmethod
from typing import Optional, Type

import backtrader as bt

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine


class BaseRecipe(ABC):
    """
    Base class for all backtesting recipes.
    
    A recipe coordinates the complete workflow of a backtest:
    1. Load data using DataEngine
    2. Configure and run backtest using BacktestEngine
    3. Process and present results
    
    Attributes:
        data_engine: Engine for loading and querying data
        backtest_engine: Engine for running backtests
    """
    
    # Strategy class used by the recipe's backtest
    strategy_cls: Optional[Type[bt.Strategy]] = None

    def __init__(
        self, 
        data_engine: DataEngine,
        backtest_engine: BacktestEngine
    ):
        """
        Initialize the recipe with required engines.
        
        Args:
            data_engine: Initialized DataEngine instance
            backtest_engine: Initialized BacktestEngine instance
        """
        self.data_engine = data_engine
        self.backtest_engine = backtest_engine
    
    @abstractmethod
    def run(self):
        """
        Execute the complete recipe workflow.
        
        This method should:
        1. Load necessary data using self.data_engine
        2. Run backtest using self.backtest_engine
        3. Process and display results
        """
        pass
