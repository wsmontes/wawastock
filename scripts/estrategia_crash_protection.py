#!/usr/bin/env python3
"""
ESTRATÉGIA HÍBRIDA v2: B&H com PROTEÇÃO em CRASH

Diferente da v1:
- Só sai do mercado em CRASH real (queda forte detectada)
- Usa SMA apenas como sinal de saída, não de entrada
- Mais conservador para não perder altas

Parâmetros otimizados por Optuna:
- crash_sma: período do SMA para detectar crash
- crash_threshold: % abaixo do SMA para considerar crash
- recovery_threshold: % acima do SMA para voltar a comprar
"""

import pandas as pd
import numpy as np
import yfinance as yf
import backtrader as bt
import optuna
from datetime import timedelta
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)


# =============================================================================
# ESTRATÉGIA v2: B&H COM PROTEÇÃO EM CRASH
# =============================================================================

class BHWithCrashProtection(bt.Strategy):
    """
    Buy & Hold com proteção em crash.
    
    - Compra e mantém por padrão
    - Só vende se detectar crash (preço muito abaixo do SMA)
    - Recompra quando preço recuperar acima do SMA
    """
    
    params = (
        ('crash_sma', 100),          # SMA para detectar crash
        ('crash_threshold', -15),    # % abaixo do SMA para vender
        ('recovery_threshold', 2),   # % acima do SMA para recomprar
    )
    
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.crash_sma)
        self.order = None
        self.in_crash_mode = False
        
    def next(self):
        if self.order:
            return
        
        # Calcular distância do SMA
        if len(self.data) < self.params.crash_sma:
            # Ainda não tem SMA, comprar e manter
            if not self.position:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
            return
        
        sma_distance = (self.data.close[0] / self.sma[0] - 1) * 100
        
        if not self.position:
            # Sem posição
            if self.in_crash_mode:
                # Em modo crash, só recompra se recuperar
                if sma_distance > self.params.recovery_threshold:
                    size = self.broker.getcash() * 0.95 / self.data.close[0]
                    self.order = self.buy(size=size)
                    self.in_crash_mode = False
            else:
                # Modo normal: comprar
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
        else:
            # Com posição: verificar crash
            if sma_distance < self.params.crash_threshold:
                self.order = self.close()
                self.in_crash_mode = True
    
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


class BuyAndHold(bt.Strategy):
    """Buy and Hold para comparação."""
    
    def __init__(self):
        self.bought = False
        
    def next(self):
        if not self.bought:
            size = self.broker.getcash() * 0.95 / self.data.close[0]
            self.buy(size=size)
            self.bought = True


# =============================================================================
# FUNÇÕES DE BACKTEST
# =============================================================================

