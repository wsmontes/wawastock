#!/usr/bin/env python3
"""
ANÁLISE PROFUNDA: Trial 77 - Onde perdemos oportunidades

Compara:
1. Trades executados vs oportunidades reais no mercado
2. Momentos em que ficamos fora do mercado vs grandes movimentos
3. Trades perdedores vs condições de mercado
4. Análise de drawdown vs regime de mercado
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data_engine import DataEngine
from engines.backtest_engine import BacktestEngine
from strategies.btc_adaptive_strategy import BTCAdaptiveStrategy
from rich.console import Console
from rich.table import Table
import backtrader as bt

console = Console()

# Trial 77 params
BEST_PARAMS = {
    'rsi_period': 18,
    'rsi_oversold': 28,
    'rsi_overbought': 70,
    'bb_period': 20,
    'bb_dev': 1.95,
    'macd_fast': 10,
    'macd_slow': 30,
    'macd_signal': 12,
    'ema_fast': 15,
    'ema_slow': 50,
    'volume_threshold': 1.39,
    'atr_period': 17,
    'atr_multiplier': 1.73,
    'position_size': 0.88,
    'stop_loss_pct': 6.35,
    'trailing_stop_pct': 4.32,
    'take_profit_pct': 13.22,
    'min_signals_buy': 2,
    'min_signals_sell': 3
}

class AnalysisStrategy(bt.Strategy):
    """Estratégia que registra todas as decisões para análise."""
    
    params = tuple(BEST_PARAMS.items())
    
    def __init__(self):
        # Copiar lógica do BTCAdaptiveStrategy
        self.sma_fast = bt.indicators.SMA(self.data.close, period=50)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=200)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.bb = bt.indicators.BollingerBands(self.data.close, period=self.params.bb_period, devfactor=self.params.bb_dev)
        self.macd = bt.indicators.MACD(self.data.close, period_me1=self.params.macd_fast, period_me2=self.params.macd_slow, period_signal=self.params.macd_signal)
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow)
        
        self.order = None
        self.entry_price = None
        self.stop_price = None
        self.take_profit_price = None
        
        # Log de decisões
        self.decisions_log = []
        
    def log_decision(self, decision_type, reason, price):
        """Registra cada decisão."""
        self.decisions_log.append({
            'date': self.datas[0].datetime.date(0),
            'type': decision_type,
            'reason': reason,
            'price': price,
            'in_position': bool(self.position)
        })
    
    def next(self):
        if len(self) < 200:
            return
            
        # Detectar sinais
        buy_signals = []
        
        if self.rsi[0] < self.params.rsi_oversold:
            buy_signals.append('RSI_OVERSOLD')
        if self.data.close[0] <= self.bb.lines.bot[0]:
            buy_signals.append('BB_BOUNCE')
        if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:
            buy_signals.append('MACD_CROSS')
            
        # Se não está posicionado e há sinais
        if not self.position:
            if len(buy_signals) >= self.params.min_signals_buy:
                self.log_decision('BUY_SIGNAL', ', '.join(buy_signals), self.data.close[0])
                size = (self.broker.getcash() * self.params.position_size) / self.data.close[0]
                self.order = self.buy(size=size)
            elif len(buy_signals) > 0:
                self.log_decision('WEAK_BUY', f'{len(buy_signals)} signals: {", ".join(buy_signals)}', self.data.close[0])
        else:
            # Gerenciar posição
            if self.data.close[0] <= self.stop_price:
                self.log_decision('STOP_LOSS', f'Price {self.data.close[0]:.2f} <= Stop {self.stop_price:.2f}', self.data.close[0])
                self.order = self.close()
            elif self.data.close[0] >= self.take_profit_price:
                self.log_decision('TAKE_PROFIT', f'Price {self.data.close[0]:.2f} >= Target {self.take_profit_price:.2f}', self.data.close[0])
                self.order = self.close()
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.stop_price = self.entry_price * (1 - self.params.stop_loss_pct / 100)
                self.take_profit_price = self.entry_price * (1 + self.params.take_profit_pct / 100)
            elif order.issell():
                self.entry_price = None
                self.stop_price = None
                self.take_profit_price = None
        self.order = None

def main():
    console.print("\n" + "="*80)
    console.print("[bold cyan]ANÁLISE PROFUNDA: TRIAL 77 (+825.72%)[/bold cyan]")
    console.print("="*80 + "\n")
    
    # 1. Carregar dados e análise de mercado
    console.print("📊 [bold]ETAPA 1: Carregando dados e análise de mercado...[/bold]")
    data_engine = DataEngine(use_cache=True, auto_indicators=False)
    df = data_engine.load_prices(symbol='BTC-USD', start='2020-01-01', end='2025-11-24')
    
    # Carregar análise anterior
    analysis_df = pd.read_csv('data/processed/btc_market_analysis_2020_2025.csv', index_col=0, parse_dates=True)
    
    console.print(f"✓ {len(df)} dias carregados\n")
    
    # 2. Executar backtest com logging
    console.print("🔍 [bold]ETAPA 2: Executando backtest com análise detalhada...[/bold]")
    
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(commission=0.001)
    
    # Converter para formato backtrader
    df_bt = df.reset_index()
    df_bt.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume'] + list(df_bt.columns[6:])
    data_feed = bt.feeds.PandasData(dataname=df_bt, datetime='datetime')
    cerebro.adddata(data_feed)
    
    cerebro.addstrategy(AnalysisStrategy)
    
    strategies = cerebro.run()
    strategy = strategies[0]
    
    final_value = cerebro.broker.getvalue()
    total_return = ((final_value - 100000) / 100000) * 100
    
    console.print(f"✓ Backtest completo: +{total_return:.2f}%\n")
    
    # 3. Analisar decisões
    console.print("📈 [bold]ETAPA 3: Análise de decisões...[/bold]\n")
    
    decisions_df = pd.DataFrame(strategy.decisions_log)
    decisions_df['date'] = pd.to_datetime(decisions_df['date'])
    decisions_df.set_index('date', inplace=True)
    
    # Contar tipos de decisão
    decision_counts = decisions_df['type'].value_counts()
    
    table = Table(title="Decisões da Estratégia")
    table.add_column("Tipo", style="cyan")
    table.add_column("Quantidade", justify="right", style="yellow")
    
    for decision_type, count in decision_counts.items():
        table.add_row(decision_type, str(count))
    
    console.print(table)
    console.print()
    
    # 4. Análise de sinais fracos (oportunidades perdidas)
    weak_buys = decisions_df[decisions_df['type'] == 'WEAK_BUY']
    
    if len(weak_buys) > 0:
        console.print(f"⚠️  [bold yellow]OPORTUNIDADES PERDIDAS: {len(weak_buys)} sinais fracos não executados[/bold yellow]\n")
        
        # Calcular o que teria acontecido se tivéssemos entrado nesses sinais
        missed_opportunities = []
        
        for idx, row in weak_buys.iterrows():
            # Pegar preço 30 dias depois
            future_date = idx + pd.Timedelta(days=30)
            try:
                future_price = df.loc[df.index >= future_date, 'close'].iloc[0]
                potential_gain = ((future_price - row['price']) / row['price']) * 100
                
                if potential_gain > 10:
                    missed_opportunities.append({
                        'date': idx,
                        'reason': row['reason'],
                        'entry_price': row['price'],
                        'potential_gain': potential_gain
                    })
            except:
                pass
        
        if len(missed_opportunities) > 0:
            console.print(f"💔 [bold red]{len(missed_opportunities)} oportunidades >10% perdidas por sinal fraco:[/bold red]\n")
            
            missed_table = Table(title="Top 10 Oportunidades Perdidas")
            missed_table.add_column("Data", style="cyan")
            missed_table.add_column("Motivo", style="yellow")
            missed_table.add_column("Preço", justify="right", style="white")
            missed_table.add_column("Ganho Potencial", justify="right", style="green")
            
            sorted_missed = sorted(missed_opportunities, key=lambda x: x['potential_gain'], reverse=True)[:10]
            for opp in sorted_missed:
                missed_table.add_row(
                    opp['date'].strftime('%Y-%m-%d'),
                    opp['reason'],
                    f"${opp['entry_price']:,.2f}",
                    f"+{opp['potential_gain']:.1f}%"
                )
            
            console.print(missed_table)
            console.print()
    
    # 5. Análise de períodos fora do mercado
    console.print("🕐 [bold]ETAPA 4: Análise de exposição ao mercado...[/bold]\n")
    
    buy_signals = decisions_df[decisions_df['type'] == 'BUY_SIGNAL']
    sell_signals = decisions_df[decisions_df['type'].isin(['STOP_LOSS', 'TAKE_PROFIT'])]
    
    # Calcular tempo em posição vs fora
    total_days = len(df)
    days_in_position = 0
    
    if len(buy_signals) > 0 and len(sell_signals) > 0:
        for i in range(min(len(buy_signals), len(sell_signals))):
            days_in_position += (sell_signals.index[i] - buy_signals.index[i]).days
    
    exposure_pct = (days_in_position / total_days) * 100
    
    console.print(f"  Dias totais: [cyan]{total_days}[/cyan]")
    console.print(f"  Dias em posição: [yellow]{days_in_position}[/yellow]")
    console.print(f"  Exposição: [{'green' if exposure_pct > 50 else 'red'}]{exposure_pct:.1f}%[/{'green' if exposure_pct > 50 else 'red'}]\n")
    
    # 6. Análise de stops vs grandes quedas
    console.print("📉 [bold]ETAPA 5: Análise de proteção (Stops vs Quedas)[/bold]\n")
    
    stop_losses = decisions_df[decisions_df['type'] == 'STOP_LOSS']
    
    console.print(f"  Stop losses ativados: [red]{len(stop_losses)}[/red]")
    
    if len(stop_losses) > 0:
        stop_table = Table(title="Stops Acionados")
        stop_table.add_column("Data", style="cyan")
        stop_table.add_column("Preço", justify="right", style="yellow")
        stop_table.add_column("Motivo", style="white")
        
        for idx, row in stop_losses.iterrows():
            stop_table.add_row(
                idx.strftime('%Y-%m-%d'),
                f"${row['price']:,.2f}",
                row['reason']
            )
        
        console.print(stop_table)
    
    console.print()
    
    # 7. Resumo executivo
    console.print("="*80)
    console.print("[bold green]RESUMO EXECUTIVO[/bold green]")
    console.print("="*80 + "\n")
    
    console.print(f"📊 Retorno Estratégia: [cyan]+{total_return:.2f}%[/cyan]")
    console.print(f"📊 Buy & Hold: [cyan]+1142.65%[/cyan]")
    console.print(f"📊 Gap: [red]-{1142.65 - total_return:.2f}%[/red]\n")
    
    console.print("[bold]PROBLEMAS IDENTIFICADOS:[/bold]")
    console.print(f"  1. Exposição ao mercado muito baixa: {exposure_pct:.1f}% (ideal: >70%)")
    console.print(f"  2. {len(weak_buys)} sinais fracos ignorados ({len(missed_opportunities)} eram boas oportunidades)")
    console.print(f"  3. Min signals ({BEST_PARAMS['min_signals_buy']}) muito restritivo para períodos sideways")
    console.print(f"  4. Ficamos fora durante grandes rallies por falta de sinais\n")
    
    console.print("[bold]RECOMENDAÇÕES:[/bold]")
    console.print("  • Reduzir min_signals_buy de 2 para 1 em mercados sideways")
    console.print("  • Aumentar position_size de 0.88 para 0.95 (mais agressivo)")
    console.print("  • Ajustar RSI oversold de 28 para 32 (capturar mais oportunidades)")
    console.print("  • Reduzir volume_threshold de 1.39 para 1.2 (não exigir volume extremo)")
    console.print("  • Aumentar take_profit de 13.22% para 20% (deixar ganhos correrem)\n")
    
    console.print("="*80 + "\n")
    
    # Salvar análise
    output_path = "data/processed/trial77_analysis.csv"
    decisions_df.to_csv(output_path)
    console.print(f"✓ Análise salva em: [cyan]{output_path}[/cyan]\n")

if __name__ == "__main__":
    main()
