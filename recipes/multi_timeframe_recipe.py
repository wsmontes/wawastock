"""
Multi-Timeframe Momentum Recipe - Maximum profitability strategy workflow.

This recipe implements an institutional-grade momentum system with
cutting-edge techniques for professional traders.
"""

from recipes.base_recipe import BaseRecipe
from strategies.multi_timeframe_strategy import MultiTimeframeMomentumStrategy
from engines.report_engine import ReportEngine


class MultiTimeframeRecipe(BaseRecipe):
    """
    Recipe for maximum profitability multi-timeframe momentum strategy.
    
    Implements professional-grade techniques including multi-timeframe analysis,
    trend strength filtering, volume confirmation, pyramiding, and sophisticated
    exit management.
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
        fast_ema: int = 21,
        slow_ema: int = 55,
        trend_ema: int = 200,
        adx_threshold: int = 25,
        risk_per_trade: float = 0.015,
        allow_pyramid: bool = True,
        pyramid_units: int = 3
    ):
        """
        Execute the Multi-Timeframe Momentum recipe.
        
        Args:
            symbol: Symbol to backtest (default: "AAPL")
            start: Start date (default: "2020-01-01")
            end: End date (default: "2023-12-31")
            fast_ema: Fast EMA period (default: 21)
            slow_ema: Slow EMA period (default: 55)
            trend_ema: Trend filter EMA (default: 200)
            adx_threshold: Minimum ADX for entry (default: 25)
            risk_per_trade: Risk per trade % (default: 0.015 = 1.5%)
            allow_pyramid: Enable pyramiding (default: True)
            pyramid_units: Max pyramid entries (default: 3)
        """
        # Print strategy header
        self.report.print_strategy_header(
            strategy_name="Multi-Timeframe Momentum with Pyramiding",
            symbol=symbol,
            start=start,
            end=end,
            params={
                'ema_system': f"{fast_ema}/{slow_ema} with {trend_ema} trend filter",
                'adx_threshold': f"{adx_threshold} (trend strength)",
                'risk_per_trade': f"{risk_per_trade*100:.2f}%",
                'pyramiding': f"{'Enabled' if allow_pyramid else 'Disabled'} ({pyramid_units} units)"
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
            strategy_cls=MultiTimeframeMomentumStrategy,
            data_df=data_df,
            fast_ema=fast_ema,
            slow_ema=slow_ema,
            trend_ema=trend_ema,
            adx_threshold=adx_threshold,
            risk_per_trade=risk_per_trade,
            allow_pyramid=allow_pyramid,
            pyramid_units=pyramid_units
        )
        
        # Display results
        self.report.print_backtest_results(results)
