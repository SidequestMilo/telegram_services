import asyncio
import httpx

async def test():
    bot_token = "8338126207:AAH31WhEldJFuEfWGvDfV--12L3h_D-UptQ"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": 1519573568,
        "text": "Link test",
        "reply_markup": {
            "inline_keyboard": [[{"text": "Click", "url": "tg://user?id=7332671226"}]]
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        print(resp.status_code)
        print(resp.text)

asyncio.run(test())
