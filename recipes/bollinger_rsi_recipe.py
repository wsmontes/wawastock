"""
Bollinger Bands + RSI Recipe - Advanced mean reversion strategy workflow.

This recipe implements a professional-grade mean reversion system with
sophisticated risk management and exit strategies.
"""

from recipes.base_recipe import BaseRecipe
from strategies.bollinger_rsi_strategy import BollingerRSIStrategy


class BollingerRSIRecipe(BaseRecipe):
    """
    Recipe for advanced Bollinger Bands + RSI strategy.
    
    Combines volatility analysis with momentum indicators for high-probability
    mean reversion trades with ATR-based position sizing.
    """
    
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
        print("=" * 80)
        print("ADVANCED STRATEGY: Bollinger Bands + RSI Mean Reversion")
        print("=" * 80)
        print(f"Symbol: {symbol}")
        print(f"Period: {start} to {end}")
        print(f"Bollinger Bands: {bb_period} period, {bb_dev} std dev")
        print(f"RSI: {rsi_period} period")
        print(f"Risk Per Trade: {risk_per_trade*100:.1f}%")
        print(f"Partial Profit: {partial_take_profit*100:.0f}% at mid-BB")
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
            strategy_cls=BollingerRSIStrategy,
            data_df=data_df,
            bb_period=bb_period,
            bb_dev=bb_dev,
            rsi_period=rsi_period,
            risk_per_trade=risk_per_trade,
            partial_take_profit=partial_take_profit
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
        print("- Entry: Price at lower BB + RSI oversold")
        print("- Partial Exit: 50% at middle BB or RSI > 50")
        print("- Full Exit: Upper BB or RSI overbought")
        print("- Position Sizing: ATR-based (2% risk per trade)")
        print("- Risk Management: Trailing stop after partial profit")
        print()
        print("Key Features:")
        print("✓ Volatility-adjusted support/resistance levels")
        print("✓ ATR-based dynamic position sizing")
        print("✓ Partial profit taking for consistent gains")
        print("✓ Trailing stop protects remaining position")
        print("✓ Multi-layered exit strategy")
        print("=" * 80)
