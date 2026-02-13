# Telegram Bot Gateway Service

Production-grade Telegram Bot Gateway built with FastAPI. This service acts as an **API Gateway + Protocol Translator** for Telegram, handling webhook events and routing them to appropriate internal services.

## 🎯 Purpose

This is a **Telegram Interface Layer** that:
- ✅ Receives Telegram webhook updates
- ✅ Manages user sessions (Redis)
- ✅ Rate limits requests (Redis)
- ✅ Routes to internal services (table-driven)
- ✅ Formats responses for Telegram

**Does NOT:**
- ❌ Contain business logic
- ❌ Call LLMs directly
- ❌ Access databases (except Redis)

## 📁 Project Structure

```
telegram_gateway/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + webhook endpoint
│   ├── config.py            # Configuration management
│   ├── session_manager.py   # Redis session management
│   ├── rate_limiter.py      # Redis rate limiting
│   ├── router.py            # Table-driven routing
│   ├── api_client.py        # Internal API client
│   └── formatter.py         # Response formatter
├── tests/
│   ├── __init__.py
│   ├── test_router.py       # Router unit tests
│   └── test_formatter.py    # Formatter unit tests
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Redis (running locally or accessible)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd telegram_gateway
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_WEBHOOK_SECRET` | Secret token for webhook verification | `my_secret_token_123` |
| `REDIS_HOST` | Redis server host | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |

See `.env.example` for all available configuration options.

### Start Redis

**Using Docker:**
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

**Or install locally:**
```bash
brew install redis  # macOS
redis-server
```

### Run the Service

**Development mode:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The service will be available at `http://localhost:8000`

## 🔗 Setting Up Telegram Webhook

### 1. Expose your local server (for development)

Use ngrok or a similar tool:
```bash
ngrok http 8000
```

This will give you a public URL like `https://abc123.ngrok.io`

### 2. Set the webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhook/telegram",
    "secret_token": "your_webhook_secret_token"
  }'
```

Replace:
- `<YOUR_BOT_TOKEN>` with your actual bot token
- `https://your-domain.com` with your public URL
- `your_webhook_secret_token` with the value in your `.env`

### 3. Verify webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## 📡 API Endpoints

### Health Check
```
GET /health
```

Returns service health status.

### Telegram Webhook
```
POST /webhook/telegram
```

Receives Telegram updates. This endpoint:
- Verifies webhook secret token
- Parses update payload
- Checks rate limits
- Manages sessions
- Routes to internal services
- **Always returns HTTP 200**

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_router.py

# Run with verbose output
pytest -v
```

## 🏗️ Architecture

### Request Flow

```
Telegram → Webhook → Secret Verification → Rate Limit Check → Session Lookup
    ↓
