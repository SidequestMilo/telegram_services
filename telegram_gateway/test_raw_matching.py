import asyncio
import httpx
import json

async def test():
    async with httpx.AsyncClient() as client:
        payload = {
            "user_id": "12345",
            "data": {
                "entities": {
                  "skills": [],
                  "interests": ["basketball"],
                  "goals": ["Find basketball partner", "Connect with startup founder"],
                  "availability": {},
                  "location": ""
                }
            },
            "top_k": 5
        }
        resp = await client.post("http://3.110.172.55:8000/conversation/matching", json=payload, timeout=10)
        print(resp.status_code)
        print(json.dumps(resp.json(), indent=2))

asyncio.run(test())
