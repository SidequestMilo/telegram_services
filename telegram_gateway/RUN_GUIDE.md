# 🚀 How to Run the Telegram Gateway (Quick Start)

Here is how to start all 3 components needed to run your bot locally.

Open **3 separate terminal windows** and run these commands in order:

### 1️⃣ Start the Telegram Gateway (Main Server)
This is the core service that processes messages.
```bash
cd telegram_gateway
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
_(Keep this running!)_

### 2️⃣ Start the AI Service (Mock Brain)
This pretends to be your AI backend (handling /chat and /generate).
```bash
cd telegram_gateway
source venv/bin/activate
python3 mock_ai_service.py
```
_(Keep this running!)_

### 3️⃣ Start the Telegram Poller (The Bridge)
This connects your local computer to real Telegram servers so you get messages.
```bash
cd telegram_gateway
source venv/bin/activate
python3 local_poller.py
```
_(Keep this running!)_

---

## ✅ How do I know it works?
1. Open Telegram.
2. Send `/start` -> You should get a welcome message.
3. Send `/generate a startup idea` -> You should get an AI idea.
4. Send `Hello` -> You should get an AI chat response.

## 🛑 How to Stop?
Press `Ctrl+C` in each terminal window to stop the services.