def run_crash_protection(df: pd.DataFrame, crash_sma: int = 100,
                         crash_threshold: float = -15, 
                         recovery_threshold: float = 2) -> Dict:
    """Executa backtest da estratégia com proteção em crash."""
    df = df.copy()
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    if len(df) < crash_sma + 20:
        return None
    
    cerebro = bt.Cerebro(stdstats=False)
    data = bt.feeds.PandasData(
        dataname=df[['open', 'high', 'low', 'close', 'volume']],
        datetime=None
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(
        BHWithCrashProtection,
        crash_sma=crash_sma,
        crash_threshold=crash_threshold,
        recovery_threshold=recovery_threshold
    )
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
    
    try:
        results = cerebro.run()
        strat = results[0]
        final = cerebro.broker.getvalue()
        ret = (final / 100000 - 1) * 100
        
        try:
            max_dd = strat.analyzers.dd.get_analysis()['max']['drawdown'] or 0
        except:
            max_dd = 0
        
        return {'return': ret, 'max_dd': max_dd}
    except:
        return None


def run_buyhold(df: pd.DataFrame) -> Dict:
    """Executa B&H."""
    df = df.copy()
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    if len(df) < 20:
        return None
    
    cerebro = bt.Cerebro(stdstats=False)
    data = bt.feeds.PandasData(
        dataname=df[['open', 'high', 'low', 'close', 'volume']],
        datetime=None
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(BuyAndHold)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
    
    try:
        results = cerebro.run()
        strat = results[0]
        final = cerebro.broker.getvalue()
        ret = (final / 100000 - 1) * 100
        
        try:
            max_dd = strat.analyzers.dd.get_analysis()['max']['drawdown'] or 0
        except:
            max_dd = 0
        
        return {'return': ret, 'max_dd': max_dd}
    except:
        return None


# =============================================================================
# WALK-FORWARD COM OPTUNA
# =============================================================================

class WalkForwardCrashProtection:
    """Walk-Forward para otimizar proteção em crash."""
    
    def __init__(
        self,
        df: pd.DataFrame,
        min_train_days: int = 365,
        test_days: int = 180,
        step_days: int = 90,
        n_trials: int = 100
    ):
        self.df = df.copy()
        if hasattr(self.df.index, 'tz') and self.df.index.tz is not None:
            self.df.index = self.df.index.tz_localize(None)
        
        self.min_train_days = min_train_days
        self.test_days = test_days
        self.step_days = step_days
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
            test_start = train_end + timedelta(days=5)
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
                })
                split_id += 1
            
            train_end += timedelta(days=self.step_days)
        
        return splits
    
    def _optimize_split(self, train_df: pd.DataFrame) -> Dict:
        """Otimiza parâmetros no treino."""
        
        def objective(trial):
            # Parâmetros de detecção de crash
            crash_sma = trial.suggest_int('crash_sma', 30, 150)
            crash_threshold = trial.suggest_int('crash_threshold', -30, -5)
            recovery_threshold = trial.suggest_int('recovery_threshold', 0, 10)
            
            result = run_crash_protection(train_df, crash_sma, 
                                          crash_threshold, recovery_threshold)
            if result is None:
                return float('-inf')
            
            # Objetivo: maximizar retorno ajustado por risco
            # Penalizar drawdown mais fortemente
            score = result['return'] - result['max_dd'] * 0.7
            return score
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
        
        return study.best_params
    
    def run(self) -> pd.DataFrame:
        """Executa walk-forward completo."""
        results = []
        
        print(f"\n{'='*85}")
        print(f"{'ESTRATÉGIA: B&H COM PROTEÇÃO EM CRASH':^85}")
        print(f"{'='*85}")
        print(f"\nLógica:")
        print(f"  • Compra e mantém (B&H) por padrão")
        print(f"  • Só VENDE se preço cair muito abaixo do SMA (crash)")
        print(f"  • Recompra quando preço recuperar acima do SMA")
        print(f"\nParâmetros Otimizados (Optuna):")
        print(f"  • crash_sma: período do SMA (30-150)")
        print(f"  • crash_threshold: % abaixo do SMA para vender (-30 a -5)")
        print(f"  • recovery_threshold: % acima do SMA para recomprar (0 a 10)")
        print(f"\nWalk-Forward:")
        print(f"  • Treino: {self.min_train_days} dias | Teste: {self.test_days} dias")
        print(f"  • Trials: {self.n_trials} | Splits: {len(self.splits)}")
        
        print(f"\n{'Split':<6}{'Período':<22}{'SMA':<6}{'Crash':<8}{'Recov':<7}{'Prot':<12}{'B&H':<12}{'Alpha':<10}{'DD Prot':<9}{'DD B&H':<9}")
        print("-" * 110)
        
        for split in self.splits:
            train_df = self.df[(self.df.index >= split['train_start']) & 
                               (self.df.index <= split['train_end'])]
            test_df = self.df[(self.df.index >= split['test_start']) & 
                              (self.df.index <= split['test_end'])]
            
            # Otimizar no treino
            best_params = self._optimize_split(train_df)
            
            # Testar out-of-sample
            prot_result = run_crash_protection(test_df, **best_params)
            bh_result = run_buyhold(test_df)
            
            if prot_result is None or bh_result is None:
                continue
            
            prot_ret = prot_result['return']
            prot_dd = prot_result['max_dd']
            bh_ret = bh_result['return']
            bh_dd = bh_result['max_dd']
            alpha = prot_ret - bh_ret
            
            period_str = f"{split['test_start'].strftime('%Y-%m')} a {split['test_end'].strftime('%Y-%m')}"
            
            print(f"{split['id']:<6}{period_str:<22}{best_params['crash_sma']:<6}{best_params['crash_threshold']:<8}{best_params['recovery_threshold']:<7}{prot_ret:>+10.1f}%{bh_ret:>+10.1f}%{alpha:>+9.1f}%{prot_dd:>8.1f}%{bh_dd:>8.1f}%")
            
            results.append({
                'split': split['id'],
                'test_start': split['test_start'],
                'test_end': split['test_end'],
                'crash_sma': best_params['crash_sma'],
                'crash_threshold': best_params['crash_threshold'],
                'recovery_threshold': best_params['recovery_threshold'],
                'prot_return': prot_ret,
                'prot_dd': prot_dd,
                'bh_return': bh_ret,
                'bh_dd': bh_dd,
                'alpha': alpha
            })
        
        results_df = pd.DataFrame(results)
        
        # Sumário
        print(f"\n{'='*85}")
        print(f"{'SUMÁRIO':^85}")
        print(f"{'='*85}")
        
        avg_prot = results_df['prot_return'].mean()
        avg_bh = results_df['bh_return'].mean()
        avg_alpha = results_df['alpha'].mean()
        avg_prot_dd = results_df['prot_dd'].mean()
        avg_bh_dd = results_df['bh_dd'].mean()
        
        win_rate = (results_df['alpha'] > 0).sum() / len(results_df) * 100
        dd_reduction = avg_bh_dd - avg_prot_dd
        
        print(f"\n📈 Performance Out-of-Sample:")
        print(f"   • Proteção média: {avg_prot:+.1f}%")
        print(f"   • B&H médio: {avg_bh:+.1f}%")
        print(f"   • Alpha médio: {avg_alpha:+.1f}%")
        print(f"   • Win Rate vs B&H: {win_rate:.0f}%")
        
        print(f"\n📉 Drawdown:")
        print(f"   • Proteção DD médio: {avg_prot_dd:.1f}%")
        print(f"   • B&H DD médio: {avg_bh_dd:.1f}%")
        print(f"   • Redução de DD: {dd_reduction:+.1f}%")
        
        # Análise por período
        bear_periods = results_df[results_df['bh_return'] < -10]
        bull_periods = results_df[results_df['bh_return'] >= 10]
        
        print(f"\n📊 Performance por Tipo de Mercado:")
        
        if len(bear_periods) > 0:
            bear_alpha = bear_periods['alpha'].mean()
            bear_dd_red = bear_periods['bh_dd'].mean() - bear_periods['prot_dd'].mean()
            print(f"\n   🔴 BEAR (B&H < -10%): {len(bear_periods)} períodos")
            print(f"      • Alpha médio: {bear_alpha:+.1f}%")
            print(f"      • Redução DD: {bear_dd_red:+.1f}%")
        
        if len(bull_periods) > 0:
            bull_alpha = bull_periods['alpha'].mean()
            print(f"\n   🟢 BULL (B&H > +10%): {len(bull_periods)} períodos")
            print(f"      • Alpha médio: {bull_alpha:+.1f}%")
        
        # Conclusão
        print(f"\n{'='*85}")
        print(f"{'CONCLUSÃO':^85}")
        print(f"{'='*85}")
        
        if avg_alpha > 0 and win_rate >= 50:
            print(f"\n✅ PROTEÇÃO EM CRASH FUNCIONA!")
            print(f"   • Alpha positivo: {avg_alpha:+.1f}%")
            print(f"   • Win Rate: {win_rate:.0f}%")
            print(f"   • Reduz drawdown em {dd_reduction:.1f}%")
        elif dd_reduction > 10 and avg_alpha > -10:
            print(f"\n⚠️ PROTEÇÃO REDUZ RISCO SIGNIFICATIVAMENTE")
            print(f"   • Alpha: {avg_alpha:+.1f}%")
            print(f"   • Mas reduz DD em {dd_reduction:.1f}%")
            print(f"   • Bom para quem prioriza proteção de capital")
        else:
            print(f"\n❌ B&H PURO É MELHOR")
            print(f"   • Alpha: {avg_alpha:+.1f}%")
            print(f"   • Proteção não compensa")
        
        # Parâmetros recomendados
        print(f"\n📋 Parâmetros Mais Frequentes (medianas):")
        print(f"   • Crash SMA: {results_df['crash_sma'].median():.0f}")
        print(f"   • Crash Threshold: {results_df['crash_threshold'].median():.0f}%")
        print(f"   • Recovery Threshold: {results_df['recovery_threshold'].median():.0f}%")
        
        # Salvar
        results_df.to_csv('crash_protection_results.csv', index=False)
        print(f"\n✅ Resultados salvos em crash_protection_results.csv")
        
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
    
    print(f"✅ {len(df)} dias carregados")
    
    # Executar otimização
    optimizer = WalkForwardCrashProtection(
        df=df,
        min_train_days=365,
        test_days=180,
        step_days=90,
        n_trials=100
    )
    
    results = optimizer.run()
