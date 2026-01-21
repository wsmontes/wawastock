#!/usr/bin/env python3
"""Monitor de progresso da otimização Optuna em tempo real."""

import time
import subprocess
from pathlib import Path

LOG_FILE = "logs/step3_optimization_log.txt"

def count_trials(log_path):
    """Conta quantos trials foram completados."""
    if not Path(log_path).exists():
        return 0
    try:
        result = subprocess.run(
            ['grep', '-c', 'Trial .* finished with value', log_path],
            capture_output=True,
            text=True
        )
        return int(result.stdout.strip()) if result.returncode == 0 else 0
    except:
        return 0

def get_best_trial(log_path):
    """Pega informação do melhor trial."""
    if not Path(log_path).exists():
        return None
    try:
        result = subprocess.run(
            ['grep', 'Best is trial', log_path],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        return lines[-1] if lines and lines[0] else None
    except:
        return None

def is_complete(log_path):
    """Verifica se otimização terminou."""
    if not Path(log_path).exists():
        return False
    try:
        result = subprocess.run(
            ['grep', '-q', 'OPTIMIZATION COMPLETE', log_path],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False

def main():
    print("\n" + "="*70)
    print("  MONITOR DE OTIMIZAÇÃO OPTUNA - BTC 2020-2025")
    print("="*70)
    print(f"Log: {LOG_FILE}\n")
    
    last_count = -1
    
    while True:
        trials_done = count_trials(LOG_FILE)
        
        if trials_done != last_count:
            percent = (trials_done / 250) * 100
            bar_length = int(percent / 2)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            
            print(f"\r  [{bar}] {trials_done}/250 trials ({percent:.1f}%)    ", end="", flush=True)
            last_count = trials_done
        
        if is_complete(LOG_FILE):
            print("\n\n✅ OTIMIZAÇÃO COMPLETA!\n")
            print("="*70)
            # Mostrar últimas 40 linhas do log
            subprocess.run(['tail', '-40', LOG_FILE])
            break
        
        if trials_done >= 250:
            print("\n\n✅ 250 trials concluídos! Aguardando finalização...\n")
            time.sleep(5)
            break
        
        time.sleep(2)
    
    print("\n" + "="*70)
    print(f"Resultado completo em: {LOG_FILE}")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitor interrompido pelo usuário.\n")
        print(f"Otimização continua rodando. Veja progresso em: {LOG_FILE}\n")
