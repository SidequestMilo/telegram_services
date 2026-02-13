# Architecture Documentation

## System Overview

The Telegram Bot Gateway acts as a **protocol translator and API gateway** between Telegram's webhook system and your internal microservices architecture.

```
┌─────────────┐
│   Telegram  │
│   Servers   │
└──────┬──────┘
       │ HTTPS Webhook
       ▼
┌────────────────────────────────────────────┐
│     Telegram Gateway Service (FastAPI)     │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  POST /webhook/telegram              │ │
│  │  • Secret Token Verification         │ │
│  │  • Update Parsing                    │ │
│  │  • Always Returns HTTP 200           │ │
│  └──────────────┬───────────────────────┘ │
│                 ▼                          │
│  ┌──────────────────────────────────────┐ │
│  │      Rate Limiter (Redis)            │ │
│  │  • 1 req/sec per telegram_user_id    │ │
│  │  • Token bucket algorithm            │ │
│  │  • Fail-open strategy                │ │
│  └──────────────┬───────────────────────┘ │
│                 ▼                          │
│  ┌──────────────────────────────────────┐ │
│  │    Session Manager (Redis)           │ │
│  │  • telegram_user_id → internal_id    │ │
│  │  • Conversation state                │ │
│  │  • TTL: 24 hours (auto-refresh)      │ │
│  └──────────────┬───────────────────────┘ │
│                 ▼                          │
│  ┌──────────────────────────────────────┐ │
│  │    Table-Driven Router               │ │
│  │  • COMMAND_ROUTES dict               │ │
│  │  • CALLBACK_ROUTES dict              │ │
│  │  • NO giant if-else blocks           │ │
│  └──────────────┬───────────────────────┘ │
│                 ▼                          │
│  ┌──────────────────────────────────────┐ │
│  │    Internal API Client (HTTPX)       │ │
│  │  • Async HTTP calls                  │ │
│  │  • Timeouts per service              │ │
│  │  • Retry once on failure             │ │
│  │  • Currently: Mock responses         │ │
│  └──────────────┬───────────────────────┘ │
│                 ▼                          │
│  ┌──────────────────────────────────────┐ │
│  │    Response Formatter                │ │
│  │  • JSON → Telegram format            │ │
│  │  • Text, keyboards, edits            │ │
│  │  • Error messages                    │ │
│  └──────────────┬───────────────────────┘ │
│                 │                          │
└─────────────────┼──────────────────────────┘
                  │ Telegram API call
                  ▼
           ┌─────────────┐
           │   Telegram  │
           │     Bot     │
           │     API     │
           └─────────────┘

       Internal Service Calls ────────────────────┐
                                                   │
    ┌──────────────┬──────────────┬──────────────┼──────────────┐
    ▼              ▼              ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐
│ Conver- │  │   User   │  │ Matching │  │  Notif.  │  │  Redis  │
│ sation  │  │ Profile  │  │ Service  │  │ Service  │  │         │
│ Service │  │ Service  │  │          │  │          │  │         │
└─────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────┘
 Timeout:5s   Timeout:3s    Timeout:3s    Timeout:3s
```

## Component Responsibilities

### 1. Webhook Endpoint
**File:** `app/main.py`

**Responsibilities:**
- ✅ Receive Telegram webhook events
- ✅ Verify secret token
- ✅ Parse update payload
- ✅ Extract user info (telegram_user_id, chat_id)
- ✅ Orchestrate request flow
- ✅ **Always return HTTP 200**

**Key Function:** `telegram_webhook()`

### 2. Rate Limiter
**File:** `app/rate_limiter.py`

**Responsibilities:**
- ✅ Limit requests per telegram_user_id
- ✅ Redis-based token bucket
- ✅ Fail-open on Redis errors
- ✅ Send friendly rate limit message

**Key Methods:**
- `is_rate_limited(telegram_user_id)`
- `reset_rate_limit(telegram_user_id)`

### 3. Session Manager
**File:** `app/session_manager.py`

