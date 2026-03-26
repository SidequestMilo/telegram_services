
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

async def check_recent_conversations():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # 5 minutes ago
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    print(f"Conversations in the last 10 minutes (since implementation):")
    cursor = db.conversations.find({"timestamp": {"$gte": cutoff}}).sort("timestamp", -1)
    
    count = 0
    async for doc in cursor:
        print(f"[{doc['telegram_user_id']}] {doc['role'].upper()}: {doc['content'][:50]}...")
        count += 1
        
    print(f"Total: {count}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_recent_conversations())
