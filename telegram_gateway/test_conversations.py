
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

async def seed_conversations():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Target User for testing
    user_id = 1519573568 # Praguni
    
    # 1. Insert dummy messages
    messages = [
        {"role": "user", "content": "Hi, how are you?", "timestamp": datetime.utcnow() - timedelta(minutes=10)},
        {"role": "bot", "content": "I am your AI assistant! How can I help you today?", "timestamp": datetime.utcnow() - timedelta(minutes=9)},
        {"role": "user", "content": "I am looking for a co-founder for my AI startup.", "timestamp": datetime.utcnow() - timedelta(minutes=8)},
        {"role": "bot", "content": "That sounds exciting! Let me check your matches for potential co-founders.", "timestamp": datetime.utcnow() - timedelta(minutes=7)},
    ]
    
    for msg in messages:
        await db.conversations.insert_one({
            "telegram_user_id": user_id,
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": msg["timestamp"]
        })
    
    print(f"✅ Seeded {len(messages)} conversation logs for user {user_id}")
    
    # 2. Fetch and display to verify
    print("\n🔍 Verifying stored conversations:")
    cursor = db.conversations.find({"telegram_user_id": user_id}).sort("timestamp", 1)
    async for doc in cursor:
        print(f"[{doc['timestamp'].strftime('%H:%M:%S')}] {doc['role'].upper()}: {doc['content']}")

    client.close()

if __name__ == "__main__":
    asyncio.run(seed_conversations())
