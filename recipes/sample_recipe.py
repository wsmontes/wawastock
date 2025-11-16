"""
Sample recipe - Example workflow using SMA crossover strategy.

This recipe demonstrates a complete backtest workflow:
1. Load price data for a symbol
2. Run SMA crossover strategy
3. Display results
"""

from recipes.base_recipe import BaseRecipe
from strategies.sample_sma_strategy import SampleSMAStrategy


class SampleRecipe(BaseRecipe):
    """
    Sample recipe that runs a SMA crossover strategy on test data.
    
    This is a simple example showing how to:
    - Load data using DataEngine
    - Execute a strategy using BacktestEngine
    - Present results to the user
    """
    
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
        print("=" * 80)
        print("SAMPLE RECIPE: SMA Crossover Strategy")
        print("=" * 80)
        print(f"Symbol: {symbol}")
        print(f"Period: {start} to {end}")
        print(f"Strategy: SMA Crossover (Fast: {fast_period}, Slow: {slow_period})")
        print("=" * 80)
        print()
        
        # Step 1: Load data
        print(f"Loading data for {symbol}...")
        try:
            data_df = self.data_engine.load_prices(
                symbol=symbol,
                start=start,
                end=end
            )
            print(f"Loaded {len(data_df)} bars of data")
            print()
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            print(f"Please create a data file at: data/processed/{symbol}.parquet")
            return
        
        # Step 2: Run backtest
        print("Running backtest...")
        print()
        results = self.backtest_engine.run_backtest(
            strategy_cls=SampleSMAStrategy,
            data_df=data_df,
            fast_period=fast_period,
            slow_period=slow_period
        )
        
        # Step 3: Display results
        print()
        print("=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)
        print(f"Initial Portfolio Value: ${results['initial_value']:,.2f}")
        print(f"Final Portfolio Value:   ${results['final_value']:,.2f}")
        print(f"Profit/Loss:             ${results['pnl']:,.2f}")
        print(f"Return:                  {results['return_pct']:.2f}%")
        
        # Display analyzer results if available
        if results['analyzers']:
            print()
            print("Performance Metrics:")
            print("-" * 80)
            
            analyzers = results['analyzers']
            
            if 'sharpe' in analyzers and analyzers['sharpe']:
                print(f"Sharpe Ratio:            {analyzers['sharpe']:.3f}")
            
            if 'max_drawdown' in analyzers and analyzers['max_drawdown']:
                print(f"Max Drawdown:            {analyzers['max_drawdown']:.2f}%")
            
            if 'total_return' in analyzers and analyzers['total_return']:
                print(f"Total Return:            {analyzers['total_return']:.2f}%")
        
        print("=" * 80)
