import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings
import json

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    users = await db.users.find().to_list(length=100)
    print(f"Total documents: {len(users)}")
    for i, u in enumerate(users):
        has_profile = 'profile' in u
        print(f"{i+1}. _id: {u['_id']} | user_id: {u.get('user_id', 'N/A')} | telegram_user_id: {u.get('telegram_user_id', 'N/A')} | has_profile: {has_profile}")

asyncio.run(main())
