"""
Redis-based rate limiting for user requests.
"""
import logging
from typing import Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

from .config import Settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter using Redis."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self.rate_limit = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_WINDOW
    
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
            logger.info("Rate limiter Redis connection established")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Rate limiter Redis connection closed")
    
    def _get_rate_limit_key(self, telegram_user_id: int) -> str:
        """Generate Redis key for rate limiting."""
        return f"ratelimit:telegram:{telegram_user_id}"
    
    async def is_rate_limited(self, telegram_user_id: int) -> bool:
        """
        Check if user is rate limited.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            True if rate limited, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis not available, rate limiting disabled")
            return False
        
        try:
            key = self._get_rate_limit_key(telegram_user_id)
            
            # Get current count
            current = await self.redis_client.get(key)
            
            if current is None:
                # First request in window
                await self.redis_client.setex(key, self.window, "1")
                logger.debug(f"Rate limit initialized for telegram_user_id={telegram_user_id}")
                return False
            
            current_count = int(current)
            
            if current_count >= self.rate_limit:
                logger.warning(
                    f"Rate limit exceeded for telegram_user_id={telegram_user_id}, "
                    f"count={current_count}"
                )
                return True
            
            # Increment counter
            await self.redis_client.incr(key)
            logger.debug(f"Rate limit check passed for telegram_user_id={telegram_user_id}")
            return False
            
        except RedisError as e:
            logger.error(f"Redis error during rate limit check: {e}")
            # Fail open - don't rate limit on error
            return False
        except ValueError as e:
            logger.error(f"Invalid rate limit counter value: {e}")
            return False
    
    async def reset_rate_limit(self, telegram_user_id: int) -> bool:
        """
        Reset rate limit for a user (useful for testing or admin actions).
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._get_rate_limit_key(telegram_user_id)
            await self.redis_client.delete(key)
            logger.info(f"Rate limit reset for telegram_user_id={telegram_user_id}")
            return True
        except RedisError as e:
            logger.error(f"Redis error while resetting rate limit: {e}")
            return False
