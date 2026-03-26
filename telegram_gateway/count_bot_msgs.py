
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def count_bot_messages():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    count = await db.conversations.count_documents({"role": "bot"})
    print(f"Total BOT messages in database: {count}")

    client.close()

if __name__ == "__main__":
    asyncio.run(count_bot_messages())
