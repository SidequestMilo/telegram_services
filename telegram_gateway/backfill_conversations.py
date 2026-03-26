
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime

async def backfill_conversations():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    print("⏳ Backfilling conversation history from existing API request logs...")
    
    # We look for AI service calls which typically contain the message text
    cursor = db.api_requests.find({
        "service_name": {"$in": ["AIService/Interpret", "AIService/Chat", "AIService/Generate"]}
    })
    
    count = 0
    async for req in cursor:
        try:
            payload = req.get("payload", {})
            response_body = req.get("response", {})
            
            # Extract Telegram User ID
            # In our payload, it's often stored as 'user_id' or 'telegram_user_id'
            user_id_raw = payload.get("user_id") or payload.get("telegram_user_id")
            if not user_id_raw:
                continue
                
            try:
                telegram_user_id = int(user_id_raw)
            except (ValueError, TypeError):
                # If it's a UUID or something else, it might not be a telegram_user_id
                # But let's check if we can skip it
                continue
                
            timestamp = req.get("timestamp", datetime.utcnow())
            request_id = req.get("request_id")
            
            # 1. Backfill User Message
            message_text = payload.get("message") or payload.get("prompt")
            if message_text:
                # Check if already exists to avoid duplicates
                existing = await db.conversations.find_one({
                    "telegram_user_id": telegram_user_id,
                    "content": message_text,
                    "role": "user"
                })
                if not existing:
                    await db.conversations.insert_one({
                        "telegram_user_id": telegram_user_id,
                        "role": "user",
                        "content": message_text,
                        "timestamp": timestamp,
                        "request_id": request_id
                    })
                    count += 1
            
            # 2. Backfill Bot Response (if available in the new logger or old logs)
            # Response might be in response_body["content"] or response_body["response"]
            bot_text = response_body.get("content") or response_body.get("response") or response_body.get("text")
            if bot_text:
                existing_bot = await db.conversations.find_one({
                    "telegram_user_id": telegram_user_id,
                    "content": bot_text,
                    "role": "bot"
                })
                if not existing_bot:
                    await db.conversations.insert_one({
                        "telegram_user_id": telegram_user_id,
                        "role": "bot",
                        "content": bot_text,
                        "timestamp": timestamp,
                        "request_id": request_id
                    })
                    count += 1
                    
        except Exception as e:
            print(f"Error processing record: {e}")
            
    print(f"✅ Backfill complete. Added {count} historical messages to the conversation logs.")
    client.close()

if __name__ == "__main__":
    asyncio.run(backfill_conversations())
