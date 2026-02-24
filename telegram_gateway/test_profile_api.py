import httpx
import json
import asyncio

async def test():
    # Insert one via POST
    print("Posting update...")
    payload = {"name": "Test User", "location": "Test Area"}
    async with httpx.AsyncClient() as c:
        resp = await c.post("http://127.0.0.1:8000/api/users/8888/profile", json=payload)
        print("POST Response:", resp.status_code)
        
    print("Fetching via GET...")
    async with httpx.AsyncClient() as c:
        resp = await c.get("http://127.0.0.1:8000/api/users/8888/profile")
        print("GET Response:", resp.status_code)
        print(json.dumps(resp.json(), indent=2))

asyncio.run(test())
