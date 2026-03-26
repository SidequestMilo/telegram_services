
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_api_requests():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    doc = await db.api_requests.find_one({"service_name": "AIService/Interpret"})
    if doc:
        print(f"Sample Interpret doc: {doc}")
    else:
        print("No AI interpret docs")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_api_requests())
