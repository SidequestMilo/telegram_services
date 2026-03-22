"""
Response formatter for converting internal responses to Telegram format.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class TelegramResponseFormatter:
    """Formats internal service responses into Telegram API payloads."""
    
    @staticmethod
    def format_text_message(
        chat_id: int,
        content: str,
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format simple text message.
        
        Args:
            chat_id: Telegram chat ID
            content: Message text
            parse_mode: Telegram parse mode (Markdown or HTML)
            
        Returns:
            Telegram sendMessage payload
        """
        payload = {
            "chat_id": chat_id,
            "text": content
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return payload
    
    @staticmethod
    def format_inline_keyboard(
        chat_id: int,
        content: str,
        buttons: List[List[Dict[str, str]]],
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format message with inline keyboard.
        
        Args:
            chat_id: Telegram chat ID
            content: Message text
            buttons: 2D array of button objects
            parse_mode: Telegram parse mode
            
        Returns:
            Telegram sendMessage payload with inline keyboard
        """
        payload = {
            "chat_id": chat_id,
            "text": content,
            "reply_markup": {
                "inline_keyboard": buttons
            }
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return payload

    @staticmethod
    def format_reply_keyboard(
        chat_id: int,
        content: str,
        buttons: List[List[Dict[str, Any]]],
        resize_keyboard: bool = True,
        one_time_keyboard: bool = False,
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format message with reply keyboard (persistent buttons).
        """
        payload = {
            "chat_id": chat_id,
            "text": content,
            "reply_markup": {
                "keyboard": buttons,
                "resize_keyboard": resize_keyboard,
                "one_time_keyboard": one_time_keyboard
            }
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return payload
    
    @staticmethod
    def format_edit_message(
        chat_id: int,
        message_id: int,
        content: str,
        buttons: Optional[List[List[Dict[str, str]]]] = None,
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format message edit (for callback queries).
        
        Args:
            chat_id: Telegram chat ID
            message_id: Original message ID to edit
            content: New message text
            buttons: Optional new inline keyboard
            parse_mode: Telegram parse mode
            
        Returns:
            Telegram editMessageText payload
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": content
        }
        
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        
        return payload
    
    def format_response(
        self,
        response: Dict[str, Any],
        chat_id: int,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Convert internal service response to Telegram format.
        
        Args:
            response: Internal service response
            chat_id: Telegram chat ID
            message_id: Optional message ID (for edits)
            
        Returns:
            Telegram API payload
        """
        response_type = response.get("type", "text")
        content = response.get("content", "No response")
        
        try:
            parse_mode = response.get("parse_mode", "Markdown")
            
            if response_type == "text":
                buttons = response.get("buttons")
                keyboard = response.get("keyboard")
                if message_id:
                    return self.format_edit_message(chat_id, message_id, content, buttons, parse_mode=parse_mode)
                if keyboard:
                    return self.format_reply_keyboard(chat_id, content, keyboard, parse_mode=parse_mode)
                if buttons:
                    return self.format_inline_keyboard(chat_id, content, buttons, parse_mode=parse_mode)
                return self.format_text_message(chat_id, content, parse_mode=parse_mode)
            
            elif response_type == "profile":
                return self.format_text_message(chat_id, content, parse_mode=parse_mode)
            
            elif response_type == "match_list":
                # Convert match list to inline keyboard
                items = response.get("items", [])
                buttons = []
                
                for item in items[:5]:  # Limit to 5 matches
                    name = item.get("name", "Unknown")
                    reason = item.get("reason", "")
                    rating = item.get("rating", 4.5)
                    match_percent = item.get("match_percentage")
                    
                    # Shorten reason to be more concise
                    shortened_reason_parts = []
                    for part in reason.split(" | "):
                        if ": " in part:
                            category, items_str = part.split(": ", 1)
                            items = [i.strip() for i in items_str.split(",")]
                            if len(items) > 3:
                                shortened_reason_parts.append(f"{category}: {', '.join(items[:3])}, etc...")
                            else:
                                shortened_reason_parts.append(part)
                        else:
                            shortened_reason_parts.append(part)
                            
                    short_reason = " | ".join(shortened_reason_parts)
                    
                    # Add match card text
                    if match_percent is not None:
                        content += f"\n\n👤 **{name}** (⭐ {rating}/5.0 • {match_percent}% Match)\n{short_reason}"
                    else:
                        content += f"\n\n👤 **{name}** (⭐ {rating}/5.0)\n{short_reason}"
                    
                    user_id = item.get("user_id", name)
                    
                    # Add action buttons for each match side-by-side
                    
                    # Store name in the callback payload to avoid needing a DB lookup on accept
                    # Callback data hard limit is 64 bytes total
                    accept_payload = f"ACCEPT:{user_id}|{name}"[:64]
                    
                    buttons.append([
                        {
                            "text": f"✅ Connect",
                            "callback_data": accept_payload
                        },
                        {
                            "text": f"⏭ Skip",
                            "callback_data": f"SKIP:{user_id}"
                        }
                    ])
                
                if message_id:
                    return self.format_edit_message(chat_id, message_id, content, buttons, parse_mode=parse_mode)
                return self.format_inline_keyboard(chat_id, content, buttons, parse_mode=parse_mode)
            
            elif response_type == "confirmation":
                buttons = [
                    [
                        {"text": "✅ Confirm", "callback_data": "CONFIRM"},
                        {"text": "❌ Cancel", "callback_data": "CANCEL"}
                    ]
                ]
                
                if message_id:
                    return self.format_edit_message(chat_id, message_id, content, buttons, parse_mode=parse_mode)
                return self.format_inline_keyboard(chat_id, content, buttons, parse_mode=parse_mode)
            
            else:
                # Fallback to text
                logger.warning(f"Unknown response type: {response_type}, falling back to text")
                if message_id:
                    return self.format_edit_message(chat_id, message_id, content, parse_mode=parse_mode)
                return self.format_text_message(chat_id, content, parse_mode=parse_mode)
                
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            error_content = "Sorry, there was an error formatting the response."
            if message_id:
                return self.format_edit_message(chat_id, message_id, error_content)
            return self.format_text_message(chat_id, error_content)
    
    @staticmethod
    def format_rate_limit_message(chat_id: int) -> Dict[str, Any]:
        """Format rate limit exceeded message."""
        return {
            "chat_id": chat_id,
            "text": "You're sending messages too fast, please slow down 🙂"
        }
    
    @staticmethod
    def format_error_message(chat_id: int) -> Dict[str, Any]:
        """Format generic error message."""
        return {
            "chat_id": chat_id,
            "text": "Something went wrong on our side. Please try again in a minute."
        }
