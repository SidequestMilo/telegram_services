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
        """
        if not self.client:
            logger.error("HTTP client not initialized")
            return None
        
        for attempt in range(2):
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
                if attempt == 1:
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
                
                error_message = f"{service_name} HTTP error: {e.response.status_code}"
                if e.response.status_code >= 400:
                    error_message += f" - {e.response.text}"
                logger.error(
                    error_message,
                    extra={
                        "request_id": request_id,
                        "service": service_name,
                        "status_code": e.response.status_code,
                        "response_text": e.response.text
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
        """Call AI Microservice /chat endpoint."""
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
        """Call AI Microservice /generate endpoint."""
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
        """Request session reset (clear history)."""
        return {
            "type": "system_action",
            "action": "reset_session",
            "content": "chat history cleared! we can start fresh now"
        }

    async def call_ai_interpret(
        self,
        chat_id: str,
        telegram_user_id: int,
        message_text: str,
        request_id: str,
        merge_preferences: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Call AI Microservice /conversation/interpret endpoint."""
        payload = {
            "chat_id": chat_id,
            "user_id": str(telegram_user_id),
            "model_id": self.settings.AI_MODEL_ID,
            "message": message_text,
            "context": {"type": "partner_matching"},
            "max_tokens": self.settings.AI_MAX_TOKENS,
            "temperature": self.settings.AI_TEMPERATURE,
            "timeout_seconds": self.settings.AI_TIMEOUT_SECONDS
        }
        
        result = await self._make_request(
            f"{self.conversation_url}/conversation/interpret",
            payload,
            self.conversation_timeout,
            "AIService/Interpret",
            request_id
        )
        
        if result:
             logger.info(f"AI Interpretation result: {result}")
             
             if self.database:
                 entities = result.get("entities")
                 if entities is not None:
                     merged_entities = entities
                     if merge_preferences:
                         existing = await self.database.get_user_preferences(telegram_user_id) or {}
                         merged_entities = dict(existing)
                         for k, v in entities.items():
                             if isinstance(v, list):
                                 existing_list = existing.get(k, [])
                                 if isinstance(existing_list, list):
                                     merged_list = existing_list.copy()
                                     for item in v:
                                         if item not in merged_list:
                                             merged_list.append(item)
                                     merged_entities[k] = merged_list
                                 else:
                                     merged_entities[k] = v
                             elif isinstance(v, str) and v:
                                 merged_entities[k] = v
                             else:
                                 merged_entities[k] = v

                     await self.database.update_user_preferences(telegram_user_id, merged_entities)
                     
                     user_profile = await self.database.get_user_profile(telegram_user_id) or {}
                     name = user_profile.get("name", f"User {telegram_user_id}")
                     intent = result.get("intent", "find_match")
                     
                     await self.call_vector_upsert(
                         chat_id=chat_id,
                         telegram_user_id=telegram_user_id,
                         entities=merged_entities,
                         intent=intent,
                         name=name,
                         request_id=request_id
                     )
             
             reply_text = result.get("reply")
             
             if not reply_text:
                 logger.info("No explicit 'reply' found from interpret endpoint, using default text")
                 reply_text = "got it! your preferences have been updated.\n\nuse /matches to see your matches"
             else:
                 if "/matches" not in reply_text:
                     reply_text += "\n\nuse /matches to see your matches"
             return {
                 "type": "text",
                 "content": reply_text
             }
        
        return {
            "type": "text",
            "content": "hmm, something went wrong. try again?"
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
        """Call AI Microservice /conversation/vector endpoint to upsert user profile for matching."""
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
        """Call user profile service."""
        logger.info(f"Calling user profile service for command {command}")
        
        if command == "/start":
            return {
                "type": "text",
                "content": "hey! i'm milo, your matchmaking companion\n\n"
                          "i help you find your perfect match by getting to know who you really are "
                          "- through conversation, not forms.\n\n"
                          "**here's what i can do:**\n"
                          "/profile - set up or view your profile\n"
                          "/connect - tell me what you're looking for\n"
                          "/new - add more preferences\n"
                          "/matches - see your match suggestions\n"
                          "/clear - start fresh\n"
                          "/help - see all commands\n\n"
                          "start by setting up your profile with /profile, or just start chatting with me!",
                "internal_user_id": f"user_{telegram_user_id}",
                "new_user": True
            }
        elif command == "/help":
            return {
                "type": "text",
                "content": "**available commands:**\n\n"
                          "/start - welcome message\n"
                          "/profile - view or set up your profile\n"
                          "/connect - share what you're looking for in a partner\n"
                          "/new - add more preferences to your profile\n"
                          "/matches - see your match suggestions\n"
                          "/clear - clear conversation history\n"
                          "/generate <prompt> - ai generation\n\n"
                          "or just message me naturally - the more we chat, the better i understand your vibe!"
            }
        elif command == "/profile":
            return {
                "type": "text",
                "content": "**your profile**\n\n"
                          "here are your details. use /connect to share what you're looking for!\n\n"
                          f"Status: Active\nID: {telegram_user_id}",
                "internal_user_id": f"user_{telegram_user_id}"
            }
        elif command == "/matches":
            return {
                "type": "match_list",
                "content": "**your matches**",
                "items": []
            }
        elif command == "/connect":
             return await self.call_ai_interpret(
                chat_id,
                telegram_user_id,
                message_text="I want to find a partner match",
                request_id=request_id
            )
        elif command == "/clear":
             return await self.call_ai_clear(
                chat_id,
                request_id
            )
        elif command.startswith("FILE:"):
             return {
                "type": "text",
                "content": "i appreciate the effort, but i don't need files! just chat with me and i'll learn about you naturally"
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
        """Call matching service endpoint."""
        logger.info(f"Calling matching service for action {action} and user {telegram_user_id}")
        
        candidate = {
            "name": "Unknown",
            "reason": "no matches available yet - keep chatting with me to build your profile!",
            "rating": 0
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
                self.conversation_timeout,
                "MatchingService/Match",
                request_id
            )
            
            candidates = []
            
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
                        
                        entities = data.get("entities") or data
                        
                        interests = entities.get("interests", [])
                        values = entities.get("values", [])
                        personality = entities.get("personality_traits", [])
                        lifestyle = entities.get("lifestyle", [])
                        humor = entities.get("humor_style", "")
                        location = entities.get("location", "")
                        
                        reason_parts = []
                        if interests:
                            reason_parts.append(f"Interests: {', '.join(interests[:3])}")
                        if values:
                            reason_parts.append(f"Values: {', '.join(values[:3])}")
                        if personality:
                            reason_parts.append(f"Personality: {', '.join(personality[:3])}")
                        if lifestyle:
                            reason_parts.append(f"Lifestyle: {', '.join(lifestyle[:3])}")
                        if humor:
                            reason_parts.append(f"Humor: {humor}")
                        if location:
                            reason_parts.append(f"Location: {location}")
                            
                        reason_str = " | ".join(reason_parts) if reason_parts else "a potential match based on your vibe!"
                        score = match_data.get("score", 0.0)
                        
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
                        candidate = candidates[0]
                        
                    if self.database:
                        await self.database.store_match_result(telegram_user_id, {"matches": matches})
            elif isinstance(result, dict) and result.get("match"):
                pass
                    
        except Exception as e:
            logger.error(f"Error calling matching API: {e}")
        
        if no_matches_found:
            return {
                "type": "text",
                "content": "no perfect matches found yet! keep chatting with me to build your profile, or check back later"
            }
            
        items_to_return = candidates if candidates else [candidate]
        
        def get_next_match(current_target: Optional[str], items: list):
            if not current_target or not items:
                return items[0] if items else candidate
                
            current_idx = -1
            current_target_clean = current_target.replace("user_", "")
            
            for i, item in enumerate(items):
                item_id_clean = str(item.get("user_id", "")).replace("user_", "")
                item_name_clean = item.get("name", "")
                
                if item_id_clean.lower() == current_target_clean.lower() or item_name_clean.lower() == current_target.lower():
                    current_idx = i
                    break
                    
            next_idx = (current_idx + 1) % len(items)
            return items[next_idx]
            
        next_candidate = get_next_match(target_user_id, items_to_return)

        if action == "CONNECT":
            display_items = candidates[:5] if candidates else [next_candidate]
            return {
                "type": "match_list",
                "content": "**your top matches:**",
                "items": display_items
            }
        elif action == "SKIP":
            import random
            emojis = ["👇", "👀", "✨", "🚀", "💡", "🌟", "🔥"]
            emoji = random.choice(emojis)
            return {
                "type": "match_list",
                "content": f"skipped! how about this one? {emoji}",
                "items": [next_candidate]
            }
        elif action == "ACCEPT":
            import re
            
            parts = target_user_id.split("|", 1) if target_user_id else []
            if not parts:
                return {"type": "text", "content": "invalid match request."}
                
            raw_target_id = parts[0]
            provided_target_name = parts[1] if len(parts) > 1 else raw_target_id
            
            m = re.search(r'\d+', raw_target_id)
            if m:
                target_tg_id = int(m.group())

                current_profile = await self.database.get_user_profile(telegram_user_id) if self.database else {}
                current_name = current_profile.get("name", "A connection")
                current_username = current_profile.get("username")

                logger.info(f"[MATCH ACCEPTED] User {telegram_user_id} connecting with {target_tg_id}.")

                if self.database:
                    await self.database.record_connection(telegram_user_id, target_tg_id, "accepted")

                target_profile = await self.database.get_user_profile(target_tg_id) if self.database else {}
                target_name = target_profile.get("name", provided_target_name) if target_profile else provided_target_name
                target_username = target_profile.get("username") if target_profile else None

                my_url = f"https://t.me/{current_username}" if current_username else f"tg://user?id={telegram_user_id}"
                their_url = f"https://t.me/{target_username}" if target_username else f"tg://user?id={target_tg_id}"

                target_message = f"<b>New Match!</b>\n\n{current_name} wants to connect with you!\n\nStart chatting:"
                target_markup = None
                if current_username:
                    target_markup = {"inline_keyboard": [[{"text": f"Message {current_name}", "url": my_url}]]}
                else:
                    target_message += f'\n<a href="{my_url}">Message {current_name}</a>'

                await self.send_direct_message(
                    target_tg_id,
                    target_message,
                    parse_mode="HTML",
                    reply_markup=target_markup
                )

                await self.call_notification(
                    str(target_tg_id),
                    "new_match",
                    request_id
                )

                current_message = f"connected with {target_name}!\n\n<b>Chat Ready</b>\nStart a direct Telegram chat:"
                current_buttons = None
                
                if target_username:
                    current_buttons = [[{"text": f"Message {target_name}", "url": their_url}]]
                else:
                    current_message += f'\n<a href="{their_url}">Message {target_name}</a>'

                response_dict = {
                    "type": "text",
                    "content": current_message,
                    "parse_mode": "HTML"
                }
                
                if current_buttons:
                    response_dict["buttons"] = current_buttons
                    
                return response_dict
            else:
                return {
                    "type": "match_list",
                    "content": f"connected with {target_user_id}! here's your next match:",
                    "items": [next_candidate]
                }
        
        return {
            "type": "text",
            "content": f"action '{action}' recorded.",
            "success": True
        }
    
    async def call_notification(
        self,
        internal_user_id: str,
        notification_type: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Call notification service."""
        payload = {
            "user_id": internal_user_id,
            "notification_type": notification_type,
            "request_id": request_id
        }
        return await self._make_request(
            self.notification_url,
            payload,
            self.notification_timeout,
            "NotificationService/Notify",
            request_id
        )

    async def send_direct_message(self, target_telegram_id: int, text: str, parse_mode: str = "Markdown", reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """Helper to send out-of-bounds explicit direct messages to Telegram users."""
        import httpx
        try:
            url = f"https://api.telegram.org/bot{self.settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": target_telegram_id, "text": text, "parse_mode": parse_mode}
            if reply_markup:
                payload["reply_markup"] = reply_markup
                
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=5.0)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send direct message to {target_telegram_id}: {e}")
            return False
