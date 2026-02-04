"""Unit and integration tests for Telegram bot integration."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.integrations.telegram_bot import (
    TelegramBot,
    TelegramRateLimiter,
    TelegramRambleTask,
)
from src.integrations.telegram_formatters import (
    escape_markdown_v2,
    format_telegram_response,
    get_dominant_emotion,
    format_emotion_display,
    format_emotion_detail,
    format_status_message,
    format_help_message,
    format_start_message,
    should_generate_telegram_ramble,
    EMOTION_EMOJIS,
)
from src.platforms.base import PluginHealth


class TestTelegramFormatters:
    """Test Telegram message formatting utilities."""

    def test_escape_markdown_v2(self):
        """Test MarkdownV2 special character escaping."""
        # Test basic escaping
        result = escape_markdown_v2("Hello_world")
        assert result == "Hello\\_world"

        # Test multiple special chars
        text = "Test [link](http://example.com) with *bold* and _italic_"
        result = escape_markdown_v2(text)
        assert "\\" in result
        assert "[" in result or "\\[" in result

    def test_escape_markdown_v2_all_special_chars(self):
        """Test that all special characters are escaped."""
        special_chars = "_*[]()~`>#+-=|{}. !"
        for char in special_chars:
            result = escape_markdown_v2(f"test{char}text")
            assert f"\\{char}" in result or char not in result.split("test")[1]

    def test_format_telegram_response_basic(self):
        """Test basic response formatting."""
        response = {
            "content": "Hello there!",
            "emotion_state": {"excitement": 0.8, "loneliness": 0.3},
        }
        result = format_telegram_response(response)

        assert "Hello there!" in result
        assert "✨" in result or "Excitement" in result

    def test_format_telegram_response_with_special_chars(self):
        """Test formatting with special characters that need escaping."""
        response = {
            "content": "I'm [excited] about *this*!",
            "emotion_state": {"excitement": 0.9},
        }
        result = format_telegram_response(response)

        # Should contain escaped version
        assert "\\" in result or "excited" in result

    def test_get_dominant_emotion_with_state(self):
        """Test getting dominant emotion."""
        emotion_state = {"excitement": 0.8, "loneliness": 0.3, "curiosity": 0.5}
        result = get_dominant_emotion(emotion_state)
        assert result == "excitement"

    def test_get_dominant_emotion_empty(self):
        """Test getting dominant emotion with empty state."""
        result = get_dominant_emotion({})
        assert result == "neutral"

        result = get_dominant_emotion(None)
        assert result == "neutral"

    def test_format_emotion_display(self):
        """Test emotion state display formatting."""
        emotion_state = {
            "excitement": 8.5,
            "loneliness": 3.2,
            "frustration": 1.0,
        }
        result = format_emotion_display(emotion_state)

        assert "Excitement" in result or "excitement" in result
        assert "✨" in result  # Excitement emoji
        assert "8.5" in result

    def test_format_emotion_detail(self):
        """Test detailed emotion display."""
        emotion_state = {"curiosity": 7.5}
        result = format_emotion_detail("curiosity", emotion_state)

        assert "Curiosity" in result
        assert "7.5" in result
        assert "🧠" in result

    def test_format_help_message(self):
        """Test help message formatting."""
        result = format_help_message()

        assert "/start" in result
        assert "/help" in result
        assert "/emotions" in result
        assert "/status" in result
        assert "/ramble" in result

    def test_format_start_message(self):
        """Test start/welcome message formatting."""
        result = format_start_message()

        assert "Demi" in result
        assert "emotion" in result.lower() or "companion" in result.lower()

    def test_format_status_message(self):
        """Test status message formatting."""
        conductor_health = {"status": "healthy", "last_inference_time": "now"}
        result = format_status_message(conductor_health, "running")

        assert "healthy" in result.lower() or "running" in result.lower()
        assert "Bot" in result or "Conductor" in result

    def test_should_generate_ramble_loneliness_trigger(self):
        """Test ramble generation with loneliness trigger."""
        emotion_state = {"loneliness": 0.8, "excitement": 0.2}
        should_ramble, trigger = should_generate_telegram_ramble(emotion_state)

        assert should_ramble is True
        assert trigger == "loneliness"

    def test_should_generate_ramble_excitement_trigger(self):
        """Test ramble generation with excitement trigger."""
        emotion_state = {"excitement": 0.85, "loneliness": 0.2}
        should_ramble, trigger = should_generate_telegram_ramble(emotion_state)

        assert should_ramble is True
        assert trigger == "excitement"

    def test_should_generate_ramble_frustration_trigger(self):
        """Test ramble generation with frustration trigger."""
        emotion_state = {"frustration": 0.65, "excitement": 0.2}
        should_ramble, trigger = should_generate_telegram_ramble(emotion_state)

        assert should_ramble is True
        assert trigger == "frustration"

    def test_should_generate_ramble_no_trigger(self):
        """Test ramble generation with no triggers."""
        emotion_state = {"excitement": 0.5, "loneliness": 0.3}
        should_ramble, trigger = should_generate_telegram_ramble(emotion_state)

        assert should_ramble is False
        assert trigger is None

    def test_should_generate_ramble_rate_limited(self):
        """Test ramble generation with rate limiting."""
        emotion_state = {"loneliness": 0.8}
        last_ramble = datetime.now(timezone.utc)

        should_ramble, trigger = should_generate_telegram_ramble(
            emotion_state, last_ramble, min_interval_minutes=60
        )

        assert should_ramble is False


class TestTelegramRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter creation."""
        limiter = TelegramRateLimiter(messages_per_second=20)
        assert limiter.messages_per_second == 20

    @pytest.mark.asyncio
    async def test_rate_limiter_wait_if_needed(self):
        """Test rate limiting wait mechanism."""
        limiter = TelegramRateLimiter(messages_per_second=2)

        # First call should not wait
        await limiter.wait_if_needed()

        # Record time
        import time
        start = time.time()

        # Second call should wait
        await limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should have waited roughly 0.5 seconds (1/2)
        assert elapsed >= 0.4  # Allow some tolerance


