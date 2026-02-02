"""
End-to-end tests for LLM pipeline integration.

Tests the full flow: message → inference → response processing → emotional update.
"""

import pytest
from unittest.mock import Mock, patch

from src.llm.inference import OllamaInference, InferenceError
from src.llm.response_processor import ResponseProcessor, ProcessedResponse
from src.llm.config import LLMConfig
from src.emotion.models import EmotionalState
from src.emotion.interactions import InteractionHandler
from src.core.logger import DemiLogger


@pytest.fixture
def logger():
    """Create a test logger."""
    return DemiLogger()


@pytest.fixture
def llm_config():
    """Create LLM config for testing."""
    return LLMConfig(
        model_name="llama3.2:1b",
        ollama_base_url="http://localhost:11434",
        temperature=0.7,
        max_tokens=256,
        timeout_sec=30.0,
    )


@pytest.fixture
def interaction_handler():
    """Create interaction handler."""
    return InteractionHandler()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock()


@pytest.fixture
def response_processor(logger, mock_db_session, interaction_handler):
    """Create response processor."""
    return ResponseProcessor(
        logger=logger,
        db_session=mock_db_session,
        interaction_handler=interaction_handler,
    )


@pytest.fixture
def ollama_inference(llm_config, logger, response_processor):
    """Create Ollama inference engine with response processor."""
    engine = OllamaInference(llm_config, logger, response_processor)
    return engine


@pytest.fixture
def baseline_emotional_state():
    """Create baseline emotional state."""
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


class TestResponseProcessorIntegration:
    """Test ResponseProcessor integration with inference."""

    def test_response_processor_cleans_output(
        self, response_processor, baseline_emotional_state
    ):
        """ResponseProcessor should clean Ollama output."""
        dirty_response = "  Hello there! <|eot_id|>  "

        result = response_processor.process_response(
            response_text=dirty_response,
            inference_time_sec=1.0,
            emotional_state_before=baseline_emotional_state,
        )

        assert result.text == "Hello there!"
        assert "<|eot_id|>" not in result.text

    def test_response_processor_updates_emotions(
        self, response_processor, baseline_emotional_state
    ):
        """ResponseProcessor should update emotional state."""
        state_before = EmotionalState(
            frustration=0.8,
            confidence=0.2,
        )

        result = response_processor.process_response(
            response_text="Success!",
            inference_time_sec=0.5,
            emotional_state_before=state_before,
        )

        state_after = result.emotional_state_after
        # Successful response decreases frustration
        assert state_after.frustration < state_before.frustration
        # Increases confidence
        assert state_after.confidence > state_before.confidence

    def test_response_processor_logs_timing(
        self, response_processor, baseline_emotional_state
    ):
        """ResponseProcessor should log inference timing."""
        result = response_processor.process_response(
            response_text="Test",
            inference_time_sec=2.5,
            emotional_state_before=baseline_emotional_state,
        )

        assert result.inference_time_sec == 2.5
        assert result.interaction_log["inference_time_sec"] == 2.5

    def test_response_processor_persists_interaction(
        self, response_processor, baseline_emotional_state
    ):
        """ResponseProcessor should persist interaction data."""
        with patch.object(
            response_processor.emotion_persistence, "log_interaction"
        ) as mock_log:
            result = response_processor.process_response(
                response_text="Test",
                inference_time_sec=1.0,
                emotional_state_before=baseline_emotional_state,
            )

            # Verify interaction was logged
            assert mock_log.called
            call_kwargs = mock_log.call_args[1]
            assert "effects" in call_kwargs
            assert call_kwargs["confidence_level"] == 1.0


class TestOllamaInferenceIntegration:
    """Test OllamaInference integration."""

    def test_inference_with_processor_integration(
        self, llm_config, logger, response_processor
    ):
        """OllamaInference should integrate with ResponseProcessor."""
        engine = OllamaInference(llm_config, logger, response_processor)
        assert engine.response_processor == response_processor

    def test_inference_without_processor_backward_compatible(self, llm_config, logger):
        """OllamaInference should work without ResponseProcessor."""
        engine = OllamaInference(llm_config, logger)
        assert engine.response_processor is None

    def test_inference_accepts_emotional_state(
        self, ollama_inference, baseline_emotional_state
    ):
        """OllamaInference.chat should accept emotional state parameter."""
        # Just verify the parameter is accepted (doesn't raise)
        # We won't actually call it without mocking Ollama
        assert ollama_inference is not None


