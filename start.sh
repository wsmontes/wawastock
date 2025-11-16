#!/bin/bash
# WawaStock - Streamlit Launcher
# Usage: ./start.sh

cd "$(dirname "$0")"

echo "🚀 Starting WawaStock Streamlit Interface..."
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "❌ Virtual environment not found!"
    echo "   Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found! Installing..."
    pip install streamlit
fi

echo "✓ Starting Streamlit..."
echo ""

# Open browser after 2 seconds
(sleep 2 && open http://localhost:8502) &

# Run streamlit
streamlit run Home.py
