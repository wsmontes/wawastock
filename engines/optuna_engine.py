"""
Optuna Optimization Engine - Otimização de hiperparâmetros com Optuna.

Este engine integra o Optuna para encontrar os melhores parâmetros
de uma estratégia de trading através de otimização bayesiana.
"""

from typing import Dict, Any, Optional, Callable
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
import backtrader as bt
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from .base_engine import BaseEngine


console = Console()


class OptunaEngine(BaseEngine):
    """
    Engine para otimização de estratégias usando Optuna.
    
    Features:
    - Otimização bayesiana (TPE sampler)
    - Pruning de trials ruins (MedianPruner)
    - Múltiplas métricas objetivo (retorno, Sharpe, drawdown)
    - Rich UI com progresso visual
    """
    
    def __init__(
        self,
        backtest_engine,
        data_df,
        strategy_cls,
        n_trials: int = 100,
        timeout: Optional[int] = None,
        objective_metric: str = 'total_return',
        direction: str = 'maximize',
        n_jobs: int = 1,
        show_progress: bool = True
    ):
        """
        Inicializar OptunaEngine.
        
        Args:
            backtest_engine: Instância do BacktestEngine
            data_df: DataFrame com dados OHLCV
            strategy_cls: Classe da estratégia a ser otimizada
            n_trials: Número de trials para otimização
            timeout: Timeout em segundos (None = sem limite)
            objective_metric: Métrica a otimizar ('total_return', 'sharpe_ratio', 'max_drawdown')
            direction: 'maximize' ou 'minimize'
            n_jobs: Número de jobs paralelos
            show_progress: Mostrar barra de progresso
        """
        super().__init__()
        self.backtest_engine = backtest_engine
        self.data_df = data_df
        self.strategy_cls = strategy_cls
        self.n_trials = n_trials
        self.timeout = timeout
        self.objective_metric = objective_metric
        self.direction = direction
        self.n_jobs = n_jobs
        self.show_progress = show_progress
        
        # Results tracking
        self.best_params = None
        self.best_value = None
        self.study = None
        self.all_results = []
    
    def run(self):
        """Executar otimização."""
        raise NotImplementedError("Use optimize() method instead")
    
    def optimize(
        self,
        param_space: Dict[str, Any],
        study_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Otimizar estratégia com os parâmetros fornecidos.
        
        Args:
            param_space: Dict com espaço de parâmetros a otimizar
                        Exemplo:
                        {
                            'rsi_period': ('int', 10, 20),
                            'rsi_oversold': ('int', 20, 35),
                            'bb_dev': ('float', 1.5, 3.0),
                        }
            study_name: Nome do estudo (opcional)
        
        Returns:
            Dict com melhores parâmetros e resultados
        """
        self.logger.info(f"Starting Optuna optimization with {self.n_trials} trials")
        
        # Create study
        sampler = TPESampler(seed=42)
        pruner = MedianPruner(n_startup_trials=10, n_warmup_steps=5)
        
        self.study = optuna.create_study(
            study_name=study_name or f"optuna_{self.strategy_cls.__name__}",
            direction=self.direction,
            sampler=sampler,
            pruner=pruner
        )
        
        # Define objective function
        def objective(trial: optuna.Trial) -> float:
            # Build params dict from trial
            params = {}
            for param_name, param_config in param_space.items():
                param_type = param_config[0]
                
                if param_type == 'int':
                    params[param_name] = trial.suggest_int(
                        param_name,
                        param_config[1],
                        param_config[2]
                    )
                elif param_type == 'float':
                    params[param_name] = trial.suggest_float(
                        param_name,
                        param_config[1],
                        param_config[2]
                    )
                elif param_type == 'categorical':
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        param_config[1]
                    )
            
            # Run backtest with these params
            try:
                results = self.backtest_engine.run_backtest(
                    strategy_cls=self.strategy_cls,
                    data_df=self.data_df,
                    **params
                )
                
                # Store results
                self.all_results.append({
                    'trial': trial.number,
                    'params': params,
                    'results': results
                })
                
                # Extract objective metric
                if self.objective_metric == 'total_return':
                    value = results.get('total_return_pct', 0.0)
                elif self.objective_metric == 'sharpe_ratio':
                    value = results.get('sharpe_ratio', 0.0)
                elif self.objective_metric == 'max_drawdown':
                    value = results.get('max_drawdown_pct', 0.0)
                elif self.objective_metric == 'profit_factor':
                    # Custom: total wins / total losses
                    wins = results.get('won_total', 0.0)
                    losses = abs(results.get('lost_total', 0.0)) or 1.0
                    value = wins / losses
                else:
                    value = results.get('total_return_pct', 0.0)
                
                return value
                
            except Exception as e:
                self.logger.error(f"Trial {trial.number} failed: {e}")
                return float('-inf') if self.direction == 'maximize' else float('inf')
        
        # Run optimization with progress bar
        if self.show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Optimizing {self.strategy_cls.__name__}...",
                    total=self.n_trials
                )
                
                def callback(study, trial):
                    progress.update(task, advance=1)
                
                self.study.optimize(
                    objective,
                    n_trials=self.n_trials,
                    timeout=self.timeout,
                    n_jobs=self.n_jobs,
                    callbacks=[callback],
                    show_progress_bar=False
                )
        else:
            self.study.optimize(
                objective,
                n_trials=self.n_trials,
                timeout=self.timeout,
                n_jobs=self.n_jobs
            )
        
        # Store best results
        self.best_params = self.study.best_params
        self.best_value = self.study.best_value
        
        self.logger.info(f"Optimization complete! Best {self.objective_metric}: {self.best_value:.4f}")
        
        return {
            'best_params': self.best_params,
            'best_value': self.best_value,
            'study': self.study,
            'all_results': self.all_results
        }
    
    def print_results(self):
        """Imprimir resultados da otimização."""
        if not self.study:
            console.print("[red]No optimization results available[/red]")
            return
        
        # Best trial info
        console.print("\n" + "="*70)
        console.print("[bold green]🏆 OPTIMIZATION RESULTS[/bold green]")
        console.print("="*70)
        
        console.print(f"\n[cyan]Best {self.objective_metric}:[/cyan] [bold]{self.best_value:.4f}[/bold]")
        console.print(f"[cyan]Best trial:[/cyan] #{self.study.best_trial.number}")
        
        # Best parameters table
        table = Table(title="\n🎯 Best Parameters", show_header=True)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        for param, value in self.best_params.items():
            if isinstance(value, float):
                table.add_row(param, f"{value:.4f}")
            else:
                table.add_row(param, str(value))
        
        console.print(table)
        
        # Top 5 trials
        top_trials = sorted(
            self.study.trials,
            key=lambda t: t.value if t.value is not None else float('-inf'),
            reverse=(self.direction == 'maximize')
        )[:5]
        
        console.print(f"\n📊 Top 5 Trials (out of {len(self.study.trials)}):")
        for i, trial in enumerate(top_trials, 1):
            value_str = f"{trial.value:.4f}" if trial.value is not None else "N/A"
            console.print(f"  {i}. Trial #{trial.number}: {value_str}")
        
        console.print("\n" + "="*70 + "\n")
    
    def get_best_backtest_results(self) -> Dict[str, Any]:
        """Obter resultados do backtest com melhores parâmetros."""
        if not self.best_params:
            raise ValueError("No optimization results available")
        
        results = self.backtest_engine.run_backtest(
            strategy_cls=self.strategy_cls,
            data_df=self.data_df,
            **self.best_params
        )
        
        return results
    
    def export_results(self, filepath: str):
        """Exportar resultados para CSV."""
        if not self.all_results:
            raise ValueError("No results to export")
        
        import pandas as pd
        
        # Flatten results
        rows = []
        for result in self.all_results:
            row = {
                'trial': result['trial'],
                **result['params'],
                **result['results']
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        self.logger.info(f"Results exported to {filepath}")
