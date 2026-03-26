
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_collections():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    collections = await db.list_collection_names()
    print(f"Collections: {collections}")
    
    for coll in collections:
        count = await db[coll].count_documents({})
        print(f"Collection {coll}: {count} documents")
        if count > 0:
            doc = await db[coll].find_one({})
            print(f"Sample doc in {coll}: {doc.keys()}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_collections())
