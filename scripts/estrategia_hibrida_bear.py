#!/usr/bin/env python3
"""
ESTRATÉGIA HÍBRIDA: B&H + SMA em BEAR

Lógica:
- Detecta regime de mercado em tempo real
- BULL/SIDEWAYS: Buy & Hold (sempre comprado)
- BEAR: Usa SMA como proteção (só compra acima da SMA)

Validação: Walk-Forward rigoroso com Optuna
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
# ESTRATÉGIA HÍBRIDA
# =============================================================================

class HybridBearSMA(bt.Strategy):
    """
    B&H por padrão, SMA só em BEAR.
    
    Detecção de BEAR:
    - Preço abaixo da SMA de tendência (sma_trend)
    - OU retorno de 60 dias < -20%
    """
    
    params = (
        ('sma_protection', 50),    # SMA para proteção em bear
        ('sma_trend', 100),        # SMA para detectar tendência
        ('bear_threshold', -10),   # % abaixo da SMA para considerar bear
        ('ret_threshold', -20),    # Retorno 60d para considerar bear
    )
    
    def __init__(self):
        self.sma_prot = bt.indicators.SMA(self.data.close, period=self.params.sma_protection)
        self.sma_trend = bt.indicators.SMA(self.data.close, period=self.params.sma_trend)
        self.order = None
        self.regime = 'UNKNOWN'
        
    def is_bear(self):
        """Detecta se estamos em mercado BEAR."""
        if len(self.data) < max(self.params.sma_trend, 60):
            return False
        
        # Critério 1: Preço muito abaixo da SMA de tendência
        trend_pct = (self.data.close[0] / self.sma_trend[0] - 1) * 100
        
        # Critério 2: Retorno de 60 dias muito negativo
        ret60 = (self.data.close[0] / self.data.close[-60] - 1) * 100
        
        # É BEAR se qualquer critério for atingido
        return trend_pct < self.params.bear_threshold or ret60 < self.params.ret_threshold
        
    def next(self):
        if self.order:
            return
        
        is_bear = self.is_bear()
        self.regime = 'BEAR' if is_bear else 'BULL/SIDEWAYS'
        
        if is_bear:
            # BEAR: Usar SMA como proteção
            if not self.position:
                # Só compra se preço está acima da SMA de proteção
                if self.data.close[0] > self.sma_prot[0]:
                    size = self.broker.getcash() * 0.95 / self.data.close[0]
                    self.order = self.buy(size=size)
            else:
                # Vende se preço cai abaixo da SMA de proteção
                if self.data.close[0] < self.sma_prot[0]:
                    self.order = self.close()
        else:
            # BULL/SIDEWAYS: Buy & Hold
            if not self.position:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=size)
            # Não vende - mantém posição
    
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

def run_hybrid(df: pd.DataFrame, sma_protection: int = 50, sma_trend: int = 100,
               bear_threshold: float = -10, ret_threshold: float = -20) -> Dict:
    """Executa backtest da estratégia híbrida."""
    df = df.copy()
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    min_period = max(sma_protection, sma_trend, 60) + 20
    if len(df) < min_period:
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
        HybridBearSMA,
        sma_protection=sma_protection,
        sma_trend=sma_trend,
        bear_threshold=bear_threshold,
        ret_threshold=ret_threshold
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

class WalkForwardHybrid:
    """Walk-Forward para otimizar a estratégia híbrida."""
    
    def __init__(
        self,
        df: pd.DataFrame,
        min_train_days: int = 365,
        test_days: int = 180,
        step_days: int = 90,
        n_trials: int = 50
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
        """Otimiza parâmetros no treino, incluindo detecção de BEAR."""
        
        def objective(trial):
            # Parâmetros de SMA
            sma_protection = trial.suggest_int('sma_protection', 20, 100)
            sma_trend = trial.suggest_int('sma_trend', 50, 150)
            
            # Parâmetros de detecção de BEAR (otimizáveis)
            bear_threshold = trial.suggest_int('bear_threshold', -30, -5)
            ret_threshold = trial.suggest_int('ret_threshold', -50, -10)
            
            result = run_hybrid(train_df, sma_protection, sma_trend, 
                               bear_threshold, ret_threshold)
            if result is None:
                return float('-inf')
            
            # Otimizar retorno ajustado pelo drawdown
            score = result['return'] - result['max_dd'] * 0.5
            return score
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
        
        return study.best_params
    
    def run(self) -> pd.DataFrame:
        """Executa walk-forward completo."""
        results = []
        
        print(f"\n{'='*80}")
        print(f"{'ESTRATÉGIA HÍBRIDA: B&H + SMA em BEAR':^80}")
        print(f"{'='*80}")
        print(f"\nLógica:")
        print(f"  • BULL/SIDEWAYS: Buy & Hold (sempre comprado)")
        print(f"  • BEAR: Usa SMA como proteção")
        print(f"\nConfigurações Walk-Forward:")
        print(f"  • Treino mínimo: {self.min_train_days} dias")
        print(f"  • Teste: {self.test_days} dias")
        print(f"  • Trials Optuna: {self.n_trials}")
        print(f"  • Splits: {len(self.splits)}")
        
        print(f"\n{'Split':<6}{'Período':<22}{'SMA Prot':<10}{'SMA Trend':<11}{'Hybrid':<12}{'B&H':<12}{'Alpha':<10}{'DD Hyb':<10}{'DD B&H':<10}")
        print("-" * 105)
        
        for split in self.splits:
            train_df = self.df[(self.df.index >= split['train_start']) & 
                               (self.df.index <= split['train_end'])]
            test_df = self.df[(self.df.index >= split['test_start']) & 
                              (self.df.index <= split['test_end'])]
            
            # Otimizar no treino
            best_params = self._optimize_split(train_df)
            
            # Testar out-of-sample
            hybrid_result = run_hybrid(test_df, **best_params)
            bh_result = run_buyhold(test_df)
            
            if hybrid_result is None or bh_result is None:
                continue
            
            hybrid_ret = hybrid_result['return']
            hybrid_dd = hybrid_result['max_dd']
            bh_ret = bh_result['return']
            bh_dd = bh_result['max_dd']
            alpha = hybrid_ret - bh_ret
            
            period_str = f"{split['test_start'].strftime('%Y-%m')} a {split['test_end'].strftime('%Y-%m')}"
            
            print(f"{split['id']:<6}{period_str:<22}{best_params['sma_protection']:<10}{best_params['sma_trend']:<11}{hybrid_ret:>+10.1f}%{bh_ret:>+10.1f}%{alpha:>+9.1f}%{hybrid_dd:>9.1f}%{bh_dd:>9.1f}%")
            
            results.append({
                'split': split['id'],
                'test_start': split['test_start'],
                'test_end': split['test_end'],
                'sma_protection': best_params['sma_protection'],
                'sma_trend': best_params['sma_trend'],
                'bear_threshold': best_params['bear_threshold'],
                'ret_threshold': best_params['ret_threshold'],
                'hybrid_return': hybrid_ret,
                'hybrid_dd': hybrid_dd,
                'bh_return': bh_ret,
                'bh_dd': bh_dd,
                'alpha': alpha
            })
        
        results_df = pd.DataFrame(results)
        
        # Sumário
        print(f"\n{'='*80}")
        print(f"{'SUMÁRIO':^80}")
        print(f"{'='*80}")
        
        avg_hybrid = results_df['hybrid_return'].mean()
        avg_bh = results_df['bh_return'].mean()
        avg_alpha = results_df['alpha'].mean()
        avg_hybrid_dd = results_df['hybrid_dd'].mean()
        avg_bh_dd = results_df['bh_dd'].mean()
        
        win_rate = (results_df['alpha'] > 0).sum() / len(results_df) * 100
        dd_reduction = (avg_bh_dd - avg_hybrid_dd)
        
        print(f"\n📈 Performance Out-of-Sample:")
        print(f"   • Hybrid médio: {avg_hybrid:+.1f}%")
        print(f"   • B&H médio: {avg_bh:+.1f}%")
        print(f"   • Alpha médio: {avg_alpha:+.1f}%")
        print(f"   • Win Rate vs B&H: {win_rate:.0f}%")
        
        print(f"\n📉 Drawdown:")
        print(f"   • Hybrid DD médio: {avg_hybrid_dd:.1f}%")
        print(f"   • B&H DD médio: {avg_bh_dd:.1f}%")
        print(f"   • Redução de DD: {dd_reduction:+.1f}%")
        
        # Análise por período (BEAR vs não-BEAR)
        # Identificar períodos de queda forte no B&H
        bear_periods = results_df[results_df['bh_return'] < -10]
        bull_periods = results_df[results_df['bh_return'] >= 10]
        
        print(f"\n📊 Performance por Tipo de Mercado:")
        
        if len(bear_periods) > 0:
            bear_alpha = bear_periods['alpha'].mean()
            bear_dd_reduction = bear_periods['bh_dd'].mean() - bear_periods['hybrid_dd'].mean()
            print(f"\n   BEAR (B&H < -10%): {len(bear_periods)} períodos")
            print(f"   • Alpha médio: {bear_alpha:+.1f}%")
            print(f"   • Redução DD: {bear_dd_reduction:+.1f}%")
        
        if len(bull_periods) > 0:
            bull_alpha = bull_periods['alpha'].mean()
            print(f"\n   BULL (B&H > +10%): {len(bull_periods)} períodos")
            print(f"   • Alpha médio: {bull_alpha:+.1f}%")
        
        # Conclusão
        print(f"\n{'='*80}")
        print(f"{'CONCLUSÃO':^80}")
        print(f"{'='*80}")
        
        # Métricas combinadas
        sharpe_like_hybrid = avg_hybrid / avg_hybrid_dd if avg_hybrid_dd > 0 else 0
        sharpe_like_bh = avg_bh / avg_bh_dd if avg_bh_dd > 0 else 0
        
        if avg_alpha > 0 and dd_reduction > 0:
            print(f"\n✅ ESTRATÉGIA HÍBRIDA FUNCIONA!")
            print(f"   • Ganha {avg_alpha:+.1f}% de alpha")
            print(f"   • Reduz drawdown em {dd_reduction:.1f}%")
            print(f"   • Win Rate: {win_rate:.0f}%")
            if len(bear_periods) > 0:
                print(f"   • Protege bem em BEAR: {bear_alpha:+.1f}% alpha")
        elif dd_reduction > 5:
            print(f"\n⚠️ HÍBRIDA REDUZ RISCO MAS PERDE RETORNO")
            print(f"   • Alpha: {avg_alpha:+.1f}%")
            print(f"   • Mas reduz DD em {dd_reduction:.1f}%")
            print(f"   • Use se priorizar proteção de capital")
        else:
            print(f"\n❌ HÍBRIDA NÃO VALE A PENA")
            print(f"   • Alpha: {avg_alpha:+.1f}%")
            print(f"   • Redução DD: {dd_reduction:+.1f}%")
            print(f"   • B&H é melhor")
        
        # Parâmetros mais frequentes
        print(f"\n📋 Parâmetros Mais Frequentes:")
        print(f"   • SMA Proteção mediana: {results_df['sma_protection'].median():.0f}")
        print(f"   • SMA Trend mediana: {results_df['sma_trend'].median():.0f}")
        print(f"   • Bear Threshold mediana: {results_df['bear_threshold'].median():.0f}%")
        
        # Salvar
        results_df.to_csv('hibrida_bear_results.csv', index=False)
        print(f"\n✅ Resultados salvos em hibrida_bear_results.csv")
        
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
    optimizer = WalkForwardHybrid(
        df=df,
        min_train_days=365,
        test_days=180,
        step_days=90,
        n_trials=100  # Mais trials para otimizar detecção de BEAR
    )
    
    results = optimizer.run()
