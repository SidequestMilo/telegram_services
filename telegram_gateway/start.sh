#!/bin/bash

# Start script for Telegram Gateway Service

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the service
echo "🚀 Starting Telegram Gateway Service..."
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
