#!/usr/bin/env python3
"""
OPTUNA + WALK-FORWARD para encontrar o melhor período SMA para BTC.

Metodologia:
1. Divide dados em splits walk-forward (treino expandindo, teste fixo)
2. Em cada split: Optuna otimiza SMA no treino, testa no teste
3. Resultado final: performance média out-of-sample

Períodos SMA testados: 20-150 (cabe em 180 dias de teste)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import backtrader as bt
import optuna
from datetime import timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)


# =============================================================================
# ESTRATÉGIA SMA
# =============================================================================

class SMAStrategy(bt.Strategy):
    """SMA Crossover simples."""
    
    params = (('period', 50),)
    
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()
    
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


# =============================================================================
# FUNÇÕES DE BACKTEST
# =============================================================================

def run_backtest(df: pd.DataFrame, sma_period: int) -> Dict:
    """Executa backtest e retorna métricas."""
    df = df.copy()
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # Precisa de dados suficientes para o SMA
    if len(df) < sma_period + 20:
        return None
    
    cerebro = bt.Cerebro(stdstats=False)
    data = bt.feeds.PandasData(
        dataname=df[['open', 'high', 'low', 'close', 'volume']],
        datetime=None
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(SMAStrategy, period=sma_period)
    
    try:
        cerebro.run()
        final = cerebro.broker.getvalue()
        ret = (final / 100000 - 1) * 100
        return {'return': ret}
    except Exception as e:
        return None


def run_buyhold(df: pd.DataFrame) -> float:
    """Calcula retorno Buy & Hold."""
    if len(df) < 2:
        return 0
    return (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100


# =============================================================================
# WALK-FORWARD COM OPTUNA
# =============================================================================

class WalkForwardOptuna:
    """
    Walk-Forward com Optuna para otimizar SMA.
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        min_train_days: int = 365,      # 1 ano mínimo de treino
        test_days: int = 180,           # 6 meses de teste
        step_days: int = 90,            # Avança 3 meses por vez
        sma_min: int = 20,              # SMA mínimo
        sma_max: int = 150,             # SMA máximo (deve caber no teste)
        n_trials: int = 30              # Trials Optuna por split
    ):
        self.df = df.copy()
        if hasattr(self.df.index, 'tz') and self.df.index.tz is not None:
            self.df.index = self.df.index.tz_localize(None)
        
        self.min_train_days = min_train_days
        self.test_days = test_days
        self.step_days = step_days
        self.sma_min = sma_min
        self.sma_max = sma_max
        self.n_trials = n_trials
        
        self.splits = self._create_splits()
    
    def _create_splits(self) -> List[Dict]:
        """Cria splits walk-forward."""
        splits = []
        
        start_date = self.df.index[0]
        end_date = self.df.index[-1]
        
        train_end = start_date + timedelta(days=self.min_train_days)
        split_id = 1
        
        while True:
            test_start = train_end + timedelta(days=5)  # Embargo
            test_end = test_start + timedelta(days=self.test_days)
            
            if test_end > end_date:
                break
            
            train_df = self.df[self.df.index <= train_end]
            test_df = self.df[(self.df.index >= test_start) & (self.df.index <= test_end)]
            
            if len(train_df) >= 200 and len(test_df) >= 100:
                splits.append({
                    'id': split_id,
                    'train_start': train_df.index[0],
                    'train_end': train_df.index[-1],
                    'test_start': test_df.index[0],
                    'test_end': test_df.index[-1],
                    'train_days': len(train_df),
                    'test_days': len(test_df)
                })
                split_id += 1
            
            train_end += timedelta(days=self.step_days)
        
        return splits
    
    def _optimize_split(self, train_df: pd.DataFrame) -> Tuple[int, float]:
        """Otimiza SMA em um período de treino."""
        
        def objective(trial):
            period = trial.suggest_int('sma_period', self.sma_min, self.sma_max)
            result = run_backtest(train_df, period)
            if result is None:
                return float('-inf')
            return result['return']
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
        
        best_period = study.best_params['sma_period']
        best_return = study.best_value
        
        return best_period, best_return
    
    def run(self) -> pd.DataFrame:
        """Executa walk-forward completo."""
        results = []
        
        print(f"\n{'='*70}")
        print(f"{'OPTUNA WALK-FORWARD: OTIMIZAÇÃO DE SMA':^70}")
        print(f"{'='*70}")
        print(f"\nConfigurações:")
        print(f"  • SMA range: {self.sma_min} - {self.sma_max}")
        print(f"  • Treino mínimo: {self.min_train_days} dias")
        print(f"  • Teste: {self.test_days} dias")
        print(f"  • Trials Optuna: {self.n_trials}")
        print(f"  • Splits: {len(self.splits)}")
        
        print(f"\n{'Split':<8}{'Período':<25}{'Best SMA':<12}{'Train Ret':<12}{'Test Ret':<12}{'B&H Test':<12}{'Alpha':<10}")
        print("-" * 90)
        
        for split in self.splits:
            train_df = self.df[(self.df.index >= split['train_start']) & 
                               (self.df.index <= split['train_end'])]
            test_df = self.df[(self.df.index >= split['test_start']) & 
                              (self.df.index <= split['test_end'])]
            
            # Otimizar no treino
            best_period, train_return = self._optimize_split(train_df)
            
            # Testar out-of-sample
            test_result = run_backtest(test_df, best_period)
            test_return = test_result['return'] if test_result else 0
            
            # B&H para comparação
            bh_return = run_buyhold(test_df)
            
            # Alpha
            alpha = test_return - bh_return
            
            period_str = f"{split['test_start'].strftime('%Y-%m')} a {split['test_end'].strftime('%Y-%m')}"
            
            print(f"{split['id']:<8}{period_str:<25}{best_period:<12}{train_return:>+10.1f}%{test_return:>+10.1f}%{bh_return:>+10.1f}%{alpha:>+9.1f}%")
            
            results.append({
                'split': split['id'],
                'test_start': split['test_start'],
                'test_end': split['test_end'],
                'best_sma': best_period,
                'train_return': train_return,
                'test_return': test_return,
                'bh_return': bh_return,
                'alpha': alpha
            })
        
        results_df = pd.DataFrame(results)
        
        # Sumário
        print(f"\n{'='*70}")
        print(f"{'SUMÁRIO':^70}")
        print(f"{'='*70}")
        
        avg_sma = results_df['best_sma'].mean()
        std_sma = results_df['best_sma'].std()
        median_sma = results_df['best_sma'].median()
        
        avg_test = results_df['test_return'].mean()
        avg_bh = results_df['bh_return'].mean()
        avg_alpha = results_df['alpha'].mean()
        
        win_rate = (results_df['alpha'] > 0).sum() / len(results_df) * 100
        
        print(f"\n📊 Melhor SMA por Split:")
        print(f"   • Média: {avg_sma:.0f} (±{std_sma:.0f})")
        print(f"   • Mediana: {median_sma:.0f}")
        print(f"   • Range: {results_df['best_sma'].min()} - {results_df['best_sma'].max()}")
        
        print(f"\n📈 Performance Out-of-Sample:")
        print(f"   • SMA médio: {avg_test:+.1f}%")
        print(f"   • B&H médio: {avg_bh:+.1f}%")
        print(f"   • Alpha médio: {avg_alpha:+.1f}%")
        print(f"   • Win Rate vs B&H: {win_rate:.0f}%")
        
        # Conclusão
        print(f"\n{'='*70}")
        print(f"{'CONCLUSÃO':^70}")
        print(f"{'='*70}")
        
        if avg_alpha > 2 and win_rate >= 50:
            print(f"\n✅ SMA FUNCIONA!")
            print(f"   Recomendação: Use SMA-{int(median_sma)} como base")
            print(f"   Alpha esperado: {avg_alpha:+.1f}% por período")
        elif avg_alpha > 0:
            print(f"\n⚠️ SMA TEM LEVE VANTAGEM")
            print(f"   Alpha positivo mas não consistente")
            print(f"   Considere usar SMA-{int(median_sma)} com cautela")
        else:
            print(f"\n❌ SMA NÃO SUPERA B&H")
            print(f"   Buy & Hold é mais eficiente para BTC")
        
        # Teste com SMA fixo (mediana encontrada)
        print(f"\n{'='*70}")
        print(f"{'VALIDAÇÃO: SMA FIXO vs OTIMIZADO':^70}")
        print(f"{'='*70}")
        
        fixed_sma = int(median_sma)
        fixed_results = []
        
        for split in self.splits:
            test_df = self.df[(self.df.index >= split['test_start']) & 
                              (self.df.index <= split['test_end'])]
            
            result = run_backtest(test_df, fixed_sma)
            test_return = result['return'] if result else 0
            bh_return = run_buyhold(test_df)
            
            fixed_results.append({
                'test_return': test_return,
                'bh_return': bh_return,
                'alpha': test_return - bh_return
            })
        
        fixed_df = pd.DataFrame(fixed_results)
        
        print(f"\nUsando SMA-{fixed_sma} fixo em todos os períodos:")
        print(f"   • Retorno médio: {fixed_df['test_return'].mean():+.1f}%")
        print(f"   • B&H médio: {fixed_df['bh_return'].mean():+.1f}%")
        print(f"   • Alpha médio: {fixed_df['alpha'].mean():+.1f}%")
        print(f"   • Win Rate: {(fixed_df['alpha'] > 0).sum()}/{len(fixed_df)} ({(fixed_df['alpha'] > 0).sum()/len(fixed_df)*100:.0f}%)")
        
        # Salvar resultados
        results_df.to_csv('optuna_walkforward_sma_results.csv', index=False)
        print(f"\n✅ Resultados detalhados salvos em optuna_walkforward_sma_results.csv")
        
        return results_df


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("📊 Carregando dados BTC...")
    
    df = yf.download('BTC-USD', start='2018-01-01', progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    print(f"✅ {len(df)} dias carregados ({df.index[0].strftime('%Y-%m-%d')} a {df.index[-1].strftime('%Y-%m-%d')})")
    
    # Executar otimização
    optimizer = WalkForwardOptuna(
        df=df,
        min_train_days=365,     # 1 ano de treino mínimo
        test_days=180,          # 6 meses de teste
        step_days=90,           # Avança 3 meses
        sma_min=20,             # SMA mínimo
        sma_max=150,            # SMA máximo
        n_trials=50             # 50 trials por split
    )
    
    results = optimizer.run()
