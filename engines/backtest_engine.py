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
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        return cerebro
    
    def run_backtest(
        self,
        strategy_cls: Type[bt.Strategy],
        data_df: pd.DataFrame,
        symbol: str = "N/A",
        **strategy_params
    ) -> Dict[str, Any]:
        """
        Run a backtest with the given strategy and data.
        
        Args:
            strategy_cls: Backtrader Strategy class to use
            data_df: DataFrame with OHLCV data (datetime index required)
            symbol: Trading symbol (for logging purposes)
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
        
        # Run backtest with progress indicator (silent logging)
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
            
            if hasattr(strategy.analyzers, 'trades'):
                trade_analysis = strategy.analyzers.trades.get_analysis()
                analyzers_results['total_trades'] = trade_analysis.get('total', {}).get('total', 0)
                analyzers_results['won_trades'] = trade_analysis.get('won', {}).get('total', 0)
                analyzers_results['lost_trades'] = trade_analysis.get('lost', {}).get('total', 0)
        
        # === RICH CONSOLE OUTPUT ===
        from rich.table import Table
        from rich.panel import Panel
        
        console.print()  # Blank line before results
        
        # Create results table
        table = Table(
            title=f"[bold cyan]Backtest Results: {symbol}[/bold cyan]", 
            show_header=True, 
            header_style="bold cyan",
            title_style="bold cyan"
        )
        table.add_column("Metric", style="bold white", width=22)
        table.add_column("Value", justify="right", style="white", width=25)
        
        # Performance metrics
        pnl_color = "green" if pnl >= 0 else "red"
        table.add_row("Symbol", f"[cyan]{symbol}[/cyan]")
        table.add_row("Strategy", f"[yellow]{strategy.__class__.__name__}[/yellow]")
        table.add_section()
        table.add_row("Initial Capital", f"${initial_value:,.2f}")
        table.add_row("Final Value", f"${final_value:,.2f}")
        table.add_row("Total P&L", f"[{pnl_color}]${pnl:,.2f}[/{pnl_color}]")
        table.add_row("Total Return", f"[{pnl_color}]{return_pct:.2f}%[/{pnl_color}]")
        
        # Risk metrics
        if analyzers_results:
            table.add_section()
            sharpe = analyzers_results.get('sharpe')
            if sharpe is not None:
                sharpe_color = "green" if sharpe > 1 else "yellow" if sharpe > 0 else "red"
                table.add_row("Sharpe Ratio", f"[{sharpe_color}]{sharpe:.4f}[/{sharpe_color}]")
            
            max_dd = analyzers_results.get('max_drawdown')
            if max_dd is not None:
                dd_color = "green" if max_dd > -10 else "yellow" if max_dd > -25 else "red"
                table.add_row("Max Drawdown", f"[{dd_color}]{max_dd:.2f}%[/{dd_color}]")
            
            # Trade statistics
            total_trades = analyzers_results.get('total_trades', 0)
            if total_trades > 0:
                table.add_section()
                won_trades = analyzers_results.get('won_trades', 0)
                lost_trades = analyzers_results.get('lost_trades', 0)
                win_rate = (won_trades / total_trades) * 100
                avg_trade = pnl / total_trades
                
                table.add_row("Total Trades", str(total_trades))
                table.add_row("Won Trades", f"[green]{won_trades}[/green]")
                table.add_row("Lost Trades", f"[red]{lost_trades}[/red]")
                
                win_rate_color = "green" if win_rate >= 50 else "yellow" if win_rate >= 40 else "red"
                table.add_row("Win Rate", f"[{win_rate_color}]{win_rate:.2f}%[/{win_rate_color}]")
                
                avg_color = "green" if avg_trade > 0 else "red"
                table.add_row("Average Trade", f"[{avg_color}]${avg_trade:,.2f}[/{avg_color}]")
        
        console.print()
        console.print(table)
        console.print()
        
        # === FULL LOGGING OF ALL METRICS ===
        self.logger.info("=" * 60)
        self.logger.info("BACKTEST RESULTS - COMPLETE METRICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Symbol: {symbol}")
        self.logger.info(f"Strategy: {strategy.__class__.__name__}")
        self.logger.info(f"Initial Capital: ${initial_value:,.2f}")
        self.logger.info(f"Final Value: ${final_value:,.2f}")
        self.logger.info(f"Total P&L: ${pnl:,.2f}")
        self.logger.info(f"Total Return: {return_pct:.2f}%")
        
        # Log analyzer metrics
        if analyzers_results:
            self.logger.info("-" * 60)
            self.logger.info("RISK METRICS")
            self.logger.info("-" * 60)
            
            sharpe = analyzers_results.get('sharpe')
            if sharpe is not None:
                self.logger.info(f"Sharpe Ratio: {sharpe:.4f}")
            
            max_dd = analyzers_results.get('max_drawdown')
            if max_dd is not None:
                self.logger.info(f"Max Drawdown: {max_dd:.2f}%")
            
            self.logger.info("-" * 60)
            self.logger.info("TRADE STATISTICS")
            self.logger.info("-" * 60)
            
            total_trades = analyzers_results.get('total_trades', 0)
            won_trades = analyzers_results.get('won_trades', 0)
            lost_trades = analyzers_results.get('lost_trades', 0)
            
            self.logger.info(f"Total Trades: {total_trades}")
            self.logger.info(f"Won Trades: {won_trades}")
            self.logger.info(f"Lost Trades: {lost_trades}")
            
            if total_trades > 0:
                win_rate = (won_trades / total_trades) * 100
                avg_trade = pnl / total_trades
                self.logger.info(f"Win Rate: {win_rate:.2f}%")
                self.logger.info(f"Average Trade: ${avg_trade:,.2f}")
        
        self.logger.info("=" * 60)
        
        # Return results
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'pnl': pnl,
            'return_pct': return_pct,
            'analyzers': analyzers_results,
            'strategy': results[0]
        }
