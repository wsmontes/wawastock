"""
MACD + EMA Recipe - Intermediary trend-following strategy workflow.

This recipe demonstrates a more sophisticated approach combining multiple
indicators for higher probability trades.
"""

from recipes.base_recipe import BaseRecipe
from strategies.macd_ema_strategy import MACDEMAStrategy


class MACDEMARecipe(BaseRecipe):
    """
    Recipe for MACD + EMA trend-following strategy.
    
    Combines MACD crossover signals with EMA trend filter for
    improved win rate and dynamic position sizing.
    """
    
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
            trail_pct: Trailing stop % (default: 0.02 = 2%)
        """
        print("=" * 80)
        print("INTERMEDIARY STRATEGY: MACD + EMA Trend Following")
        print("=" * 80)
        print(f"Symbol: {symbol}")
        print(f"Period: {start} to {end}")
        print(f"MACD: {macd_fast}/{macd_slow}/{macd_signal}")
        print(f"Trend Filter: {trend_ema} EMA")
        print(f"Position Size: {position_size_pct*100:.0f}% of equity")
        print(f"Trailing Stop: {trail_pct*100:.1f}%")
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
            strategy_cls=MACDEMAStrategy,
            data_df=data_df,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            trend_ema=trend_ema,
            position_size_pct=position_size_pct,
            trail_pct=trail_pct
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
        print("- Entry: MACD crosses above signal + price above 200 EMA")
        print("- Exit: MACD crosses below signal OR trailing stop")
        print("- Position Sizing: 95% of equity per trade")
        print("- Risk Management: Dynamic trailing stop")
        print()
        print("Key Features:")
        print("✓ Trend filter reduces false signals")
        print("✓ Trailing stop protects profits")
        print("✓ Full position sizing for trending markets")
        print("=" * 80)
