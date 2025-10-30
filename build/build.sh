#!/bin/bash
# Build script for Acoustic Analysis Tool - macOS Version
# Creates macOS .app bundle using PyInstaller

set -e  # Exit on error

echo "=========================================="
echo "Acoustic Analysis Tool - macOS Build"
echo "=========================================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check if virtual environment exists and activate it
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: No virtual environment found (.venv or venv)"
    echo "Continuing with system Python..."
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Using Python: $PYTHON_VERSION"

# Run the build script
echo ""
echo "Running build.py..."
python3 build/build.py

# Check if build was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Build completed successfully!"
    echo "=========================================="
    echo "Application bundle: build/deploy/AcousticAnalysisTool.app"
    echo ""
    echo "To test the application:"
    echo "  open build/deploy/AcousticAnalysisTool.app"
    echo ""
    echo "To create a DMG installer:"
    echo "  ./build/deploy.sh"
else
    echo ""
    echo "=========================================="
    echo "Build failed!"
    echo "=========================================="
    exit 1
fi

