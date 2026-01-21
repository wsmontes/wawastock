#!/bin/bash
# Monitor script para acompanhar progresso da otimização

LOG_FILE="logs/step3_optimization_log.txt"

echo "📊 Monitorando otimização..."
echo "Log: $LOG_FILE"
echo ""

while true; do
    clear
    echo "==================================================================="
    echo "OPTUNA OPTIMIZATION MONITOR"
    echo "==================================================================="
    echo ""
    
    if [ -f "$LOG_FILE" ]; then
        # Mostrar trials concluídos
        TRIALS_DONE=$(grep -c "Trial .* finished with value" "$LOG_FILE" 2>/dev/null || echo "0")
        echo "✓ Trials concluídos: $TRIALS_DONE / 250"
        echo ""
        
        # Mostrar melhor resultado até agora
        echo "🏆 Melhor resultado atual:"
        grep "Best is trial" "$LOG_FILE" | tail -1 | sed 's/\[I.*\] //' || echo "  Aguardando..."
        echo ""
        
        # Mostrar últimos 5 trials
        echo "📈 Últimos 5 trials:"
        grep "Trial .* finished" "$LOG_FILE" | tail -5 | while read line; do
            trial_num=$(echo "$line" | grep -o "Trial [0-9]*" | grep -o "[0-9]*")
            return_val=$(echo "$line" | grep -o "value: [0-9.]*" | grep -o "[0-9.]*")
            echo "  Trial $trial_num: ${return_val}% return"
        done
        echo ""
        
        # Verificar se terminou
        if grep -q "OPTIMIZATION COMPLETE" "$LOG_FILE" 2>/dev/null; then
            echo "✅ OTIMIZAÇÃO COMPLETA!"
            echo ""
            echo "📊 Resultado final:"
            tail -30 "$LOG_FILE"
            break
        fi
    else
        echo "⏳ Aguardando início da otimização..."
    fi
    
    echo ""
    echo "-------------------------------------------------------------------"
    echo "Atualiza a cada 5 segundos. Pressione Ctrl+C para sair."
    
    sleep 5
done
