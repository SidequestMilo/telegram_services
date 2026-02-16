# System Workflow & API Interaction Guide

This document outlines how the Telegram Gateway processes different types of user interactions and which internal APIs are called during each flow.

## 1. Chat Flow (Text Messages)
**Trigger**: User sends a regular text message (e.g., "Hello AI").

1.  **Telegram -> Gateway**:
    *   Gateway receives a `message` update.
    *   Extracts `chat_id` (Telegram ID) and `text`.
    *   Resolves persistent `session_id` (UUID) from Database/Redis.

2.  **Gateway -> AI Service**:
    *   **API**: `POST {CONVERSATION_SERVICE_URL}/chat`
    *   **URL Example**: `http://3.110.172.55:8000/chat`
    *   **Payload**:
        ```json
        {
          "chat_id": "5db9df90-2677-43b8-9457-4fd162bf7616",
          "model_id": "mistral-small-latest",
          "message": "Hello AI",
          "max_tokens": 1024,
          "temperature": 0.7,
          "timeout_seconds": 30
        }
        ```

3.  **AI Service -> Gateway**:
    *   **Response**:
        ```json
        {
          "response": "Hello! How can I help you today?",
          "usage": { ... }
        }
        ```

4.  **Gateway -> Telegram**:
    *   Gateway sends the `response` text back to the user.

---

## 2. Generation Flow (Command)
**Trigger**: User sends `/generate <prompt>` (e.g., `/generate a poem about code`).

1.  **Telegram -> Gateway**:
    *   Gateway parses the command `/generate`.
    *   Extracts the prompt: "a poem about code".

2.  **Gateway -> AI Service**:
    *   **API**: `POST {CONVERSATION_SERVICE_URL}/generate`
    *   **URL Example**: `http://3.110.172.55:8000/generate`
    *   **Payload**:
        ```json
        {
          "prompt": "a poem about code"
        }
        ```

3.  **AI Service -> Gateway**:
    *   **Response**: Returns the generated content.

4.  **Gateway -> Telegram**:
    *   Gateway sends the generated content to the user.

---

## 3. User & Profile Flow (Internal/Mocked)
**Trigger**: User sends `/start`, `/help`, or `/profile`.

*   **Current State**: These endpoints are currently handled by **internal logic** in `app/api_client.py` (Mocked).
*   **Future State**: Will trigger calls to `USER_PROFILE_SERVICE_URL`.

1.  **Gateway Logic**:
    *   Checks command (`/start`).
    *   Returns specific hardcoded response layouts (e.g., Welcome Message, Profile Stats).

---

## 4. Matching Flow (Interactive Buttons)
**Trigger**: User clicks an inline button (e.g., "✅ Connect", "⏭ Skip").

*   **Current State**: Handled by **internal logic** in `app/api_client.py` (Mocked).
*   **Future State**: Will trigger calls to `MATCHING_SERVICE_URL`.

1.  **Telegram -> Gateway**:
    *   Gateway receives `callback_query`.
    *   Data format: `ACTION:PARAM` (e.g., `ACCEPT:Ankit`).

2.  **Gateway Processing**:
    *   Parses Action: `ACCEPT`.
    *   Target: `Ankit`.
    *   **Response**: Updates the message to confirm the action (e.g., "✅ Action 'ACCEPT' recorded").

---

## Summary of Configuration (.env)
| Service | Config Variable | Current Value |
| :--- | :--- | :--- |
| **Chat/Generate** | `CONVERSATION_SERVICE_URL` | `http://3.110.172.55:8000` |
| **User Profile** | `USER_PROFILE_SERVICE_URL` | *(Mocked)* |
| **Matching** | `MATCHING_SERVICE_URL` | *(Mocked)* |
| **Notification** | `NOTIFICATION_SERVICE_URL` | *(Mocked)* |
