import asyncio
import json
from app.api_client import InternalAPIClient
from app.config import get_settings

async def test():
    settings = get_settings()
    # Mocking _make_request to simply return the exact payload the user specified
    client = InternalAPIClient(settings)
    
    async def mock_make_request(*args, **kwargs):
        # The user's exact JSON format example
        return [
            {
                "user_id": "1519573568",
                "name": "Praguni Sanotra",
                "data": {
                    "intent": "find_match",
                    "entities": {
                        "skills": ["Python", "FastAPI"],
                        "interests": ["AI"],
                        "goals": ["Find mentor"],
                        "availability": {},
                        "location": "Remote"
                    }
                },
                "score": 0.9346
            }
        ]
        
    client._make_request = mock_make_request
    
    # We pass None for database to avoid trying to store real matches in this test
    client.database = None
    
    resp = await client.call_matching("chat123", 1519573568, "CONNECT", None, "req123")
    
    # Render with the Formatter as though the Router triggered it
    from app.formatter import TelegramResponseFormatter
    formatter = TelegramResponseFormatter()
    
    formatted = formatter.format_response(resp, "chat123", None)
    
    print("------- Result -------")
    print(formatted["text"])

asyncio.run(test())
