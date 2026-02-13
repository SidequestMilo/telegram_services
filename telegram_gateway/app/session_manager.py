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

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions in Redis with automatic TTL refresh."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self.session_ttl = settings.SESSION_TTL
    
    async def connect(self):
        """Establish Redis connection."""
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
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    def _get_session_key(self, telegram_user_id: int) -> str:
        """Generate Redis key for user session."""
        return f"session:telegram:{telegram_user_id}"
    
    async def get_session(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve user session from Redis.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            Session data dictionary or None if not found
        """
        if not self.redis_client:
            logger.warning("Redis not available, operating without session")
            return None
        
        try:
            key = self._get_session_key(telegram_user_id)
            session_data = await self.redis_client.get(key)
            
            if session_data:
                session = json.loads(session_data)
                # Refresh TTL on activity
                await self.redis_client.expire(key, self.session_ttl)
                logger.info(f"Session retrieved for telegram_user_id={telegram_user_id}")
                return session
            
            logger.info(f"No session found for telegram_user_id={telegram_user_id}")
            return None
            
        except RedisError as e:
            logger.error(f"Redis error while getting session: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode session data: {e}")
            return None
    
    async def create_session(
        self,
        telegram_user_id: int,
        chat_id: str,
        internal_user_id: Optional[str] = None
    ) -> bool:
        """
        Create or update user session in Redis.
        
        Args:
            telegram_user_id: Telegram user ID
            chat_id: Unique UUID for AI chat session
            internal_user_id: Optional internal system user ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot create session")
            return False
        
        try:
            key = self._get_session_key(telegram_user_id)
            session_data = {
                "telegram_user_id": telegram_user_id,
                "chat_id": chat_id,
                "internal_user_id": internal_user_id or f"user_{telegram_user_id}",
                "last_interaction_timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.setex(
                key,
                self.session_ttl,
                json.dumps(session_data)
            )
            
            logger.info(f"Session created for telegram_user_id={telegram_user_id}")
            return True
            
        except RedisError as e:
            logger.error(f"Redis error while creating session: {e}")
            return False
    
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
