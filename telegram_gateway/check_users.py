
import asyncio
import aiosqlite
import os

async def check_db():
    db_path = "users.db"
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return

    async with aiosqlite.connect(db_path) as db:
        print("--- Users in Database ---")
        try:
            async with db.execute("SELECT telegram_user_id, chat_id, created_at FROM users") as cursor:
                async for row in cursor:
                    print(f"Telegram User: {row[0]} | ChatID: {row[1]} | Created: {row[2]}")
        except Exception as e:
            print(f"Error querying database: {e}")
            print("Ensure the table 'users' exists.")

if __name__ == "__main__":
    asyncio.run(check_db())
