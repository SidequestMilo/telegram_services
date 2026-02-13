"""Unit tests for webhook parsing and routing."""
import pytest
from app.router import TelegramRouter
from app.api_client import InternalAPIClient
from app.config import Settings


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        TELEGRAM_BOT_TOKEN="test_token",
        TELEGRAM_WEBHOOK_SECRET="test_secret",
        REDIS_HOST="localhost"
    )


@pytest.fixture
def api_client(settings):
    """Create API client for testing."""
    return InternalAPIClient(settings)


@pytest.fixture
def router(api_client):
    """Create router for testing."""
    return TelegramRouter(api_client)


class TestWebhookParsing:
    """Test webhook update parsing."""
    
    def test_extract_message_info(self):
        """Test extracting info from message update."""
        from app.main import extract_user_info
        
        update = {
            "message": {
                "from": {"id": 12345},
                "chat": {"id": 67890},
                "text": "Hello"
            }
        }
        
        user_id, chat_id, message_id = extract_user_info(update)
        
        assert user_id == 12345
        assert chat_id == 67890
        assert message_id is None
    
    def test_extract_callback_info(self):
        """Test extracting info from callback query update."""
        from app.main import extract_user_info
        
        update = {
            "callback_query": {
                "from": {"id": 12345},
                "message": {
                    "chat": {"id": 67890},
                    "message_id": 999
                },
                "data": "ACCEPT:user_123"
            }
        }
        
        user_id, chat_id, message_id = extract_user_info(update)
        
        assert user_id == 12345
        assert chat_id == 67890
        assert message_id == 999


class TestRouting:
    """Test router mapping."""
    
    @pytest.mark.asyncio
    async def test_command_routing(self, router):
        """Test command is routed correctly."""
        update = {
            "message": {
                "from": {"id": 12345},
                "chat": {"id": 67890},
                "text": "/start"
            }
        }
        
        response = await router.route_update(
            update,
            "user_12345",
            12345,
            "test_request_id"
        )
        
        assert response is not None
        assert response["type"] == "text"
        assert "Welcome" in response["content"]
    
    @pytest.mark.asyncio
    async def test_text_routing(self, router):
        """Test text message is routed to conversation service."""
        update = {
            "message": {
                "from": {"id": 12345},
                "chat": {"id": 67890},
                "text": "Hello there"
            }
        }
        
        response = await router.route_update(
            update,
            "user_12345",
            12345,
            "test_request_id"
        )
        
        assert response is not None
        assert response["type"] == "text"
        # Should echo the message in mock
        assert "Hello there" in response["content"]
    
    @pytest.mark.asyncio
    async def test_callback_routing(self, router):
        """Test callback query is routed correctly."""
        update = {
            "callback_query": {
                "from": {"id": 12345},
                "message": {
                    "chat": {"id": 67890},
                    "message_id": 999
                },
                "data": "CONNECT"
            }
        }
        
        response = await router.route_update(
            update,
            "user_12345",
            12345,
            "test_request_id"
        )
        
        assert response is not None
        assert response["type"] == "match_list"
        assert "items" in response
    
    @pytest.mark.asyncio
    async def test_unknown_command(self, router):
        """Test unknown command returns helpful message."""
        update = {
            "message": {
                "from": {"id": 12345},
                "chat": {"id": 67890},
                "text": "/unknown"
            }
        }
        
        response = await router.route_update(
            update,
            "user_12345",
            12345,
            "test_request_id"
        )
        
        assert response is not None
        assert "Unknown command" in response["content"]
        assert "/help" in response["content"]


class TestRouterMapping:
    """Test router table mappings."""
    
    def test_command_routes_defined(self, router):
        """Test all expected commands are in routing table."""
        expected_commands = ["/start", "/help", "/profile"]
        
        for cmd in expected_commands:
            assert cmd in router.COMMAND_ROUTES
            assert callable(router.COMMAND_ROUTES[cmd])
    
    def test_callback_routes_defined(self, router):
        """Test all expected callbacks are in routing table."""
        expected_callbacks = ["CONNECT", "ACCEPT", "REJECT", "SKIP", "CONFIRM", "CANCEL"]
        
        for cb in expected_callbacks:
            assert cb in router.CALLBACK_ROUTES
            assert callable(router.CALLBACK_ROUTES[cb])
    
    def test_no_duplicate_routes(self, router):
        """Test routing tables have no duplicate entries."""
        command_keys = list(router.COMMAND_ROUTES.keys())
        callback_keys = list(router.CALLBACK_ROUTES.keys())
        
        assert len(command_keys) == len(set(command_keys))
        assert len(callback_keys) == len(set(callback_keys))
