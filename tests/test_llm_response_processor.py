"""
Tests for ResponseProcessor.

Validates text cleaning, interaction logging, emotional state updates,
and response persistence.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, MagicMock, patch

from src.llm.response_processor import ResponseProcessor, ProcessedResponse
from src.emotion.models import EmotionalState
from src.emotion.interactions import InteractionHandler, InteractionType
from src.core.logger import DemiLogger


@pytest.fixture
def logger():
    """Create a test logger."""
    return DemiLogger()


@pytest.fixture
def interaction_handler():
    """Create an interaction handler."""
    return InteractionHandler()


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def response_processor(logger, mock_db_session, interaction_handler):
    """Create a ResponseProcessor instance."""
    return ResponseProcessor(
        logger=logger,
        db_session=mock_db_session,
        interaction_handler=interaction_handler,
    )


@pytest.fixture
def baseline_emotional_state():
    """Create a baseline emotional state."""
    return EmotionalState(
        loneliness=0.5,
        excitement=0.5,
        frustration=0.5,
        jealousy=0.5,
        vulnerability=0.5,
        confidence=0.5,
        curiosity=0.5,
        affection=0.5,
        defensiveness=0.5,
    )


class TestCleanText:
    """Test text cleaning functionality."""

    def test_clean_text_strips_whitespace(self, response_processor):
        """Whitespace should be stripped from text."""
        input_text = "  hello world  \n\n  "
        output = response_processor._clean_text(input_text)
        assert output == "hello world"
        assert output.startswith("h")
        assert output.endswith("d")

    def test_clean_text_removes_special_tokens(self, response_processor):
        """Special tokens should be removed."""
        input_text = "hello <|end|> world"
        output = response_processor._clean_text(input_text)
        assert output == "hello world"
        assert "<|end|>" not in output

    def test_clean_text_removes_eot_token(self, response_processor):
        """EOT token should be removed."""
        input_text = "response <|eot_id|> end"
        output = response_processor._clean_text(input_text)
        assert "<|eot_id|>" not in output
        assert "response" in output
        assert "end" in output

    def test_clean_text_normalizes_newlines(self, response_processor):
        """Multiple newlines should be normalized to single."""
        input_text = "line1\n\n\nline2"
        output = response_processor._clean_text(input_text)
        assert "\n\n\n" not in output
        assert "line1" in output and "line2" in output

    def test_clean_text_empty_returns_fallback(self, response_processor):
        """Empty text should return fallback."""
        output = response_processor._clean_text("")
        assert output == "I forgot what I was thinking... try again?"

    def test_clean_text_only_tokens_returns_fallback(self, response_processor):
        """Text with only special tokens should return fallback."""
        input_text = "   <|end|>   <|eot_id|>   "
        output = response_processor._clean_text(input_text)
        assert output == "I forgot what I was thinking... try again?"

    def test_clean_text_complex_example(self, response_processor):
        """Complex example with mixed artifacts."""
        input_text = "  Hey! <|eot_id|>  I'm happy\n\n\n  to help!  <|end|>  "
        output = response_processor._clean_text(input_text)
        assert output.strip() == "Hey! I'm happy\n\nto help!"
        assert "<|eot_id|>" not in output
        assert "<|end|>" not in output


class TestTokenCounting:
    """Test token counting."""

    def test_count_tokens_fallback_estimation(self, response_processor):
        """Token count should use fallback (1 token ≈ 4 chars)."""
        text = "a" * 100
        tokens = response_processor._count_tokens(text)
        assert tokens == 25  # 100 / 4

    def test_count_tokens_minimum_one(self, response_processor):
        """Token count should never be 0."""
        tokens = response_processor._count_tokens("")
        assert tokens == 1

    def test_count_tokens_short_text(self, response_processor):
        """Short text should count as at least 1 token."""
        tokens = response_processor._count_tokens("hi")
        assert tokens >= 1


class TestProcessResponse:
    """Test complete response processing."""

    def test_process_response_basic(self, response_processor, baseline_emotional_state):
        """Basic response processing should work."""
        response_text = "Hello there!"
        result = response_processor.process_response(
            response_text=response_text,
            inference_time_sec=1.5,
            emotional_state_before=baseline_emotional_state,
            interaction_type="successful_response",
        )

        assert isinstance(result, ProcessedResponse)
        assert result.text == response_text
        assert result.tokens_generated > 0
        assert result.inference_time_sec == 1.5
        assert result.emotional_state_after is not None

    def test_process_response_cleans_text(
        self, response_processor, baseline_emotional_state
    ):
        """Response text should be cleaned during processing."""
        dirty_text = "  Hey <|eot_id|> there!  "
        result = response_processor.process_response(
            response_text=dirty_text,
            inference_time_sec=1.0,
            emotional_state_before=baseline_emotional_state,
        )

        assert result.text == "Hey there!"
        assert "<|eot_id|>" not in result.text

    def test_process_response_updates_emotional_state(
        self, response_processor, baseline_emotional_state
    ):
        """Emotional state should be updated after response."""
        state_before = EmotionalState(
            frustration=0.8,
            confidence=0.3,
            affection=0.4,
        )

        result = response_processor.process_response(
            response_text="Success!",
            inference_time_sec=1.0,
            emotional_state_before=state_before,
            interaction_type="successful_response",
        )

        state_after = result.emotional_state_after
        assert state_after is not None
        # Successful response should decrease frustration
        assert state_after.frustration < state_before.frustration
        # Should increase confidence
        assert state_after.confidence > state_before.confidence

    def test_process_response_logs_interaction(
        self, response_processor, baseline_emotional_state
    ):
        """Interaction should be logged in ProcessedResponse."""
        result = response_processor.process_response(
            response_text="Test response",
            inference_time_sec=0.5,
            emotional_state_before=baseline_emotional_state,
        )

        log = result.interaction_log
        assert log["interaction_type"] == "successful_response"
        assert log["inference_time_sec"] == 0.5
        assert log["response_text"] == "Test response"
        assert log["token_count"] > 0
        assert "timestamp" in log

    def test_process_response_handles_empty_response(
        self, response_processor, baseline_emotional_state
    ):
        """Empty responses should be replaced with fallback."""
        result = response_processor.process_response(
            response_text="",
            inference_time_sec=0.1,
            emotional_state_before=baseline_emotional_state,
        )

        assert result.text == "I forgot what I was thinking... try again?"

    def test_process_response_timing_recorded(
        self, response_processor, baseline_emotional_state
    ):
        """Inference timing should be recorded accurately."""
        timings = [0.5, 1.0, 2.5, 3.0]

        for timing in timings:
            result = response_processor.process_response(
                response_text="Test",
                inference_time_sec=timing,
                emotional_state_before=baseline_emotional_state,
            )
            assert result.inference_time_sec == timing


class TestEmotionalStateUpdate:
    """Test emotional state updates."""

    def test_emotional_state_before_preserved(
        self, response_processor, baseline_emotional_state
    ):
        """Original emotional state should not be modified."""
        state_copy = EmotionalState(
            loneliness=baseline_emotional_state.loneliness,
            excitement=baseline_emotional_state.excitement,
            frustration=baseline_emotional_state.frustration,
            jealousy=baseline_emotional_state.jealousy,
            vulnerability=baseline_emotional_state.vulnerability,
            confidence=baseline_emotional_state.confidence,
            curiosity=baseline_emotional_state.curiosity,
            affection=baseline_emotional_state.affection,
            defensiveness=baseline_emotional_state.defensiveness,
        )

        response_processor.process_response(
            response_text="Test",
            inference_time_sec=1.0,
            emotional_state_before=baseline_emotional_state,
        )

        # Original should be unchanged
        assert baseline_emotional_state.loneliness == state_copy.loneliness
        assert baseline_emotional_state.frustration == state_copy.frustration

    def test_successful_response_increases_confidence(self, response_processor):
        """Successful response should increase confidence."""
        state_before = EmotionalState(confidence=0.3)

        result = response_processor.process_response(
            response_text="Done!",
            inference_time_sec=1.0,
            emotional_state_before=state_before,
            interaction_type="successful_response",
        )

        assert result.emotional_state_after.confidence > state_before.confidence

    def test_successful_response_decreases_frustration(self, response_processor):
        """Successful response should decrease frustration."""
        state_before = EmotionalState(frustration=0.8)

        result = response_processor.process_response(
            response_text="All good!",
            inference_time_sec=1.0,
            emotional_state_before=state_before,
            interaction_type="successful_response",
        )

        assert result.emotional_state_after.frustration < state_before.frustration


class TestDataPersistence:
    """Test database persistence."""

    def test_persist_interaction_called(
        self, response_processor, baseline_emotional_state
    ):
        """Interaction should be persisted."""
        with patch.object(
            response_processor.emotion_persistence, "log_interaction"
        ) as mock_log:
            response_processor.process_response(
                response_text="Test",
                inference_time_sec=1.0,
                emotional_state_before=baseline_emotional_state,
            )

            # Verify log_interaction was called
            assert mock_log.called

    def test_persist_interaction_with_metadata(
        self, response_processor, baseline_emotional_state
    ):
        """Persisted interaction should include metadata."""
        with patch.object(
            response_processor.emotion_persistence, "log_interaction"
        ) as mock_log:
            response_processor.process_response(
                response_text="Test response",
                inference_time_sec=0.75,
                emotional_state_before=baseline_emotional_state,
            )

            # Check call arguments
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["confidence_level"] == 1.0
            assert "effects" in call_kwargs


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_processing_pipeline(
        self, response_processor, baseline_emotional_state
    ):
        """Full pipeline: clean → count → log → update emotion → persist."""
        response_text = "  Hey! I'm <|eot_id|> happy to help!  \n\n  "

        result = response_processor.process_response(
            response_text=response_text,
            inference_time_sec=1.25,
            emotional_state_before=baseline_emotional_state,
            interaction_type="successful_response",
        )

        # Verify each step
        assert result.text == "Hey! I'm happy to help!"  # Cleaned
        assert result.tokens_generated > 0  # Counted
        assert result.inference_time_sec == 1.25  # Timed
        assert result.emotional_state_after is not None  # Updated
        assert "timestamp" in result.interaction_log  # Logged

    def test_multiple_responses_sequential(
        self, response_processor, baseline_emotional_state
    ):
        """Multiple responses should be processed sequentially."""
        responses = [
            "First response",
            "  Second <|end|> response  ",
            "Third response",
        ]

        for text in responses:
            result = response_processor.process_response(
                response_text=text,
                inference_time_sec=1.0,
                emotional_state_before=baseline_emotional_state,
            )
            assert result.text  # All should produce output
            assert result.emotional_state_after is not None

    def test_response_with_very_long_text(
        self, response_processor, baseline_emotional_state
    ):
        """Long responses should be handled correctly."""
        long_text = "This is a very long response. " * 100

        result = response_processor.process_response(
            response_text=long_text,
            inference_time_sec=2.5,
            emotional_state_before=baseline_emotional_state,
        )

        assert len(result.text) > 1000
        assert result.tokens_generated > 0
        assert result.emotional_state_after is not None

    def test_response_with_special_characters(
        self, response_processor, baseline_emotional_state
    ):
        """Special characters should be preserved when cleaning."""
        text_with_chars = "Hello! 🎉 How are you? (doing great!) #awesome"

        result = response_processor.process_response(
            response_text=text_with_chars,
            inference_time_sec=0.5,
            emotional_state_before=baseline_emotional_state,
        )

        assert "Hello!" in result.text
        assert "awesome" in result.text