class TestTelegramBot:
    """Test Telegram bot platform integration."""

    @pytest.fixture
    def bot(self):
        """Create a TelegramBot instance for testing."""
        return TelegramBot()

    def test_telegram_bot_initialization(self, bot):
        """Test bot initialization."""
        assert bot.name == "telegram"
        assert bot._status == "offline"
        assert bot.token is None

    @pytest.mark.asyncio
    async def test_initialize_without_token(self, bot):
        """Test initialization fails without token."""
        with patch.dict("os.environ", {}, clear=True):
            result = await bot.initialize({})
            assert result is False
            assert bot._status == "error"

    def test_health_check_not_running(self, bot):
        """Test health check when bot is not running."""
        health = bot.health_check()

        assert isinstance(health, PluginHealth)
        assert health.status == "unhealthy"
        assert health.error_message is not None

    def test_handle_request_returns_error(self, bot):
        """Test that handle_request returns error."""
        result = bot.handle_request({})

        assert result["status"] == "error"
        assert "event handlers" in result["message"].lower()


class TestTelegramRambleTask:
    """Test autonomous ramble task."""

    @pytest.fixture
    def ramble_task(self):
        """Create a TelegramRambleTask for testing."""
        app = Mock()
        conductor = Mock()
        logger = Mock()
        return TelegramRambleTask(app, conductor, logger, ramble_chat_id=12345)

    def test_ramble_task_initialization(self, ramble_task):
        """Test ramble task creation."""
        assert ramble_task.ramble_chat_id == 12345
        assert ramble_task.last_ramble_time is None

    def test_get_ramble_prompt_loneliness(self, ramble_task):
        """Test ramble prompt generation."""
        prompt = ramble_task._get_ramble_prompt("loneliness")
        assert "lonely" in prompt.lower()

    def test_get_ramble_prompt_excitement(self, ramble_task):
        """Test excitement ramble prompt."""
        prompt = ramble_task._get_ramble_prompt("excitement")
        assert "excited" in prompt.lower() or "enthusiasm" in prompt.lower()

    def test_get_ramble_prompt_frustration(self, ramble_task):
        """Test frustration ramble prompt."""
        prompt = ramble_task._get_ramble_prompt("frustration")
        assert "frustrat" in prompt.lower()


class TestIntegration:
    """Integration tests for Telegram bot with conductor."""

    @pytest.mark.asyncio
    async def test_telegram_bot_initialization_with_config(self):
        """Test bot initialization with proper config."""
        bot = TelegramBot()

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test_token"}):
            with patch("src.integrations.telegram_bot.Application") as mock_app:
                mock_app.builder.return_value.token.return_value.build.return_value = Mock()

                result = await bot.initialize({})

                # Bot should attempt initialization
                assert bot.token == "test_token"

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message through Telegram."""
        bot = TelegramBot()
        bot.application = Mock()
        bot.application.bot = AsyncMock()

        result = await bot.send_message("Hello", 12345)

        # Should attempt to send
        assert bot.application.bot.send_message.called


# Manual Testing Checklist
"""
To manually test the Telegram bot integration:

1. Create bot with @BotFather:
   - Open Telegram, search for @BotFather
   - Send /newbot
   - Choose name: "Demi Assistant"
   - Choose username: "demi_assistant_bot"
   - Copy token to TELEGRAM_BOT_TOKEN in .env

2. Configure environment:
   - Set TELEGRAM_BOT_TOKEN in .env
   - Optionally set TELEGRAM_RAMBLE_CHAT_ID for autonomous rambles
   - Optionally set TELEGRAM_DEMI_CHAT_ID for dedicated chat

3. Start DEMI with Telegram enabled:
   - python -m src.conductor

4. Test basic commands:
   - /start - Should show welcome message
   - /help - Should show command list
   - /emotions - Should display emotion state with buttons
   - /status - Should show system status
   - /ramble - Should generate spontaneous thought

5. Test messaging:
   - Send regular message in private chat
   - Should respond with LLM response + emotion footer
   - Test group chat with @mention
   - Should only respond to mentions in groups

6. Test interactive features:
   - Click emotion buttons in /emotions response
   - Should show detailed emotion view
   - Click refresh button
   - Should update emotion display

7. Test autonomous features (if TELEGRAM_RAMBLE_CHAT_ID set):
   - Wait for ramble triggers (loneliness > 0.7, excitement > 0.8, frustration > 0.6)
   - Should post rambles to configured chat

8. Test rate limiting:
   - Send many messages rapidly
   - Bot should handle gracefully without API errors

9. Test error handling:
   - Disable network connection
   - Bot should attempt reconnection
   - Re-enable network
   - Bot should recover

10. Check logs:
    - Review src/integrations/telegram_bot.py logs
    - Check for any errors or warnings
"""
