#!/bin/bash

set -e

echo "🔨 Building Arbitrage Scanner for macOS Apple Silicon..."

# Clean previous builds
rm -rf build/ dist/ *.egg-info

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Build with PyInstaller
echo "🚀 Building with PyInstaller..."
pyinstaller --windowed --onedir pyinstaller.spec

echo "✅ Build complete! Application is ready at: dist/Arbitrage Scanner.app"
echo "💡 Run with: open 'dist/Arbitrage Scanner.app'"
