#!/bin/bash

# Quick start script for Telegram Gateway Service

set -e

echo "🚀 Telegram Gateway Service - Quick Start"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your actual values."
    echo ""
    echo "Required variables:"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - TELEGRAM_WEBHOOK_SECRET"
    echo ""
    read -p "Press Enter to continue after editing .env..."
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "⚠️  Redis is not running!"
    echo "   Start Redis with: redis-server"
    echo "   Or with Docker: docker run -d -p 6379:6379 redis:7-alpine"
    echo ""
    read -p "Press Enter when Redis is running..."
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the service:"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Or run: ./start.sh"
echo ""
