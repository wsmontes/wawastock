"""
FASE 1: Análise de Regimes de Mercado - BTC 2020-2025

Objetivo:
- Classificar períodos históricos em regimes (bull/bear/sideways/high-vol/low-vol)
- Calcular estatísticas por regime
- Identificar quando é possível/difícil bater B&H
- Encontrar transições entre regimes

Output:
- Tabela de regimes por período
- Estatísticas por tipo de regime
- Recomendações estratégicas
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta

from engines.data_engine import DataEngine

console = Console()


def calculate_rolling_metrics(df: pd.DataFrame, window: int = 90) -> pd.DataFrame:
    """
    Calcula métricas rolling para detectar regimes.
    """
    df = df.copy()
    
    # Returns
    df['daily_return'] = df['close'].pct_change()
    df['rolling_return'] = df['close'].pct_change(window)
    
    # Volatility (ATR normalizado)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['volatility'] = (df['atr'] / df['close']) * 100  # ATR como % do preço
    df['vol_regime'] = df['volatility'].rolling(window).mean()
    
    # Trend strength (slope da SMA)
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()
    df['trend_slope'] = ((df['sma_50'] - df['sma_50'].shift(window)) / df['sma_50'].shift(window)) * 100
    df['sma_distance'] = ((df['close'] - df['sma_200']) / df['sma_200']) * 100
    
    # Momentum consistency (% dias up vs down)
    df['up_day'] = (df['daily_return'] > 0).astype(int)
    df['momentum_consistency'] = df['up_day'].rolling(window).mean()  # 0.5 = choppy, >0.6 = strong up, <0.4 = strong down
    
    # Drawdown from peak
    df['cummax'] = df['close'].cummax()
    df['drawdown'] = ((df['close'] - df['cummax']) / df['cummax']) * 100
    df['max_dd_period'] = df['drawdown'].rolling(window).min()
    
    # Volume regime
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    df['avg_volume_ratio'] = df['volume_ratio'].rolling(window).mean()
    
    return df


def classify_regime(row) -> str:
    """
    Classifica regime baseado em múltiplas features.
    
    Regimes:
    - BULL_STRONG: >50% return em 90d, low volatility, consistent momentum
    - BULL_VOLATILE: >50% return em 90d, high volatility, choppy
    - SIDEWAYS_UP: 0-50% return, price > SMA200
    - SIDEWAYS_DOWN: 0-50% return, price < SMA200
    - BEAR_MODERATE: -20% to 0% return
    - BEAR_CRASH: <-20% return in 90d
    - TRANSITION: changing regime (high volatility + inconsistent momentum)
    """
    ret_90d = row['rolling_return'] * 100
    volatility = row['vol_regime']
    momentum = row['momentum_consistency']
    sma_dist = row['sma_distance']
    
    # Thresholds
    high_vol = volatility > 5.0  # >5% ATR/price = alta volatilidade
    consistent_up = momentum > 0.55
    consistent_down = momentum < 0.45
    above_sma = sma_dist > 0
    
    # Bull regimes
    if ret_90d > 50:
        if high_vol or not consistent_up:
            return "BULL_VOLATILE"
        else:
            return "BULL_STRONG"
    
    # Sideways regimes
    elif 0 <= ret_90d <= 50:
        if above_sma:
            return "SIDEWAYS_UP"
        else:
            return "SIDEWAYS_DOWN"
    
    # Bear regimes
    elif -20 <= ret_90d < 0:
        return "BEAR_MODERATE"
    
    elif ret_90d < -20:
        return "BEAR_CRASH"
    
    # Transition (mudança rápida)
    if high_vol and abs(momentum - 0.5) < 0.1:
        return "TRANSITION"
    
    return "UNKNOWN"


def analyze_regime_periods(df: pd.DataFrame):
    """
    Agrupa períodos consecutivos do mesmo regime.
    """
    df = df.copy()
    df['regime_change'] = (df['regime'] != df['regime'].shift(1)).astype(int)
    df['regime_period_id'] = df['regime_change'].cumsum()
    
    regime_periods = []
    
    for period_id in df['regime_period_id'].unique():
        if pd.isna(period_id):
            continue
            
        period_df = df[df['regime_period_id'] == period_id]
        
        if len(period_df) < 5:  # Skip muito curtos
            continue
        
        start_date = period_df.index[0]
        end_date = period_df.index[-1]
        regime = period_df['regime'].iloc[0]
        
        start_price = period_df['close'].iloc[0]
        end_price = period_df['close'].iloc[-1]
        return_pct = ((end_price - start_price) / start_price) * 100
        
        max_dd = period_df['drawdown'].min()
        avg_vol = period_df['volatility'].mean()
        days = len(period_df)
        
        regime_periods.append({
            'start': start_date,
            'end': end_date,
            'regime': regime,
            'days': days,
            'return_pct': return_pct,
            'max_dd': max_dd,
            'avg_volatility': avg_vol,
            'start_price': start_price,
            'end_price': end_price
        })
    
    return pd.DataFrame(regime_periods)


def calculate_regime_statistics(df: pd.DataFrame, regime_periods: pd.DataFrame):
    """
    Calcula estatísticas agregadas por tipo de regime.
    """
    stats_by_regime = []
    
    for regime_type in regime_periods['regime'].unique():
        periods = regime_periods[regime_periods['regime'] == regime_type]
        
        total_days = periods['days'].sum()
        num_periods = len(periods)
        avg_duration = periods['days'].mean()
        
        avg_return = periods['return_pct'].mean()
        avg_volatility = periods['avg_volatility'].mean()
        avg_max_dd = periods['max_dd'].mean()
        
        # Calcular quantos trades seriam necessários para bater B&H
        if avg_return > 0:
            # Em bull, cada trade precisa capturar mais que B&H
            required_win_rate = max(60, min(90, 50 + avg_return / 10))
            difficulty = "MUITO DIFÍCIL" if avg_return > 100 else "DIFÍCIL" if avg_return > 50 else "MODERADO"
        else:
            # Em bear, qualquer trade positivo já ganha de B&H
            required_win_rate = 40
            difficulty = "FÁCIL"
        
        stats_by_regime.append({
            'regime': regime_type,
            'num_periods': num_periods,
            'total_days': total_days,
            'avg_days': int(avg_duration),
            'avg_return': avg_return,
            'avg_volatility': avg_volatility,
            'avg_max_dd': avg_max_dd,
            'required_win_rate': required_win_rate,
            'difficulty': difficulty
        })
    
    return pd.DataFrame(stats_by_regime)


def recommend_strategy_per_regime(stats_df: pd.DataFrame):
    """
    Recomenda abordagem estratégica para cada regime.
    """
    recommendations = []
    
    for _, row in stats_df.iterrows():
        regime = row['regime']
        avg_return = row['avg_return']
        difficulty = row['difficulty']
        
        if regime in ['BULL_STRONG', 'BULL_VOLATILE']:
            if avg_return > 100:
                strategy = "HOLD ONLY - Não tente timing, só segure"
                sizing = "90-95% (agressivo)"
                exit = "Trailing stop largo (20%+) ou quebra de trend"
            else:
                strategy = "MOMENTUM FOLLOW - Entre em dips, segure trend"
                sizing = "70-85% (moderado-agressivo)"
                exit = "Trailing stop médio (15%) ou MACD bearish cross"
        
        elif regime in ['SIDEWAYS_UP', 'SIDEWAYS_DOWN']:
            strategy = "MEAN REVERSION - Compre oversold, venda overbought"
            sizing = "50-70% (moderado)"
            exit = "Take profit rápido (+10-20%) ou stop apertado (-8%)"
        
        elif regime in ['BEAR_MODERATE']:
            strategy = "SELECTIVE LONG - Só bounces fortes, cash majority"
            sizing = "30-50% (conservador)"
            exit = "Stop loss apertado (-5%) ou exit rápido (+5-10%)"
        
        elif regime in ['BEAR_CRASH']:
            strategy = "CASH / SHORT BIAS - Proteja capital, espere capitulation"
            sizing = "0-20% (muito conservador)"
            exit = "Exit imediato em deterioração"
        
        elif regime == 'TRANSITION':
            strategy = "WAIT & SEE - Reduz exposição, espera definição"
            sizing = "20-40% (conservador)"
            exit = "Stops apertados em ambas direções"
        
        else:
            strategy = "UNDEFINED"
            sizing = "50%"
            exit = "Standard stops"
        
        recommendations.append({
            'regime': regime,
            'strategy': strategy,
            'position_sizing': sizing,
            'exit_rules': exit,
            'difficulty': difficulty
        })
    
    return pd.DataFrame(recommendations)


def main():
    console.print("\n" + "="*80)
    console.print("🔬 FASE 1: ANÁLISE DE REGIMES DE MERCADO - BTC 2020-2025")
    console.print("="*80 + "\n")
    
    # Load data
    console.print("[yellow]📥 Carregando dados BTC...[/yellow]")
    data_engine = DataEngine(use_cache=True, auto_indicators=False)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
    df = df.set_index('datetime') if 'datetime' in df.columns else df
    
    console.print(f"[green]✓[/green] {len(df)} dias carregados\n")
    
    # Calculate rolling metrics
    console.print("[yellow]📊 Calculando métricas rolling...[/yellow]")
    df = calculate_rolling_metrics(df, window=90)
    
    # Classify regimes
    console.print("[yellow]🏷️  Classificando regimes...[/yellow]")
    df['regime'] = df.apply(classify_regime, axis=1)
    
    # Remove initial NaN period
    df = df.dropna(subset=['regime'])
    
    console.print(f"[green]✓[/green] Classificação completa\n")
    
    # Analyze regime periods
    console.print("[yellow]📅 Analisando períodos de regime...[/yellow]")
    regime_periods = analyze_regime_periods(df)
    
    # Display regime timeline
    console.print("\n" + "="*80)
    console.print("📅 TIMELINE DE REGIMES")
    console.print("="*80 + "\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Início", style="dim")
    table.add_column("Fim", style="dim")
    table.add_column("Regime", style="bold")
    table.add_column("Dias", justify="right")
    table.add_column("Return", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Volatility", justify="right")
    
    for _, row in regime_periods.iterrows():
        regime_color = {
            'BULL_STRONG': 'bold green',
            'BULL_VOLATILE': 'green',
            'SIDEWAYS_UP': 'yellow',
            'SIDEWAYS_DOWN': 'yellow',
            'BEAR_MODERATE': 'red',
            'BEAR_CRASH': 'bold red',
            'TRANSITION': 'cyan'
        }.get(row['regime'], 'white')
        
        table.add_row(
            row['start'].strftime('%Y-%m-%d'),
            row['end'].strftime('%Y-%m-%d'),
            f"[{regime_color}]{row['regime']}[/{regime_color}]",
            str(row['days']),
            f"{row['return_pct']:+.1f}%",
            f"{row['max_dd']:.1f}%",
            f"{row['avg_volatility']:.1f}%"
        )
    
    console.print(table)
    
    # Calculate statistics by regime type
    console.print("\n" + "="*80)
    console.print("📊 ESTATÍSTICAS POR TIPO DE REGIME")
    console.print("="*80 + "\n")
    
    stats_df = calculate_regime_statistics(df, regime_periods)
    
    table2 = Table(show_header=True, header_style="bold cyan")
    table2.add_column("Regime", style="bold")
    table2.add_column("Períodos", justify="right")
    table2.add_column("Dias Totais", justify="right")
    table2.add_column("Média Duração", justify="right")
    table2.add_column("Return Médio", justify="right")
    table2.add_column("Volatilidade", justify="right")
    table2.add_column("Win Rate Mínimo", justify="right")
    table2.add_column("Dificuldade", style="bold")
    
    for _, row in stats_df.iterrows():
        difficulty_color = {
            'FÁCIL': 'green',
            'MODERADO': 'yellow',
            'DIFÍCIL': 'red',
            'MUITO DIFÍCIL': 'bold red'
        }.get(row['difficulty'], 'white')
        
        table2.add_row(
            row['regime'],
            str(row['num_periods']),
            str(row['total_days']),
            f"{row['avg_days']}d",
            f"{row['avg_return']:+.1f}%",
            f"{row['avg_volatility']:.1f}%",
            f"{row['required_win_rate']:.0f}%",
            f"[{difficulty_color}]{row['difficulty']}[/{difficulty_color}]"
        )
    
    console.print(table2)
    
    # Strategy recommendations
    console.print("\n" + "="*80)
    console.print("🎯 RECOMENDAÇÕES ESTRATÉGICAS POR REGIME")
    console.print("="*80 + "\n")
    
    recommendations = recommend_strategy_per_regime(stats_df)
    
    for _, rec in recommendations.iterrows():
        panel_content = f"""
