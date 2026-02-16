"""
Telegram Bot Gateway Service - Main Application
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Tuple, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, Response, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
import httpx

from .config import get_settings, Settings
from .session_manager import SessionManager
from .database import Database
from .rate_limiter import RateLimiter
from .api_client import InternalAPIClient
from .router import TelegramRouter
from .formatter import TelegramResponseFormatter

# Configure logging
def setup_logging(settings: Settings):
    """Configure structured logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    if settings.LOG_FORMAT == "json":
        # In production, you might use python-json-logger
        logging.basicConfig(
            level=log_level,
            format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
            stream=sys.stdout
        )
    else:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )

settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)

# Global instances
session_manager: SessionManager
database: Database
rate_limiter: RateLimiter
api_client: InternalAPIClient
router: TelegramRouter
formatter: TelegramResponseFormatter
telegram_http_client: httpx.AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global session_manager, rate_limiter, api_client, router, formatter, telegram_http_client
    
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize components
    database = Database(db_path=settings.DB_PATH)
    session_manager = SessionManager(settings, database)
    rate_limiter = RateLimiter(settings)
    api_client = InternalAPIClient(settings)
    router = TelegramRouter(api_client)
    formatter = TelegramResponseFormatter()
    
    # Connect to services
    await session_manager.connect()
    await rate_limiter.connect()
    await api_client.connect()
    
    # Initialize Telegram HTTP client
    telegram_http_client = httpx.AsyncClient(
        base_url=f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
    )
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down services")
    await session_manager.disconnect()
    await rate_limiter.disconnect()
    await api_client.disconnect()
    await telegram_http_client.aclose()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)


def get_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid4())


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
    request_id: str = Depends(get_request_id)
):
    """
    Telegram webhook endpoint.
    
    ALWAYS returns HTTP 200 to Telegram.
    Errors are handled internally and reported via Telegram messages.
    """
    try:
        # Verify secret token
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning(
                "Invalid webhook secret token",
                extra={"request_id": request_id}
            )
            # Still return 200 to Telegram
            return Response(status_code=200)
        
        # Parse update payload
        try:
            update = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse update JSON: {e}", extra={"request_id": request_id})
            return Response(status_code=200)
        
        # Extract telegram_user_id and chat_id
        telegram_user_id, chat_id, message_id = extract_user_info(update)
        
        if not telegram_user_id or not chat_id:
            logger.error("Could not extract user info from update", extra={"request_id": request_id})
            return Response(status_code=200)
        
        logger.info(
            f"Processing update for telegram_user_id={telegram_user_id}",
            extra={
                "request_id": request_id,
                "telegram_user_id": telegram_user_id,
                "chat_id": chat_id
            }
        )
        
        # Check rate limit
        if await rate_limiter.is_rate_limited(telegram_user_id):
            logger.warning(
                f"Rate limit exceeded for telegram_user_id={telegram_user_id}",
                extra={"request_id": request_id, "telegram_user_id": telegram_user_id}
            )
            await send_telegram_message(
                formatter.format_rate_limit_message(chat_id),
                request_id
            )
            return Response(status_code=200)
        
        # Get or create session
        session = await session_manager.get_session(telegram_user_id)
        
        if not session:
            # Generate new persistent chat_id (UUID)
            chat_id_uuid = str(uuid4())
            logger.info(f"Creating new session with chat_id={chat_id_uuid} for user {telegram_user_id}")
            
            # Create session
            await session_manager.create_session(
                telegram_user_id,
                chat_id_uuid
            )
        else:
            chat_id_uuid = session.get("chat_id")
            if not chat_id_uuid:
                # Migration: if session exists but no chat_id, add one
                chat_id_uuid = str(uuid4())
                await session_manager.create_session(
                    telegram_user_id,
                    chat_id_uuid,
                    internal_user_id=session.get("internal_user_id")
                )

        internal_user_id = session.get("internal_user_id", f"user_{telegram_user_id}") if session else f"user_{telegram_user_id}"
        
        # Route update to appropriate handler
        response = await router.route_update(
            update,
            chat_id_uuid,
            telegram_user_id,
            request_id
        )
        
        if not response:
            logger.error("No response from router", extra={"request_id": request_id})
            await send_telegram_message(
                formatter.format_error_message(chat_id),
                request_id
            )
            return Response(status_code=200)
        
        # Format response for Telegram
        telegram_payload = formatter.format_response(
            response,
            chat_id,
            message_id
        )
        
        # Send response to Telegram
        await send_telegram_message(telegram_payload, request_id)
        
        logger.info(
            "Update processed successfully",
            extra={
                "request_id": request_id,
                "telegram_user_id": telegram_user_id
            }
        )
        
    except Exception as e:
        logger.error(
            f"Unexpected error in webhook handler: {e}",
            exc_info=True,
            extra={"request_id": request_id}
        )
        
        # Try to send error message if we have chat_id
        try:
            if 'chat_id' in locals():
                await send_telegram_message(
                    formatter.format_error_message(chat_id),
                    request_id
                )
        except:
            pass
    
    # ALWAYS return 200
    return Response(status_code=200)


def extract_user_info(update: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Extract telegram_user_id, chat_id, and message_id from update.
    
    Returns:
        Tuple of (telegram_user_id, chat_id, message_id)
    """
    try:
        if "message" in update:
            message = update["message"]
            return (
                message.get("from", {}).get("id"),
                message.get("chat", {}).get("id"),
                None
            )
        elif "callback_query" in update:
            callback = update["callback_query"]
            return (
                callback.get("from", {}).get("id"),
                callback.get("message", {}).get("chat", {}).get("id"),
                callback.get("message", {}).get("message_id")
            )
    except Exception as e:
        logger.error(f"Error extracting user info: {e}")
    
    return None, None, None


async def send_telegram_message(payload: Dict[str, Any], request_id: str):
    """
    Send message to Telegram API with retry logic.
    
    Args:
        payload: Telegram API payload
        request_id: Request ID for logging
    """
    # Determine endpoint based on payload
    if "message_id" in payload:
        endpoint = "/editMessageText"
    else:
        endpoint = "/sendMessage"
    
    for attempt in range(2):  # Try twice
        try:
            response = await telegram_http_client.post(
                endpoint,
                json=payload,
                timeout=5.0
            )
            
            response.raise_for_status()
            
            logger.info(
                f"Telegram message sent successfully via {endpoint}",
                extra={"request_id": request_id, "attempt": attempt + 1}
            )
            return
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Telegram API error (attempt {attempt + 1}): {e.response.status_code}",
                extra={"request_id": request_id, "response": e.response.text}
            )
            if attempt == 1:  # Last attempt
                raise
                
        except Exception as e:
            logger.error(
                f"Failed to send Telegram message (attempt {attempt + 1}): {e}",
                extra={"request_id": request_id}
            )
            if attempt == 1:
                raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
