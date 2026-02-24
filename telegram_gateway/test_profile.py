import asyncio
import json
from app.api_client import InternalAPIClient
from app.config import get_settings
from app.database import Database
from app.router import TelegramRouter

async def main():
    class MockSession:
        def __init__(self): self.states = {}
        async def get_persistent_state(self, uid): return self.states.get(uid)
        async def set_persistent_state(self, uid, state): self.states[uid] = state
        
    settings = get_settings()
    db = Database(settings.MONGO_URI, settings.MONGO_DB_NAME)
    await db.connect()
    
    client = InternalAPIClient(settings, database=db)
    router = TelegramRouter(client, MockSession())
    
    uid = 999123
    
    msg1 = await router.route_update({"message": {"from": {"id": uid}, "chat": {"id": "c1"}, "text": "/profile"}}, "c1", uid, "req1")
    print("1 /profile:", msg1["content"])
    
    msg2 = await router.route_update({"message": {"from": {"id": uid}, "chat": {"id": "c1"}, "text": "Alice"}}, "c1", uid, "req2")
    print("2 Ans1:", msg2["content"])
    
    msg3 = await router.route_update({"message": {"from": {"id": uid}, "chat": {"id": "c1"}, "text": "Engineer"}}, "c1", uid, "req3")
    print("3 Ans2:", msg3["content"])
    
    msg4 = await router.route_update({"message": {"from": {"id": uid}, "chat": {"id": "c1"}, "text": "New York"}}, "c1", uid, "req4")
    print("4 Ans3:", msg4["content"])
    
    msg5 = await router.route_update({"message": {"from": {"id": uid}, "chat": {"id": "c1"}, "text": "/profile"}}, "c1", uid, "req5")
    print("5 /profile check:")
    print(msg5["content"])

asyncio.run(main())
