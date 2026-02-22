import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": "test-cooking-id",
            "user_id": "12345",
            "model_id": "mistral-small-latest",
            "message": "I am looking for a cooking partner",
            "context": {"type": "connection_matching"}
        }
        res = await client.post("http://3.110.172.55:8000/conversation/interpret", json=payload, timeout=20)
        print(res.text)

if __name__ == "__main__":
    asyncio.run(test())
