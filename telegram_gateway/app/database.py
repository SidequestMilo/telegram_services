"""
Persistent database for user mappings using SQLite.
"""
import aiosqlite
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Database:
    """Manages persistent user data."""
    
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Establish database connection and ensure tables exist."""
        try:
            self._conn = await aiosqlite.connect(self.db_path)
            # Create user_mappings table
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_user_id INTEGER PRIMARY KEY,
                    chat_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await self._conn.commit()
            logger.info("Database connection established and schema verified")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

    async def disconnect(self):
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed")

    async def get_chat_id(self, telegram_user_id: int) -> Optional[str]:
        """
        Retrieve persistent chat_id for a telegram user.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            Persistent chat_id (UUID) or None
        """
        if not self._conn:
            logger.error("Database not connected")
            return None
            
        try:
            cursor = await self._conn.execute(
                "SELECT chat_id FROM users WHERE telegram_user_id = ?",
                (telegram_user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error retrieving chat_id: {e}")
            return None

    async def store_user_mapping(self, telegram_user_id: int, chat_id: str) -> bool:
        """
        Store permanent user mapping.
        
        Args:
            telegram_user_id: Telegram user ID
            chat_id: Unique chat UUID
            
        Returns:
            True if successful
        """
        if not self._conn:
            logger.error("Database not connected")
            return False
            
        try:
            await self._conn.execute(
                "INSERT OR REPLACE INTO users (telegram_user_id, chat_id) VALUES (?, ?)",
                (telegram_user_id, chat_id)
            )
            await self._conn.commit()
            logger.info(f"Persisted mapping for user {telegram_user_id} -> {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing user mapping: {e}")
            return False
