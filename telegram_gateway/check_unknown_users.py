
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
    users = await db.users.find({}).to_list(length=200)
    print(f"{'User ID':<15} | {'Profile Name':<20} | {'TG Username':<20}")
    print("-" * 60)
    
    unknown_users = []
    
    for u in users:
        profile = u.get("profile", {})
        name = profile.get("name")
        username = profile.get("username", "N/A")
        
        if not name or name == "None" or name == "Unknown":
            unknown_users.append((u.get("telegram_user_id"), name, username))
            print(f"{str(u.get('telegram_user_id')):<15} | {str(name):<20} | @{str(username):<20}")

    print(f"\nTotal 'Unknown' Users found: {len(unknown_users)}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_db())
