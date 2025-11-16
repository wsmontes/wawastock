"""
Base engine module - Abstract base class for all engines.
"""

from abc import ABC, abstractmethod
from utils.logger import get_logger


class BaseEngine(ABC):
    """
    Base class for all engine types (backtest, data, etc.).
    
    Engines are components responsible for specific tasks in the framework:
    - DataEngine: handles data loading and querying
    - BacktestEngine: handles backtest execution with backtrader
    
    All engines must implement the run() method.
    """
    
    def __init__(self):
        """Initialize base engine with logger."""
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def run(self):
        """
        Execute the main functionality of the engine.
        
        This method should be implemented by subclasses to define
        the specific behavior of each engine type.
        """
        pass