**Responsibilities:**
- ✅ Map telegram_user_id → internal_user_id
- ✅ Store conversation state
- ✅ Auto-refresh TTL on activity
- ✅ Graceful degradation if Redis fails

**Key Methods:**
- `get_session(telegram_user_id)`
- `create_session(telegram_user_id, internal_user_id)`
- `update_conversation_state(telegram_user_id, state)`

### 4. Router
**File:** `app/router.py`

**Responsibilities:**
- ✅ Table-driven routing (NO if-else chains)
- ✅ Route commands to handlers
- ✅ Route callbacks to handlers
- ✅ Route text to conversation service

**Route Tables:**
```python
COMMAND_ROUTES = {
    "/start": handler_func,
    "/help": handler_func,
    "/profile": handler_func
}

CALLBACK_ROUTES = {
    "CONNECT": handler_func,
    "ACCEPT": handler_func,
    "REJECT": handler_func,
    "SKIP": handler_func,
    ...
}
```

### 5. Internal API Client
**File:** `app/api_client.py`

**Responsibilities:**
- ✅ Async HTTP calls to internal services
- ✅ Service-specific timeouts
- ✅ Retry once on failure
- ✅ Structured error logging

**Key Methods:**
- `call_conversation()`
- `call_user_profile()`
- `call_matching()`
- `call_notification()`

**Current State:** Returns mock responses. Uncomment real implementation when services are ready.

### 6. Response Formatter
**File:** `app/formatter.py`

**Responsibilities:**
- ✅ Convert internal JSON → Telegram format
- ✅ Support text, keyboards, message edits
- ✅ Handle multiple response types
- ✅ Generate error messages

**Supported Response Types:**
- `text` - Plain text message
- `profile` - User profile data
- `match_list` - List with inline keyboard
- `confirmation` - Message with Confirm/Cancel buttons

### 7. Configuration
**File:** `app/config.py`

**Responsibilities:**
- ✅ Environment variable management
- ✅ Type validation (Pydantic)
- ✅ Default values
- ✅ Cached settings singleton

## Data Flow

### Example: User sends `/start` command

```
1. Telegram sends webhook:
   POST /webhook/telegram
   {
     "message": {
       "from": {"id": 12345},
       "chat": {"id": 12345},
       "text": "/start"
     }
   }

2. Gateway verifies secret token
   ✅ Valid → Continue
   ❌ Invalid → Log warning, return 200

3. Rate limiter checks
   Redis: GET ratelimit:telegram:12345
   ✅ Under limit → Continue
   ❌ Rate limited → Send "slow down" message, return 200

4. Session manager lookup
   Redis: GET session:telegram:12345
   ✅ Found → Use internal_user_id
   ❌ Not found → Create session with internal_user_id="user_12345"

5. Router identifies command
   "/start" → COMMAND_ROUTES["/start"] → call_user_profile()

6. API client calls User Profile Service
   POST http://user-profile-service/api/user/profile
   {
     "telegram_user_id": 12345,
     "command": "/start",
     "request_id": "abc-123"
   }
   
   Timeout: 3 seconds
   Retry: Once on failure
   
   Response (mock):
   {
     "type": "text",
     "content": "Welcome! ...",
     "internal_user_id": "user_12345"
   }

7. Formatter converts to Telegram format
   {
     "chat_id": 12345,
     "text": "Welcome! ...",
     "parse_mode": "Markdown"
   }

8. Send to Telegram API
   POST https://api.telegram.org/bot<token>/sendMessage
   
   Retry: Once on failure

9. Return HTTP 200 to Telegram
```

## Resilience Patterns

### 1. Always Return 200
**Why:** Telegram expects HTTP 200, otherwise it will retry

**Implementation:**
```python
try:
    # All processing logic
    ...
except Exception as e:
    logger.error(...)
    # Still return 200
return Response(status_code=200)
```

### 2. Fail-Open Rate Limiting
**Why:** Better to allow request than to break service

**Implementation:**
```python
try:
    if await rate_limiter.is_rate_limited(user_id):
        return rate_limit_message
except RedisError:
    # Redis is down, allow request anyway
    logger.warning("Redis unavailable, bypassing rate limit")
    continue_processing()
```

