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
    
    def __init__(self, settings: Settings):
        self.settings = settings
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
                logger.info(
                    f"Calling {service_name} (attempt {attempt + 1})",
                    extra={"request_id": request_id, "service": service_name}
                )
                
                response = await self.client.post(
                    url,
                    json=payload,
                    timeout=timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
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
                logger.error(
                    f"{service_name} HTTP error: {e.response.status_code}",
                    extra={
                        "request_id": request_id,
                        "service": service_name,
                        "status_code": e.response.status_code
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
            "prompt": prompt
        }
        
        return await self._make_request(
            f"{self.conversation_url}/generate",
            payload,
            self.conversation_timeout,
            "AIService/Generate",
            request_id
        )
    
    async def call_user_profile(
        self,
        telegram_user_id: int,
        command: str,
        request_id: str
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
                          "I'll help you connect with like-minded people.\n\n"
                          "Use /profile to view your profile or just start chatting!",
                "internal_user_id": f"user_{telegram_user_id}",
                "new_user": True
            }
        elif command == "/help":
            return {
                "type": "text",
                "content": "🤖 **Available Commands:**\n\n"
                          "/start - Welcome message\n"
                          "/help - Show this help\n"
                          "/profile - View your profile\n\n"
                          "Just message me naturally to start a conversation!"
            }
        elif command == "/profile":
            return {
                "type": "profile",
                "content": "👤 **Your Profile**\n\n"
                          f"Telegram ID: {telegram_user_id}\n"
                          f"Internal ID: user_{telegram_user_id}\n"
                          "Matches: 5\n"
                          "Status: Active",
                "internal_user_id": f"user_{telegram_user_id}"
            }
        
        return {
            "type": "text",
            "content": "Unknown command",
            "internal_user_id": f"user_{telegram_user_id}"
        }
    
    async def call_matching(
        self,
        internal_user_id: str,
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
        
        if action == "CONNECT":
            return {
                "type": "match_list",
                "content": "🔍 **Suggested Matches:**",
                "items": [
                    {"name": "Ankit", "reason": "Both interested in ML and AI"},
                    {"name": "Priya", "reason": "Share passion for startups"},
                    {"name": "Rahul", "reason": "Both love hiking"}
                ]
            }
        elif action in ["ACCEPT", "REJECT", "SKIP"]:
            return {
                "type": "text",
                "content": f"✅ Action '{action}' recorded for match.",
                "success": True
            }
        
        return {
            "type": "text",
            "content": "Matching service error"
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
