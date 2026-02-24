"""Unit tests for response formatter."""
import pytest
from app.formatter import TelegramResponseFormatter


@pytest.fixture
def formatter():
    """Create formatter instance."""
    return TelegramResponseFormatter()


class TestTextFormatting:
    """Test text message formatting."""
    
    def test_format_simple_text(self, formatter):
        """Test formatting simple text message."""
        result = formatter.format_text_message(
            chat_id=12345,
            content="Hello, world!"
        )
        
        assert result["chat_id"] == 12345
        assert result["text"] == "Hello, world!"
        assert "parse_mode" not in result
    
    def test_format_text_with_html(self, formatter):
        """Test formatting text with HTML parse mode."""
        result = formatter.format_text_message(
            chat_id=12345,
            content="<b>Bold text</b>",
            parse_mode="HTML"
        )
        
        assert result["parse_mode"] == "HTML"


class TestInlineKeyboard:
    """Test inline keyboard formatting."""
    
    def test_format_inline_keyboard(self, formatter):
        """Test formatting message with inline keyboard."""
        buttons = [
            [{"text": "Button 1", "callback_data": "ACTION1"}],
            [{"text": "Button 2", "callback_data": "ACTION2"}]
        ]
        
        result = formatter.format_inline_keyboard(
            chat_id=12345,
            content="Choose an option:",
            buttons=buttons
        )
        
        assert result["chat_id"] == 12345
        assert result["text"] == "Choose an option:"
        assert "reply_markup" in result
        assert result["reply_markup"]["inline_keyboard"] == buttons


class TestMessageEdit:
    """Test message editing."""
    
    def test_format_edit_message_text_only(self, formatter):
        """Test formatting message edit without buttons."""
        result = formatter.format_edit_message(
            chat_id=12345,
            message_id=999,
            content="Updated text"
        )
        
        assert result["chat_id"] == 12345
        assert result["message_id"] == 999
        assert result["text"] == "Updated text"
        assert "reply_markup" not in result
    
    def test_format_edit_message_with_buttons(self, formatter):
        """Test formatting message edit with buttons."""
        buttons = [[{"text": "New Button", "callback_data": "NEW"}]]
        
        result = formatter.format_edit_message(
            chat_id=12345,
            message_id=999,
            content="Updated text",
            buttons=buttons
        )
        
        assert result["message_id"] == 999
        assert "reply_markup" in result
        assert result["reply_markup"]["inline_keyboard"] == buttons


class TestResponseFormatting:
    """Test formatting of internal service responses."""
    
    def test_format_text_response(self, formatter):
        """Test formatting text response type."""
        response = {
            "type": "text",
            "content": "This is a text response"
        }
        
        result = formatter.format_response(response, chat_id=12345)
        
        assert result["chat_id"] == 12345
        assert result["text"] == "This is a text response"
    
    def test_format_profile_response(self, formatter):
        """Test formatting profile response type."""
        response = {
            "type": "profile",
            "content": "User Profile:\nName: John\nAge: 25"
        }
        
        result = formatter.format_response(response, chat_id=12345)
        
        assert result["text"] == "User Profile:\nName: John\nAge: 25"
    
    def test_format_match_list_response(self, formatter):
        """Test formatting match list with buttons."""
        response = {
            "type": "match_list",
            "content": "Here are your matches:",
            "items": [
                {"name": "Alice", "reason": "Both like hiking"},
                {"name": "Bob", "reason": "Both interested in AI"}
            ]
        }
        
        result = formatter.format_response(response, chat_id=12345)
        
        assert "Alice" in result["text"]
        assert "Bob" in result["text"]
        assert "reply_markup" in result
        assert len(result["reply_markup"]["inline_keyboard"]) > 0
    
    def test_format_confirmation_response(self, formatter):
        """Test formatting confirmation response with buttons."""
        response = {
            "type": "confirmation",
            "content": "Are you sure?"
        }
        
        result = formatter.format_response(response, chat_id=12345)
        
        assert "reply_markup" in result
        buttons = result["reply_markup"]["inline_keyboard"]
        assert any("Confirm" in btn["text"] for row in buttons for btn in row)
        assert any("Cancel" in btn["text"] for row in buttons for btn in row)
    
    def test_format_unknown_response_type(self, formatter):
        """Test formatting unknown response type falls back to text."""
        response = {
            "type": "unknown_type",
            "content": "Some content"
        }
        
        result = formatter.format_response(response, chat_id=12345)
        
        # Should still work, falling back to text
        assert result["text"] == "Some content"
    
    def test_format_response_with_message_edit(self, formatter):
        """Test formatting response as message edit."""
        response = {
            "type": "text",
            "content": "Edited content"
        }
        
        result = formatter.format_response(
            response,
            chat_id=12345,
            message_id=999
        )
        
        assert result["message_id"] == 999
        assert result["text"] == "Edited content"


class TestSpecialMessages:
    """Test special message formatting."""
    
    def test_rate_limit_message(self, formatter):
        """Test rate limit message formatting."""
        result = formatter.format_rate_limit_message(chat_id=12345)
        
        assert result["chat_id"] == 12345
        assert "too fast" in result["text"].lower()
        assert "🙂" in result["text"]
    
    def test_error_message(self, formatter):
        """Test error message formatting."""
        result = formatter.format_error_message(chat_id=12345)
        
        assert result["chat_id"] == 12345
        assert "wrong" in result["text"].lower()
        assert "try again" in result["text"].lower()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_format_empty_match_list(self, formatter):
        """Test formatting match list with no items."""
        response = {
            "type": "match_list",
            "content": "No matches found",
            "items": []
        }
        
        result = formatter.format_response(response, chat_id=12345)
        
        assert result["text"] == "No matches found"
    
    def test_format_many_matches_limited(self, formatter):
        """Test formatting match list limits to 5 items."""
        response = {
            "type": "match_list",
            "content": "Your matches:",
            "items": [
                {"name": f"User{i}", "reason": f"Reason {i}"}
                for i in range(10)
            ]
        }
        
        result = formatter.format_response(response, chat_id=12345)
        
        # Should only show 5 matches
        assert "User0" in result["text"]
        assert "User4" in result["text"]
        # User5 and beyond should not be included
        assert "User9" not in result["text"]
