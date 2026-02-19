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
            "/matches": self._handle_matches_command,
        }
        
        # Callback routing table
        self.CALLBACK_ROUTES: Dict[str, Callable] = {
            "CONNECT": self._handle_connect_callback,
            "ACCEPT": self._handle_accept_callback,
            "REJECT": self._handle_reject_callback,
            "SKIP": self._handle_skip_callback,
            "CONFIRM": self._handle_confirm_callback,
            "CANCEL": self._handle_cancel_callback,
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
        
        if state == "AWAITING_CONNECT_RESPONSE":
            await self.session_manager.set_persistent_state(telegram_user_id, None)  # Clear state
            return await self.api_client.call_ai_interpret(
                chat_id,
                telegram_user_id,
                text,
                request_id
            )
            
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
        """Handle /connect command."""
        # Set persistent state
        await self.session_manager.set_persistent_state(telegram_user_id, "AWAITING_CONNECT_RESPONSE")
        
        return {
             "type": "text",
             "content": "🤝 **Let's Connect!**\n\n"
                        "Tell me a bit about what you are looking for?\n"
                        "(e.g., 'Looking for a co-founder', 'Someone to hike with', 'Coding buddy')\n\n"
                        "Reply to this message and I'll find the best people for you!"
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
        return await self.api_client.call_user_profile(
            telegram_user_id,
            "/start",
            request_id,
            chat_id=chat_id
        )
    
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
        return await self.api_client.call_user_profile(
            telegram_user_id,
            "/profile",
            request_id,
            chat_id=chat_id
        )
    
    async def _handle_generate_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /generate command."""
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
        

    async def _handle_matches_command(
        self,
        chat_id: str,
        telegram_user_id: int,
        text: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle /matches command."""
        return await self.api_client.call_user_profile(
            telegram_user_id,
            "/matches",
            request_id,
            chat_id=chat_id
        )
    
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
            "CONNECT",
            None,
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
        return await self.api_client.call_matching(
            chat_id,
            "ACCEPT",
            param,
            request_id
        )
    
    async def _handle_reject_callback(
        self,
        chat_id: str,
        telegram_user_id: int,
        param: Optional[str],
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle REJECT callback."""
        return await self.api_client.call_matching(
            chat_id,
            "REJECT",
            param,
            request_id
        )
    
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