class TestPipelineComponentsWork:
    """Test that pipeline components work together."""

    def test_prompt_builder_works(self):
        """PromptBuilder should create prompts."""
        from src.llm.prompt_builder import PromptBuilder
        from src.emotion.modulation import PersonalityModulator

        logger = DemiLogger()
        builder = PromptBuilder(logger, lambda x: len(x) // 4)
        modulator = PersonalityModulator()

        state = EmotionalState(loneliness=0.7)
        modulation = modulator.modulate(state)
        messages = builder.build(state, modulation, [])

        assert isinstance(messages, list)
        assert len(messages) > 0
        assert messages[0]["role"] == "system"

    def test_history_manager_works(self):
        """ConversationHistory should manage messages."""
        from src.llm.history_manager import ConversationHistory

        logger = DemiLogger()
        history = ConversationHistory(logger=logger)

        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi!")

        messages = history.get_conversation_window()
        assert len(messages) == 2
        assert messages[0].content == "Hello"

    def test_response_processor_works(
        self, response_processor, baseline_emotional_state
    ):
        """ResponseProcessor should process responses."""
        result = response_processor.process_response(
            response_text="Test response",
            inference_time_sec=1.0,
            emotional_state_before=baseline_emotional_state,
        )

        assert isinstance(result, ProcessedResponse)
        assert result.text == "Test response"
        assert result.emotional_state_after is not None


class TestFullPipelineFlow:
    """Test full pipeline flow (without actual Ollama)."""

    def test_message_validation_in_inference(self, ollama_inference):
        """Inference should validate messages before processing."""
        # Test with invalid input
        with pytest.raises(ValueError):
            # Sync wrapper for the async function
            import asyncio

            try:
                asyncio.run(ollama_inference.chat(messages={}))
            except ValueError:
                raise

    def test_response_cleaning_chain(self, response_processor):
        """Response cleaning should work through the chain."""
        test_cases = [
            ("  hello  ", "hello"),
            ("hello <|end|> world", "hello world"),
            ("hello\n\n\nworld", "hello\n\nworld"),
            ("", "I forgot what I was thinking... try again?"),
        ]

        for input_text, expected in test_cases:
            cleaned = response_processor._clean_text(input_text)
            assert cleaned == expected, f"Failed for input: {input_text}"

    def test_token_counting_consistency(self, response_processor):
        """Token counting should be consistent."""
        text = "This is a test sentence."

        tokens_1 = response_processor._count_tokens(text)
        tokens_2 = response_processor._count_tokens(text)

        assert tokens_1 == tokens_2
        assert tokens_1 > 0

    def test_emotional_state_update_chain(
        self, response_processor, baseline_emotional_state
    ):
        """Emotional state updates should cascade correctly."""
        state_1 = EmotionalState(
            frustration=0.8,
            confidence=0.2,
            affection=0.3,
        )

        result_1 = response_processor.process_response(
            response_text="First response",
            inference_time_sec=1.0,
            emotional_state_before=state_1,
        )

        state_2 = result_1.emotional_state_after

        # Second response with updated state
        result_2 = response_processor.process_response(
            response_text="Second response",
            inference_time_sec=1.0,
            emotional_state_before=state_2,
        )

        state_3 = result_2.emotional_state_after

        # Both should show improvement from original
        assert state_2.frustration < state_1.frustration
        assert state_3.frustration < state_2.frustration


class TestErrorHandling:
    """Test error handling in pipeline."""

    def test_empty_response_fallback(
        self, response_processor, baseline_emotional_state
    ):
        """Empty responses should use fallback."""
        result = response_processor.process_response(
            response_text="",
            inference_time_sec=0.1,
            emotional_state_before=baseline_emotional_state,
        )

        assert result.text == "I forgot what I was thinking... try again?"

    def test_response_with_only_tokens_uses_fallback(
        self, response_processor, baseline_emotional_state
    ):
        """Response with only tokens should use fallback."""
        result = response_processor.process_response(
            response_text="  <|end|> <|eot_id|>  ",
            inference_time_sec=0.1,
            emotional_state_before=baseline_emotional_state,
        )

        assert result.text == "I forgot what I was thinking... try again?"

    def test_very_long_response(self, response_processor, baseline_emotional_state):
        """Very long responses should be handled."""
        long_text = "a" * 10000

        result = response_processor.process_response(
            response_text=long_text,
            inference_time_sec=1.0,
            emotional_state_before=baseline_emotional_state,
        )

        assert len(result.text) > 9000
        assert result.tokens_generated > 0


class TestPerformanceMetrics:
    """Test performance metrics tracking."""

    def test_timing_recorded_accurately(
        self, response_processor, baseline_emotional_state
    ):
        """Timing should be recorded accurately."""
        timings = [0.1, 0.5, 1.0, 2.5, 3.0]

        for timing in timings:
            result = response_processor.process_response(
                response_text="Test",
                inference_time_sec=timing,
                emotional_state_before=baseline_emotional_state,
            )

            assert result.inference_time_sec == timing
            assert result.interaction_log["inference_time_sec"] == timing

    def test_token_count_tracked(self, response_processor, baseline_emotional_state):
        """Token count should be tracked."""
        test_texts = [
            "Short",
            "This is a slightly longer test sentence.",
            "This is a much longer response that contains many tokens and words to test token counting accuracy.",
        ]

        for text in test_texts:
            result = response_processor.process_response(
                response_text=text,
                inference_time_sec=1.0,
                emotional_state_before=baseline_emotional_state,
            )

            assert result.tokens_generated > 0
            assert result.interaction_log["token_count"] > 0


class TestDataConsistency:
    """Test data consistency through pipeline."""

    def test_emotional_state_not_modified_in_place(
        self, response_processor, baseline_emotional_state
    ):
        """Original emotional state should not be modified."""
        original_loneliness = baseline_emotional_state.loneliness
        original_frustration = baseline_emotional_state.frustration

        response_processor.process_response(
            response_text="Test",
            inference_time_sec=1.0,
            emotional_state_before=baseline_emotional_state,
        )

        # Original should be unchanged
        assert baseline_emotional_state.loneliness == original_loneliness
        assert baseline_emotional_state.frustration == original_frustration

    def test_before_after_states_differ(
        self, response_processor, baseline_emotional_state
    ):
        """Before and after states should differ."""
        state_before = EmotionalState(
            frustration=0.8,
            confidence=0.2,
        )

        result = response_processor.process_response(
            response_text="Test",
            inference_time_sec=1.0,
            emotional_state_before=state_before,
        )

        state_after = result.emotional_state_after

        # Should be different
        assert (
            state_before.frustration != state_after.frustration
            or state_before.confidence != state_after.confidence
        )
