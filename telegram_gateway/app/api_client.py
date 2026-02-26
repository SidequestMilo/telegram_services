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
        self.vector_url = f"{settings.CONVERSATION_SERVICE_URL}/conversation/vector"
        
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
             
             # Store interpreted preferences in the database
             if self.database:
                 entities = result.get("entities")
                 if entities:
                     await self.database.update_user_preferences(telegram_user_id, entities)
                     
                     # Get current user profile for the name and UPSERT to vector DB
                     user_profile = await self.database.get_user_profile(telegram_user_id)
                     name = user_profile.get("name", f"User {telegram_user_id}")
                     intent = result.get("intent", "find_match")
                     
                     await self.call_vector_upsert(
                         chat_id=chat_id,
                         telegram_user_id=telegram_user_id,
                         entities=entities,
                         intent=intent,
                         name=name,
                         request_id=request_id
                     )
             
             reply_text = result.get("reply")
             
             # If the interpret endpoint lacks a direct reply (e.g. initial /connect)
             if not reply_text:
                 logger.info("No explicit 'reply' found from interpret endpoint, using default text")
                 reply_text = "Got it! Your connection preferences have been updated. Use /matches to see your suggestions!"
             
             return {
                 "type": "text",
                 "content": reply_text
             }
        
        return {
            "type": "text",
            "content": "Failed to interpret message."
        }

    async def call_vector_upsert(
        self,
        chat_id: str,
        telegram_user_id: int,
        entities: Dict[str, Any],
        intent: str,
        name: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call AI Microservice /conversation/vector endpoint to upsert user profile
        for matching.
        """
        payload = {
            "user_id": str(telegram_user_id),
            "data": {
                "name": name,
                "intent": intent,
                "entities": entities
            }
        }
        return await self._make_request(
            self.vector_url,
            payload,
            self.conversation_timeout,
            "AIService/VectorUpsert",
            request_id
        )
        
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
                telegram_user_id,
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
        telegram_user_id: int,
        action: str,
        target_user_id: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call matching service endpoint.
        """
        logger.info(f"Calling matching service for action {action} and user {telegram_user_id}")
        
        # Default fallback candidate
        candidate = {
            "name": "Alex (Fallback)",
            "reason": "We couldn't generate an exact specific match right now, but here's someone interested in connecting!",
            "rating": 4.5
        }
        
        no_matches_found = False
        
        try:
            payload = {
                "user_id": str(telegram_user_id),
                "top_k": 5
            }
            
            result = await self._make_request(
                f"{self.conversation_url}/conversation/matching",
                payload,
                # use conversation timeout since matching can involve AI latency
                self.conversation_timeout,
                "MatchingService/Match",
                request_id
            )
            
            candidates = []
            
            # Extract matches list flexibly
            matches = None
            if isinstance(result, list):
                matches = result
            elif isinstance(result, dict):
                matches = result.get("matches") if "matches" in result else (result if not result.get("status") else None)
            
            if matches is not None:
                if not matches:
                    no_matches_found = True
                else:
                    for match_data in matches:
                        match_user = match_data.get("user_id", f"User_{target_user_id}" if target_user_id else "Unknown User")
                        data = match_data.get("data", {})
                        
                        # Some versions of the endpoint return entities directly in data, while others nest it
                        entities = data.get("entities") or data
                        
                        interests = entities.get("interests", [])
                        skills = entities.get("skills", [])
                        goals = entities.get("goals", [])
                        location = entities.get("location", "")
                        role = entities.get("role", "")
                        
                        reason_parts = []
                        if role:
                            reason_parts.append(f"Role: {role.title()}")
                        if goals:
                            reason_parts.append(f"Goals: {', '.join(goals)}")
                        if interests:
                            reason_parts.append(f"Interests: {', '.join(interests)}")
                        if skills:
                            reason_parts.append(f"Skills: {', '.join(skills)}")
                        if location:
                            reason_parts.append(f"Location: {location}")
                            
                        reason_str = " | ".join(reason_parts) if reason_parts else "A great potential connection based on your request!"
                        score = match_data.get("score", 0.0)
                        
                        # Prioritize explicitly returned name
                        explicit_name = match_data.get("name")
                        if explicit_name:
                            display_name = explicit_name
                        else:
                            display_name = match_user.replace("user_", "User ") if match_user.startswith("user_") else match_user
                        
                        candidates.append({
                            "user_id": match_user,
                            "name": display_name,
                            "reason": reason_str,
                            "rating": round(score * 5.0, 1) if score else 5.0,
                            "match_percentage": round(score * 100) if score else 100
                        })
                    
                    if candidates:
                        candidate = candidates[0]  # Update fallback just in case
                        
                    if self.database:
                        await self.database.store_match_result(telegram_user_id, {"matches": matches})
            elif isinstance(result, dict) and result.get("match"):
                # Fallback to older format handling if necessary
                pass # Not removing the old entirely just in case, but keeping it simple
                    
        except Exception as e:
            logger.error(f"Error calling matching API: {e}")
        
        if no_matches_found:
            return {
                "type": "text",
                "content": "No perfect matches found at the moment! Try broadening your profile or checking back later. 🔍"
            }
            
        items_to_return = candidates if candidates else [candidate]
        
        # Helper function to find the next match in the list
        def get_next_match(current_target: Optional[str], items: list):
            if not current_target or not items:
                return items[0] if items else candidate
                
            # Try to find exactly where we currently are
            current_idx = -1
            for i, item in enumerate(items):
                # match the display name format we applied (e.g. "User 456" instead of "user_456")
                expected_name = current_target.replace("user_", "User ") if current_target.startswith("user_") else current_target
                if item["name"].lower() == expected_name.lower():
                    current_idx = i
                    break
                    
            # Wrap around or safely get the next item
            next_idx = (current_idx + 1) % len(items)
            return items[next_idx]
            
        next_candidate = get_next_match(target_user_id, items_to_return)

        if action == "CONNECT":
            return {
                "type": "match_list",
                "content": "🔍 **Suggested Match for You:**",
                "items": [next_candidate]  # Only show the 1st
            }
        elif action == "SKIP":
            return {
                "type": "match_list",
                "content": f"Skipped {target_user_id}. How about this match? 👇",
                "items": [next_candidate]
            }
        elif action == "ACCEPT":
            import re
            
            # Extract target user_id and optionally target_name if separated by |
            parts = target_user_id.split("|", 1) if target_user_id else []
            if not parts:
                return {"type": "text", "content": "❌ Invalid match request."}
                
            raw_target_id = parts[0]
            provided_target_name = parts[1] if len(parts) > 1 else raw_target_id
            
            m = re.search(r'\d+', raw_target_id)
            if m:
                target_tg_id = int(m.group())

                current_profile = await self.database.get_user_profile(telegram_user_id) if self.database else {}
                current_name = current_profile.get("name", "A connection")

                logger.info(f"🔗 [MATCH ACCEPTED] User {telegram_user_id} generated a native direct message portal to connect with {target_tg_id}.")

                # Fetch target's name so we can nicely link to it
                target_profile = await self.database.get_user_profile(target_tg_id) if self.database else {}
                target_name = target_profile.get("name", provided_target_name) if target_profile else provided_target_name

                # Native Telegram URL syntax for private chat
                my_link = f"[Click here to message {current_name}](tg://user?id={telegram_user_id})"
                their_link = f"[Click here to message {target_name}](tg://user?id={target_tg_id})"

                await self.send_direct_message(
                    target_tg_id,
                    f"🎉 **New Connection!**\n\n{current_name} is interested in connecting with you!\n\n"
                    f"You can now chat natively in a private Telegram DM:\n👉 {my_link}"
                )

                return {
                    "type": "text",
                    "content": f"✅ Connected with {target_name}!\n\n💬 **Private Chat Ready**\nYou can now start a direct Telegram chat with them here:\n👉 {their_link}"
                }
            else:
                return {
                    "type": "match_list",
                    "content": f"✅ Connected with {target_user_id}!\n\nHere is your next match 👇",
                    "items": [next_candidate]
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
        """
        logger.info(f"[MOCK] Calling notification service for type {notification_type}")
        
        return {
            "type": "text",
            "content": "🔔 Notification sent successfully",
            "success": True
        }

    async def send_direct_message(self, target_telegram_id: int, text: str) -> bool:
        """Helper to send out-of-bounds explicit direct messages to Telegram users."""
        import httpx
        try:
            url = f"https://api.telegram.org/bot{self.settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"chat_id": target_telegram_id, "text": text, "parse_mode": "Markdown"}, timeout=5.0)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send direct message to {target_telegram_id}: {e}")
            return False
