import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util

async def test():
    client = AsyncIOMotorClient("mongodb+srv://Praguni:6sKiJdQgR8ijGuUb@cluster0.zhswkru.mongodb.net/apl?retryWrites=true&w=majority&appName=Cluster0")
    db = client["telegram_gateway"]
    cursor = db.api_requests.find({"endpoint": {"$regex": "interpret"}}).sort("timestamp", -1).limit(5)
    docs = await cursor.to_list(length=5)
    print(json.dumps(docs, default=json_util.default, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
