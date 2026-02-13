# 🧪 How to Test the Telegram Gateway

This guide covers three ways to test your Telegram Gateway service:
1.  **Manual Simulation** (Fastest, no external tools needed)
2.  **Unit Tests** (Best for code verification)
3.  **Real End-to-End Testing** (Best for full integration)

---

## 1. Manual Simulation (via Curl)

You can simulate a Telegram webhook event locally without needing a public URL or `ngrok`. This validates that your logic is working.

### Step 1: Ensure the service is running
Make sure your service is running on `localhost:8000`.

### Step 2: Send a simulated `/start` command
Open a new terminal window and run:

```bash
curl -v -X POST "http://localhost:8000/webhook/telegram" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: my_test_secret_token_12345" \
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
      "text": "/start"
    }
  }'
```

### Expected Output:
-   **HTTP 200 OK**: The command should succeed.
-   **Terminal Logs**: Check the terminal where your service is running. You should see logs indicating the update was processed:
    ```
    INFO:     Processing update for telegram_user_id=1111111
    INFO:     Update processed successfully
    ```

---

## 2. Unit Tests (Pytest)

The project comes with a test suite to verify routing and formatting logic.

### Step 1: Activate Virtual Environment
Make sure you are in the `telegram_gateway` directory and your virtual environment is active:
```bash
cd telegram_gateway
source venv/bin/activate
```

### Step 2: Run Tests
Run the full test suite:
```bash
pytest -v
```

### Expected Output:
You should see all tests passing:
```
test_router.py::TestWebhookParsing::test_extract_message_info PASSED
test_router.py::TestRouting::test_command_routing PASSED
...
```

---

## 3. Real End-to-End Testing (Telegram App)

To test with the real Telegram app, your local server needs to be accessible from the internet.

### Step 1: Install ngrok
If you don't have it, install ngrok (a tool to expose local servers):
-   **Mac (Homebrew):** `brew install ngrok`
-   **Manual:** Download from [ngrok.com](https://ngrok.com/download)

### Step 2: Expose Port 8000
```bash
ngrok http 8000
```
Copy the HTTPS URL generated (e.g., `https://a1b2c3d4.ngrok.io`).

### Step 3: Set the Webhook
Tell Telegram to send updates to your ngrok URL:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<YOUR_NGROK_URL>/webhook/telegram",
    "secret_token": "my_test_secret_token_12345"
  }'
```

### Step 4: Chat with your Bot
1.  Open Telegram.
2.  Search for your bot (by username).
3.  Send `/start` or `Hello`.
4.  Watch your local terminal for logs!

---

## 🔍 Troubleshooting

-   **404 Not Found**: Ensure you are POSTing to `/webhook/telegram`, not just `/`.
-   **401 Unauthorized**: Check that `X-Telegram-Bot-Api-Secret-Token` header matches the `TELEGRAM_WEBHOOK_SECRET` in your `.env` file.
-   **Connection Refused**: Ensure your `uvicorn` server is running on port 8000.
