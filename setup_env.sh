#!/usr/bin/env bash
# Environment Setup Script for Quantum Scheduler
# Enforces Python 3.10 compatibility for OpenQAOA

set -e

echo "🔍 Checking Python version requirements..."

# OpenQAOA requires Python < 3.11. We explicitly target 3.10.
if command -v python3.10 &>/dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3 &>/dev/null && python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 10) else 1)'; then
    PYTHON_CMD="python3"
else
    echo "❌ Error: Python 3.10 is required but not found on this system."
    echo ""
    echo "OpenQAOA requires Python >= 3.8 and < 3.11."
    echo ""
    echo "🛠️  How to install Python 3.10:"
    echo "  - Ubuntu/Debian:"
    echo "      sudo add-apt-repository ppa:deadsnakes/ppa"
    echo "      sudo apt update"
    echo "      sudo apt install python3.10 python3.10-venv python3.10-dev"
    echo "  - macOS (Homebrew):"
    echo "      brew install python@3.10"
    echo ""
    echo "Please install Python 3.10 and re-run this script."
    exit 1
fi

echo "✅ Found $PYTHON_CMD"

echo "📦 Creating virtual environment in .venv..."
if [ -d .venv ]; then
    echo "⚠️  .venv already exists. Set FORCE_RECREATE_VENV=1 to recreate it."
    if [ "${FORCE_RECREATE_VENV:-0}" != "1" ]; then
        exit 1
    fi
    rm -rf .venv
fi
$PYTHON_CMD -m venv .venv

echo "🔄 Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

echo "📥 Installing dependencies from requirements.txt..."
.venv/bin/python -m pip install -r requirements.txt

echo "🚀 Environment setup complete! Activate it using:"
echo "    source .venv/bin/activate"
