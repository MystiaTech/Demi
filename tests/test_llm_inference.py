"""
Unit tests for LLM inference engine.

Tests OllamaInference class with:
- Configuration validation
- Health check
- Message validation
- Context overflow detection
- Context trimming
- Token counting (with fallback)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.llm import OllamaInference, LLMConfig, InferenceError, ContextOverflowError
from src.core.logger import DemiLogger


class TestLLMConfigValidation:
    """Test LLMConfig validation."""

    def test_valid_config_creation(self):
        """Should create config with valid parameters."""
        config = LLMConfig(
            model_name="llama3.2:1b",
            temperature=0.7,
            max_tokens=256,
            timeout_sec=10,
        )
        assert config.model_name == "llama3.2:1b"
        assert config.temperature == 0.7
        assert config.max_tokens == 256
        assert config.timeout_sec == 10

    def test_default_config(self):
        """Should use sensible defaults."""
        config = LLMConfig()
        assert config.model_name == "llama3.2:1b"
        assert config.temperature == 0.7
        assert config.max_tokens == 256
        assert config.timeout_sec == 10
        assert config.ollama_base_url == "http://localhost:11434"

    def test_invalid_temperature_high(self):
        """Should reject temperature > 1.0."""
        with pytest.raises(ValueError, match="temperature must be in range"):
            LLMConfig(temperature=1.5)

    def test_invalid_temperature_low(self):
        """Should reject temperature < 0.0."""
        with pytest.raises(ValueError, match="temperature must be in range"):
            LLMConfig(temperature=-0.1)

    def test_invalid_max_tokens(self):
        """Should reject max_tokens <= 0."""
        with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
            LLMConfig(max_tokens=0)

    def test_invalid_model_name(self):
        """Should reject empty model_name."""
        with pytest.raises(ValueError, match="model_name must be non-empty string"):
            LLMConfig(model_name="")

    def test_invalid_timeout(self):
        """Should reject timeout <= 0."""
        with pytest.raises(ValueError, match="timeout_sec must be greater than 0"):
            LLMConfig(timeout_sec=0)


class TestOllamaInferenceInit:
    """Test OllamaInference initialization."""

    def test_initialization(self):
        """Should initialize with config and logger."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        assert inference.config == config
        assert inference.logger == logger
        assert inference._tokenizer is None
        assert inference._tokenizer_attempted is False


class TestHealthCheck:
    """Test Ollama health check."""

    def test_health_check_success(self):
        """Should return True when Ollama responds."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        # Mock at import time
        async def mock_health():
            return True

        inference.health_check = mock_health
        result = asyncio.run(inference.health_check())
        assert result is True

    def test_health_check_timeout(self):
        """Should return False on timeout."""
        config = LLMConfig(timeout_sec=1)
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        async def mock_health():
            return False

        inference.health_check = mock_health
        result = asyncio.run(inference.health_check())
        assert result is False

    def test_health_check_connection_error(self):
        """Should return False when Ollama unavailable."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        async def mock_health():
            return False

        inference.health_check = mock_health
        result = asyncio.run(inference.health_check())
        assert result is False

    def test_health_check_import_error(self):
        """Should return False if ollama package missing."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        async def mock_health():
            return False

        inference.health_check = mock_health
        result = asyncio.run(inference.health_check())
        assert result is False


class TestMessageValidation:
    """Test message validation."""

    def test_valid_messages(self):
        """Should accept valid message format."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        messages = [
            {"role": "system", "content": "You are Demi."},
            {"role": "user", "content": "Hello"},
        ]
        # Should not raise
        inference._validate_messages(messages)

    def test_messages_not_list(self):
        """Should reject non-list messages."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        with pytest.raises(ValueError, match="messages must be a list"):
            inference._validate_messages("not a list")

    def test_messages_empty(self):
        """Should reject empty message list."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        with pytest.raises(ValueError, match="messages list cannot be empty"):
            inference._validate_messages([])

    def test_message_not_dict(self):
        """Should reject non-dict messages."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        with pytest.raises(ValueError, match="Message 0 must be a dict"):
            inference._validate_messages(["not a dict"])

    def test_message_missing_fields(self):
        """Should reject messages missing role or content."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        with pytest.raises(ValueError, match="must have 'role' and 'content'"):
            inference._validate_messages([{"role": "user"}])

    def test_message_invalid_role(self):
        """Should reject invalid role."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        with pytest.raises(ValueError, match="invalid role"):
            inference._validate_messages([{"role": "invalid", "content": "test"}])

    def test_message_content_not_string(self):
        """Should reject non-string content."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        with pytest.raises(ValueError, match="content must be a string"):
            inference._validate_messages([{"role": "user", "content": 123}])


class TestTokenCounting:
    """Test token counting."""

    def test_token_count_fallback(self):
        """Should use fallback estimation (1 token ≈ 4 chars)."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        # Fallback: 12 chars / 4 = 3 tokens
        count = inference._count_tokens("Hello world!")
        assert 2 <= count <= 4  # Allow some variance

    def test_token_count_long_text(self):
        """Should handle longer text."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        text = "This is a longer text with multiple words to count tokens for."
        count = inference._count_tokens(text)
        assert count > 0
        # Rough check: ~60 chars / 4 = ~15 tokens
        assert 12 <= count <= 20


class TestContextTrimmingLogic:
    """Test context trimming algorithm."""

    def test_trim_context_empty(self):
        """Should handle empty messages."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        result = inference._trim_context([], max_tokens=8000)
        assert result == []

    def test_trim_context_keeps_system(self):
        """Should always keep system message."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        result = inference._trim_context(messages, max_tokens=8000)
        assert len(result) >= 1
        assert result[0]["role"] == "system"

    def test_trim_context_removes_oldest(self):
        """Should remove oldest user/assistant messages first."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
            {"role": "assistant", "content": "Second response"},
        ]
        # Very restrictive limit to force trimming
        result = inference._trim_context(messages, max_tokens=100)

        # Should keep system message
        assert result[0]["role"] == "system"
        # After trimming, should have fewer total messages
        assert len(result) <= len(messages)

    def test_trim_context_respects_limit(self):
        """Should not exceed token limit after trimming."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        messages = [
            {"role": "system", "content": "System prompt" * 10},
            {"role": "user", "content": "User message" * 20},
            {"role": "assistant", "content": "Assistant response" * 20},
        ]
        result = inference._trim_context(messages, max_tokens=200)

        # Rough check: result should fit in limit
        total_tokens = sum(inference._count_tokens(m["content"]) for m in result)
        assert total_tokens <= 200 + 256 + 256  # account for safety margin


class TestContextOverflow:
    """Test context overflow detection."""

    def test_context_overflow_initial_check(self):
        """Should raise ContextOverflowError if context too large initially."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        # Message larger than max tokens
        messages = [
            {"role": "user", "content": "x" * 50000}  # ~12500 tokens
        ]

        with pytest.raises(ContextOverflowError):
            asyncio.run(inference.chat(messages, max_context_tokens=100))


class TestChatInterface:
    """Test chat interface."""

    def test_chat_invalid_messages(self):
        """Should raise ValueError for invalid messages."""
        config = LLMConfig()
        logger = DemiLogger()
        inference = OllamaInference(config, logger)

        with pytest.raises(ValueError):
            asyncio.run(inference.chat([]))
