
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_all_conversations():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "milo_db")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    print(f"Checking DB: {db_name}")
    count = await db.conversations.count_documents({})
    print(f"Total conversations in DB: {count}")
    
    if count > 0:
        cursor = db.conversations.find().sort("timestamp", -1).limit(5)
        async for doc in cursor:
            print(f"[{doc['telegram_user_id']}] {doc['role'].upper()}: {doc['content'][:50]}... ({doc['timestamp']})")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_all_conversations())