Router (table-driven) → Internal Service (API call) → Response Formatter → Telegram
```

### Components

#### 1. **Session Manager** (`session_manager.py`)
- Stores `telegram_user_id → internal_user_id` mapping
- TTL: 24 hours (refreshed on activity)
- Gracefully degrades if Redis is unavailable

#### 2. **Rate Limiter** (`rate_limiter.py`)
- Limits: 1 request per second per user
- Token bucket algorithm
- Fail-open strategy (continues on error)

#### 3. **Router** (`router.py`)
- **Table-driven** (no giant if-else blocks)
- Command routes: `/start`, `/help`, `/profile`
- Callback routes: `CONNECT`, `ACCEPT`, `REJECT`, `SKIP`
- Text messages → Conversation Service

#### 4. **API Client** (`api_client.py`)
- Async HTTP client (httpx)
- Timeout configuration per service
- Retry once on failure
- Currently returns **mock responses**

#### 5. **Response Formatter** (`formatter.py`)
- Converts internal JSON to Telegram format
- Supports:
  - Plain text messages
  - Inline keyboards
  - Message edits (for callbacks)

## 🔧 Configuration

All configuration is managed via environment variables (see `.env.example`).

**Key settings:**

- **Session TTL:** `SESSION_TTL=86400` (24 hours)
- **Rate Limit:** `RATE_LIMIT_REQUESTS=1` per `RATE_LIMIT_WINDOW=1` second
- **Timeouts:**
  - Conversation: 5s
  - Matching: 3s
  - Notification: 3s
  - User Profile: 3s

## 📊 Logging

Structured logging with request tracking:

```json
{
  "time": "2024-01-15T10:30:00",
  "level": "INFO",
  "name": "app.main",
  "message": "Processing update",
  "request_id": "abc-123",
  "telegram_user_id": 12345,
  "route": "conversation"
}
```

Logs include:
- ✅ Request ID
- ✅ Telegram user ID
- ✅ Route taken
- ✅ Downstream latency
- ❌ Does NOT log full message text (privacy)

## 🔐 Security

- ✅ Webhook secret token verification
- ✅ Rate limiting per user
- ✅ No business logic (minimized attack surface)
- ✅ Graceful error handling (never crashes)
- ✅ Always returns HTTP 200 to Telegram

## 🚨 Error Handling

The service **never crashes** and **always returns HTTP 200** to Telegram.

### Error Scenarios:

| Scenario | Behavior |
|----------|----------|
| Invalid secret token | Log warning, return 200 |
| Malformed JSON | Log error, return 200 |
| Rate limit exceeded | Send friendly message, return 200 |
| Redis unavailable | Continue without session, return 200 |
| Internal service timeout | Send apology message, return 200 |
| Telegram API fails | Retry once, log error |

Generic error message:
> "Something went wrong on our side. Please try again in a minute."

Rate limit message:
> "You're sending messages too fast, please slow down 🙂"

## 🔄 Internal Service Integration

The API client currently returns **mock responses**. To integrate with real services:

1. **Uncomment real implementation** in `api_client.py`
2. **Update service URLs** in `.env`
3. **Ensure services accept POST requests** with JSON payload

### Expected Payload Format

**Conversation Service:**
```json
{
  "user_id": "user_12345",
  "telegram_user_id": 12345,
  "message": "Hello",
  "request_id": "abc-123"
}
```

**User Profile Service:**
```json
{
  "telegram_user_id": 12345,
  "command": "/start",
  "request_id": "abc-123"
}
```

**Matching Service:**
```json
{
  "user_id": "user_12345",
  "action": "CONNECT",
  "target_user_id": "user_67890",
  "request_id": "abc-123"
}
```

## 🧩 Adding New Routes

### Add a Command

1. Define handler in `router.py`:
```python
async def _handle_my_command(self, internal_user_id, telegram_user_id, text, request_id):
    # Your logic here
    return {"type": "text", "content": "Response"}
```

2. Add to `COMMAND_ROUTES`:
```python
self.COMMAND_ROUTES = {
    "/mycommand": self._handle_my_command,
    # ... existing routes
}
```

### Add a Callback

1. Define handler in `router.py`:
```python
async def _handle_my_callback(self, internal_user_id, telegram_user_id, param, request_id):
    # Your logic here
    return {"type": "text", "content": "Action completed"}
```

2. Add to `CALLBACK_ROUTES`:
```python
self.CALLBACK_ROUTES = {
    "MY_ACTION": self._handle_my_callback,
    # ... existing routes
}
```

## 📈 Production Deployment

### Recommendations

1. **Use a process manager:** systemd, supervisor, or Docker
2. **Run multiple workers:** `--workers 4`
3. **Use a reverse proxy:** nginx or Caddy
4. **Enable HTTPS:** Required for Telegram webhooks
5. **Monitor logs:** Use ELK stack or similar
6. **Set up alerting:** Monitor error rates and latency
7. **Use Redis cluster:** For high availability

### Example with Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Example with systemd

```ini
[Unit]
Description=Telegram Gateway Service
After=network.target

[Service]
Type=simple
User=telegram
WorkingDirectory=/opt/telegram_gateway
Environment="PATH=/opt/telegram_gateway/venv/bin"
ExecStart=/opt/telegram_gateway/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🤝 Contributing

This is a production-grade template. Customize as needed for your use case.

## 📝 License

MIT

---

**Built with ❤️ using FastAPI**
