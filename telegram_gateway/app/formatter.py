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
    def format_photo_message(
        chat_id: int,
        photo_id: str,
        caption: Optional[str] = None,
        buttons: Optional[List[List[Dict[str, str]]]] = None,
        parse_mode: Optional[str] = "Markdown"
    ) -> Dict[str, Any]:
        """Format message with a photo."""
        payload = {
            "chat_id": chat_id,
            "photo": photo_id
        }
        if caption:
            payload["caption"] = caption
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
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
        
        # Ensure content is never empty as Telegram forbids empty messages
        if not content or str(content).strip() == "":
            content = "Sorry, I couldn't generate a response. Please try again."

        
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
                # Convert match list to multiple individual cards for better UX
                items = response.get("items", [])
                payloads = []
                
                # Intro message if no matches yet or as header
                if items:
                   payloads.append(self.format_text_message(chat_id, content, parse_mode=parse_mode))
                
                for item in items[:5]:  # Limit to 5 matches
                    name = item.get("name", "Unknown")
                    age = item.get("age")
                    gender = item.get("gender")
                    reason = item.get("reason", "")
                    rating = item.get("rating", 4.5)
                    match_percent = item.get("match_percentage")
                    photo_id = item.get("photo_id")
                    user_id = item.get("user_id", name)
                    
                    age_str = f" ({age})" if age else ""
                    gender_str = f" | {gender}" if gender else ""
                    
                    match_card_text = f"👤 **{name}{age_str}**{gender_str}\n"
                    if match_percent:
                        match_card_text += f"⭐ {rating}/5.0 • {match_percent}% Match\n"
                    else:
                        match_card_text += f"⭐ {rating}/5.0\n"
                    
                    match_card_text += f"\n{reason}"
                    
                    # Store name in the callback payload to avoid needing a DB lookup on accept
                    accept_payload = f"ACCEPT:{user_id}|{name}"[:64]
                    buttons = [[
                        {"text": "✅ Connect", "callback_data": accept_payload},
                        {"text": "⏭ Skip", "callback_data": f"SKIP:{user_id}"}
                    ]]
                    
                    if photo_id:
                        payloads.append(self.format_photo_message(chat_id, photo_id, caption=match_card_text, buttons=buttons, parse_mode=parse_mode))
                    else:
                        payloads.append(self.format_inline_keyboard(chat_id, match_card_text, buttons, parse_mode=parse_mode))
                
                if not payloads:
                    return self.format_text_message(chat_id, "No matches found right now. Try updating your preferences!", parse_mode=parse_mode)
                
                return payloads # Return the list of payloads
            
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
