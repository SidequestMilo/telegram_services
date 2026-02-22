import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": "test-chat-endpoint",
            "model_id": "mistral-small-latest",
            "message": "I am looking for a cooking partner",
            "max_tokens": 1024,
            "temperature": 0.7,
            "timeout_seconds": 30
        }
        res = await client.post("http://3.110.172.55:8000/chat", json=payload, timeout=20)
        print(res.text)

if __name__ == "__main__":
    asyncio.run(test())
