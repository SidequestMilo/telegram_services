import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    users = await db.users.find().to_list(length=10)
    for u in users:
        print(u)

asyncio.run(main())
