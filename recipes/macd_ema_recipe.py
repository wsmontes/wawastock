"""
MACD + EMA Recipe - Intermediary trend-following strategy workflow.

This recipe demonstrates a more sophisticated approach combining multiple
indicators for higher probability trades.
"""

from recipes.base_recipe import BaseRecipe
from strategies.macd_ema_strategy import MACDEMAStrategy
from engines.report_engine import ReportEngine
from rich.console import Console

console = Console()


class MACDEMARecipe(BaseRecipe):
    """
    Recipe for MACD + EMA trend-following strategy.
    
    Combines MACD crossover signals with EMA trend filter for
    improved win rate and dynamic position sizing.
    """
    
    def __init__(self, data_engine, backtest_engine):
        """Initialize recipe with engines."""
        super().__init__(data_engine, backtest_engine)
        self.report = ReportEngine()
    
    def run(
        self,
        symbol: str = "AAPL",
        start: str = "2020-01-01",
        end: str = "2023-12-31",
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        trend_ema: int = 200,
        position_size_pct: float = 0.95,
        stop_loss_pct: float = 0.03,
        trail_pct: float = 0.02
    ):
        """
        Execute the MACD + EMA recipe.
        
        Args:
            symbol: Symbol to backtest (default: "AAPL")
            start: Start date (default: "2020-01-01")
            end: End date (default: "2023-12-31")
            macd_fast: MACD fast period (default: 12)
            macd_slow: MACD slow period (default: 26)
            macd_signal: MACD signal period (default: 9)
            trend_ema: Trend filter EMA (default: 200)
            position_size_pct: Position size as % of equity (default: 0.95 = 95%)
            stop_loss_pct: Initial stop loss % (default: 0.03 = 3%)
            trail_pct: Trailing stop % (default: 0.02 = 2%)
        """
        # Load data first
        self.report.print_step(f"Loading data for {symbol}...")
        try:
            data_df = self.data_engine.load_prices(
                symbol=symbol,
                start=start,
                end=end
            )
        except FileNotFoundError as e:
            self.report.print_error(
                "Data not found",
                f"Run 'python main.py data load {symbol}' to download data"
            )
            return
        
        # Run backtest
        self.report.print_step("Running backtest...")
        results = self.backtest_engine.run_backtest(
            strategy_cls=MACDEMAStrategy,
            data_df=data_df,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            trend_ema=trend_ema,
            position_size_pct=position_size_pct,
            stop_loss_pct=stop_loss_pct,
            trail_pct=trail_pct
        )
        
        # Print strategy header with configuration
        console.print()
        self.report.print_strategy_header(
            strategy_name="MACD + EMA Trend Following",
            symbol=symbol,
            start=start,
            end=end,
            params={
                'macd': f"{macd_fast}/{macd_slow}/{macd_signal}",
                'trend_filter': f"{trend_ema} EMA",
                'position_size': f"{position_size_pct*100:.0f}%",
                'stop_loss': f"{stop_loss_pct*100:.1f}%",
                'trailing_stop': f"{trail_pct*100:.1f}%"
            }
        )
        
        # Display results
        self.report.print_backtest_results(results)
