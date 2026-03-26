
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

async def seed_jiakcurry_conversations():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Target User from screenshot
    user_id = 158055984 # jiakcurry
    
    # 1. Insert dummy messages
    messages = [
        {"role": "user", "content": "Hello! I am in Singapore.", "timestamp": datetime.utcnow() - timedelta(hours=1)},
        {"role": "bot", "content": "Welcome! How can I help you today in Singapore?", "timestamp": datetime.utcnow() - timedelta(minutes=55)},
        {"role": "user", "content": "I like coffee and looking for a buddy.", "timestamp": datetime.utcnow() - timedelta(minutes=50)},
        {"role": "bot", "content": "Great! I've noted your interest in coffee. I'll search for buddies for you.", "timestamp": datetime.utcnow() - timedelta(minutes=45)},
    ]
    
    for msg in messages:
        await db.conversations.insert_one({
            "telegram_user_id": user_id,
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": msg["timestamp"]
        })
    
    print(f"✅ Seeded {len(messages)} conversation logs for user {user_id} (@jiakcurry)")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_jiakcurry_conversations())
