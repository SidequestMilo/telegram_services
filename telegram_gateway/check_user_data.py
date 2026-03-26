
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_user_data():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    doc = await db.user_data.find_one({})
    if doc:
        print(f"Sample user_data doc: {doc}")
    else:
        print("No docs in user_data")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_user_data())