[bold]Estratégia:[/bold] {rec['strategy']}
[bold]Position Sizing:[/bold] {rec['position_sizing']}
[bold]Exit Rules:[/bold] {rec['exit_rules']}
[bold]Dificuldade:[/bold] {rec['difficulty']}
        """
        
        regime_color = {
            'BULL_STRONG': 'green',
            'BULL_VOLATILE': 'green',
            'SIDEWAYS_UP': 'yellow',
            'SIDEWAYS_DOWN': 'yellow',
            'BEAR_MODERATE': 'red',
            'BEAR_CRASH': 'red',
            'TRANSITION': 'cyan'
        }.get(rec['regime'], 'white')
        
        console.print(Panel(
            panel_content.strip(),
            title=f"[{regime_color}]{rec['regime']}[/{regime_color}]",
            border_style=regime_color
        ))
    
    # Save results
    regime_periods.to_csv('phase1_regime_periods.csv', index=False)
    stats_df.to_csv('phase1_regime_statistics.csv', index=False)
    recommendations.to_csv('phase1_strategy_recommendations.csv', index=False)
    
    console.print("\n" + "="*80)
    console.print("💾 Resultados salvos:")
    console.print("   - phase1_regime_periods.csv")
    console.print("   - phase1_regime_statistics.csv")
    console.print("   - phase1_strategy_recommendations.csv")
    console.print("="*80 + "\n")
    
    # Summary insights
    console.print(Panel.fit(
        f"""
[bold yellow]🔍 INSIGHTS PRINCIPAIS:[/bold yellow]

1. [bold]Distribuição de regimes:[/bold]
   {stats_df['total_days'].sum()} dias analisados
   {len(stats_df)} tipos de regime identificados

2. [bold]Maior desafio:[/bold]
   Regimes bull fortes ({stats_df[stats_df['difficulty'].str.contains('DIFÍCIL')]['total_days'].sum()} dias)
   Return médio: {stats_df[stats_df['regime'].str.contains('BULL')]['avg_return'].mean():.1f}%
   → Estratégia precisa segurar trend, não fazer timing

3. [bold]Maior oportunidade:[/bold]
   Regimes bear/sideways ({stats_df[~stats_df['regime'].str.contains('BULL')]['total_days'].sum()} dias)
   → Aqui que ganhamos alpha vs B&H

4. [bold]Próximo passo:[/bold]
   Criar detector de regime em tempo real
   Implementar estratégias específicas para cada regime
        """,
        title="📋 RESUMO EXECUTIVO",
        border_style="bold cyan"
    ))


if __name__ == '__main__':
    main()
