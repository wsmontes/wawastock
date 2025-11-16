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
    
    strategy_cls = BollingerRSIStrategy

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
        rsi_oversold: int = 35,
        rsi_overbought: int = 65,
        atr_period: int = 14,
        risk_per_trade: float = 0.02,
        partial_take_profit: float = 0.5,
        profit_target_mult: float = 2.0,
        trail_pct: float = 0.015,
        **extra_strategy_kwargs
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
            rsi_oversold: RSI level for entries (default: 35)
            rsi_overbought: RSI level for exits (default: 65)
            atr_period: ATR period for sizing (default: 14)
            risk_per_trade: Risk per trade as % of equity (default: 0.02 = 2%)
            partial_take_profit: % to close at first target (default: 0.5 = 50%)
            profit_target_mult: ATR multiple for profit target (default: 2.0)
            trail_pct: Trailing stop percentage after partial profit (default: 0.015)
            extra_strategy_kwargs: Forward compatibility for new params
        """
        # Print strategy header
        self.report.print_strategy_header(
            strategy_name="Bollinger Bands + RSI Mean Reversion",
            symbol=symbol,
            start=start,
            end=end,
            params={
                'bollinger': f"{bb_period} period, {bb_dev} std dev",
                'rsi': f"{rsi_period} period ({rsi_oversold}/{rsi_overbought})",
                'atr_period': atr_period,
                'risk_per_trade': f"{risk_per_trade*100:.1f}%",
                'partial_profit': f"{partial_take_profit*100:.0f}% at mid-BB",
                'trail_pct': f"{trail_pct*100:.2f}%",
                'profit_target': f"{profit_target_mult} ATR"
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
             rsi_oversold=rsi_oversold,
             rsi_overbought=rsi_overbought,
             atr_period=atr_period,
            risk_per_trade=risk_per_trade,
             partial_take_profit=partial_take_profit,
             profit_target_mult=profit_target_mult,
             trail_pct=trail_pct,
             **extra_strategy_kwargs
        )
        
        # Display results
        self.report.print_backtest_results(results)
