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
    
    strategy_cls = MultiTimeframeMomentumStrategy

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
        rsi_period: int = 14,
        rsi_entry_min: int = 50,
        adx_period: int = 14,
        adx_threshold: int = 25,
        atr_period: int = 14,
        risk_per_trade: float = 0.015,
        max_position_size: float = 0.3,
        allow_pyramid: bool = True,
        pyramid_units: int = 3,
        pyramid_spacing: float = 0.02,
        profit_target_atr: float = 3.0,
        trail_start_atr: float = 2.0,
        trail_pct: float = 0.02,
        max_hold_bars: int = 50,
        volume_ma_period: int = 20,
        volume_threshold: float = 1.2,
        **extra_strategy_kwargs
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
            rsi_period: RSI period (default: 14)
            rsi_entry_min: Minimum RSI for entries (default: 50)
            adx_period: ADX calculation period (default: 14)
            adx_threshold: Minimum ADX for entry (default: 25)
            atr_period: ATR period for sizing (default: 14)
            risk_per_trade: Risk per trade % (default: 0.015 = 1.5%)
            max_position_size: Max % of equity per position (default: 0.3)
            allow_pyramid: Enable pyramiding (default: True)
            pyramid_units: Max pyramid entries (default: 3)
            pyramid_spacing: % move required for next entry (default: 0.02)
            profit_target_atr: ATR multiple for profit target (default: 3.0)
            trail_start_atr: ATR multiple before trailing stop kicks in (default: 2.0)
            trail_pct: Trailing stop percentage (default: 0.02)
            max_hold_bars: Maximum bars to hold a trade (default: 50)
            volume_ma_period: Volume moving average period (default: 20)
            volume_threshold: Minimum volume multiple vs MA (default: 1.2)
            extra_strategy_kwargs: Forward compatibility for new params
        """
        allow_pyramid_bool = bool(allow_pyramid)
        
        # Print strategy header
        self.report.print_strategy_header(
            strategy_name="Multi-Timeframe Momentum with Pyramiding",
            symbol=symbol,
            start=start,
            end=end,
            params={
                'ema_system': f"{fast_ema}/{slow_ema} w/ {trend_ema} trend",
                'momentum': f"RSI {rsi_period} min {rsi_entry_min}",
                'trend_strength': f"ADX {adx_period}/{adx_threshold}",
                'risk': f"{risk_per_trade*100:.2f}% risk, max {max_position_size*100:.0f}% position",
                'pyramiding': f"{'On' if allow_pyramid_bool else 'Off'} ({pyramid_units} units, {pyramid_spacing*100:.1f}% spacing)",
                'targets': f"{profit_target_atr}x ATR target, {trail_pct*100:.1f}% trail",
                'volume': f"{volume_ma_period}-MA x{volume_threshold:.2f}"
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
            rsi_period=rsi_period,
            rsi_entry_min=rsi_entry_min,
            adx_period=adx_period,
            adx_threshold=adx_threshold,
            atr_period=atr_period,
            risk_per_trade=risk_per_trade,
            max_position_size=max_position_size,
            allow_pyramid=allow_pyramid_bool,
            pyramid_units=pyramid_units,
            pyramid_spacing=pyramid_spacing,
            profit_target_atr=profit_target_atr,
            trail_start_atr=trail_start_atr,
            trail_pct=trail_pct,
            max_hold_bars=max_hold_bars,
            volume_ma_period=volume_ma_period,
            volume_threshold=volume_threshold,
            **extra_strategy_kwargs
        )
        
        # Display results
        self.report.print_backtest_results(results)
