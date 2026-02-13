# Internal Service Contracts

This document defines the request/response contracts between the Telegram Gateway and internal services.

## General Principles

- All endpoints accept JSON POST requests
- All endpoints return JSON responses
- All requests include a `request_id` for tracing
- Timeouts are enforced by the gateway

---

## 1. Conversation Service

### Endpoint
```
POST /api/conversation
```

### Request
```json
{
  "user_id": "user_12345",
  "telegram_user_id": 12345,
  "message": "Hello, I need help with...",
  "request_id": "abc-123-def-456"
}
```

### Response
```json
{
  "type": "text",
  "content": "I understand you need help. Let me assist you...",
  "conversation_id": "conv_789"
}
```

### Timeout
5 seconds

---

## 2. User Profile Service

### Endpoint
```
POST /api/user/profile
```

### Request
```json
{
  "telegram_user_id": 12345,
  "command": "/start",
  "request_id": "abc-123-def-456"
}
```

### Response for `/start` (New User)
```json
{
  "type": "text",
  "content": "Welcome! Please complete your profile...",
  "internal_user_id": "user_12345",
  "new_user": true
}
```

### Response for `/profile`
```json
{
  "type": "profile",
  "content": "**Your Profile**\n\nName: John Doe\nInterests: AI, ML\nMatches: 5",
  "internal_user_id": "user_12345"
}
```

### Response for `/help`
```json
{
  "type": "text",
  "content": "**Available Commands:**\n\n/start - Get started\n/help - Show help\n/profile - View profile"
}
```

### Timeout
3 seconds

---

## 3. Matching Service

### Endpoint
```
POST /api/matching
```

### Request (Get Matches)
```json
{
  "user_id": "user_12345",
  "action": "CONNECT",
  "target_user_id": null,
  "request_id": "abc-123-def-456"
}
```

### Response (Match List)
```json
{
  "type": "match_list",
  "content": "Here are your suggested matches:",
  "items": [
    {
      "name": "Alice",
      "user_id": "user_67890",
      "reason": "Both interested in AI and machine learning",
      "match_score": 0.85
    },
    {
      "name": "Bob",
      "user_id": "user_11111",
      "reason": "Share passion for startups",
      "match_score": 0.78
    }
  ]
}
```

### Request (Accept/Reject/Skip)
```json
{
  "user_id": "user_12345",
  "action": "ACCEPT",
  "target_user_id": "user_67890",
  "request_id": "abc-123-def-456"
}
```

### Response (Action Confirmation)
```json
{
  "type": "text",
  "content": "✅ You and Alice are now connected!",
  "success": true
}
```

### Timeout
3 seconds

---

## 4. Notification Service

### Endpoint
```
POST /api/notification
```

### Request
```json
{
  "user_id": "user_12345",
  "notification_type": "new_match",
  "request_id": "abc-123-def-456"
}
```

### Response
```json
{
  "type": "text",
  "content": "🔔 You have 3 new notifications",
  "success": true
}
```

### Timeout
3 seconds

---

## Response Types

The gateway supports the following response types from internal services:

### 1. Text Response
```json
{
  "type": "text",
  "content": "Simple text message"
}
```

Rendered as: Plain text message

---

### 2. Profile Response
```json
{
  "type": "profile",
  "content": "Formatted profile information"
}
```

Rendered as: Text message (supports Markdown)

---

### 3. Match List Response
```json
{
  "type": "match_list",
  "content": "Header text",
  "items": [
    {"name": "Alice", "reason": "Both like AI"}
  ]
}
```

Rendered as: Text with inline keyboard buttons for each match

---

### 4. Confirmation Response
```json
{
  "type": "confirmation",
  "content": "Are you sure you want to proceed?"
}
```

Rendered as: Text with Confirm/Cancel buttons

---

## Error Handling

If an internal service returns an error or times out:

1. Gateway logs the error with `request_id`
2. Gateway sends generic error message to user:
   ```
   "Something went wrong on our side. Please try again in a minute."
   ```
3. Gateway still returns HTTP 200 to Telegram

## Mock Responses

For development/testing, the gateway currently returns **mock responses** from `api_client.py`. 

To switch to real services:
1. Uncomment the real implementation in `api_client.py`
2. Update service URLs in `.env`
3. Ensure services are running and accessible

## Adding New Response Types

To add a new response type:

1. Define the JSON structure
2. Add handling in `formatter.py` → `format_response()`
3. Update this documentation

Example:
```python
elif response_type == "custom_type":
    # Your formatting logic here
    return self.format_text_message(chat_id, content)
```
