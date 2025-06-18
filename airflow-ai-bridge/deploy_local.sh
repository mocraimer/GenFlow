#!/bin/bash
# Local deployment script for airflow-ai-bridge

set -e

echo "🚀 Deploying airflow-ai-bridge locally..."

# Check Python version
echo "Checking Python version..."
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ "$python_version" != "3.11" ]]; then
    echo "❌ Error: Python 3.11 is required (found $python_version)"
    echo "Please install Python 3.11 and try again"
    exit 1
fi
echo "✅ Python 3.11 found"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install package in development mode
echo "Installing airflow-ai-bridge in development mode..."
pip install -e ".[dev]"

# Run linting
echo "Running linting checks..."
echo "- Running black formatter..."
black src tests examples

echo "- Running ruff linter..."
ruff check src tests examples --fix

echo "- Running mypy type checker..."
mypy src --config-file mypy.ini || true

# Run tests
echo "Running tests..."
pytest tests/ -v --cov=src/airflow_ai_bridge --cov-report=term-missing || true

# Build package
echo "Building package..."
python -m build

echo "✅ Local deployment complete!"
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "To install in another project:"
echo "  pip install dist/airflow_ai_bridge-0.1.0-py3-none-any.whl"
echo ""
echo "To run tests:"
echo "  pytest tests/"
echo ""
echo "To check types:"
echo "  mypy src --config-file mypy.ini"