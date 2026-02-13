# 🚀 Quick Start Guide

## Get Up and Running in 5 Minutes

### Prerequisites
- ✅ Python 3.11+ installed
- ✅ Redis installed or Docker available
- ✅ Telegram bot token from [@BotFather](https://t.me/botfather)

---

## Step-by-Step Setup

### 1️⃣ Initial Setup (2 minutes)

```bash
cd telegram_gateway

# Run the automated setup script
./setup.sh

# This will:
# - Create virtual environment
# - Install all dependencies
# - Create .env from template
# - Check for Redis
```

### 2️⃣ Configure Your Bot (1 minute)

Edit the `.env` file with your bot credentials:

```bash
# Open .env in your editor
nano .env

# Set these required values:
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET=my_super_secret_token_123

# Save and exit
```

**Where to get these:**
- `TELEGRAM_BOT_TOKEN`: Get from [@BotFather](https://t.me/botfather) in Telegram
- `TELEGRAM_WEBHOOK_SECRET`: Make up any strong random string

### 3️⃣ Start Redis (30 seconds)

**Option A - With Docker (Recommended):**
```bash
docker run -d -p 6379:6379 --name telegram-redis redis:7-alpine
```

**Option B - Local Redis:**
```bash
redis-server
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### 4️⃣ Start the Service (30 seconds)

```bash
./start.sh
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5️⃣ Test Health Check (10 seconds)

In a new terminal:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Telegram Gateway",
  "version": "1.0.0"
}
```

✅ **Your service is now running!**

---

## For Development/Testing

You can test with the mock services (no external services needed):

### Test the webhook locally:

```bash
curl -X POST http://localhost:8000/webhook/telegram \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: my_super_secret_token_123" \
  -d '{
    "update_id": 1,
    "message": {
      "message_id": 1,
      "from": {"id": 123456789, "first_name": "John"},
      "chat": {"id": 123456789},
      "text": "/start"
    }
  }'
```

Check the logs - you should see the request being processed!

---

## For Production (Telegram Integration)

### 1️⃣ Expose Your Service

**For testing - Use ngrok:**
```bash
# In a new terminal
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

**For production - Use your server:**
```
https://your-domain.com
```

### 2️⃣ Set Telegram Webhook

```bash
# Replace <YOUR_BOT_TOKEN> with your actual token
# Replace <YOUR_URL> with your ngrok or production URL
# Replace <YOUR_SECRET> with the same secret from .env

curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<YOUR_URL>/webhook/telegram",
    "secret_token": "<YOUR_SECRET>"
  }'
```

Example:
```bash
curl -X POST "https://api.telegram.org/bot1234567890:ABCdefGHI/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://abc123.ngrok.io/webhook/telegram",
    "secret_token": "my_super_secret_token_123"
  }'
```

### 3️⃣ Verify Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Should return:
```json
{
  "ok": true,
  "result": {
    "url": "https://abc123.ngrok.io/webhook/telegram",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### 4️⃣ Test with Real Telegram

1. Open Telegram on your phone
2. Find your bot (search for the username)
3. Send: `/start`
4. You should receive a welcome message!

---

## Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_router.py -v
```

---

## Common Issues

### ❌ "Redis connection failed"
**Fix:** Make sure Redis is running
```bash
# Check if Redis is running
redis-cli ping

# If not, start it
docker run -d -p 6379:6379 redis:7-alpine
```

### ❌ "Invalid webhook secret token"
**Fix:** Make sure the secret in `.env` matches what you sent to Telegram
```bash
# Check your .env file
cat .env | grep WEBHOOK_SECRET

# Update if needed
```

### ❌ "Module not found"
**Fix:** Install dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ Telegram not sending updates
**Fix:** Verify webhook is set correctly
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"

# If URL is wrong, set it again
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d '{"url": "https://your-url.com/webhook/telegram", "secret_token": "your_secret"}'
```

---

## What's Happening Under the Hood?

When you send `/start` to your bot:

1. ✅ Telegram sends webhook to your service
2. ✅ Service verifies secret token
3. ✅ Checks rate limit (1 req/second)
4. ✅ Gets/creates session in Redis
5. ✅ Routes `/start` to User Profile Service (mock)
6. ✅ Formats response for Telegram
7. ✅ Sends message back to user
8. ✅ Returns HTTP 200 to Telegram

All of this happens in milliseconds!

---

## Next Steps

### Development
- ✅ Service is running with mock responses
- ✅ Test all commands: `/start`, `/help`, `/profile`
- ✅ Review logs to understand the flow
- ✅ Read `ARCHITECTURE.md` for design details

### Integration
- ⏳ Deploy your internal services (Conversation, User Profile, etc.)
- ⏳ Update service URLs in `.env`
- ⏳ Uncomment real implementation in `app/api_client.py`
- ⏳ Test integration

### Production
- ⏳ Set up proper domain with SSL
- ⏳ Deploy to production server
- ⏳ Set up Redis cluster
- ⏳ Configure monitoring and alerts
- ⏳ Run load tests

---

## Useful Commands

```bash
# Start service
./start.sh

# Validate project
./validate.sh

# View logs (if running in background)
tail -f logs/telegram_gateway.log

# Stop service
# Press Ctrl+C in the terminal running the service

# Check Redis data
redis-cli
> KEYS session:telegram:*
> GET session:telegram:123456789
```

---

## Documentation

- 📘 **README.md** - Full documentation
- 🏗️ **ARCHITECTURE.md** - System design
- 📝 **SERVICE_CONTRACTS.md** - API specifications
- 🧪 **TESTING.md** - Testing guide
- 📊 **PROJECT_SUMMARY.md** - Complete overview

---

## Support

**Need help?**
1. Check the logs for error messages
2. Review `TESTING.md` for debugging tips
3. Verify Redis is running: `redis-cli ping`
4. Check `.env` configuration
5. Run validation: `./validate.sh`

---

## 🎉 Congratulations!

You now have a production-grade Telegram Bot Gateway running!

The service is currently using **mock responses** for development. When you're ready to integrate with real services, see `SERVICE_CONTRACTS.md` for the API specifications.

**Happy coding! 🚀**
