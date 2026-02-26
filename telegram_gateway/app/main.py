"""
Telegram Bot Gateway Service - Main Application
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Tuple, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, Response, Header, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
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
    global session_manager, database, rate_limiter, api_client, router, formatter, telegram_http_client
    
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize components
    database = Database(mongo_uri=settings.MONGO_URI, db_name=settings.MONGO_DB_NAME)
    session_manager = SessionManager(settings, database)
    rate_limiter = RateLimiter(settings)
    api_client = InternalAPIClient(settings, database)

    router = TelegramRouter(api_client, session_manager)
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


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None


@app.get("/api/users/{telegram_user_id}/profile")
async def get_profile(telegram_user_id: int):
    """Fetch a user's profile from the database."""
    if not database:
        raise HTTPException(status_code=503, detail="Database not initialized")
        
    profile = await database.get_user_profile(telegram_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return {"status": "success", "telegram_user_id": telegram_user_id, "profile": profile}


@app.post("/api/users/{telegram_user_id}/profile")
async def update_profile(telegram_user_id: int, profile_data: ProfileUpdate):
    """Directly update a user's profile via API."""
    if not database:
        raise HTTPException(status_code=503, detail="Database not initialized")
        
    updated = False
    
    if profile_data.name is not None:
        await database.update_user_profile_field(telegram_user_id, "name", profile_data.name)
        updated = True
    if profile_data.occupation is not None:
        await database.update_user_profile_field(telegram_user_id, "occupation", profile_data.occupation)
        updated = True
    if profile_data.location is not None:
        await database.update_user_profile_field(telegram_user_id, "location", profile_data.location)
        updated = True
        
    if not updated:
        raise HTTPException(status_code=400, detail="No fields provided to update")
        
    # Return updated profile
    profile = await database.get_user_profile(telegram_user_id)
    return {"status": "success", "message": "Profile updated", "profile": profile}


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
            
        # Store user message ID for history tracking
        if message_id:
            await database.add_message(telegram_user_id, message_id)
        
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
            sent_msg_id = await send_telegram_message(
                formatter.format_rate_limit_message(chat_id),
                request_id
            )
            if sent_msg_id:
                await database.add_message(telegram_user_id, sent_msg_id)
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
        
        logger.info(f"[DEBUG_FLOW] calling route_update for {telegram_user_id}", extra={"request_id": request_id})
        
        # Route update to appropriate handler
        response = await router.route_update(
            update,
            chat_id_uuid,
            telegram_user_id,
            request_id
        )
        
        logger.info(f"[DEBUG_FLOW] route_update returned: {response}", extra={"request_id": request_id})
        
        # specific handling for system actions (like session reset)
        if response and response.get("type") == "system_action":
            sys_action = response.get("action")
            logger.info(f"[DEBUG_FLOW] handling system action: {sys_action}", extra={"request_id": request_id})
            
            if sys_action == "reset_session":
                try:
                    logger.info("Starting session reset process...", extra={"request_id": request_id})
                    
                    # 1. Delete all previous messages
                    try:
                        logger.info(f"Deleting message history for user {telegram_user_id}", extra={"request_id": request_id})
                        msg_ids = await database.get_messages(telegram_user_id)
                        logger.info(f"Found {len(msg_ids)} messages to delete", extra={"request_id": request_id})
                        
                        for msg_id in msg_ids:
                            try:
                                await telegram_http_client.post(
                                    "/deleteMessage",
                                    json={"chat_id": chat_id, "message_id": msg_id},
                                    timeout=5.0
                                )
                            except Exception as del_e:
                                # Start logging these errors to debug
                                logger.warning(f"Failed to delete message {msg_id}: {del_e}")
                                pass
                        
                        # Clear from DB
                        await database.clear_messages(telegram_user_id)
                        logger.info("Message history cleared from DB", extra={"request_id": request_id})
                        
                    except Exception as db_e:
                         logger.error(f"Error handling message history deletion: {db_e}", extra={"request_id": request_id})

                    # 2. Rotate session ID to "clear" AI context
                    new_chat_id = str(uuid4())
                    logger.info(f"Creating new session with ID: {new_chat_id}", extra={"request_id": request_id})
                    await session_manager.create_session(telegram_user_id, new_chat_id)
                    
                    logger.info(
                        f"Session reset (history cleared) for user {telegram_user_id}. New chat_id: {new_chat_id}",
                        extra={"request_id": request_id}
                    )
                    
                    # Convert back to text response for display
                    response["type"] = "text"
                
                except Exception as reset_e:
                    logger.error(f"CRITICAL ERROR in reset_session: {reset_e}", exc_info=True, extra={"request_id": request_id})
                    # Fallback so user still gets a response
                    response["type"] = "text"
                    response["content"] = "Chat history cleared (with some internal errors)."
        
        if not response:
            logger.error("No response from router", extra={"request_id": request_id})
            sent_msg_id = await send_telegram_message(
                formatter.format_error_message(chat_id),
                request_id
            )
            if sent_msg_id:
                await database.add_message(telegram_user_id, sent_msg_id)
            return Response(status_code=200)
        
        # Determine if we should edit or send new
        # We only edit if it was a callback query
        is_callback = "callback_query" in update
        target_message_id = message_id if is_callback else None

        # Format response for Telegram
        telegram_payload = formatter.format_response(
            response,
            chat_id,
            target_message_id
        )
        
        # Send response to Telegram
        sent_msg_id = await send_telegram_message(telegram_payload, request_id)
        # Store outgoing bot message ID
        if sent_msg_id:
            await database.add_message(telegram_user_id, sent_msg_id)
        
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
                sent_msg_id = await send_telegram_message(
                    formatter.format_error_message(chat_id),
                    request_id
                )
                if sent_msg_id:
                    # We can't easily await database here if we are inside broad exception handler
                    # but we can try
                    pass
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
                message.get("message_id")
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


async def send_telegram_message(payload: Dict[str, Any], request_id: str) -> Optional[int]:
    """
    Send message to Telegram API with retry logic.
    
    Args:
        payload: Telegram API payload
        request_id: Request ID for logging
        
    Returns:
        Message ID of the sent/edited message, or None if failed
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
            result = response.json()
            
            logger.info(
                f"Telegram message sent successfully via {endpoint}",
                extra={"request_id": request_id, "attempt": attempt + 1}
            )
            
            # Extract message_id
            if endpoint == "/sendMessage":
                return result.get("result", {}).get("message_id")
            elif endpoint == "/editMessageText":
                 # For edit, return the original message_id or the new one if different
                 # Usually result is the Message object
                 return result.get("result", {}).get("message_id")
            
            return None
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Telegram API error (attempt {attempt + 1}): {e.response.status_code}",
                extra={"request_id": request_id, "response": e.response.text}
            )
            
            # If the error is just that the message hasn't changed, ignore it gracefully
            if e.response.status_code == 400 and "message is not modified" in e.response.text.lower():
                logger.info("Ignoring 'message is not modified' error from Telegram API.")
                return payload.get("message_id")
                
            if attempt == 1:  # Last attempt
                raise
                
        except Exception as e:
            logger.error(
                f"Failed to send Telegram message (attempt {attempt + 1}): {e}",
                extra={"request_id": request_id}
            )
            if attempt == 1:
                raise
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
