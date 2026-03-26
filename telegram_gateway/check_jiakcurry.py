
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_user_jiakcurry():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    doc = await db.users.find_one({"profile.username": "jiakcurry"})
    if doc:
        print(f"JiakCurry user info: {doc}")
    else:
        print("User jiakcurry not found.")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_user_jiakcurry())
