
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_last_conversations():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    print("Latest 10 conversations in DB:")
    cursor = db.conversations.find().sort("timestamp", -1).limit(10)
    async for doc in cursor:
        print(f"[{doc['telegram_user_id']}] {doc['role'].upper()}: {doc['content'][:50]}...")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_last_conversations())
