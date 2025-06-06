#!/bin/bash
# TermSage Runner Script - Automatically uses virtual environment
cd "$(dirname "$0")"

# Check if test_venv exists, otherwise use venv
if [ -d "test_venv" ]; then
    VENV_DIR="test_venv"
elif [ -d "venv" ]; then
    VENV_DIR="venv"
else
    echo "❌ No virtual environment found!"
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements_minimal.txt"
    exit 1
fi

echo "🚀 Starting TermSage with $VENV_DIR..."
source $VENV_DIR/bin/activate
python3 main.py "$@"