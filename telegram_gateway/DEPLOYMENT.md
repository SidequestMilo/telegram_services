
# 🚀 Deployment Guide

This guide covers how to deploy the Telegram Gateway service. The recommended method is using **Docker** and **Docker Compose** for a robust, production-ready setup with persistent storage.

## ✅ Prerequisites

1.  **Server/VPS**: Any Linux server (Ubuntu 20.04+ recommended) with a public IP.
    *   Examples: AWS EC2, DigitalOcean Droplet, Hetzner, etc.
2.  **Domain Name**: Recommended for SSL/HTTPS (required for Telegram Webhooks).
3.  **Installed Tools**:
    *   Docker & Docker Compose
    *   Git

## 🛠 Option 1: Docker Compose (Recommended)

This method automatically sets up the application, Redis, and persistent volumes.

### 1. Clone the Repository
SSH into your server and clone your code:
```bash
git clone <your-repo-url>
cd telegram_gateway
```

### 2. Configure Environment
Create a production `.env` file:
```bash
cp .env.example .env
nano .env
```

**Critical Variables to Set:**
*   `TELEGRAM_BOT_TOKEN`: Your bot token from BotFather.
*   `TELEGRAM_WEBHOOK_SECRET`: A long, random string.
*   `CONVERSATION_SERVICE_URL`: **REQUIRED** - The full URL to your AI backend (e.g., `http://3.110.172.55:8000` or `https://ai.yourdomain.com`).
*   **AI Configuration**:
    *   `AI_MODEL_ID`: The ID of the model to use (e.g., `gpt-4`, `claude-3`, or your custom model ID).
    *   `AI_MAX_TOKENS`: Max tokens for response (default `0` for unlimited).
    *   `AI_TEMPERATURE`: strictness (default `1.0`).
    *   `AI_TIMEOUT_SECONDS`: Request timeout.

**Note on Networking**:
Since your AI service is hosted externally (e.g., `http://3.110.172.55`), docker containers can reach it directly. Just ensure the IP is correct in `.env`. DO NOT use `localhost` or `127.0.0.1` unless running on the same host network (which is tricky with Docker). Use the public IP or domain.

### 3. Start the Service
Build and run the containers in detached mode:
```bash
docker-compose up -d --build
```

### 4. Verify Status
Check if containers are running:
```bash
docker-compose ps
```
View logs:
```bash
docker-compose logs -f
```

### 5. Setup Webhook (HTTPS)
Telegram **requires** HTTPS for webhooks. You have two common options:

#### A. Using Nginx + Certbot (Reverse Proxy)
Run Nginx on the host to terminate SSL and proxy to port 8000.
1.  Install Nginx: `sudo apt install nginx`
2.  Get SSL Cert: `sudo certbot --nginx -d your-domain.com`
3.  Configure Nginx Proxy:
    ```nginx
    location /webhook/telegram {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    ```

#### B. Using Cloudflare Tunnel (Easier)
If you use Cloudflare, you can use `cloudflared` to expose port 8000 securely without opening ports on your firewall.

### 6. Register the Webhook
Once your URL is live (e.g., `https://your-domain.com/webhook/telegram`), tell Telegram to send updates there:

```bash
curl -F "url=https://your-domain.com/webhook/telegram" \
     -F "secret_token=<YOUR_SECRET_TOKEN>" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

---

## 💾 Persistent Storage
The application uses SQLite to store user mappings (`users.db`).
*   **Location**: Inside the container at `/app/data/users.db`.
*   **Host Mapping**: Mapped to `./data` in your project folder.
*   **Backup**: backup the `./data` folder on your host machine to prevent data loss.

---

## 🔄 Updating
To deploy new code changes:
1.  `git pull`
2.  `docker-compose up -d --build` (Rebuilds and restarts updated services only)

## ⚡️ Troubleshooting
*   **Connection Refused**: Ensure persistent `users.db` is writable. Docker handles this with the `useradd` and `chown` steps in the Dockerfile.
*   **Telegram 400 Errors**: Check if your Bot Token is correct and that you aren't sending malformed payloads.
*   **Redis Errors**: Ensure the `redis` service in docker-compose is happy (`docker-compose logs redis`).
