from app.api_client import InternalAPIClient
from app.config import get_settings
import asyncio

settings = get_settings()
payload = {
  "status": "success",
  "message": None,
  "matches": [
    {
      "user_id": "user_456",
      "data": {
        "intent": "find_match",
        "entities": {
          "skills": ["Python", "Backend"],
          "interests": ["AI"],
          "goals": ["Find mentor"],
          "availability": {},
          "location": "Remote"
        }
      },
      "score": 0.985
    }
  ]
}

async def mock_call(*args, **kwargs):
    return payload

client = InternalAPIClient(settings)
client._make_request = mock_call

async def main():
    result = await client.call_matching("chat", 123, "CONNECT", None, "req")
    import json
    print(json.dumps(result, indent=2))

asyncio.run(main())
