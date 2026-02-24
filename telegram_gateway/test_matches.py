import asyncio
import json
from app.api_client import InternalAPIClient
from app.config import get_settings
from app.database import Database

async def main():
    settings = get_settings()
    db = Database(settings.MONGO_URI, settings.MONGO_DB_NAME)
    
    # Needs a running loop for Motor
    await db.connect()
    
    client = InternalAPIClient(settings, database=db)
    await client.connect()
    
    # 1. Connect User
    tel_id = 12345
    print("Sending /connect...")
    interpret = await client.call_ai_interpret(
        "test_chat", tel_id, "I want to connect with a startup founder", "req-test"
    )
    print("Interpret Result:")
    print(json.dumps(interpret, indent=2))
    
    # Check preferences in DB
    prefs = await db.get_user_preferences(tel_id)
    print("\nSaved DB Preferences:")
    print(json.dumps(prefs, indent=2))
    
    # 2. Match
    print("\nSending /matches...")
    result = await client.call_matching("test_chat", tel_id, "CONNECT", None, "req-match")
    print("Match Result:")
    print(json.dumps(result, indent=2))
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
