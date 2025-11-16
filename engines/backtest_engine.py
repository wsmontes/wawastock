"""
Backtest engine module - Handles backtest execution using backtrader.
"""

from typing import Type, Dict, Any, List
import pandas as pd
import backtrader as bt
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .base_engine import BaseEngine


console = Console()


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
        super().__init__()
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
        # Validate data
        if data_df.empty:
            raise ValueError("Cannot run backtest: DataFrame is empty")
        
        min_bars_required = 250  # Conservative minimum for most indicators
        if len(data_df) < min_bars_required:
            console.print(f"\n[yellow]⚠️  WARNING: Dataset has only {len(data_df)} bars[/yellow]")
            console.print(f"[yellow]   Recommended minimum: {min_bars_required} bars[/yellow]")
            console.print(f"[yellow]   Strategy may not have enough data for indicators to initialize properly[/yellow]")
            console.print(f"[yellow]   Consider using a longer time period for more reliable results[/yellow]\n")
            
            # Check if we have at least bare minimum
            if len(data_df) < 50:
                raise ValueError(
                    f"Insufficient data: {len(data_df)} bars\n"
                    f"   Minimum required: 50 bars\n"
                    f"   Please use a longer time period (e.g., --start 2023-01-01 --end 2023-12-31)"
                )
        
        # Validate required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check for NaN values
        if data_df[required_cols].isnull().any().any():
            console.print("[yellow]⚠️  Warning: Data contains NaN values, filling forward...[/yellow]")
            data_df = data_df.ffill().bfill()
        
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
        
        # Run backtest with progress indicator
        self.logger.info(f"Starting Portfolio Value: ${initial_value:,.2f}")
        self.logger.info(f"Running backtest with {len(data_df)} bars...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running backtest...", total=None)
            
            try:
                results = cerebro.run()
                progress.update(task, completed=True)
            except Exception as e:
                progress.stop()
                raise RuntimeError(f"Backtest execution failed: {str(e)}")
        
        # Get final value
        final_value = cerebro.broker.getvalue()
        pnl = final_value - initial_value
        return_pct = (pnl / initial_value) * 100
        
        self.logger.info(f"Final Portfolio Value: ${final_value:,.2f}")
        pnl_color = "green" if pnl >= 0 else "red"
        console.print(f"PnL: [{pnl_color}]${pnl:,.2f} ({return_pct:.2f}%)[/{pnl_color}]")
        
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
