#!/bin/bash
cd /home/ubuntu/telegram_gateway
echo "Killing old process..."
pkill -f local_poller.py || true
screen -S poller -X quit || true

echo "Backing up log..."
mv -f poller.log poller.log.$(date +%Y%m%d_%H%M%S).bak 2>/dev/null || true
touch poller.log

echo "Starting poller..."
screen -dmS poller bash -c "./venv/bin/python -u local_poller.py >> poller.log 2>&1"

echo "Waiting 10 seconds for it to boot..."
sleep 10

echo "--- SCREEN STATUS ---"
screen -ls || true

echo "--- PROCESS STATUS ---"
pgrep -af local_poller.py || true

echo "--- POLLER LOG ---"
cat poller.log
