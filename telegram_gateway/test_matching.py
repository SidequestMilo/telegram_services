import asyncio
import httpx
import json

async def test():
    async with httpx.AsyncClient() as client:
        payload = {
            "user_id": "1519573568"
        }
        try:
            res = await client.post("http://3.110.172.55:8000/conversation/matching", json=payload, timeout=20)
            print(res.status_code)
            print(json.dumps(res.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
