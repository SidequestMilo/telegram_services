import asyncio
import os
import signal
import sys
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
# Use 127.0.0.1 to avoid ipv6 loading issues on some macs
GATEWAY_URL = "http://127.0.0.1:8000/webhook/telegram"

if not TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env")
    sys.exit(1)

async def forward_update(client, update):
    """Forward a single update to the local gateway."""
    update_id = update.get("update_id")
    try:
        # Forward to local webhook endpoint
        response = await client.post(
            GATEWAY_URL,
            json=update,
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET or ""},
            timeout=10.0
        )
        if response.status_code == 200:
            print(f"✅ Forwarded Update {update_id} -> Local Gateway (200 OK)")
        else:
            print(f"⚠️  Forwarded Update {update_id} -> Local Gateway ({response.status_code})")
    except Exception as e:
        print(f"❌ Failed to forward update {update_id}: {e}")

async def main():
    print(f"🚀 Starting Local Poller Bridge...")
    print(f"📥 Polling Telegram -> Forwarding to {GATEWAY_URL}")
    print("Press Ctrl+C to stop.")

    async with httpx.AsyncClient(timeout=httpx.Timeout(40.0, connect=10.0)) as client:
        # 1. Delete existing webhook to enable polling
        try:
            resp = await client.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
            if resp.status_code == 200:
                print("✅ Webhook deleted (polling enabled)")
            else:
                print(f"⚠️ Failed to delete webhook: {resp.text}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return

        # 2. Start Polling Loop
        print("✅ Polling started. You can now use your bot in Telegram!")
        offset = 0
        
        while True:
            try:
                response = await client.get(
                    f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                    params={
                        "offset": offset,
                        "timeout": 30,
                        "allowed_updates": ["message", "callback_query"]
                    }
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("ok"):
                    print(f"⚠️ Telegram API Error: {data}")
                    await asyncio.sleep(5)
                    continue

                updates = data.get("result", [])

                for update in updates:
                    await forward_update(client, update)
                    offset = update["update_id"] + 1

            except asyncio.CancelledError:
                break

            except httpx.TimeoutException:
                # Timeout is expected for long polling.
                continue

            except httpx.ConnectError as e:
                print(f"⚠️ Connection error: {e}. Retrying in 5s...")
                await asyncio.sleep(5)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    # 409 means another getUpdates consumer exists.
                    print("⚠️ Polling conflict (409). Retrying in 5s...")
                    await asyncio.sleep(5)
                else:
                    print(f"⚠️ HTTP error: {e}. Retrying in 3s...")
                    await asyncio.sleep(3)

            except Exception as e:
                print(f"⚠️ Polling error: {e}. Retrying in 2s...")
                await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bridge stopped.")
