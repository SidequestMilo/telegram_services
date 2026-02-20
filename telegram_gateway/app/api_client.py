"""
Internal API client for downstream service communication.
"""
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class InternalAPIClient:
    """Async HTTP client for internal service communication."""
    
    def __init__(self, settings: Settings, database: Any = None):
        self.settings = settings
        self.database = database
        self.client: Optional[httpx.AsyncClient] = None
        
        # Service endpoints
        self.conversation_url = settings.CONVERSATION_SERVICE_URL
        self.user_profile_url = settings.USER_PROFILE_SERVICE_URL
        self.matching_url = settings.MATCHING_SERVICE_URL
        self.notification_url = settings.NOTIFICATION_SERVICE_URL
        
        # Timeouts
        self.conversation_timeout = settings.CONVERSATION_TIMEOUT
        self.matching_timeout = settings.MATCHING_TIMEOUT
        self.notification_timeout = settings.NOTIFICATION_TIMEOUT
        self.user_profile_timeout = settings.USER_PROFILE_TIMEOUT
    
    async def connect(self):
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(
            headers={"User-Agent": f"{self.settings.APP_NAME}/{self.settings.APP_VERSION}"}
        )
        logger.info("Internal API client initialized")
    
    async def disconnect(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            logger.info("Internal API client closed")
    
    async def _make_request(
        self,
        url: str,
        payload: Dict[str, Any],
        timeout: int,
        service_name: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: Target URL
            payload: Request payload
            timeout: Request timeout in seconds
            service_name: Name of the service for logging
            request_id: Unique request ID
            
        Returns:
            Response JSON or None on failure
        """
        if not self.client:
            logger.error("HTTP client not initialized")
            return None
        
        for attempt in range(2):  # 0 = first attempt, 1 = retry
            try:
                import time
                start_time = time.time()
                
                logger.info(
                    f"Calling {service_name} (attempt {attempt + 1})",
                    extra={"request_id": request_id, "service": service_name}
                )
                
                response = await self.client.post(
                    url,
                    json=payload,
                    timeout=timeout
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                response.raise_for_status()
                result = response.json()
                
                if getattr(self, "database", None):
                    try:
                        await self.database.store_api_request(
                            service_name=service_name,
                            endpoint=url,
                            payload=payload,
                            latency_ms=latency_ms,
                            status_code=response.status_code,
                            request_id=request_id
                        )
                    except Exception as db_e:
                        logger.error(f"Failed to store API request: {db_e}")
                
                logger.info(
                    f"{service_name} call successful",
                    extra={
                        "request_id": request_id,
                        "service": service_name,
                        "status_code": response.status_code
                    }
                )
                
                return result
                
            except httpx.TimeoutException as e:
                logger.warning(
                    f"{service_name} timeout (attempt {attempt + 1}): {e}",
                    extra={"request_id": request_id, "service": service_name}
                )
                if attempt == 1:  # Last retry
                    return None
                    
            except httpx.HTTPStatusError as e:
                latency_ms = (time.time() - start_time) * 1000 if 'start_time' in locals() else 0
                if getattr(self, "database", None):
                    try:
                        await self.database.store_api_request(
                            service_name=service_name,
                            endpoint=url,
                            payload=payload,
                            latency_ms=latency_ms,
                            status_code=e.response.status_code,
                            request_id=request_id
                        )
                    except Exception as db_e:
                        logger.error(f"Failed to store API request: {db_e}")
                
                # Log response.text for HTTP errors (status_code >= 400)
                error_message = f"{service_name} HTTP error: {e.response.status_code}"
                if e.response.status_code >= 400:
                    error_message += f" - {e.response.text}"
                logger.error(
                    error_message,
                    extra={
                        "request_id": request_id,
                        "service": service_name,
                        "status_code": e.response.status_code,
                        "response_text": e.response.text # Also add to extra for structured logging
                    }
                )
                if attempt == 1:
                    return None
                    
            except Exception as e:
                logger.error(
                    f"{service_name} unexpected error: {e}",
                    extra={"request_id": request_id, "service": service_name}
                )
                return None
        
        return None
    

    
    async def call_ai_chat(
        self,
        chat_id: str,
        telegram_user_id: int,
        message_text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call AI Microservice /chat endpoint.
        
        Args:
            chat_id: Persistent session ID (UUID)
            telegram_user_id: Telegram user ID
            message_text: User message
            request_id: Request ID
            
        Returns:
            AI response payload
        """
        # Logging/Telemetry for the chat request
        logger.info(
            f"Sending chat message to AI model {self.settings.AI_MODEL_ID}",
            extra={
                "request_id": request_id,
                "chat_id": chat_id,
                "telegram_user_id": telegram_user_id,
                "model_id": self.settings.AI_MODEL_ID,
                "temperature": self.settings.AI_TEMPERATURE
            }
        )
        
        payload = {
            "chat_id": chat_id,
            "model_id": self.settings.AI_MODEL_ID,
            "message": message_text,
            "max_tokens": self.settings.AI_MAX_TOKENS,
            "temperature": self.settings.AI_TEMPERATURE,
            "timeout_seconds": self.settings.AI_TIMEOUT_SECONDS
        }
        
        # Use conversation_url as the AI service base URL
        # e.g., http://3.110.172.55:8000/chat
        result = await self._make_request(
            f"{self.conversation_url}/chat",
            payload,
            self.conversation_timeout,
            "AIService/Chat",
            request_id
        )
        
        if result and "response" in result:
            return {
                "type": "text",
                "content": result["response"]
            }
            
        return result

    async def call_ai_generate(
        self,
        prompt: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call AI Microservice /generate endpoint.
        
        Args:
            prompt: Generation prompt
            request_id: Request ID
            
        Returns:
            AI generation response
        """
        payload = {
            "model_id": self.settings.AI_MODEL_ID,
            "prompt": prompt,
            "max_tokens": self.settings.AI_MAX_TOKENS,
            "temperature": self.settings.AI_TEMPERATURE,
            "timeout_seconds": self.settings.AI_TIMEOUT_SECONDS
        }
        
        result = await self._make_request(
            f"{self.conversation_url}/generate",
            payload,
            self.conversation_timeout,
            "AIService/Generate",
            request_id
        )

        # Standardize return of text content if possible
        if result and ("response" in result or "text" in result or "content" in result):
             content = result.get("response") or result.get("text") or result.get("content")
             return {
                 "type": "text",
                 "content": content
             }
        
        return result
    
    async def call_ai_clear(
        self,
        chat_id: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Request session reset (clear history).
        Instead of calling external API (which may not exist), we signal the gateway to rotate the session ID.
        
        Args:
            chat_id: Persistent session ID (UUID)
            request_id: Request ID
            
        Returns:
            System action response to trigger session rotation
        """
        return {
            "type": "system_action",
            "action": "reset_session",
            "content": "🧹 **Chat History Cleared**.\n\nWe can start fresh now!"
        }

    async def call_ai_interpret(
        self,
        chat_id: str,
        telegram_user_id: int,
        message_text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call AI Microservice /conversation/interpret endpoint.
        
        Args:
            chat_id: Persistent session ID
            telegram_user_id: User's telegram ID
            message_text: Text to interpret
            request_id: Request ID
            
        Returns:
            Interpretation result
        """
        payload = {
            "chat_id": chat_id,
            "user_id": str(telegram_user_id),
            "model_id": self.settings.AI_MODEL_ID,
            "message": message_text,
            "context": {"type": "connection_matching"},
            "max_tokens": self.settings.AI_MAX_TOKENS,
            "temperature": self.settings.AI_TEMPERATURE,
            "timeout_seconds": self.settings.AI_TIMEOUT_SECONDS
        }
        
        # Note: path is /conversation/interpret based on user requirement
        result = await self._make_request(
            f"{self.conversation_url}/conversation/interpret",
            payload,
            self.conversation_timeout,
            "AIService/Interpret",
            request_id
        )
        
        if result:
             logger.info(f"AI Interpretation result: {result}")
             # Simply return the 'reply' field from the interpret endpoint
             reply_text = result.get("reply", "I'm sorry, I couldn't understand that. Could you please rephrase?")
             return {
                 "type": "text",
                 "content": reply_text
             }
        
        return {
            "type": "text",
            "content": "Failed to interpret message."
        }
        
    async def call_user_profile(
        self,
        telegram_user_id: int,
        command: str,
        request_id: str,
        chat_id: str = "unknown"
    ) -> Optional[Dict[str, Any]]:
        """
        Call user profile service.
        
        Returns:
            Mock response with user profile or command result
        """
        logger.info(f"[MOCK] Calling user profile service for command {command}")
        
        if command == "/start":
            return {
                "type": "text",
                "content": "👋 Welcome! I'm your AI matching assistant.\n\n"
                          "Use /profile to view your profile details.\n"
                          "Use /connect to find matches.\n"
                          "Use /help to see all commands.",
                "internal_user_id": f"user_{telegram_user_id}",
                "new_user": True
            }
        elif command == "/help":
            return {
                "type": "text",
                "content": "🤖 **Available Commands:**\n\n"
                          "/start - Welcome message\n"
                          "/profile - View your profile details\n"
                          "/connect - Find new matches\n"
                          "/matches - View your matches\n"
                          "/clear - Clear conversation history\n"
                          "/generate <prompt> - AI Generation\n\n"
                          "Just message me naturally to start a conversation!"
            }
        elif command == "/profile":
            return {
                "type": "text",
                "content": "👤 **Your Profile**\n\n"
                          "Here are your details. Use /connect to find new matches based on your profile!\n\n"
                          f"Status: Active\nID: {telegram_user_id}",
                "internal_user_id": f"user_{telegram_user_id}"
            }
        elif command == "/matches":
            return {
                "type": "match_list",
                "content": "❤️ **Your Matches**",
                "items": [
                    {"name": "Ankit", "reason": "Both interested in ML and AI"},
                    {"name": "Priya", "reason": "Share passion for startups"},
                    {"name": "Rahul", "reason": "Both love hiking"},
                    {"name": "Sara", "reason": "Fellow Python developer"}
                ]
            }
        elif command == "/connect":
             return await self.call_ai_interpret(
                chat_id,
                message_text="I want to connect with someone",
                request_id=request_id
            )
        elif command == "/clear":
             return await self.call_ai_clear(
                chat_id,
                request_id
            )
        elif command.startswith("FILE:"):
             # Handle file upload mock
             filename = command.split(":", 1)[1]
             return {
                "type": "text",
                "content": f"📄 **Resume Received**: `{filename}`\n\n"
                           "I'm analyzing your profile... (Mock processed)\n"
                           "Profile updated successfully!"
            }
        return {
            "type": "text",
            "content": "Unknown command",
            "internal_user_id": f"user_{telegram_user_id}"
        }
    
    async def call_matching(
        self,
        chat_id: str,
        action: str,
        target_user_id: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call matching service.
        
        Returns:
            Mock response with match results or action confirmation
        """
        logger.info(f"[MOCK] Calling matching service for action {action}")
        
        import json
        
        # Default candidate if the AI parsing fails
        candidate = {"name": "Alex", "reason": "A highly relevant connection based on your interests!"}
        
        try:
            # We use call_ai_chat with the user's specific chat_id so the AI reads the chat history context
            prompt = (
                "System: Based strictly on the user's LAST FEW messages about what they are looking for, "
                "generate ONE highly relevant and very specific fake user profile for them to connect with. "
                "It is critical that the match directly addresses the user's most recent request. "
                "Output EXACTLY valid JSON with three keys: 'name' (a fake first name), 'reason' (a 5 to 10 word ultra-specific reason why they match the user's exact query), and 'rating' (a float out of 5.0, e.g., 4.8). "
                "Do NOT include any generic markdown or extra text. ONLY raw JSON like {\"name\": \"Alex\", \"reason\": \"Loves baking cakes too!\", \"rating\": 4.9}."
            )
            ai_res = await self.call_ai_chat(chat_id, 0, prompt, request_id)
            
            if ai_res and "content" in ai_res:
                content = ai_res["content"]
                # Clean up potential markdown formatting around JSON
                cleaned = content.replace("```json", "").replace("```", "").strip()
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(cleaned[start:end])
                    if "name" in parsed and "reason" in parsed:
                        candidate = parsed
                        if "rating" not in candidate:
                            candidate["rating"] = 4.5
        except Exception as e:
            logger.error(f"Error generating dynamic context match: {e}")
        
        if action == "CONNECT":
            return {
                "type": "match_list",
                "content": "🔍 **Suggested Match for You:**",
                "items": [candidate]
            }
        elif action == "SKIP":
            return {
                "type": "match_list",
                "content": f"Skipped {target_user_id}. How about this match? 👇",
                "items": [candidate]
            }
        elif action == "ACCEPT":
            return {
                "type": "match_list",
                "content": f"✅ Connected with {target_user_id}!\n\nHere is your next match 👇",
                "items": [candidate]
            }
        
        # Fallback for REJECT (if we use it)
        return {
            "type": "text",
            "content": f"✅ Action '{action}' recorded for {target_user_id}.",
            "success": True
        }
    
    async def call_notification(
        self,
        internal_user_id: str,
        notification_type: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call notification service.
        
        Returns:
            Mock response with notification status
        """
        logger.info(f"[MOCK] Calling notification service for type {notification_type}")
        
        return {
            "type": "text",
            "content": "🔔 Notification sent successfully",
            "success": True
        }
