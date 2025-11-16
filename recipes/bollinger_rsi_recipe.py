"""
Bollinger Bands + RSI Recipe - Advanced mean reversion strategy workflow.

This recipe implements a professional-grade mean reversion system with
sophisticated risk management and exit strategies.
"""

from recipes.base_recipe import BaseRecipe
from strategies.bollinger_rsi_strategy import BollingerRSIStrategy
from engines.report_engine import ReportEngine


class BollingerRSIRecipe(BaseRecipe):
    """
    Recipe for advanced Bollinger Bands + RSI strategy.
    
    Combines volatility analysis with momentum indicators for high-probability
    mean reversion trades with ATR-based position sizing.
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
        bb_period: int = 20,
        bb_dev: float = 2.0,
        rsi_period: int = 14,
        risk_per_trade: float = 0.02,
        partial_take_profit: float = 0.5
    ):
        """
        Execute the Bollinger + RSI recipe.
        
        Args:
            symbol: Symbol to backtest (default: "AAPL")
            start: Start date (default: "2020-01-01")
            end: End date (default: "2023-12-31")
            bb_period: Bollinger Bands period (default: 20)
            bb_dev: BB standard deviations (default: 2.0)
            rsi_period: RSI period (default: 14)
            risk_per_trade: Risk per trade as % of equity (default: 0.02 = 2%)
            partial_take_profit: % to close at first target (default: 0.5 = 50%)
        """
        # Print strategy header
        self.report.print_strategy_header(
            strategy_name="Bollinger Bands + RSI Mean Reversion",
            symbol=symbol,
            start=start,
            end=end,
            params={
                'bollinger': f"{bb_period} period, {bb_dev} std dev",
                'rsi': f"{rsi_period} period",
                'risk_per_trade': f"{risk_per_trade*100:.1f}%",
                'partial_profit': f"{partial_take_profit*100:.0f}% at mid-BB"
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
            strategy_cls=BollingerRSIStrategy,
            data_df=data_df,
            bb_period=bb_period,
            bb_dev=bb_dev,
            rsi_period=rsi_period,
            risk_per_trade=risk_per_trade,
            partial_take_profit=partial_take_profit
        )
        
        # Display results
        self.report.print_backtest_results(results)
