"""
RSI Recipe - Basic mean reversion strategy workflow.

This recipe demonstrates a simple RSI-based trading system suitable for
beginners learning algorithmic trading.
"""

from recipes.base_recipe import BaseRecipe
from strategies.rsi_strategy import RSIStrategy
from engines.report_engine import ReportEngine


class RSIRecipe(BaseRecipe):
    """
    Recipe for RSI mean reversion strategy.
    
    Uses oversold/overbought conditions to identify reversal opportunities
    with stop loss protection.
    """
    
    strategy_cls = RSIStrategy

    def __init__(self, data_engine, backtest_engine):
        """Initialize recipe with engines."""
        super().__init__(data_engine, backtest_engine)
        self.report = ReportEngine()
    
    def run(
        self,
        symbol: str = "AAPL",
        start: str = "2020-01-01",
        end: str = "2023-12-31",
        rsi_period: int = 14,
        oversold: int = 30,
        overbought: int = 70,
        stop_loss_pct: float = 0.02
    ):
        """
        Execute the RSI recipe.
        
        Args:
            symbol: Symbol to backtest (default: "AAPL")
            start: Start date (default: "2020-01-01")
            end: End date (default: "2023-12-31")
            rsi_period: RSI period (default: 14)
            oversold: Oversold threshold (default: 30)
            overbought: Overbought threshold (default: 70)
            stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        """
        # Print strategy header
        self.report.print_strategy_header(
            strategy_name="RSI Mean Reversion",
            symbol=symbol,
            start=start,
            end=end,
            params={
                'rsi_period': rsi_period,
                'oversold': oversold,
                'overbought': overbought,
                'stop_loss_pct': f"{stop_loss_pct*100:.1f}%"
            }
        )
        
        # Load data
        self.report.print_step(f"Loading data for {symbol}...")
        try:
            data_df = self.data_engine.load_prices(
                symbol=symbol,
                start=start,
                end=end
            )
            self.report.print_data_summary(
                rows=len(data_df),
                start_date=str(data_df.index[0].date()),
                end_date=str(data_df.index[-1].date())
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
            strategy_cls=RSIStrategy,
            data_df=data_df,
            rsi_period=rsi_period,
            oversold=oversold,
            overbought=overbought,
            stop_loss_pct=stop_loss_pct
        )
        
        # Display results
        self.report.print_backtest_results(results)

