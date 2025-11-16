"""
RSI Recipe - Basic mean reversion strategy workflow.

This recipe demonstrates a simple RSI-based trading system suitable for
beginners learning algorithmic trading.
"""

from recipes.base_recipe import BaseRecipe
from strategies.rsi_strategy import RSIStrategy


class RSIRecipe(BaseRecipe):
    """
    Recipe for RSI mean reversion strategy.
    
    Uses oversold/overbought conditions to identify reversal opportunities
    with stop loss protection.
    """
    
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
        print("=" * 80)
        print("BASIC STRATEGY: RSI Mean Reversion")
        print("=" * 80)
        print(f"Symbol: {symbol}")
        print(f"Period: {start} to {end}")
        print(f"RSI Period: {rsi_period}")
        print(f"Oversold: {oversold} | Overbought: {overbought}")
        print(f"Stop Loss: {stop_loss_pct*100:.1f}%")
        print("=" * 80)
        print()
        
        # Load data
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
            print(f"Hint: Run 'python main.py data load {symbol}' to download data")
            return
        
        # Run backtest
        print("Running backtest...")
        print()
        results = self.backtest_engine.run_backtest(
            strategy_cls=RSIStrategy,
            data_df=data_df,
            rsi_period=rsi_period,
            oversold=oversold,
            overbought=overbought,
            stop_loss_pct=stop_loss_pct
        )
        
        # Display results
        print()
        print("=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)
        print(f"Final Portfolio Value: ${results['final_value']:,.2f}")
        print(f"Total Return: {results['return_pct']:.2f}%")
        print()
        print("Strategy Overview:")
        print("- Entry: RSI crosses above oversold threshold")
        print("- Exit: RSI crosses below overbought OR stop loss hit")
        print("- Risk Management: Fixed stop loss per trade")
        print("=" * 80)
