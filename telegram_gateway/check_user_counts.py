
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_user_counts():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "milo_db")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    total_users = len(await db.users.distinct("telegram_user_id"))
    users_with_convs = len(await db.conversations.distinct("telegram_user_id"))
    total_conv_msgs = await db.conversations.count_documents({})
    
    print(f"Total Users: {total_users}")
    print(f"Users with conversations: {users_with_convs}")
    print(f"Total messages: {total_conv_msgs}")
    
    # Check users missing convs
    all_users = set(await db.users.distinct("telegram_user_id"))
    conv_users = set(await db.conversations.distinct("telegram_user_id"))
    missing = all_users - conv_users
    print(f"Users missing conversations in DB: {len(missing)}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_user_counts())
