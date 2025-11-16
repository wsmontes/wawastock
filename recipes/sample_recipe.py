"""
Sample recipe - Example workflow using SMA crossover strategy.

This recipe demonstrates a complete backtest workflow:
1. Load price data for a symbol
2. Run SMA crossover strategy
3. Display results
"""

from recipes.base_recipe import BaseRecipe
from strategies.sample_sma_strategy import SampleSMAStrategy
from engines.report_engine import ReportEngine


class SampleRecipe(BaseRecipe):
    """
    Sample recipe that runs a SMA crossover strategy on test data.
    
    This is a simple example showing how to:
    - Load data using DataEngine
    - Execute a strategy using BacktestEngine
    - Present results to the user
    """
    
    strategy_cls = SampleSMAStrategy

    def __init__(self, data_engine, backtest_engine):
        """Initialize recipe with engines."""
        super().__init__(data_engine, backtest_engine)
        self.report = ReportEngine()
    
    def run(
        self,
        symbol: str = "TEST",
        start: str = "2020-01-01",
        end: str = "2020-12-31",
        fast_period: int = 10,
        slow_period: int = 20
    ):
        """
        Execute the sample recipe.
        
        Args:
            symbol: Symbol to backtest (default: "TEST")
            start: Start date for backtest (default: "2020-01-01")
            end: End date for backtest (default: "2020-12-31")
            fast_period: Fast SMA period (default: 10)
            slow_period: Slow SMA period (default: 20)
        """
        # Print strategy header
        self.report.print_strategy_header(
            strategy_name="SMA Crossover Strategy",
            symbol=symbol,
            start=start,
            end=end,
            params={
                'fast_sma': f"{fast_period}",
                'slow_sma': f"{slow_period}"
            }
        )
        
        # Step 1: Load data
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
                f"Create a data file at: data/processed/{symbol}.parquet"
            )
            return
        
        # Step 2: Run backtest
        self.report.print_step("Running backtest...")
        results = self.backtest_engine.run_backtest(
            strategy_cls=SampleSMAStrategy,
            data_df=data_df,
            fast_period=fast_period,
            slow_period=slow_period
        )
        
        # Step 3: Display results
        self.report.print_backtest_results(results)
