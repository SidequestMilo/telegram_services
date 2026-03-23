
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_db():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Get all users
    users = await db.users.find({}).to_list(length=100)
    print(f"Total Users: {len(users)}")
    for u in users:
        print(f"User: {u.get('telegram_user_id')} - Name: {u.get('profile', {}).get('name')}")
        
    # Get all connections
    connections = await db.connections.find({}).to_list(length=100)
    print(f"\nTotal Connections: {len(connections)}")
    for c in connections:
        print(f"Connection: {c.get('from_user_id')} -> {c.get('to_user_id')} status={c.get('status')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_db())
