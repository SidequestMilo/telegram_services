
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

async def seed_all_users_welcome():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "milo_db")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Fetch all user telegram IDs
    all_users = await db.users.distinct("telegram_user_id")
    print(f"Total Users: {len(all_users)}")
    
    count = 0
    for user_id in all_users:
        if not user_id: continue
        
        # Check if they already have a bot welcome
        existing = await db.conversations.find_one({"telegram_user_id": user_id, "role": "bot"})
        if not existing:
             # Add a welcome bot message for everyone!
             await db.conversations.insert_one({
                 "telegram_user_id": user_id,
                 "role": "bot",
                 "content": "👋 Welcome to Milo! I can help you find startup partners, co-founders, or business buddies. How are you doing today?",
                 "timestamp": datetime.utcnow() - timedelta(days=1), # Make it look old
                 "request_id": "seed-welcome"
             })
             count += 1
             
    print(f"✅ Added {count} bot welcome messages to ensure every user has a 2-way starting presence.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_all_users_welcome())
