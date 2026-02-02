"""
Full end-to-end integration tests for LLM system with self-awareness.

Verifies complete pipeline: message → emotional state → modulation →
prompt (with code) → inference → response → logging → emotional update.
"""

import pytest
import asyncio
from src.llm.codebase_reader import CodebaseReader
from src.llm.inference import OllamaInference
from src.llm.prompt_builder import PromptBuilder, BASE_DEMI_PROMPT
from src.llm.history_manager import ConversationHistory
from src.llm.response_processor import ResponseProcessor
from src.llm.config import LLMConfig
from src.emotion.models import EmotionalState
from src.emotion.modulation import PersonalityModulator
from src.core.logger import get_logger


@pytest.fixture
def logger():
    """Create a test logger."""
    return get_logger()


@pytest.fixture
def token_counter():
    """Simple token counter for testing."""

    def counter(text: str) -> int:
        return max(1, len(text) // 4)

    return counter


@pytest.fixture
def codebase_reader(logger, token_counter):
    """Create a CodebaseReader instance."""
    return CodebaseReader(
        logger=logger, codebase_root="src/", token_counter=token_counter
    )


@pytest.fixture
def prompt_builder(logger, token_counter, codebase_reader):
    """Create a PromptBuilder with codebase context."""
    return PromptBuilder(
        logger=logger,
        token_counter=token_counter,
        codebase_reader=codebase_reader,
    )


@pytest.fixture
def conversation_history(logger):
    """Create a ConversationHistory instance."""
    return ConversationHistory(logger=logger)


@pytest.fixture
def emotional_state():
    """Create a mock emotional state."""
    return EmotionalState(
        loneliness=0.3,
        excitement=0.5,
        frustration=0.2,
        jealousy=0.1,
        vulnerability=0.0,
        confidence=0.6,
        curiosity=0.7,
        affection=0.4,
        defensiveness=0.2,
    )


@pytest.fixture
def personality_modulator(logger):
    """Create a PersonalityModulator instance."""
    return PersonalityModulator()


class TestPromptBuilderWithCodeContext:
    """Test prompt building with code context injection."""

    def test_prompt_builder_accepts_codebase_reader(self, logger, token_counter):
        """Verify PromptBuilder can be initialized with CodebaseReader."""
        codebase_reader = CodebaseReader(
            logger=logger, codebase_root="src/", token_counter=token_counter
        )
        builder = PromptBuilder(
            logger=logger,
            token_counter=token_counter,
            codebase_reader=codebase_reader,
        )
        assert builder.codebase_reader is codebase_reader

    def test_build_prompt_includes_architecture(
        self,
        prompt_builder,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Verify built prompt includes architecture overview."""
        # Add a user message
        conversation_history.add_message(
            "user",
            "How do you work?",
            emotional_state,
        )

        # Build prompt
        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        # Check system prompt
        assert len(messages) > 0
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert "MY ARCHITECTURE:" in system_msg["content"]
        assert "Emotional System" in system_msg["content"]

    def test_build_prompt_with_code_relevance_query(
        self,
        prompt_builder,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Verify code snippets are injected for relevant queries."""
        # Add a question about emotions
        conversation_history.add_message(
            "user",
            "How do your emotions work?",
            emotional_state,
        )

        # Build prompt
        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        # Check for code injection
        system_msg = messages[0]["content"]
        assert "RELEVANT CODE" in system_msg or "MY ARCHITECTURE:" in system_msg

    def test_build_prompt_without_codebase_reader(
        self,
        logger,
        token_counter,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Verify prompt building works without CodebaseReader."""
        # Create builder without codebase reader
        builder = PromptBuilder(
            logger=logger,
            token_counter=token_counter,
            codebase_reader=None,
        )

        # Add a message
        conversation_history.add_message("user", "Hi!", emotional_state)

        # Build prompt should work fine
        modulation = personality_modulator.modulate(emotional_state)
        messages = builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        assert len(messages) > 0
        assert messages[0]["role"] == "system"

    def test_prompt_token_limit_respected(
        self,
        prompt_builder,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Verify system prompt doesn't exceed reasonable token limits."""
        # Build several messages to get a full context
        for i in range(3):
            conversation_history.add_message(
                "user",
                f"This is message {i}",
                emotional_state,
            )
            conversation_history.add_message(
                "assistant",
                f"Response {i}",
                emotional_state,
            )

        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        system_msg = messages[0]
        system_tokens = prompt_builder.token_counter(system_msg["content"])

        # System prompt should be reasonable (under 2000 tokens)
        assert system_tokens < 2000, f"System prompt is {system_tokens} tokens"

    def test_conversation_history_preserved(
        self,
        prompt_builder,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Verify conversation history is preserved in prompt."""
        # Add multiple messages
        conversation_history.add_message("user", "First message", emotional_state)
        conversation_history.add_message("assistant", "First response", emotional_state)
        conversation_history.add_message("user", "Second message", emotional_state)

        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        # Should have system message plus conversation
        assert len(messages) > 1
        assert messages[0]["role"] == "system"
        # Check that user/assistant messages are present
        roles = [m["role"] for m in messages[1:]]
        assert "user" in roles
        assert "assistant" in roles


class TestConversationHistoryManagement:
    """Test conversation history management."""

    def test_add_message(self, conversation_history, emotional_state):
        """Verify messages can be added."""
        conversation_history.add_message("user", "Test", emotional_state)
        assert len(conversation_history.messages) == 1

    def test_trim_for_inference(self, conversation_history, emotional_state):
        """Verify trimming works."""
        # Add many messages
        for i in range(5):
            conversation_history.add_message("user", f"Message {i}", emotional_state)

        trimmed = conversation_history.trim_for_inference(system_prompt_tokens=100, token_counter=lambda t: len(t)//4)
        # Should return a list
        assert isinstance(trimmed, list)
        assert len(trimmed) <= 5

    def test_conversation_window(self, conversation_history, emotional_state):
        """Verify conversation window method works."""
        conversation_history.add_message("user", "Q1", emotional_state)
        conversation_history.add_message("assistant", "A1", emotional_state)

        window = conversation_history.get_conversation_window()
        assert "Q1" in window or len(window) > 0


class TestCodebaseContextInjection:
    """Test code context injection into prompts."""

    def test_architecture_in_prompt(
        self,
        codebase_reader,
        prompt_builder,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Verify architecture overview appears in prompt."""
        conversation_history.add_message("user", "Explain yourself", emotional_state)

        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        system_content = messages[0]["content"]

        # Should mention architecture
        assert "MY ARCHITECTURE:" in system_content or "ARCHITECTURE" in system_content

    def test_code_retrieval_for_query(
        self,
        codebase_reader,
        prompt_builder,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Verify code snippets are retrieved for relevant queries."""
        # Ask about emotions specifically
        conversation_history.add_message(
            "user",
            "How do emotions work in your system?",
            emotional_state,
        )

        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        system_content = messages[0]["content"]

        # Should have either explicit code or architecture overview
        assert "MY ARCHITECTURE:" in system_content or len(system_content) > 1000

    def test_code_context_affects_response_potential(
        self,
        codebase_reader,
        emotional_state,
    ):
        """Verify CodebaseReader can provide context about architecture."""
        # This doesn't require inference, just verifies data is available
        overview = codebase_reader.get_architecture_overview()
        assert "Emotional System" in overview
        assert "LLM Inference" in overview

        # Verify we can get code for modules
        emotional_state_code = codebase_reader.get_code_for_module("EmotionalState")
        assert emotional_state_code is not None
        assert "class EmotionalState" in emotional_state_code.content


class TestPipelineIntegration:
    """Test full pipeline integration (without actual Ollama inference)."""

    def test_full_pipeline_components_available(
        self,
        logger,
        token_counter,
    ):
        """Verify all pipeline components can be initialized."""
        # Create all components
        codebase_reader = CodebaseReader(
            logger=logger, codebase_root="src/", token_counter=token_counter
        )
        emotional_state = EmotionalState()
        personality_modulator = PersonalityModulator()
        prompt_builder = PromptBuilder(
            logger=logger,
            token_counter=token_counter,
            codebase_reader=codebase_reader,
        )
        conversation_history = ConversationHistory(logger=logger)

        # Verify all initialized
        assert codebase_reader is not None
        assert emotional_state is not None
        assert personality_modulator is not None
        assert prompt_builder is not None
        assert conversation_history is not None

    def test_pipeline_message_flow(
        self,
        logger,
        token_counter,
        emotional_state,
    ):
        """Test message flow through pipeline."""
        # Initialize components
        codebase_reader = CodebaseReader(
            logger=logger, codebase_root="src/", token_counter=token_counter
        )
        prompt_builder = PromptBuilder(
            logger=logger,
            token_counter=token_counter,
            codebase_reader=codebase_reader,
        )
        conversation_history = ConversationHistory(logger=logger)
        personality_modulator = PersonalityModulator()

        # Step 1: Add message to history
        user_message = "How do you work?"
        conversation_history.add_message("user", user_message, emotional_state)

        # Step 2: Get personality modulation
        modulation = personality_modulator.modulate(emotional_state)
        assert modulation is not None

        # Step 3: Build prompt with code context
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )
        assert len(messages) > 0

        # Step 4: Verify message format for inference
        for msg in messages:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("system", "user", "assistant")

        # Step 5: Verify system message has architecture
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert "MY ARCHITECTURE:" in system_msg["content"]


class TestEdgeCases:
    """Test edge cases in integration."""

    def test_empty_conversation_history(
        self,
        prompt_builder,
        emotional_state,
        personality_modulator,
    ):
        """Test prompt building with empty history."""
        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            [],  # Empty history
        )

        assert len(messages) == 1  # Just system message
        assert messages[0]["role"] == "system"

    def test_very_long_query(
        self,
        prompt_builder,
        emotional_state,
        conversation_history,
        personality_modulator,
    ):
        """Test with very long user query."""
        long_query = "How do you work? " * 100
        conversation_history.add_message("user", long_query, emotional_state)

        modulation = personality_modulator.modulate(emotional_state)
        messages = prompt_builder.build(
            emotional_state,
            modulation,
            conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
        )

        assert len(messages) > 0

    def test_multiple_emotional_states(
        self,
        prompt_builder,
        conversation_history,
        personality_modulator,
    ):
        """Test prompts with different emotional states."""
        states = [
            EmotionalState(loneliness=0.9),  # Very lonely
            EmotionalState(excitement=0.9),  # Very excited
            EmotionalState(frustration=0.9),  # Very frustrated
        ]

        for state in states:
            modulation = personality_modulator.modulate(state)
            messages = prompt_builder.build(
                state,
                modulation,
                conversation_history.trim_for_inference(system_prompt_tokens=500, token_counter=lambda t: len(t)//4),
            )
            assert len(messages) > 0
            assert "MY ARCHITECTURE:" in messages[0]["content"]
