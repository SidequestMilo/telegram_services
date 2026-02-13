#!/bin/bash

# Simple script to simulate a Telegram webhook update
# Requires: curl

# Default URL
URL="http://localhost:8000/webhook/telegram"
SECRET="my_test_secret_token_12345"

echo "🧪 Sending test update to $URL..."
echo "Simulating user sending '/start' command..."

curl -v -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $SECRET" \
  -d '{
    "update_id": 10000,
    "message": {
      "message_id": 1365,
      "from": {
        "id": 1111111,
        "is_bot": false,
        "first_name": "Test",
        "username": "TestUser"
      },
      "chat": {
        "id": 1111111,
        "first_name": "Test",
        "username": "TestUser",
        "type": "private"
      },
      "date": 1441645532,
      "text": "/generate a futuristic city description"
    }
  }'

echo ""
echo "✅ Request sent! Check server logs for processing details."
