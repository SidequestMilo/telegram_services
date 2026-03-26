
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_activity_logs():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    doc = await db.activity_logs.find_one({})
    if doc:
        print(f"Sample activity_log: {doc}")
    else:
        print("Activity logs empty.")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_activity_logs())
