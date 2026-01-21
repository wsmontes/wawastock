#!/usr/bin/env python3
"""
Optimize SMA Strategy using Optuna

SMA-50 beat B&H with +283% alpha, but let's find the optimal parameters:
- SMA period (20 to 200 days)
- Optional: Stop loss, trailing stop, volume filter

Goal: Maximize Sharpe ratio while maintaining positive alpha
"""

import sys
import os
from datetime import datetime
import optuna
import pandas as pd
import backtrader as bt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.base_strategy import BaseStrategy


class OptimizableSMAStrategy(BaseStrategy):
    """
    Optimizable SMA strategy with additional parameters.
    """
    
    params = (
        ('sma_period', 50),
        ('use_stop_loss', False),
        ('stop_loss_pct', 10.0),  # Stop loss percentage
        ('use_trailing_stop', False),
        ('trailing_stop_pct', 15.0),  # Trailing stop percentage
        ('verbose', False),
    )
    
    def __init__(self):
        """Initialize indicators."""
        super().__init__()
        
        # Main trend indicator
        self.sma = bt.indicators.SMA(
            self.data.close,
            period=self.params.sma_period
        )
        
        # Track position and entry price
        self.order = None
        self.in_position = False
        self.entry_price = None
        self.highest_price = None
    
    def next(self):
        """Execute strategy logic on each bar."""
        # Skip if order pending
        if self.order:
            return
        
        current_price = self.data.close[0]
        sma_value = self.sma[0]
        
        # Not in position - check for entry signal
        if not self.in_position:
            # Entry: Price closes above SMA
            if current_price > sma_value:
                if self.params.verbose:
                    self.log(f"ENTRY: ${current_price:.2f} > SMA ${sma_value:.2f}")
                
                cash = self.broker.get_cash()
                size = (cash * 0.95) / current_price
                self.order = self.buy(size=size)
                self.in_position = True
                self.entry_price = current_price
                self.highest_price = current_price
        
        # In position - check for exit signals
        else:
            # Update highest price for trailing stop
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            should_exit = False
            exit_reason = ""
            
            # Check stop loss
            if self.params.use_stop_loss:
                loss_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                if loss_pct <= -self.params.stop_loss_pct:
                    should_exit = True
                    exit_reason = f"STOP LOSS ({loss_pct:.1f}%)"
            
            # Check trailing stop
            if self.params.use_trailing_stop and not should_exit:
                drawdown_from_high = ((current_price - self.highest_price) / self.highest_price) * 100
                if drawdown_from_high <= -self.params.trailing_stop_pct:
                    should_exit = True
                    exit_reason = f"TRAILING STOP ({drawdown_from_high:.1f}% from high)"
            
            # Check trend exit (price below SMA)
            if not should_exit and current_price < sma_value:
                should_exit = True
                exit_reason = f"TREND EXIT (${current_price:.2f} < SMA ${sma_value:.2f})"
            
            if should_exit:
                if self.params.verbose:
                    self.log(f"EXIT: {exit_reason}")
                self.order = self.close()
                self.in_position = False
                self.entry_price = None
                self.highest_price = None
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                if self.params.verbose:
                    self.log(f"BUY: ${order.executed.price:.2f}, Size {order.executed.size:.4f}")
            elif order.issell():
                if self.params.verbose:
                    self.log(f"SELL: ${order.executed.price:.2f}, Size {order.executed.size:.4f}")
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications."""
        if not trade.isclosed:
            return
        
        if self.params.verbose:
            self.log(f"TRADE: P&L ${trade.pnl:.2f}, Net ${trade.pnlcomm:.2f}")


def objective(trial, df, bh_return):
    """
    Optuna objective function to optimize.
    
    Args:
        trial: Optuna trial object
        df: Price data
        bh_return: Buy & Hold return for comparison
    
    Returns:
        Score to maximize (weighted combination of Sharpe and alpha)
    """
    # Suggest parameters
    sma_period = trial.suggest_int('sma_period', 20, 200, step=10)
    use_stop_loss = trial.suggest_categorical('use_stop_loss', [True, False])
    stop_loss_pct = trial.suggest_float('stop_loss_pct', 5.0, 20.0, step=1.0) if use_stop_loss else 10.0
    use_trailing_stop = trial.suggest_categorical('use_trailing_stop', [True, False])
    trailing_stop_pct = trial.suggest_float('trailing_stop_pct', 10.0, 30.0, step=2.0) if use_trailing_stop else 15.0
    
    # Run backtest
    engine = BacktestEngine(
        initial_cash=100000,
        commission=0.001
    )
    
    try:
        results = engine.run_backtest(
            strategy_cls=OptimizableSMAStrategy,
            data_df=df,
            symbol='BTC-USD',
            sma_period=sma_period,
            use_stop_loss=use_stop_loss,
            stop_loss_pct=stop_loss_pct,
            use_trailing_stop=use_trailing_stop,
            trailing_stop_pct=trailing_stop_pct,
            verbose=False
        )
        
        # Extract metrics
        final_value = results.get('final_value', 100000)
        total_return = ((final_value / 100000) - 1) * 100
        alpha = total_return - bh_return
        sharpe = results.get('sharpe_ratio', 0)
        max_drawdown = abs(results.get('max_drawdown_pct', 100))
        total_trades = results.get('total_trades', 0)
        
        # Penalize if underperforms B&H significantly
        if alpha < -100:
            return -1000
        
        # Penalize excessive trading (>20 trades/year)
        trades_per_year = total_trades / 6
        if trades_per_year > 20:
            trade_penalty = (trades_per_year - 20) * 10
        else:
            trade_penalty = 0
        
        # Penalize high drawdown (>60%)
        if max_drawdown > 60:
            dd_penalty = (max_drawdown - 60) * 5
        else:
            dd_penalty = 0
        
        # Score: weighted combination
        # - 40% Sharpe ratio (risk-adjusted return)
        # - 30% Alpha (outperformance)
        # - 20% Drawdown (lower is better)
        # - 10% Trade frequency (prefer fewer trades)
        
        sharpe_score = sharpe * 40
        alpha_score = (alpha / 100) * 30  # Normalize alpha
        dd_score = (100 - max_drawdown) / 100 * 20  # Lower DD = higher score
        trade_score = max(0, (20 - trades_per_year) / 20) * 10  # Fewer trades = higher score
        
        total_score = sharpe_score + alpha_score + dd_score + trade_score - trade_penalty - dd_penalty
        
        # Store additional metrics for analysis
        trial.set_user_attr('total_return', total_return)
        trial.set_user_attr('alpha', alpha)
        trial.set_user_attr('sharpe', sharpe)
        trial.set_user_attr('max_drawdown', max_drawdown)
        trial.set_user_attr('trades', total_trades)
        trial.set_user_attr('trades_per_year', trades_per_year)
        
        return total_score
        
    except Exception as e:
        print(f"Error in trial: {e}")
        return -1000


def main():
    print("\n" + "="*80)
    print("🔬 OPTUNA OPTIMIZATION: SMA Strategy")
    print("="*80)
    print("Optimizing SMA-based trend following strategy")
    print("Target: Maximize Sharpe ratio + Alpha vs Buy & Hold")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. LOAD DATA
    # =========================================================================
    print("📊 Loading BTC-USD data...")
    data_engine = DataEngine()
    df = data_engine.load_prices(
        symbol='BTC-USD',
        start='2020-01-01',
        end='2025-12-31'
    )
    print(f"✅ Loaded {len(df)} days of data\n")
    
    # Calculate Buy & Hold benchmark
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    bh_return = ((end_price / start_price) - 1) * 100
    
    print(f"📈 Buy & Hold Benchmark: +{bh_return:.1f}%\n")
    
    # =========================================================================
    # 2. RUN OPTIMIZATION
    # =========================================================================
    print("🔍 Starting Optuna optimization...")
    print("   This may take several minutes...\n")
    
    # Create study
    study = optuna.create_study(
        direction='maximize',
        study_name='sma_strategy_optimization',
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    
    # Optimize
    study.optimize(
        lambda trial: objective(trial, df, bh_return),
        n_trials=100,  # 100 trials
        show_progress_bar=True
    )
    
    # =========================================================================
    # 3. RESULTS
    # =========================================================================
    print("\n" + "="*80)
    print("🏆 OPTIMIZATION RESULTS")
    print("="*80 + "\n")
    
    best_trial = study.best_trial
    
    print(f"Best Score: {best_trial.value:.2f}")
    print(f"\n📊 Best Parameters:")
    for key, value in best_trial.params.items():
        print(f"   • {key}: {value}")
    
    print(f"\n📈 Best Performance:")
    print(f"   • Total Return: +{best_trial.user_attrs['total_return']:.1f}%")
    print(f"   • Alpha vs B&H: {best_trial.user_attrs['alpha']:+.1f}%")
    print(f"   • Sharpe Ratio: {best_trial.user_attrs['sharpe']:.2f}")
    print(f"   • Max Drawdown: {best_trial.user_attrs['max_drawdown']:.1f}%")
    print(f"   • Total Trades: {best_trial.user_attrs['trades']}")
    print(f"   • Trades/Year: {best_trial.user_attrs['trades_per_year']:.1f}")
    
    # =========================================================================
    # 4. TOP 5 TRIALS
    # =========================================================================
    print("\n" + "="*80)
    print("🥇 TOP 5 CONFIGURATIONS")
    print("="*80 + "\n")
    
    sorted_trials = sorted(study.trials, key=lambda t: t.value if t.value else -1000, reverse=True)
    
    print(f"{'Rank':<6} {'SMA':<6} {'Stop':<6} {'Trail':<7} {'Return':<10} {'Alpha':<10} {'Sharpe':<8} {'DD%':<8}")
    print("-" * 90)
    
    for i, trial in enumerate(sorted_trials[:5], 1):
        if trial.value and trial.value > -1000:
            sma = trial.params['sma_period']
            stop = f"{trial.params['stop_loss_pct']:.0f}%" if trial.params['use_stop_loss'] else "No"
            trail = f"{trial.params['trailing_stop_pct']:.0f}%" if trial.params['use_trailing_stop'] else "No"
            ret = trial.user_attrs['total_return']
            alpha = trial.user_attrs['alpha']
            sharpe = trial.user_attrs['sharpe']
            dd = trial.user_attrs['max_drawdown']
            
            print(f"#{i:<5} {sma:<6} {stop:<6} {trail:<7} {ret:>8.1f}% {alpha:>8.1f}% {sharpe:>6.2f} {dd:>6.1f}%")
    
    # =========================================================================
    # 5. PARAMETER IMPORTANCE
    # =========================================================================
    print("\n" + "="*80)
    print("📊 PARAMETER IMPORTANCE")
    print("="*80 + "\n")
    
    try:
        importance = optuna.importance.get_param_importances(study)
        
        print("Most important parameters (higher = more impact on results):\n")
        for param, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {param}: {score:.3f}")
    except Exception as e:
        print(f"Could not calculate parameter importance: {e}")
    
    # =========================================================================
    # 6. COMPARISON WITH ORIGINAL SMA-50
    # =========================================================================
    print("\n" + "="*80)
    print("📊 COMPARISON: Optimized vs Original SMA-50")
    print("="*80 + "\n")
    
    print(f"{'Metric':<25} {'Original SMA-50':<20} {'Optimized':<20} {'Improvement':<15}")
    print("-" * 85)
    
    # Original SMA-50 results (from previous test)
    original_return = 1425.7
    original_alpha = 283.1
    original_sharpe = 0.95
    original_dd = 55.6
    original_trades = 56
    
    opt_return = best_trial.user_attrs['total_return']
    opt_alpha = best_trial.user_attrs['alpha']
    opt_sharpe = best_trial.user_attrs['sharpe']
    opt_dd = best_trial.user_attrs['max_drawdown']
    opt_trades = best_trial.user_attrs['trades']
    
    def format_improvement(original, optimized, lower_is_better=False):
        if lower_is_better:
            diff = original - optimized
            pct = (diff / original) * 100 if original != 0 else 0
            symbol = "✅" if diff > 0 else "❌"
        else:
            diff = optimized - original
            pct = (diff / original) * 100 if original != 0 else 0
            symbol = "✅" if diff > 0 else "❌"
        return f"{symbol} {diff:+.1f} ({pct:+.1f}%)"
    
    print(f"{'Total Return':<25} {original_return:>18.1f}% {opt_return:>18.1f}% {format_improvement(original_return, opt_return):<15}")
    print(f"{'Alpha vs B&H':<25} {original_alpha:>18.1f}% {opt_alpha:>18.1f}% {format_improvement(original_alpha, opt_alpha):<15}")
    print(f"{'Sharpe Ratio':<25} {original_sharpe:>18.2f} {opt_sharpe:>18.2f} {format_improvement(original_sharpe, opt_sharpe):<15}")
    print(f"{'Max Drawdown':<25} {original_dd:>18.1f}% {opt_dd:>18.1f}% {format_improvement(original_dd, opt_dd, lower_is_better=True):<15}")
    print(f"{'Total Trades':<25} {original_trades:>18.0f} {opt_trades:>18.0f} {format_improvement(original_trades, opt_trades, lower_is_better=True):<15}")
    
    # =========================================================================
    # 7. RECOMMENDATIONS
    # =========================================================================
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80 + "\n")
    
    if opt_alpha > original_alpha * 1.1:
        print("✅ OPTIMIZATION SUCCESSFUL!")
        print(f"   Optimized strategy shows {((opt_alpha/original_alpha - 1) * 100):.1f}% better alpha")
        print("\n🚀 Recommended configuration:")
        print(f"   • SMA Period: {best_trial.params['sma_period']} days")
        if best_trial.params['use_stop_loss']:
            print(f"   • Stop Loss: {best_trial.params['stop_loss_pct']:.1f}%")
        if best_trial.params['use_trailing_stop']:
            print(f"   • Trailing Stop: {best_trial.params['trailing_stop_pct']:.1f}%")
        print("\n📝 Next steps:")
        print("   1. Implement optimized parameters in production strategy")
        print("   2. Test on different time periods for robustness")
        print("   3. Consider walk-forward optimization")
    
    elif opt_alpha > 0:
        print("⚠️  MARGINAL IMPROVEMENT")
        print(f"   Optimized alpha ({opt_alpha:.1f}%) vs original ({original_alpha:.1f}%)")
        print("\n💭 Considerations:")
        print("   • Original SMA-50 was already near-optimal")
        print("   • Small improvements may not justify added complexity")
        print("   • Keep original simple strategy for robustness")
    
    else:
        print("❌ OPTIMIZATION DID NOT IMPROVE RESULTS")
        print("   Original SMA-50 remains the best choice")
        print("\n🔍 Possible reasons:")
        print("   • SMA-50 is already at local optimum")
        print("   • Additional parameters (stops) add noise")
        print("   • Simple is better for this asset/period")
    
    # Save study for future analysis
    try:
        study_file = 'data/optuna_sma_study.pkl'
        import pickle
        with open(study_file, 'wb') as f:
            pickle.dump(study, f)
        print(f"\n💾 Study saved to: {study_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save study: {e}")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
