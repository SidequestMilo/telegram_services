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

    async with httpx.AsyncClient() as client:
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
                # Use a new client for each long-poll to avoid connection reuse issues
                # with some ISPs/DNS when holding connections open for 30s
                async with httpx.AsyncClient(timeout=40.0) as poll_client:
                    try:
                        response = await poll_client.get(
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
                            # Forward locally
                            await forward_update(poll_client, update)
                            # Confirm we processed it
                            offset = update["update_id"] + 1
                            
                    except httpx.TimeoutException:
                        # Timeout is normal for long polling, just continue
                        continue
                        
                    except httpx.ConnectError:
                        print("⚠️ Connection error. Retrying in 5s...")
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        print(f"⚠️ Polling error: {e}. Retrying in 2s...")
                        await asyncio.sleep(2)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"💥 Critical Loop Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bridge stopped.")
