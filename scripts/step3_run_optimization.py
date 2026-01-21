"""
Step 3: Run Optuna optimization on Bitcoin data
Uses the data from step 1 and generates detailed optimization log.
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import run_recipe_programmatic

def main():
    print("=" * 80)
    print("STEP 3: RUNNING OPTUNA OPTIMIZATION")
    print("=" * 80)
    print()
    
    # Check if data exists
    data_file = project_root / "data" / "processed" / "btc_2020_2025_raw.csv"
    if not data_file.exists():
        print(f"❌ ERROR: Data file not found: {data_file}")
        print("Please run step1_download_btc_data.py first")
        return 1
    
    print(f"📂 Using data: {data_file}")
    print()
    
    # Optimization parameters
    symbol = "BTC-USD"
    start_date = "2020-01-01"
    end_date = "2025-11-24"
    n_trials = 250
    
    print(f"⚙️  OPTIMIZATION PARAMETERS")
    print(f"Symbol:      {symbol}")
    print(f"Period:      {start_date} to {end_date}")
    print(f"Trials:      {n_trials}")
    print(f"Objective:   total_return")
    print()
    
    print("🚀 Starting optimization (this may take 20-40 minutes)...")
    print()
    
    start_time = datetime.now()
    
    try:
        results = run_recipe_programmatic(
            recipe_name='btc_optuna',
            symbol=symbol,
            start=start_date,
            end=end_date,
            n_trials=n_trials,
            objective_metric='total_return',
            export_csv=True
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if not results:
            print("❌ ERROR: No results returned from optimization")
            return 1
        
        print()
        print("=" * 80)
        print("OPTIMIZATION RESULTS")
        print("=" * 80)
        print()
        
        # Extract results
        best_return = results['best_results'].get('total_return_pct', 0)
        bh_return = results['buy_hold_return']
        outperformance = best_return - bh_return
        
        total_trades = results['best_results'].get('total_trades', 0)
        win_rate = results['best_results'].get('win_rate', 0)
        max_dd = results['best_results'].get('max_drawdown', 0)
        
        print(f"⏱️  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print()
        print(f"📊 PERFORMANCE")
        print(f"Buy & Hold:           {bh_return:+.2f}%")
        print(f"Optimized Strategy:   {best_return:+.2f}%")
        print(f"Outperformance:       {outperformance:+.2f}%")
        print()
        print(f"📈 STATISTICS")
        print(f"Total Trades:         {total_trades}")
        print(f"Win Rate:             {win_rate:.2f}%")
        print(f"Max Drawdown:         {max_dd:.2f}%")
        print()
        
        # Best parameters
        print(f"🎯 BEST PARAMETERS")
        best_params = results.get('best_params', {})
        for key, value in sorted(best_params.items()):
            if isinstance(value, float):
                print(f"{key:20s}: {value:.4f}")
            else:
                print(f"{key:20s}: {value}")
        print()
        
        # Save detailed log
        log_file = project_root / "logs" / "step3_optimization_log.txt"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("STEP 3: OPTUNA OPTIMIZATION LOG\n")
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Duration: {duration:.1f} seconds\n")
            f.write(f"\nPARAMETERS\n")
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Period: {start_date} to {end_date}\n")
            f.write(f"Trials: {n_trials}\n")
            f.write(f"\nRESULTS\n")
            f.write(f"Buy & Hold: {bh_return:+.2f}%\n")
            f.write(f"Optimized Strategy: {best_return:+.2f}%\n")
            f.write(f"Outperformance: {outperformance:+.2f}%\n")
            f.write(f"\nSTATISTICS\n")
            f.write(f"Total Trades: {total_trades}\n")
            f.write(f"Win Rate: {win_rate:.2f}%\n")
            f.write(f"Max Drawdown: {max_dd:.2f}%\n")
            f.write(f"\nBEST PARAMETERS\n")
            for key, value in sorted(best_params.items()):
                if isinstance(value, float):
                    f.write(f"{key}: {value:.4f}\n")
                else:
                    f.write(f"{key}: {value}\n")
            f.write(f"\nCSV Export: data/processed/optuna_BTC_USD_250trials.csv\n")
        
        print(f"📝 Log saved to: {log_file}")
        print()
        
        if outperformance > 0:
            print(f"🎉 SUCCESS: Strategy beat Buy & Hold by {abs(outperformance):.2f}%")
        else:
            print(f"⚠️  WARNING: Strategy underperformed Buy & Hold by {abs(outperformance):.2f}%")
        
        print()
        print("✅ STEP 3 COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
