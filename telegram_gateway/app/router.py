"""
Table-driven routing for Telegram updates.
"""
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, TYPE_CHECKING
from enum import Enum

from .api_client import InternalAPIClient

if TYPE_CHECKING:
    from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    """Route types for different update handlers."""
    COMMAND = "command"
    CALLBACK = "callback"
    TEXT = "text"


class TelegramRouter:
    """Table-driven router for Telegram updates."""
    
    def __init__(self, api_client: InternalAPIClient, session_manager: 'SessionManager'):
        self.api_client = api_client
        self.session_manager = session_manager
        
        # Command routing table
        self.COMMAND_ROUTES: Dict[str, Callable] = {
            "/start": self._handle_start_command,
            "/help": self._handle_help_command,
            "/profile": self._handle_profile_command,
            "/generate": self._handle_generate_command,
            "/clear": self._handle_clear_command,
            "/connect": self._handle_connect_command,
            "/new": self._handle_new_command,
            "/matches": self._handle_matches_command,
            "/end": self._handle_end_command,
        }
        
        # Callback routing table
        self.CALLBACK_ROUTES: Dict[str, Callable] = {
            "CONNECT": self._handle_connect_callback,
            "ACCEPT": self._handle_accept_callback,
            "REJECT": self._handle_reject_callback,
            "SKIP": self._handle_skip_callback,
            "CONFIRM": self._handle_confirm_callback,
            "CANCEL": self._handle_cancel_callback,
            "PROFILE_EDIT": self._handle_profile_edit_callback,
            "VIEW_PROFILE": self._handle_view_profile_callback,
            "START_CHAT": self._handle_start_chat_callback,
            "CONNECTIONS": self._handle_connections_command,
            "matches_back": self._handle_matches_command,
            "GENDER": self._handle_gender_callback,
            "INTENT": self._handle_intent_callback,
            "LOCATION": self._handle_location_callback,
        }
    
    async def route_update(
        self,
        update: Dict[str, Any],
        chat_id: str,
        telegram_user_id: int,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        # ... (same as before) ...
        try:
            # Detect update type and route accordingly
            if "message" in update:
                message = update["message"]
                
                # Check for document upload (Resume)
                if "document" in message:
                    return await self._route_document(
                        message,
                        chat_id,
                        telegram_user_id,
                        request_id
                    )
                
                # Check for photo upload
                if "photo" in message:
                    return await self._route_photo(
                        message,
                        chat_id,
                        telegram_user_id,
                        request_id
                    )
                
                return await self._route_message(
                    message,
                    chat_id,
                    telegram_user_id,
                    request_id
                )
            
            elif "callback_query" in update:
                return await self._route_callback_query(
                    update["callback_query"],
                    chat_id,
                    telegram_user_id,
                    request_id
                )
            
            else:
                logger.warning(f"Unknown update type: {update.keys()}")
                return None
                
        except Exception as e:
            logger.error(f"Error routing update: {e}", exc_info=True)
            return None
    
    async def _route_message(
        self,
        message: Dict[str, Any],
        chat_id: str,
        telegram_user_id: int,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Route message updates."""
        text = message.get("text", "")
        
        # Check if it's a command
        if text.startswith("/"):
            command = text.split()[0].lower()
            
            # Allow /start, /profile, /help even if not onboarded
            is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
            if not is_onboarded and command not in ["/start", "/profile", "/help"]:
                return {
                    "type": "text", 
                    "content": "Please complete your profile first using `/profile` to access this command.",
                    "keyboard": [[{"text": "Set Profile"}]]
                }

            handler = self.COMMAND_ROUTES.get(command)
            
            if handler:
                logger.info(
                    f"Routing to command handler: {command}",
                    extra={"request_id": request_id, "command": command}
                )
                return await handler(
                    chat_id,
                    telegram_user_id,
                    text,
                    request_id
                )
            else:
                logger.warning(f"Unknown command: {command}")
                return {
                    "type": "text",
                    "content": f"Unknown command: {command}\n\nUse /help to see available commands."
                }
        
        # Regular text message -> Check State or Conversation Service
        logger.info(
            "Routing to conversation service",
            extra={"request_id": request_id, "route": "conversation"}
        )
        
        # New Matchmaking Logic Integration
        if text in ["Set Profile", "My Profile"]:
            # If user already exists, show profile, else start setup
            user_profile = await self.api_client.database.get_user_profile(telegram_user_id)
            if user_profile and user_profile.get("name"):
                return await self._handle_profile_command(chat_id, telegram_user_id, "/profile", request_id)
            else:
                 return await self._handle_profile_command(chat_id, telegram_user_id, "/profile setup", request_id)
        elif text == "Set Goal":
            return await self._handle_connect_command(chat_id, telegram_user_id, "/connect", request_id)
        elif text == "Find Matches":
            return await self._handle_matches_command(chat_id, telegram_user_id, "/matches", request_id)
        elif text == "My Connections":
            return await self._handle_connections_command(chat_id, telegram_user_id, "/connections", request_id)
            
        return await self._handle_text_message(
            chat_id,
            telegram_user_id,
            text,
            request_id
        )

    # ... (other methods) ...

    async def _handle_text_message(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle regular text messages."""
        # Check strict state
        state = await self.session_manager.get_persistent_state(telegram_user_id)
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        
        # If not onboarded, only allow if they are in a setup state
        is_in_setup = state and str(state).startswith("AWAITING_PROFILE_")
        if not is_onboarded and not is_in_setup:
             return {
                "type": "text",
                "content": "Please complete your profile first to start chatting with Milo! 🚀\n\nHit /profile to set it up.",
                "keyboard": [[{"text": "Set Profile"}]]
             }
        
        if state and str(state).startswith("IN_CHAT:"):
            target_tg_id = int(str(state).split(":")[1])
            
            # Identify current user's name
            current_profile = await self.api_client.database.get_user_profile(telegram_user_id) if getattr(self.api_client, "database", None) else {}
            current_name = current_profile.get("name", "Connection")
            
            # Proxy message to the other person dynamically
            logger.info(f"🔒 [CHAT ROOM PROXY] Sending message from {telegram_user_id} ({current_name}) -> To user {target_tg_id}")
            success = await self.api_client.send_direct_message(
                target_tg_id, 
                f"💬 **{current_name}:**\n{text}"
            )
            
            if not success:
               logger.warning(f"🔒 [CHAT ROOM ERROR] Failed to deliver from {telegram_user_id} to {target_tg_id}")
               return {"type": "text", "content": "Failed to send message to the chat room. The other user may have blocked the bot."}
               
            return None # We handled the message successfully as a transparent proxy.
            
        if state == "AWAITING_CONNECT_PERSON":
            # State transition to second question, save first answer in state string
            import base64
            # Using base64 to safely store arbitrary text in the state string
            encoded_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            await self.session_manager.set_persistent_state(telegram_user_id, f"AWAITING_CONNECT_EXPLORE:{encoded_text}")
            return {
                "type": "text",
                "content": "would you like to explore something new together?"
            }

        if state and str(state).startswith("AWAITING_CONNECT_EXPLORE:"):
            # State completed, clear it
            encoded_text = str(state).split(":", 1)[1]
            import base64
            try:
                first_answer = base64.b64decode(encoded_text.encode('utf-8')).decode('utf-8')
            except Exception:
                first_answer = ""
                
            await self.session_manager.set_persistent_state(telegram_user_id, None)
            
            combined_text = f"Kind of person looking for: {first_answer}\nWant to explore new things together?: {text}"
            
            # Hit interpret to extract and store their preferences
            return await self.api_client.call_ai_interpret(
                chat_id,
                telegram_user_id,
                combined_text,
                request_id
            )
            
        if state == "AWAITING_NEW_RESPONSE":
            # State completed, clear it
            await self.session_manager.set_persistent_state(telegram_user_id, None)
            
            # Hit interpret to extract and merge their preferences
            return await self.api_client.call_ai_interpret(
                chat_id,
                telegram_user_id,
                text,
                request_id,
                merge_preferences=True
            )
            
        if state == "AWAITING_PROFILE_NAME":
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_profile_field(telegram_user_id, "name", text)
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_AGE")
            return {"type": "text", "content": "Nice to meet you! **(Step 2/6)**\n\nHow old are you?"}

        if state == "AWAITING_PROFILE_AGE":
            # Validation for age
            try:
                age_val = int(text)
                if age_val < 13 or age_val > 120:
                    return {"type": "text", "content": "Please enter a realistic age (between 13 and 120)."}
            except ValueError:
                return {"type": "text", "content": "Please enter a valid number for your age."}
                
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_profile_field(telegram_user_id, "age", str(age_val))
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_GENDER")
            return {
                "type": "text",
                "content": "Got it! **(Step 3/6)**\n\nWhat is your **Gender**?",
                "buttons": [
                    [{"text": "Male", "callback_data": "GENDER:Male"}, {"text": "Female", "callback_data": "GENDER:Female"}],
                    [{"text": "Non-binary", "callback_data": "GENDER:Non-binary"}, {"text": "Prefer not to say", "callback_data": "GENDER:Other"}]
                ]
            }

        if state == "AWAITING_PROFILE_GENDER":
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_profile_field(telegram_user_id, "gender", text)
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_INTERESTS")
            return {
                "type": "text",
                "content": "Got it! **(Step 4/6)**\n\nTell us more about your interests or stuff that you are into these days (Coding, Startups, Music, Reading, etc.)"
            }

        if state == "AWAITING_PROFILE_INTERESTS":
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_profile_field(telegram_user_id, "interests", text)
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_INTENT")
            return {
                "type": "text",
                "content": "Got it! **(Step 5/6)**\n\nWhat are you hoping to find through Milo right now?\n(New friends, Build / startup buddy, Event buddy, People in my niche, Just exploring)",
                "buttons": [
                    [{"text": "🤝 New friends", "callback_data": "INTENT:New friends"}, {"text": "💻 Build / startup buddy", "callback_data": "INTENT:Build buddy"}],
                    [{"text": "🎉 Event buddy", "callback_data": "INTENT:Event buddy"}, {"text": "🎯 People in my niche", "callback_data": "INTENT:Niche people"}],
                    [{"text": "✨ Just exploring", "callback_data": "INTENT:Exploring"}]
                ]
            }

        if state == "AWAITING_PROFILE_INTENT":
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_preferences(telegram_user_id, {"connection_intent": text})
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_LOCATION")
            return {
                "type": "text", 
                "content": "Got it! **(Step 6/6)**\n\nWhich part of Singapore are you usually around?",
                "buttons": [
                    [{"text": "North", "callback_data": "LOCATION:North"}, {"text": "South", "callback_data": "LOCATION:South"}],
                    [{"text": "East", "callback_data": "LOCATION:East"}, {"text": "West", "callback_data": "LOCATION:West"}]
                ]
            }

        if state == "AWAITING_PROFILE_LOCATION":
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_profile_field(telegram_user_id, "location", text)
                await self.api_client.database.set_onboarding_status(telegram_user_id, True)
                
            await self.session_manager.set_persistent_state(telegram_user_id, None)
            return {
                "type": "text",
                "content": "✨ **Profile complete!**\n\nNow you can use 'Find Matches' to see who's around! 🚀",
                "keyboard": [
                    [{"text": "My Profile"}, {"text": "Find Matches"}]
                ]
            }
            
        if state == "AWAITING_INTENT_INPUT":
            # Clear state
            await self.session_manager.set_persistent_state(telegram_user_id, None)
            
            # 1. Interpret to extract and save their preferences into DB
            await self.api_client.call_ai_interpret(
                chat_id,
                telegram_user_id,
                f"I am looking for: {text}",
                request_id
            )
            
            # 2. Explicitly save as connection_intent so /matches recognizes it
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_preferences(telegram_user_id, {"connection_intent": text})
            
            # 2. Confirm update and IMMEDIATELY show matches
            return await self.api_client.call_matching(
                chat_id,
                telegram_user_id,
                "CONNECT",
                None,
                request_id
            )
            
        if state == "AWAITING_CONNECT_MATCHES":
            # Legacy cleanup just in case any user is stuck in it
            await self.session_manager.set_persistent_state(telegram_user_id, None)
            
        db = getattr(self.api_client, "database", None)
        if db:
            count = await db.increment_message_count(telegram_user_id)
            if count % 3 == 0:
                async def _bg_extract():
                    try:
                        await self.api_client.call_ai_interpret(
                            chat_id, telegram_user_id, text, request_id,
                            merge_preferences=True
                        )
                    except Exception as e:
                        logger.error(f"Background personality extraction failed: {e}")
                asyncio.create_task(_bg_extract())

        return await self.api_client.call_ai_chat(
            chat_id,
            telegram_user_id,
            text,
            request_id
        )

    async def _handle_connect_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /connect command - purely to set/update goal."""
        # Check onboarding
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        if not is_onboarded:
            return {
                "type": "text",
                "content": "Please complete your profile first by clicking 'Set Profile'.",
                "keyboard": [[{"text": "Set Profile"}]]
            }

        # Extract everything after the /connect command
        query = text.lower().replace("/connect", "").strip()
        
        if query:
            # 1. Interpret to save preferences
            await self.api_client.call_ai_interpret(
                chat_id,
                telegram_user_id,
                message_text=query,
                request_id=request_id
            )
            
            # 2. Explicitly save as connection_intent
            if getattr(self.api_client, "database", None):
                await self.api_client.database.update_user_preferences(telegram_user_id, {"connection_intent": query})
            
            # 3. IMMEDIATELY show matches for this query
            return await self.api_client.call_matching(
                chat_id,
                telegram_user_id,
                "CONNECT",
                None,
                request_id
            )
        else:
            # Ask the user what they are looking for
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_INTENT_INPUT")
            return {
                 "type": "text",
                 "content": "✨ **What are you looking for right now?**\n\n(e.g., 'baking buddy', 'startup partner', 'fellow designer')\n\nOnce updated, Milo will find people who match your request! 🚀"
            }

    async def _handle_new_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /new command."""
        # Check onboarding
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        if not is_onboarded:
            return {
                "type": "text",
                "content": "Please complete your profile first by clicking 'Set Profile'.",
                "keyboard": [[{"text": "Set Profile"}]]
            }
            
        # Extract everything after the /new command
        query = text.lower().replace("/new", "").strip()
        
        if query:
            # They provided preferences right in the command so interpret it directly
            return await self.api_client.call_ai_interpret(
                chat_id,
                telegram_user_id,
                message_text=query,
                request_id=request_id,
                merge_preferences=True
            )
        else:
            # Ask the user what they are looking for so they reply next
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_NEW_RESPONSE")
            return {
                 "type": "text",
                 "content": "➕ **Add new connection preferences!**\n\n"
                            "What else are you looking for right now?\n"
                            "(Your existing preferences will be kept intact.)\n\n"
                            "Reply to this message with your new preferences!"
            }
    
    async def _route_callback_query(
        self,
        callback_query: Dict[str, Any],
        chat_id: str,
        telegram_user_id: int,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Route callback query updates."""
        callback_data = callback_query.get("data", "")
        
        # Parse callback data (format: "ACTION:param")
        parts = callback_data.split(":", 1)
        action = parts[0]
        param = parts[1] if len(parts) > 1 else None
        
        handler = self.CALLBACK_ROUTES.get(action)
        
        if handler:
            logger.info(
                f"Routing to callback handler: {action}",
                extra={"request_id": request_id, "action": action}
            )
            return await handler(
                chat_id,
                telegram_user_id,
                param,
                request_id
            )
        else:
            logger.warning(f"Unknown callback action: {action}")
            return {
                "type": "text",
                "content": f"Unknown action: {action}"
            }
    
    # Command Handlers
    
    async def _handle_start_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /start command."""
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        
        profile_btn = "My Profile" if is_onboarded else "Set Profile"
        keyboard = [
            [{"text": "My Profile"}, {"text": "Find Matches"}]
        ]
        
        content = (
            "Hey, I’m Milo ☕️\n\n"
            "I’m here to help you find people you’ll actually click with through shared interests, intentions, and real-life events.\n\n"
            "Think: gym buddy, study buddy, event buddy, hobby friend - whatever fits where you’re at right now.\n\n"
            "I’ll get to know you a little first so I can suggest the right people, communities, and events for you.\n\n"
            "Your profile stays private - nothing is shown publicly.\n\n"
            "Join our announcement channel to keep in touch with the changes we bring to Milo - \n\n"
            "First, let’s build your profile. Hit /profile command to set up your profile"
        )
            
        return {
            "type": "text",
            "content": content,
            "keyboard": keyboard
        }
    
    async def _handle_help_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /help command."""
        return await self.api_client.call_user_profile(
            telegram_user_id,
            "/help",
            request_id,
            chat_id=chat_id
        )
    
    async def _handle_profile_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /profile command."""
        # Check if user wants a new setup
        if "setup" in text.lower():
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_NAME")
            return {
                "type": "text", 
                "content": "Let’s build your Milo profile 👋\n"
                           "I’ll keep this quick. Your answers will stay private and help me suggest better people, communities, and events.\n\n"
                           "First - what should I call you?"
            }
            
        # Get profile from DB
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        if not is_onboarded:
            await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_NAME")
            return {
                "type": "text", 
                "content": "Let’s build your Milo profile 👋\n"
                           "I’ll keep this quick. Your answers will stay private and help me suggest better people, communities, and events.\n\n"
                           "First - what should I call you?"
            }
            
        # Build Profile Card
        profile = await self.api_client.database.get_user_profile(telegram_user_id)
        if not profile:
            return {"type": "text", "content": "Error finding profile."}

        name = profile.get("name", "N/A")
        age = profile.get("age", "N/A")
        gender = profile.get("gender", "N/A")
        interests = profile.get("interests", "N/A")
        location = profile.get("location", "N/A")
        content = f"👤 **Your Profile**\n\n**Name:** {name}\n**Age:** {age}\n**Gender:** {gender}\n**Interests:** {interests}\n**Location:** {location}\n"
        
        # Add personality summary if available
        personality = await self.api_client.database.get_personality_profile(telegram_user_id)
        if personality:
            intent = personality.get("connection_intent")
            if intent:
                content += f"\n🎯 **Current Goal:** {intent}\n"
                
        content += "\nTo update your profile, click the button below or type `/profile setup`."
        
        return {
            "type": "text",
            "content": content,
            "buttons": [
                [{"text": "📝 Edit Profile", "callback_data": "PROFILE_EDIT"}],
                [{"text": "🔗 View My Connections", "callback_data": "CONNECTIONS"}]
            ]
        }
    
    async def _handle_profile_edit_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle PROFILE_EDIT callback."""
        await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_NAME")
        return {
            "type": "text",
            "content": "Let’s build your Milo profile 👋\n"
                       "I’ll keep this quick. Your answers will stay private and help me suggest better people, communities, and events.\n\n"
                       "First - what should I call you?"
        }
    
    async def _handle_generate_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /generate command."""
        # Check onboarding
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        if not is_onboarded:
            return {
                "type": "text",
                "content": "Please complete your profile first by clicking 'Set Profile'.",
                "keyboard": [[{"text": "Set Profile"}]]
            }
            
        # Strip command to get prompt
        prompt = text.replace("/generate", "", 1).strip()
        
        if not prompt:
            return {
                "type": "text",
                "content": "Please provide a prompt. Example: /generate a story about a cat."
            }
            
        return await self.api_client.call_ai_generate(
            prompt,
            request_id
        )

    async def _handle_clear_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /clear command."""
        return await self.api_client.call_user_profile(
            telegram_user_id,
            "/clear",
            request_id,
            chat_id=chat_id
        )

    async def _handle_end_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /end command to exit a chat room."""
        state = await self.session_manager.get_persistent_state(telegram_user_id)
        if state and str(state).startswith("IN_CHAT:"):
            target_tg_id = int(str(state).split(":")[1])
            logger.info(f"🚪 [CHAT ROOM CLOSED] User {telegram_user_id} explicitly left chat room with {target_tg_id}.")
            
            # Break locks
            await self.session_manager.set_persistent_state(telegram_user_id, None)
            
            target_state = await self.session_manager.get_persistent_state(target_tg_id)
            if target_state and str(target_state) == f"IN_CHAT:{telegram_user_id}":
                await self.session_manager.set_persistent_state(target_tg_id, None)
                # Notify them
                await self.api_client.send_direct_message(
                    target_tg_id,
                    "🚪 The other user has left the chat room. You can now use normal bot commands."
                )
            
            return {
                "type": "text",
                "content": "🚪 You have successfully left the private chat room."
            }
            
        return {
            "type": "text",
            "content": "You are not currently in a private chat room."
        }
        

    async def _handle_matches_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /matches command - ONLY show new discovery cards."""
        # Check onboarding
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        if not is_onboarded:
            return {
                "type": "text",
                "content": "Please complete your profile first by clicking 'Set Profile'.",
                "keyboard": [[{"text": "Set Profile"}]]
            }
            
        # Immediately trigger discovery flow
        return await self.api_client.call_matching(
            chat_id,
            telegram_user_id,
            "CONNECT",
            None,
            request_id
        )

    async def _handle_connections_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /connections command - show existing connections and requests."""
        # Check onboarding
        is_onboarded = await self.api_client.database.get_onboarding_status(telegram_user_id)
        if not is_onboarded:
            return {
                "type": "text",
                "content": "Please complete your profile first.",
                "keyboard": [[{"text": "Set Profile"}]]
            }

        incoming = await self.api_client.database.get_incoming_requests(telegram_user_id)
        outgoing = await self.api_client.database.get_outgoing_requests(telegram_user_id)
        all_connections = await self.api_client.database.get_all_connections(telegram_user_id)
        
        if not incoming and not outgoing and not all_connections:
            return {
                "type": "text",
                "content": "No connections found yet. Try 'Find Matches' to search for new people! 🔍",
                "keyboard": [
                    [{"text": "My Profile"}, {"text": "Find Matches"}]
                ]
            }
            
        content = "🔗 **Your Connections & Requests**\n\n"
        buttons = []
        
        if all_connections:
            content += "🤝 **Established Connections:**\n"
            for conn in all_connections:
                other_name = conn['other_name']
                other_id = conn['other_id']
                content += f"• **{other_name}**\n"
                buttons.append([
                    {"text": f"👤 Profile: {other_name}", "callback_data": f"VIEW_PROFILE:{other_id}"},
                    {"text": f"💬 Chat: {other_name}", "callback_data": f"START_CHAT:{other_id}"}
                ])
            content += "\n"

        if incoming:
            content += "📩 **Incoming Requests:**\n"
            for req in incoming:
                from_name = req.get("from_name", "Someone")
                from_id = req.get("from_user_id")
                content += f"• **{from_name}** wants to connect\n"
                buttons.append([
                    {"text": f"✅ Accept {from_name}", "callback_data": f"ACCEPT:{from_id}"},
                    {"text": f"❌ Reject {from_name}", "callback_data": f"REJECT:{from_id}"}
                ])
            
        if outgoing:
            content += "📤 **Outgoing Requests:**\n"
            for req in outgoing:
                to_name = req.get("to_name", "Someone")
                to_id = req.get("to_user_id")
                content += f"• Sent to **{to_name}** ({req['status']})\n"
                
        return {
            "type": "text",
            "content": content,
            "buttons": buttons if buttons else None,
            "keyboard": [
                [{"text": "My Profile"}],
                [{"text": "Find Matches"}, {"text": "My Connections"}]
            ]
        }

    async def _handle_view_profile_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle VIEW_PROFILE callback."""
        if not param:
            return {"type": "text", "content": "Error: Missing user ID."}
            
        try:
            target_id = int(param)
        except ValueError:
            return {"type": "text", "content": "Error: Invalid user ID."}
            
        # Get target profile
        profile = await self.api_client.database.get_user_profile(target_id)
        if not profile:
            return {"type": "text", "content": "Error: Could not find user profile."}
            
        # Get personality/preferences
        personality = await self.api_client.database.get_personality_profile(target_id)
        
        name = profile.get("name", "N/A")
        interests = profile.get("interests", "N/A")
        location = profile.get("location", "N/A")
        region = profile.get("region", "N/A")
        
        content = f"👤 **Profile: {name}**\n\n"
        content += f"**Interests:** {interests}\n"
        content += f"**Location:** {location}\n"
        content += f"**Region:** {region}\n"
        
        if personality:
            intent = personality.get("connection_intent")
            if intent:
                content += f"🎯 **Looking for:** {intent}\n"
            
            # Show other fields if they exist
            if "skills" in personality and personality["skills"]:
                content += f"🛠 **Skills:** {', '.join(personality['skills']) if isinstance(personality['skills'], list) else personality['skills']}\n"
            if "goals" in personality and personality["goals"]:
                content += f"🚀 **Goals:** {', '.join(personality['goals']) if isinstance(personality['goals'], list) else personality['goals']}\n"

        # Check connection status to provide relevant buttons
        status = await self.api_client.database.get_connection_status(telegram_user_id, target_id)
        
        buttons = []
        if status == "accepted":
            buttons.append([{"text": f"💬 Start Chat with {name}", "callback_data": f"START_CHAT:{target_id}"}])
        elif status == "pending":
            # Check direction
            incoming = await self.api_client.database.get_incoming_requests(telegram_user_id)
            is_incoming = any(req["from_user_id"] == target_id for req in incoming)
            if is_incoming:
                buttons.append([
                    {"text": "✅ Accept", "callback_data": f"ACCEPT:{target_id}"},
                    {"text": "❌ Reject", "callback_data": f"REJECT:{target_id}"}
                ])
            else:
                content += "\n(Waiting for their response...)"
        else:
            # Not connected or other status
            buttons.append([{"text": "🤝 Request Connection", "callback_data": f"CONNECT:{target_id}"}])
            
        buttons.append([{"text": "📋 Back to Matches", "callback_data": "matches_back"}]) # We'll need to handle this back button

        return {
            "type": "text",
            "content": content,
            "buttons": buttons if buttons else None
        }

    async def _handle_start_chat_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle START_CHAT callback."""
        if not param:
            return {"type": "text", "content": "Error: Missing user ID."}
            
        try:
            target_id = int(param)
        except ValueError:
            return {"type": "text", "content": "Error: Invalid user ID."}
            
        # Verify connection status
        status = await self.api_client.database.get_connection_status(telegram_user_id, target_id)
        if status != "accepted":
            return {"type": "text", "content": "You can only chat with established connections."}
            
        # Get target profile for name
        profile = await self.api_client.database.get_user_profile(target_id)
        name = profile.get("name", "User") if profile else "User"
        
        # Set state to IN_CHAT
        await self.session_manager.set_persistent_state(telegram_user_id, f"IN_CHAT:{target_id}")
        
        # Notify user they've entered the chat
        return {
            "type": "text",
            "content": f"🔒 **Private Chat Room with {name}**\n\nYour messages will now be sent directly to {name}.\n\nType `/end` to leave the chat and return to the main menu."
        }
    
    async def _route_document(
        self,
        message: Dict[str, Any],
        chat_id: str,
        telegram_user_id: int,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Route document/file uploads."""
        document = message.get("document", {})
        file_name = document.get("file_name", "unknown_file")
        mime_type = document.get("mime_type", "")
        
        logger.info(
            f"Received document: {file_name} ({mime_type})",
            extra={"request_id": request_id, "file": file_name}
        )
        
        # In a real system, we'd download the file here using document["file_id"]
        # For now, we mock the upload process by sending a special command to the profile service
        
        return await self.api_client.call_user_profile(
            telegram_user_id,
            f"FILE:{file_name}",
            request_id,
            chat_id=chat_id
        )

    # Text Message Handler
    

    
    # Callback Query Handlers
    
    async def _handle_intent_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle INTENT selection callback."""
        if getattr(self.api_client, "database", None):
            await self.api_client.database.update_user_preferences(telegram_user_id, {"connection_intent": param or "Exploring"})
        
        await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_LOCATION")
        return {
            "type": "text", 
            "content": "Got it! **(Step 6/6)**\n\nWhich part of Singapore are you usually around?",
            "buttons": [
                [{"text": "North", "callback_data": "LOCATION:North"}, {"text": "South", "callback_data": "LOCATION:South"}],
                [{"text": "East", "callback_data": "LOCATION:East"}, {"text": "West", "callback_data": "LOCATION:West"}]
            ]
        }

    async def _handle_location_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle Singapore LOCATION selection callback."""
        if getattr(self.api_client, "database", None):
            await self.api_client.database.update_user_profile_field(telegram_user_id, "location", param or "Singapore")
            await self.api_client.database.set_onboarding_status(telegram_user_id, True)
            
        await self.session_manager.set_persistent_state(telegram_user_id, None)
        return {
            "type": "text",
            "content": "✨ **Profile complete!**\n\nNow you can use 'Find Matches' to see who's around! 🚀",
            "keyboard": [
                [{"text": "My Profile"}],
                [{"text": "Find Matches"}, {"text": "View Matches"}]
            ]
        }

    async def _handle_gender_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle GENDER selection callback."""
        if getattr(self.api_client, "database", None):
            await self.api_client.database.update_user_profile_field(telegram_user_id, "gender", param or "Other")
        
        await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_PROFILE_INTERESTS")
        return {
            "type": "text", 
            "content": "Got it! **(Step 4/6)**\n\nTell us more about your interests or stuff that you are into these days (Coding, Startups, Music, Reading, etc.)"
        }

    async def _route_photo(
        self,
        message: Dict[str, Any],
        chat_id: str,
        telegram_user_id: int,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Route photo uploads."""
        # Extract file_id from the largest photo
        photos = message.get("photo", [])
        if not photos:
            return None
            
        photo_id = photos[-1]["file_id"]
        
        if getattr(self.api_client, "database", None):
            await self.api_client.database.update_user_profile_field(telegram_user_id, "photo_id", photo_id)
            
        return {
            "type": "text",
            "content": "📸 **Photo updated!**"
        }

    async def _handle_connect_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle CONNECT callback."""
        return await self.api_client.call_matching(
            chat_id,
            telegram_user_id,
            "CONNECT",
            param,
            request_id
        )
    
    async def _handle_accept_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle ACCEPT callback."""
        if not param: return None
        # Extract target user_id (the requester)
        try:
            target_id = int(param.split('|')[0])
        except (ValueError, IndexError):
            return {"type": "text", "content": "Error: Invalid request parameter."}
            
        success = await self.api_client.database.update_connection_status(target_id, telegram_user_id, "accepted")
        if not success:
            return {"type": "text", "content": "Failed to update match status."}
            
        # Notify requester
        user = await self.api_client.database.get_user_profile(telegram_user_id)
        name = user.get("name", "Someone") if user else "Someone"
        
        try:
            await self.api_client.send_direct_message(
                target_id,
                f"🎉 **Match Accepted!**\n\nYou are now connected with **{name}**!"
            )
        except Exception:
            pass # Non-critical if notification fails
            
        return {"type": "text", "content": f"✅ Match accepted! You are now connected with the requester."}
    
    async def _handle_reject_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle REJECT callback."""
        if not param: return None
        try:
            target_id = int(param.split('|')[0])
        except (ValueError, IndexError):
            return None
            
        await self.api_client.database.update_connection_status(target_id, telegram_user_id, "rejected")
        
        # Notify the person who was rejected
        rejecter_profile = await self.api_client.database.get_user_profile(telegram_user_id)
        rejecter_name = rejecter_profile.get("name", "Someone")
        
        await self.api_client.send_direct_message(
            target_id,
            f"Milo: Sorry, **{rejecter_name}** has declined your connection request for now. Don't worry, there are plenty of other people to connect with! 🚀"
        )
        
        return {"type": "text", "content": "❌ Request declined."}
    
    async def _handle_skip_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle SKIP callback."""
        return await self.api_client.call_matching(
            chat_id,
            telegram_user_id,
            "SKIP",
            param,
            request_id
        )
    
    async def _handle_confirm_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle CONFIRM callback."""
        return {
            "type": "text",
            "content": "✅ Confirmed!"
        }
    
    async def _handle_cancel_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle CANCEL callback."""
        return {
            "type": "text",
            "content": "❌ Cancelled"
        }
