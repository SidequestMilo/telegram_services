
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

async def create_dummy_data():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "telegram_gateway")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    praguni_id = 1519573568
    ian_id = 301194804
    axle_id = 572700426
    rajvee_id = 7332671226
    
    # Ensure Axel has profile info for VIEW_PROFILE to work well
    await db.users.update_one(
        {"telegram_user_id": axle_id},
        {"$set": {
            "profile": {
                "name": "Axle",
                "interests": "Formula 1, Engineering, Sustainable Tech",
                "location": "Germany"
            },
            "preferences": {
                "connection_intent": "Startup partner for green tech",
                "skills": ["Python", "Mechanical Design", "Fundraising"],
                "goals": ["Launch a CO2-neutral delivery drone startup"]
            }
        }},
        upsert=True
    )
    
    # Establish connection with Ian
    await db.connections.update_one(
        {"from_user_id": praguni_id, "to_user_id": ian_id},
        {"$set": {"status": "accepted", "updated_at": datetime.utcnow()}, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    
    # Establish connection with Axel
    await db.connections.update_one(
        {"from_user_id": praguni_id, "to_user_id": axle_id},
        {"$set": {"status": "accepted", "updated_at": datetime.utcnow()}, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    
    # Pending incoming request from Rajvee
    await db.connections.update_one(
        {"from_user_id": rajvee_id, "to_user_id": praguni_id},
        {"$set": {"status": "pending", "intent": "Frontend developer partnership", "updated_at": datetime.utcnow()}, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    
    print("Dummy connection data created for Praguni (1519573568).")
    client.close()

if __name__ == "__main__":
    asyncio.run(create_dummy_data())
