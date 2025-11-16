"""
Multi-Timeframe Momentum Recipe - Maximum profitability strategy workflow.

This recipe implements an institutional-grade momentum system with
cutting-edge techniques for professional traders.
"""

from recipes.base_recipe import BaseRecipe
from strategies.multi_timeframe_strategy import MultiTimeframeMomentumStrategy


class MultiTimeframeRecipe(BaseRecipe):
    """
    Recipe for maximum profitability multi-timeframe momentum strategy.
    
    Implements professional-grade techniques including multi-timeframe analysis,
    trend strength filtering, volume confirmation, pyramiding, and sophisticated
    exit management.
    """
    
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
        print("=" * 80)
        print("MAXIMUM STRATEGY: Multi-Timeframe Momentum with Pyramiding")
        print("=" * 80)
        print(f"Symbol: {symbol}")
        print(f"Period: {start} to {end}")
        print(f"EMA System: {fast_ema}/{slow_ema} with {trend_ema} trend filter")
        print(f"ADX Threshold: {adx_threshold} (trend strength)")
        print(f"Risk Per Trade: {risk_per_trade*100:.2f}%")
        print(f"Pyramiding: {'Enabled' if allow_pyramid else 'Disabled'} ({pyramid_units} units)")
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
        print()
        print("=" * 80)
        print("BACKTEST RESULTS - INSTITUTIONAL GRADE STRATEGY")
        print("=" * 80)
        print(f"Final Portfolio Value: ${results['final_value']:,.2f}")
        print(f"Total Return: {results['return_pct']:.2f}%")
        print()
        print("Strategy Overview:")
        print("─" * 80)
        print("ENTRY CRITERIA (All must be met):")
        print(f"  1. Price > {trend_ema} EMA (higher timeframe uptrend)")
        print(f"  2. Fast EMA ({fast_ema}) crosses above Slow EMA ({slow_ema})")
        print(f"  3. ADX > {adx_threshold} (strong trending market)")
        print("  4. RSI > 50 (momentum confirmation)")
        print("  5. Volume > 120% of 20-period average")
        print()
        print("EXIT STRATEGIES (Multiple layers):")
        print("  • Profit Target: 3x ATR from average entry")
        print("  • Trailing Stop: 2% after 2x ATR profit")
        print("  • Stop Loss: 2x ATR below entry")
        print("  • Time Exit: 50 bars maximum hold")
        print("  • Signal Reversal: EMA crossover reversal")
        print()
        print("POSITION MANAGEMENT:")
        print(f"  • Initial Position: 1.5% risk per trade")
        print(f"  • Pyramiding: Up to {pyramid_units} entries on 2% moves")
        print("  • ATR-based position sizing (volatility-adjusted)")
        print("  • Maximum 30% of equity per symbol")
        print()
        print("KEY FEATURES:")
        print("─" * 80)
        print("✓ Multi-timeframe trend alignment")
        print("✓ Trend strength filtering (ADX)")
        print("✓ Volume confirmation for entries")
        print("✓ Pyramiding into winners (scaling)")
        print("✓ ATR-based dynamic position sizing")
        print("✓ Multiple exit strategies for risk management")
        print("✓ Professional-grade money management")
        print()
        print("TYPICAL USE CASES:")
        print("  → Strong trending stocks (AAPL, MSFT, NVDA)")
        print("  → Momentum ETFs (QQQ, SPY)")
        print("  → Cryptocurrency trends (BTC, ETH)")
        print("=" * 80)
