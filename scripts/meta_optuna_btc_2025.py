"""
META-OPTUNA ADAPTATIVO - BTC 2025 (5 minutos)
Baseado nos hiperparâmetros otimizados pelo Optuna

Hiperparâmetros:
- lookback_days: 14
- reward_factor: 1.40
- penalty_factor: 0.90
- weight_decay: 0.91
- target_pct: 0.40%
- stop_pct: 0.49%
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import warnings
import json
import sys
from datetime import datetime
from pathlib import Path

warnings.filterwarnings('ignore')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# === HIPERPARÂMETROS OTIMIZADOS ===
LOOKBACK_DAYS = 14
REWARD_FACTOR = 1.40
PENALTY_FACTOR = 0.90
WEIGHT_DECAY = 0.91
TARGET_PCT = 0.0040   # 0.40%
STOP_PCT = 0.0049     # 0.49%
MIN_PRECISION = 0.56

print("="*70)
print("META-OPTUNA ADAPTATIVO - BTC 2025 (5 minutos)")
print("="*70)
print(f"Hiperparâmetros: lookback={LOOKBACK_DAYS}, reward={REWARD_FACTOR:.2f}, penalty={PENALTY_FACTOR:.2f}")
print(f"                 decay={WEIGHT_DECAY:.2f}, target={TARGET_PCT*100:.2f}%, stop={STOP_PCT*100:.2f}%")

# === DADOS ===
print("\n[1] Carregando dados...")
df = pd.read_parquet('data/processed/BTC-USD-5m-clean.parquet')

# Normalizar colunas para lowercase
df.columns = df.columns.str.lower()

print(f"    Período: {df.index[0]} a {df.index[-1]}")
print(f"    {len(df):,} barras de 5 minutos")

# Calcular features adicionais se necessário
print("\n[2] Calculando features...")

# NATR (Normalized ATR)
if 'natr_14' not in df.columns:
    df.ta.natr(length=14, append=True)
    df.columns = df.columns.str.lower()

# Bollinger Bands Width (se não existir)
if 'bbb_20' not in df.columns and 'bbb_20_2.0_2.0' in df.columns:
    df['bbb_20'] = df['bbb_20_2.0_2.0']
elif 'bbb_20' not in df.columns:
    bb20 = df.ta.bbands(length=20, std=2)
    if bb20 is not None:
        df['bbb_20'] = (bb20.iloc[:, 0] - bb20.iloc[:, 2]) / bb20.iloc[:, 1] * 100

# EMAs
if 'ema_9' not in df.columns:
    df.ta.ema(length=9, append=True)
    df.columns = df.columns.str.lower()

if 'ema_21' not in df.columns:
    df.ta.ema(length=21, append=True)
    df.columns = df.columns.str.lower()

# Derived features
df['price_vs_ema9'] = (df['close'] - df['ema_9']) / df['ema_9'] * 100 if 'ema_9' in df.columns else 0
df['price_vs_ema21'] = (df['close'] - df['ema_21']) / df['ema_21'] * 100 if 'ema_21' in df.columns else 0

# RSI
if 'rsi_14' not in df.columns:
    df.ta.rsi(length=14, append=True)
    df.columns = df.columns.str.lower()

# Momentum
df['momentum_10'] = df['close'].pct_change(10) * 100

df = df.dropna()
df['date'] = df.index.date

print(f"    {len(df):,} barras após limpeza")

# Definir features disponíveis
FEATURES = ['natr_14', 'bbb_20', 'price_vs_ema9', 'price_vs_ema21', 'rsi_14', 'momentum_10']
FEATURES = [f for f in FEATURES if f in df.columns]
print(f"    Features: {FEATURES}")

# Pré-calcular quantiles por dia
print("\n[3] Pré-calculando quantiles por dia...")
unique_dates = sorted(df['date'].unique())
date_quantiles = {}

for d in unique_dates:
    day_data = df[df['date'] == d]
    date_quantiles[d] = {
        feat: {
            'q10': day_data[feat].quantile(0.1),
            'q90': day_data[feat].quantile(0.9),
        } for feat in FEATURES if feat in day_data.columns
    }

print(f"    {len(unique_dates)} dias de trading")

# === SIMULAÇÃO ===
print("\n[4] Rodando simulação...")
print("-"*70)

weights = {f: 1.0 for f in FEATURES}
capital = 100000
initial_capital = capital
position = 0
entry_price = 0
current_features = []

all_trades = []
daily_results = []
start_idx = LOOKBACK_DAYS

for i in range(start_idx, len(unique_dates)):
    trade_date = unique_dates[i]
    
    day_mask = df['date'] == trade_date
    day_data = df[day_mask]
    
    if len(day_data) < 10:
        continue
    
    # Top 3 features por peso
    sorted_feats = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Gerar sinais
    signals = pd.Series(True, index=day_data.index)
    active_feats = []
    
    for feat, w in sorted_feats:
        if feat not in day_data.columns:
            continue
        
        q = date_quantiles.get(trade_date, {}).get(feat, {})
        if not q:
            continue
        
        if 'ema' in feat.lower() or 'momentum' in feat.lower():
            thresh = q['q10'] + (q['q90'] - q['q10']) * 0.3
            signals = signals & (day_data[feat] < thresh)
        else:
            thresh = q['q10'] + (q['q90'] - q['q10']) * 0.5
            signals = signals & (day_data[feat] > thresh)
        
        active_feats.append(feat)
    
    signal_bars = day_data[signals]
    day_pnl = 0
    day_trades = 0
    day_wins = 0
    
    for idx in signal_bars.index:
        bar = day_data.loc[idx]
        
        if position == 0:
            entry_price = bar['close']
            position = 1
            current_features = active_feats.copy()
            day_trades += 1
        
        elif position == 1:
            pnl = (bar['close'] - entry_price) / entry_price
            
            if pnl >= TARGET_PCT or pnl <= -STOP_PCT:
                won = pnl > 0
                trade_pnl = capital * 0.95 * pnl
                capital += trade_pnl
                day_pnl += trade_pnl
                
                if won:
                    day_wins += 1
                
                # Aprendizado adaptativo
                for feat in current_features:
                    if feat in weights:
                        factor = REWARD_FACTOR if won else PENALTY_FACTOR
                        weights[feat] = max(0.1, min(5.0, weights[feat] * factor))
                
                all_trades.append({
                    'date': trade_date,
                    'entry': entry_price,
                    'exit': bar['close'],
                    'pnl_pct': pnl * 100,
                    'pnl_usd': trade_pnl,
                    'won': won,
                    'features': current_features.copy()
                })
                
                position = 0
    
    # Fechar posição no fim do dia
    if position == 1:
        last = day_data.iloc[-1]
        pnl = (last['close'] - entry_price) / entry_price
        trade_pnl = capital * 0.95 * pnl
        capital += trade_pnl
        day_pnl += trade_pnl
        won = pnl > 0
        
        if won:
            day_wins += 1
        
        for feat in current_features:
            if feat in weights:
                factor = REWARD_FACTOR if won else PENALTY_FACTOR
                weights[feat] = max(0.1, min(5.0, weights[feat] * factor))
        
        all_trades.append({
            'date': trade_date,
            'entry': entry_price,
            'exit': last['close'],
            'pnl_pct': pnl * 100,
            'pnl_usd': trade_pnl,
            'won': won,
            'features': current_features.copy()
        })
        
        position = 0
    
    # Weight decay
    for feat in weights:
        weights[feat] = 1.0 + (weights[feat] - 1.0) * WEIGHT_DECAY
    
    daily_results.append({
        'date': trade_date,
        'capital': capital,
        'pnl': day_pnl,
        'trades': day_trades,
        'wins': day_wins,
        'weights': weights.copy()
    })
    
    # Progress a cada 30 dias
    if (i - start_idx + 1) % 30 == 0:
        ret = (capital - initial_capital) / initial_capital * 100
        wr = sum(1 for t in all_trades if t['won']) / len(all_trades) * 100 if all_trades else 0
        print(f"    Dia {i-start_idx+1}/{len(unique_dates)-start_idx}: {trade_date} | ${capital:,.0f} ({ret:+.1f}%) | WR: {wr:.1f}%")

# === RESULTADOS ===
print("\n" + "="*70)
print("📊 RESULTADOS FINAIS - BTC 2025 (5 min)")
print("="*70)

trades_df = pd.DataFrame(all_trades)
daily_df = pd.DataFrame(daily_results)

total_trades = len(trades_df)
total_wins = len(trades_df[trades_df['won']]) if len(trades_df) > 0 else 0
win_rate = total_wins / total_trades * 100 if total_trades > 0 else 0
final_return = (capital - initial_capital) / initial_capital * 100

print(f"\n💰 Capital Inicial:  ${initial_capital:,.0f}")
print(f"💰 Capital Final:    ${capital:,.2f}")
print(f"📈 Return:           {final_return:+.2f}%")
print(f"\n🔄 Total Trades:     {total_trades:,}")
print(f"✅ Wins:             {total_wins:,}")
print(f"❌ Losses:           {total_trades - total_wins:,}")
print(f"🎯 Win Rate:         {win_rate:.1f}%")

if len(trades_df) > 0:
    avg_win = trades_df[trades_df['won']]['pnl_pct'].mean() if total_wins > 0 else 0
    avg_loss = trades_df[~trades_df['won']]['pnl_pct'].mean() if (total_trades - total_wins) > 0 else 0
    
    print(f"\n📊 Média P&L/trade:  {trades_df['pnl_pct'].mean():.3f}%")
    print(f"📊 Média Win:        {avg_win:.3f}%")
    print(f"📊 Média Loss:       {avg_loss:.3f}%")
    print(f"📊 Melhor trade:     {trades_df['pnl_pct'].max():.2f}%")
    print(f"📊 Pior trade:       {trades_df['pnl_pct'].min():.2f}%")
    
    # Profit Factor
    gross_profit = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum()
    gross_loss = abs(trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    print(f"📊 Profit Factor:    {profit_factor:.2f}")

# Max Drawdown
if len(daily_df) > 0:
    daily_df['peak'] = daily_df['capital'].cummax()
    daily_df['drawdown'] = (daily_df['capital'] - daily_df['peak']) / daily_df['peak'] * 100
    max_dd = daily_df['drawdown'].min()
    print(f"\n📉 Max Drawdown:     {max_dd:.2f}%")
    
    # Sharpe aproximado
    if len(daily_df) > 1:
        daily_returns = daily_df['capital'].pct_change().dropna()
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        print(f"📊 Sharpe (aprox):   {sharpe:.2f}")

# Pesos finais
print("\n" + "-"*50)
print("🧠 PESOS FINAIS (Aprendizado Adaptativo):")
print("-"*50)
sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
for feat, w in sorted_weights:
    status = "★" if w > 1.5 else "✗" if w < 0.5 else " "
    print(f"  {status} {feat:20s}: {w:.3f}")

# Análise por mês
if len(trades_df) > 0:
    print("\n" + "-"*50)
    print("📅 PERFORMANCE POR MÊS:")
    print("-"*50)
    trades_df['month'] = pd.to_datetime(trades_df['date']).dt.to_period('M')
    monthly = trades_df.groupby('month').agg({
        'pnl_usd': 'sum',
        'won': ['sum', 'count']
    })
    monthly.columns = ['pnl', 'wins', 'trades']
    monthly['wr'] = monthly['wins'] / monthly['trades'] * 100
    
    for month, row in monthly.iterrows():
        wr_emoji = "🟢" if row['wr'] >= 55 else "🟡" if row['wr'] >= 50 else "🔴"
        pnl_emoji = "📈" if row['pnl'] > 0 else "📉"
        print(f"  {month}: {pnl_emoji} ${row['pnl']:+,.0f} | {int(row['trades'])} trades | {wr_emoji} {row['wr']:.1f}% WR")

# Salvar resultados
output_dir = Path('outputs')
output_dir.mkdir(exist_ok=True)

output = {
    'strategy': 'META-OPTUNA Adaptativo',
    'asset': 'BTC/USDT',
    'timeframe': '5m',
    'period': '2025',
    'hyperparams': {
        'lookback_days': LOOKBACK_DAYS,
        'reward_factor': REWARD_FACTOR,
        'penalty_factor': PENALTY_FACTOR,
        'weight_decay': WEIGHT_DECAY,
        'target_pct': TARGET_PCT,
        'stop_pct': STOP_PCT
    },
    'results': {
        'initial_capital': initial_capital,
        'final_capital': float(capital),
        'return_pct': float(final_return),
        'total_trades': total_trades,
        'win_rate': float(win_rate),
        'max_drawdown': float(max_dd) if len(daily_df) > 0 else 0,
        'profit_factor': float(profit_factor) if 'profit_factor' in dir() else 0
    },
    'final_weights': dict(sorted_weights)
}

with open(output_dir / 'meta_optuna_btc_2025.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)

daily_df.to_csv(output_dir / 'meta_optuna_btc_2025_daily.csv', index=False)
trades_df.to_csv(output_dir / 'meta_optuna_btc_2025_trades.csv', index=False)

print("\n" + "="*70)
print("✓ Resultados salvos em outputs/meta_optuna_btc_2025*")
print("="*70)