### 3. Graceful Session Degradation
**Why:** Service should work even without sessions

**Implementation:**
```python
session = await session_manager.get_session(user_id)
if not session:
    # Create temporary user_id
    internal_user_id = f"user_{telegram_user_id}"
    # Continue processing
```

### 4. Retry Logic
**Why:** Network blips shouldn't cause failures

**Implementation:**
```python
for attempt in range(2):  # Try twice
    try:
        response = await client.post(url, json=payload, timeout=timeout)
        return response.json()
    except Exception as e:
        if attempt == 1:  # Last attempt
            return None
```

### 5. Timeout Enforcement
**Why:** Don't let slow services block the gateway

**Implementation:**
```python
response = await client.post(
    url,
    json=payload,
    timeout=5.0  # Hard timeout
)
```

## Scalability

### Horizontal Scaling
Run multiple workers:
```bash
uvicorn app.main:app --workers 4
```

Or multiple instances behind a load balancer:
```
┌──────────────┐
│ Load         │
│ Balancer     │
└───┬────┬─────┘
    │    │
    ▼    ▼
  [G1] [G2] [G3] [G4]  ← Gateway instances
    │    │    │    │
    └────┴────┴────┘
          │
          ▼
      ┌────────┐
      │ Redis  │
      │Cluster │
      └────────┘
```

### Performance Characteristics

**Without downstream calls:**
- Latency: ~10-50ms
- Throughput: 1000+ req/s per worker

**With downstream calls:**
- Latency: Dominated by slowest service
- Conversation: +5s max
- Others: +3s max

### Bottleneck: Redis
**Mitigation:**
- Use Redis cluster
- Use connection pooling
- Monitor Redis latency

## Security

### 1. Webhook Secret Verification
```python
if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
    return Response(status_code=200)
```

### 2. No Message Content Logging
Privacy protection:
```python
# ❌ Don't do this
logger.info(f"Message: {message_text}")

# ✅ Do this
logger.info("Processing message", extra={"request_id": request_id})
```

### 3. Rate Limiting
Prevents abuse and DoS

### 4. No Business Logic
Minimizes attack surface - gateway only routes requests

## Monitoring & Observability

### Structured Logging
Every log includes:
- `request_id` - Unique identifier
- `telegram_user_id` - User identifier
- `service` - Target service name
- `route` - Route taken

### Key Metrics to Track
1. **Request rate** per endpoint
2. **Rate limit hits** per user
3. **Downstream latency** per service
4. **Error rate** per service
5. **Redis connection health**

### Health Checks
```bash
curl http://localhost:8000/health
```

## Deployment Architecture

### Development
```
Developer Machine
├── FastAPI (localhost:8000)
├── Redis (localhost:6379)
└── ngrok → Telegram webhook
```

### Production
```
                ┌──────────────┐
                │   Telegram   │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │   Firewall   │
                │   / WAF      │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │   nginx      │
                │  (SSL term)  │
                └──────┬───────┘
                       │
            ┌──────────┴──────────┐
            │                     │
      ┌─────▼─────┐       ┌─────▼─────┐
      │ Gateway   │       │ Gateway   │
      │ Instance1 │       │ Instance2 │
      └─────┬─────┘       └─────┬─────┘
            │                   │
            └──────────┬────────┘
                       │
                ┌──────▼───────┐
                │    Redis     │
                │   Cluster    │
                └──────────────┘
```

## Extension Points

### Adding New Commands
1. Add handler to `router.py`
2. Add to `COMMAND_ROUTES` dict
3. No other changes needed

### Adding New Response Types
1. Add handling in `formatter.py`
2. Document in `SERVICE_CONTRACTS.md`

### Integrating Real Services
1. Update service URLs in `.env`
2. Uncomment real implementation in `api_client.py`
3. Deploy services

---

**This architecture ensures:**
- ✅ Clean separation of concerns
- ✅ Easy to test and maintain
- ✅ Horizontally scalable
- ✅ Resilient to failures
- ✅ Production-ready patterns
