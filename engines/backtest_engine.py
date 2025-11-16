"""
Backtest engine module - Handles backtest execution using backtrader.
"""

from typing import Type, Dict, Any, List
import pandas as pd
import backtrader as bt

from .base_engine import BaseEngine


class BacktestEngine(BaseEngine):
    """
    Engine responsible for running backtests using the backtrader library.
    
    Encapsulates Cerebro setup, data feed configuration, and execution.
    """
    
    def __init__(
        self, 
        initial_cash: float = 100000.0,
        commission: float = 0.001,  # 0.1%
        stake: int = 100
    ):
        """
        Initialize the BacktestEngine with default parameters.
        
        Args:
            initial_cash: Starting capital for backtests
            commission: Commission rate (0.001 = 0.1%)
            stake: Default number of shares/contracts per trade
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.stake = stake
    
    def run(self):
        """
        Not implemented for BacktestEngine - use run_backtest() instead.
        """
        raise NotImplementedError("BacktestEngine doesn't have a general run() method. Use run_backtest().")
    
    def create_cerebro(self) -> bt.Cerebro:
        """
        Create and configure a Cerebro instance with default settings.
        
        Returns:
            Configured Cerebro instance
        """
        cerebro = bt.Cerebro()
        
        # Set initial cash
        cerebro.broker.setcash(self.initial_cash)
        
        # Set commission
        cerebro.broker.setcommission(commission=self.commission)
        
        # Add analyzers for performance metrics
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        return cerebro
    
    def run_backtest(
        self,
        strategy_cls: Type[bt.Strategy],
        data_df: pd.DataFrame,
        **strategy_params
    ) -> Dict[str, Any]:
        """
        Run a backtest with the given strategy and data.
        
        Args:
            strategy_cls: Backtrader Strategy class to use
            data_df: DataFrame with OHLCV data (datetime index required)
            **strategy_params: Parameters to pass to the strategy
            
        Returns:
            Dictionary with backtest results including:
            - final_value: Final portfolio value
            - initial_value: Initial portfolio value
            - pnl: Profit and loss
            - return_pct: Return percentage
            - analyzers: Dictionary of analyzer results
        """
        # Create Cerebro
        cerebro = self.create_cerebro()
        
        # Convert DataFrame to backtrader data feed
        data_feed = bt.feeds.PandasData(
            dataname=data_df,
            datetime=None,  # Use index as datetime
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1  # Not used
        )
        
        # Add data feed to Cerebro
        cerebro.adddata(data_feed)
        
        # Add strategy with parameters
        cerebro.addstrategy(strategy_cls, **strategy_params)
        
        # Get initial value
        initial_value = cerebro.broker.getvalue()
        
        # Run backtest
        print(f"Starting Portfolio Value: ${initial_value:,.2f}")
        results = cerebro.run()
        
        # Get final value
        final_value = cerebro.broker.getvalue()
        pnl = final_value - initial_value
        return_pct = (pnl / initial_value) * 100
        
        print(f"Final Portfolio Value: ${final_value:,.2f}")
        print(f"PnL: ${pnl:,.2f} ({return_pct:.2f}%)")
        
        # Extract analyzer results
        strategy = results[0]
        analyzers_results = {}
        
        if hasattr(strategy, 'analyzers'):
            if hasattr(strategy.analyzers, 'sharpe'):
                sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
                analyzers_results['sharpe'] = sharpe_analysis.get('sharperatio', None)
            
            if hasattr(strategy.analyzers, 'drawdown'):
                dd_analysis = strategy.analyzers.drawdown.get_analysis()
                analyzers_results['max_drawdown'] = dd_analysis.get('max', {}).get('drawdown', None)
            
            if hasattr(strategy.analyzers, 'returns'):
                ret_analysis = strategy.analyzers.returns.get_analysis()
                analyzers_results['total_return'] = ret_analysis.get('rtot', None)
        
        # Return results
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'pnl': pnl,
            'return_pct': return_pct,
            'analyzers': analyzers_results,
            'strategy': results[0]
        }
