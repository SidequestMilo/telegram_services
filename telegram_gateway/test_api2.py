import asyncio
import httpx
import json

async def test():
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": "test-chat-id-1234",
            "user_id": "12345",
            "model_id": "mistral-small-latest",
            "message": "I am looking for a hiking friend",
            "context": {"type": "connection_matching"},
            "max_tokens": 1024,
            "temperature": 0.7,
            "timeout_seconds": 30
        }
        resp = await client.post("http://3.110.172.55:8000/conversation/interpret", json=payload, timeout=10)
        print(resp.status_code)
        print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test())
