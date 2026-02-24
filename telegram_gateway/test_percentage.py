from app.formatter import TelegramResponseFormatter
f = TelegramResponseFormatter()
payload = {
    "type": "match_list",
    "items": [
        {
            "name": "User 456",
            "reason": "Goals: Find mentor | Interests: AI",
            "rating": 4.9,
            "match_percentage": 98
        }
    ]
}
msg = f.format_response(payload, "123", None)
print(msg["text"])
