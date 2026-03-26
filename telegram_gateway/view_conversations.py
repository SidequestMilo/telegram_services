
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def view_conversations():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Target User
    user_id = 1519573568 # Praguni
    
    print(f"📄 Fetching conversation logs for user {user_id}...")
    cursor = db.conversations.find({"telegram_user_id": user_id}).sort("timestamp", 1)
    
    count = 0
    async for doc in cursor:
        timestamp = doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        role = doc['role'].upper()
        content = doc['content']
        print(f"[{timestamp}] {role:<5}: {content}")
        count += 1
        
    if count == 0:
        print("No conversations found. Have you started chatting with the bot yet?")
    else:
        print(f"\n✅ Total {count} messages found.")

    client.close()

if __name__ == "__main__":
    asyncio.run(view_conversations())
