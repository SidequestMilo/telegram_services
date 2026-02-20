"""
Persistent database for user mappings using MongoDB (Motor).
"""
import logging
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class Database:
    """Manages persistent user data with MongoDB."""
    
    def __init__(self, mongo_uri: str, db_name: str = "telegram_gateway"):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Establish database connection and ensure indexes."""
        try:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            
            # Create indexes
            # Ensure unique telegram_user_id in users (sparse=True ignores null/missing)
            await self.db.users.create_index("telegram_user_id", unique=True, sparse=True)
            # Ensure unique chat_id in users
            await self.db.users.create_index("chat_id", unique=True, sparse=True)
            
            # Ensure unique message tracking (sparse to tolerate missing fields)
            await self.db.messages.create_index(
                [("telegram_user_id", 1), ("message_id", 1)], 
                unique=True,
                sparse=True
            )
            
            # Verify connection
            await self.client.admin.command('ping')
            logger.info("MongoDB connection established and indexes verified")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

    async def disconnect(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")

    async def get_chat_id(self, telegram_user_id: int) -> Optional[str]:
        """Retrieve persistent chat_id."""
        if self.db is None: return None
        try:
            doc = await self.db.users.find_one({"telegram_user_id": telegram_user_id})
            return doc.get("chat_id") if doc else None
        except Exception as e:
            logger.error(f"Error retrieving chat_id: {e}")
            return None

    async def get_user_state(self, telegram_user_id: int) -> Optional[str]:
        """Retrieve user state."""
        if self.db is None: return None
        try:
            doc = await self.db.users.find_one({"telegram_user_id": telegram_user_id})
            return doc.get("state") if doc else None
        except Exception as e:
            logger.error(f"Error retrieving state: {e}")
            return None

    async def update_user_state(self, telegram_user_id: int, state: Optional[str]) -> bool:
        """Update user state."""
        if self.db is None: return False
        try:
            await self.db.users.update_one(
                {"telegram_user_id": telegram_user_id},
                {"$set": {"state": state, "telegram_user_id": telegram_user_id}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating state: {e}")
            return False

    async def store_user_mapping(self, telegram_user_id: int, chat_id: str) -> bool:
        """
        Store permanent user mapping.
        
        Args:
            telegram_user_id: Telegram user ID
            chat_id: Unique chat UUID
            
        Returns:
            True if successful
        """
        if self.db is None:
            logger.error("Database not connected")
            return False
            
        try:
            # Upsert chat_id
            await self.db.users.update_one(
                {"telegram_user_id": telegram_user_id},
                {"$set": {"chat_id": chat_id, "telegram_user_id": telegram_user_id}},
                upsert=True
            )
            logger.info(f"Persisted mapping for user {telegram_user_id} -> {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing user mapping: {e}")
            return False

    async def add_message(self, telegram_user_id: int, message_id: int) -> bool:
        """Log a message ID for a user."""
        if self.db is None:
            return False
        try:
            await self.db.messages.update_one(
                {"telegram_user_id": telegram_user_id, "message_id": message_id},
                {"$set": {"telegram_user_id": telegram_user_id, "message_id": message_id}},
                upsert=True
            )
            return True
        except Exception:
            return False

    async def get_messages(self, telegram_user_id: int) -> List[int]:
        """Get all message IDs for a user."""
        if self.db is None:
            return []
        try:
            cursor = self.db.messages.find({"telegram_user_id": telegram_user_id})
            messages = []
            async for doc in cursor:
                messages.append(doc["message_id"])
            return messages
        except Exception:
            return []

    async def clear_messages(self, telegram_user_id: int) -> bool:
        """Clear message history for a user from DB."""
        if self.db is None:
            return False
        try:
            await self.db.messages.delete_many({"telegram_user_id": telegram_user_id})
            return True
        except Exception:
            return False

    async def store_api_request(
        self,
        service_name: str,
        endpoint: str,
        payload: dict,
        latency_ms: float,
        status_code: int,
        request_id: str
    ) -> bool:
        """Store API request metrics."""
        if self.db is None:
            return False
        try:
            from datetime import datetime
            await self.db.api_requests.insert_one({
                "service_name": service_name,
                "endpoint": endpoint,
                "payload": payload,
                "latency_ms": latency_ms,
                "status_code": status_code,
                "request_id": request_id,
                "timestamp": datetime.utcnow()
            })
            return True
        except Exception as e:
            logger.error(f"Error storing API request: {e}")
            return False
