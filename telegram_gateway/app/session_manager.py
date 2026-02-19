"""
Redis-based session management for user sessions.
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime
import logging

import redis.asyncio as redis
from redis.exceptions import RedisError

from .config import Settings
from .database import Database

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions in Redis with automatic TTL refresh and persistent storage."""
    
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.redis_client: Optional[redis.Redis] = None
        self.session_ttl = settings.SESSION_TTL
    
    async def connect(self):
        """Establish Redis and Database connections."""
        # Connect to Database first (Critical)
        try:
            await self.database.connect()
        except Exception as e:
            logger.error(f"Failed to connect to Database: {e}")
            raise

        # Connect to Redis (Cache)
        try:
            self.redis_client = await redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=self.settings.REDIS_DB,
                password=self.settings.REDIS_PASSWORD,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis and Database connections."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
            
        await self.database.disconnect()
    
    def _get_session_key(self, telegram_user_id: int) -> str:
        """Generate Redis key for user session."""
        return f"session:telegram:{telegram_user_id}"
    
    async def get_session(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve user session from Redis or DB.
        """
        session = None
        
        # 1. Try Redis first (if available)
        if self.redis_client:
            try:
                key = self._get_session_key(telegram_user_id)
                session_data = await self.redis_client.get(key)
                
                if session_data:
                    try:
                        session = json.loads(session_data)
                        # Refresh TTL on activity
                        await self.redis_client.expire(key, self.session_ttl)
                        logger.info(f"Session retrieved from Redis for telegram_user_id={telegram_user_id}")
                        return session
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode session data: {e}")
                        # Continue to DB fallback
            except RedisError as e:
                logger.error(f"Redis error while getting session: {e}")
                # Continue to DB fallback

        # 2. Fallback to Persistent DB
        logger.info(f"Checking DB for telegram_user_id={telegram_user_id}")
        chat_id = await self.database.get_chat_id(telegram_user_id)
        
        if chat_id:
            # Found in DB
            logger.info(f"Restoring session from DB for telegram_user_id={telegram_user_id}")
            
            # Create session object
            session = {
                "telegram_user_id": telegram_user_id,
                "chat_id": chat_id,
                "internal_user_id": f"user_{telegram_user_id}",
                "last_interaction_timestamp": datetime.utcnow().isoformat()
            }
            
            # Restore to Redis if possible
            if self.redis_client:
                try:
                    await self.create_session(telegram_user_id, chat_id)
                except Exception as e:
                    logger.warning(f"Failed to restore session to Redis: {e}")
            
            return session
        
        logger.info(f"No session found anywhere for telegram_user_id={telegram_user_id}")
        return None
    
    async def create_session(
        self,
        telegram_user_id: int,
        chat_id: str,
        internal_user_id: Optional[str] = None
    ) -> bool:
        """
        Create or update user session in DB and Redis.
        """
        # 1. Store in Persistent DB first (Critical)
        success = await self.database.store_user_mapping(telegram_user_id, chat_id)
        if not success:
            logger.error("Failed to persist user mapping to DB")
            # We continue to try Redis, but this is bad.
        
        # 2. Store in Redis (Cache)
        session_data = {
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "internal_user_id": internal_user_id or f"user_{telegram_user_id}",
            "last_interaction_timestamp": datetime.utcnow().isoformat()
        }
        
        if self.redis_client:
            try:
                key = self._get_session_key(telegram_user_id)
                await self.redis_client.setex(
                    key,
                    self.session_ttl,
                    json.dumps(session_data)
                )
                logger.info(f"Session created in Redis for telegram_user_id={telegram_user_id}")
            except RedisError as e:
                logger.error(f"Redis error while creating session: {e}")
                # We return True because DB write worked (or we tried)
        
        return True
    
    async def update_conversation_state(
        self,
        telegram_user_id: int,
        conversation_state: str
    ) -> bool:
        """
        Update conversation state for existing session.
        
        Args:
            telegram_user_id: Telegram user ID
            conversation_state: New conversation state
            
        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(telegram_user_id)
        if not session:
            logger.warning(f"Cannot update state: no session for telegram_user_id={telegram_user_id}")
            return False
        
        session["conversation_state"] = conversation_state
        session["last_interaction_timestamp"] = datetime.utcnow().isoformat()
        
        if not self.redis_client:
            return False
        
        try:
            key = self._get_session_key(telegram_user_id)
            await self.redis_client.setex(
                key,
                self.session_ttl,
                json.dumps(session)
            )
            return True
        except RedisError as e:
            logger.error(f"Redis error while updating conversation state: {e}")
            return False
    
    async def delete_session(self, telegram_user_id: int) -> bool:
        """
        Delete user session from Redis.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._get_session_key(telegram_user_id)
            await self.redis_client.delete(key)
            logger.info(f"Session deleted for telegram_user_id={telegram_user_id}")
            return True
        except RedisError as e:
            logger.error(f"Redis error while deleting session: {e}")
            return False
    async def set_persistent_state(self, telegram_user_id: int, state: Optional[str]) -> bool:
        """Set persistent user state in DB."""
        return await self.database.update_user_state(telegram_user_id, state)

    async def get_persistent_state(self, telegram_user_id: int) -> Optional[str]:
        """Get persistent user state from DB."""
        return await self.database.get_user_state(telegram_user_id)
