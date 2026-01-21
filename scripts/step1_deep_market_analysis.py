#!/usr/bin/env python3
"""
STEP 1: ANÁLISE PROFUNDA DO MERCADO BTC 2020-2025

Objetivos:
1. Mapear todos os regimes de mercado (bull, bear, sideways)
2. Identificar pontos ideais de entrada e saída
3. Detectar padrões que precedem grandes movimentos
4. Quantificar oportunidades perdidas e perdas evitáveis
5. Gerar relatório detalhado para construir estratégia ótima
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from rich.console import Console
from rich.table import Table

console = Console()

def identify_market_regimes(df, window=50):
    """Identifica regimes de mercado (bull/bear/sideways)."""
    df = df.copy()
    
    # Calcular tendência de longo prazo
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    
    # Momentum
    df['roc_20'] = ((df['close'] - df['close'].shift(20)) / df['close'].shift(20)) * 100
    
    # Volatilidade
    df['volatility'] = df['close'].pct_change().rolling(window=20).std() * 100
    
    # Classificar regime
    conditions = [
        (df['sma_50'] > df['sma_200']) & (df['roc_20'] > 5),  # Strong Bull
        (df['sma_50'] > df['sma_200']) & (df['roc_20'] > 0),  # Bull
        (df['sma_50'] < df['sma_200']) & (df['roc_20'] < -5), # Strong Bear
        (df['sma_50'] < df['sma_200']) & (df['roc_20'] < 0),  # Bear
    ]
    choices = ['STRONG_BULL', 'BULL', 'STRONG_BEAR', 'BEAR']
    df['regime'] = np.select(conditions, choices, default='SIDEWAYS')
    
    return df

def find_optimal_entry_exit_points(df):
    """Identifica os melhores pontos de entrada e saída retrospectivamente."""
    df = df.copy()
    
    # Calcular retornos futuros de diferentes períodos
    for days in [7, 14, 30, 60, 90]:
        df[f'future_return_{days}d'] = ((df['close'].shift(-days) - df['close']) / df['close']) * 100
    
    # Identificar oportunidades significativas (>10% em 30 dias)
    df['major_opportunity'] = df['future_return_30d'] > 10
    
    # Identificar riscos significativos (queda >10% em 30 dias)
    df['major_risk'] = df['future_return_30d'] < -10
    
    return df

def analyze_indicator_effectiveness(df):
    """Analisa quais indicadores melhor preveem movimentos."""
    df = df.copy()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_cross'] = df['macd'] > df['macd_signal']
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # Volume analysis
    df['volume_sma'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    
    # Price momentum
    df['momentum_5'] = df['close'].pct_change(5) * 100
    df['momentum_20'] = df['close'].pct_change(20) * 100
    
    return df

def calculate_perfect_strategy_returns(df):
    """Calcula o retorno de uma estratégia perfeita (comprar em fundos, vender em topos)."""
    df = df.copy()
    
    # Identificar fundos locais (mínimos de 30 dias)
    df['is_local_bottom'] = df['close'] == df['close'].rolling(window=30, center=True).min()
    
    # Identificar topos locais (máximos de 30 dias)
    df['is_local_top'] = df['close'] == df['close'].rolling(window=30, center=True).max()
    
    return df

def main():
    console.print("\n" + "="*80)
    console.print("[bold cyan]STEP 1: ANÁLISE PROFUNDA DO MERCADO BTC 2020-2025[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Carregar dados
    console.print("📊 [bold]Carregando dados...[/bold]")
    data_engine = DataEngine(use_cache=True, auto_indicators=False)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
    
    console.print(f"✓ {len(df)} dias carregados\n")
    
    # Análise 1: Regimes de mercado
    console.print("🔍 [bold]Identificando regimes de mercado...[/bold]")
    df = identify_market_regimes(df)
    
    regime_counts = df['regime'].value_counts()
    regime_table = Table(title="Distribuição de Regimes de Mercado")
    regime_table.add_column("Regime", style="cyan")
    regime_table.add_column("Dias", justify="right", style="yellow")
    regime_table.add_column("% do Tempo", justify="right", style="green")
    
    for regime, count in regime_counts.items():
        pct = (count / len(df)) * 100
        regime_table.add_row(regime, str(count), f"{pct:.1f}%")
    
    console.print(regime_table)
    console.print()
    
    # Análise 2: Oportunidades e Riscos
    console.print("🎯 [bold]Mapeando oportunidades e riscos...[/bold]")
    df = find_optimal_entry_exit_points(df)
    
    opportunities = df['major_opportunity'].sum()
    risks = df['major_risk'].sum()
    
    console.print(f"  Oportunidades principais (>10% em 30d): [green]{opportunities} dias[/green]")
    console.print(f"  Riscos principais (<-10% em 30d): [red]{risks} dias[/red]\n")
    
    # Análise 3: Efetividade de indicadores
    console.print("📈 [bold]Analisando indicadores técnicos...[/bold]")
    df = analyze_indicator_effectiveness(df)
    
    # Análise 4: Estratégia perfeita
    df = calculate_perfect_strategy_returns(df)
    
    local_bottoms = df['is_local_bottom'].sum()
    local_tops = df['is_local_top'].sum()
    
    console.print(f"  Fundos locais identificados: [cyan]{local_bottoms}[/cyan]")
    console.print(f"  Topos locais identificados: [cyan]{local_tops}[/cyan]\n")
    
    # Análise detalhada por ano
    console.print("📅 [bold]Análise ano a ano:[/bold]\n")
    
    year_table = Table(title="Performance e Características por Ano")
    year_table.add_column("Ano", style="cyan")
    year_table.add_column("Retorno", justify="right", style="yellow")
    year_table.add_column("Max DD", justify="right", style="red")
    year_table.add_column("Volatilidade", justify="right", style="magenta")
    year_table.add_column("Regime Dominante", style="green")
    year_table.add_column("Oportunidades", justify="right", style="blue")
    
    for year in range(2020, 2026):
        year_data = df[df.index.year == year]
        if len(year_data) == 0:
            continue
        
        # Calcular métricas do ano
        year_return = ((year_data['close'].iloc[-1] - year_data['close'].iloc[0]) / year_data['close'].iloc[0]) * 100
        
        # Max drawdown
        cummax = year_data['close'].cummax()
        drawdown = ((year_data['close'] - cummax) / cummax) * 100
        max_dd = drawdown.min()
        
        # Volatilidade anual
        daily_returns = year_data['close'].pct_change()
        annual_vol = daily_returns.std() * np.sqrt(252) * 100
        
        # Regime dominante
        dominant_regime = year_data['regime'].mode()[0] if len(year_data['regime'].mode()) > 0 else "N/A"
        
        # Oportunidades
        year_opps = year_data['major_opportunity'].sum()
        
        year_table.add_row(
            str(year),
            f"{year_return:+.1f}%",
            f"{max_dd:.1f}%",
            f"{annual_vol:.1f}%",
            dominant_regime,
            str(year_opps)
        )
    
    console.print(year_table)
    console.print()
    
    # Análise de correlação entre indicadores e retornos futuros
    console.print("🔬 [bold]Correlação indicadores vs retornos futuros:[/bold]\n")
    
    correlation_data = []
    indicators = ['rsi', 'macd', 'bb_position', 'volume_ratio', 'momentum_5', 'momentum_20']
    
    for indicator in indicators:
        if indicator in df.columns:
            corr_7d = df[indicator].corr(df['future_return_7d'])
            corr_30d = df[indicator].corr(df['future_return_30d'])
            correlation_data.append({
                'indicator': indicator,
                'corr_7d': corr_7d,
                'corr_30d': corr_30d
            })
    
    corr_table = Table(title="Poder Preditivo dos Indicadores")
    corr_table.add_column("Indicador", style="cyan")
    corr_table.add_column("Correlação 7d", justify="right", style="yellow")
    corr_table.add_column("Correlação 30d", justify="right", style="green")
    
    for item in correlation_data:
        corr_table.add_row(
            item['indicator'],
            f"{item['corr_7d']:.4f}",
            f"{item['corr_30d']:.4f}"
        )
    
    console.print(corr_table)
    console.print()
    
    # Salvar dados processados
    output_path = "data/processed/btc_market_analysis_2020_2025.csv"
    df.to_csv(output_path)
    console.print(f"✓ Análise completa salva em: [cyan]{output_path}[/cyan]\n")
    
    # Resumo executivo
    console.print("="*80)
    console.print("[bold green]RESUMO EXECUTIVO[/bold green]")
    console.print("="*80 + "\n")
    
    total_return = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
    
    console.print(f"📊 Buy & Hold total: [cyan]+{total_return:.2f}%[/cyan]")
    console.print(f"🎯 Oportunidades mapeadas: [green]{opportunities}[/green] dias com potencial >10%")
    console.print(f"⚠️  Riscos identificados: [red]{risks}[/red] dias com risco >10%")
    console.print(f"🔄 Mudanças de regime: [yellow]{(df['regime'] != df['regime'].shift()).sum()}[/yellow] transições")
    console.print(f"📈 Fundos/Topos para swing trade: [magenta]{local_bottoms}/{local_tops}[/magenta]\n")
    
    console.print("="*80)
    console.print("[bold]PRÓXIMO PASSO:[/bold] Usar essas análises para construir estratégia adaptativa")
    console.print("="*80 + "\n")

if __name__ == "__main__":
    main()
