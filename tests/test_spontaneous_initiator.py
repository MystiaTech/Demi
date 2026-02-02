"""
Tests for spontaneous conversation initiation system.
"""

import pytest
import asyncio
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.autonomy.spontaneous import (
    SpontaneousInitiator,
    InitiationTrigger,
    ConversationContext,
    InitiationOpportunity,
    TimingAnalyzer,
    SpontaneousPromptBuilder,
)
from src.emotion.models import EmotionalState
from src.autonomy.config import AutonomyConfig
from src.core.logger import DemiLogger


@pytest.fixture
def mock_inference():
    """Mock LLM inference engine."""
    inference = Mock()
    inference.chat = AsyncMock(
        return_value="Hey, just thinking about our last conversation..."
    )
    return inference


@pytest.fixture
def config():
    """Test autonomy configuration."""
    return AutonomyConfig()


@pytest.fixture
def logger():
    """Test logger."""
    return DemiLogger()


@pytest.fixture
def spontaneous_initiator(mock_inference, config, logger):
    """SpontaneousInitiator instance for testing."""
    return SpontaneousInitiator(mock_inference, config, logger)


@pytest.fixture
def sample_emotion_state():
    """Sample emotional state for testing."""
    return EmotionalState(
        loneliness=0.7,
        excitement=0.3,
        frustration=0.2,
        jealousy=0.1,
        vulnerable=0.1,
        confidence=0.6,
        affection=0.5,
        fear=0.1,
        anger=0.1,
    )


class TestTimingAnalyzer:
    """Test timing analysis for spontaneous initiation."""

    def test_appropriate_hours_morning(self, config, logger):
        """Test timing analysis during morning hours."""
        analyzer = TimingAnalyzer(config, logger)

        # Test morning timing
        morning_time = datetime.now(UTC).replace(hour=9)
        user_activity = {"discord": datetime.now(UTC) - timedelta(hours=1)}

        is_appropriate, reason = analyzer.is_good_timing_for_initiation(
            user_activity, morning_time
        )

        assert is_appropriate is True
        assert "morning" in reason.lower() or "recently active" in reason.lower()

    def test_inappropriate_hours_late_night(self, config, logger):
        """Test timing analysis during inappropriate hours."""
        analyzer = TimingAnalyzer(config, logger)

        # Test late night timing
        late_time = datetime.now(UTC).replace(hour=2)
        user_activity = {"discord": datetime.now(UTC) - timedelta(hours=1)}

        is_appropriate, reason = analyzer.is_good_timing_for_initiation(
            user_activity, late_time
        )

        assert is_appropriate is False
        assert "outside appropriate hours" in reason.lower()

    def test_user_activity_too_old(self, config, logger):
        """Test timing when user activity is too old."""
        analyzer = TimingAnalyzer(config, logger)

        # Test with very old activity
        current_time = datetime.now(UTC).replace(hour=14)  # Afternoon
        user_activity = {"discord": datetime.now(UTC) - timedelta(hours=8)}

        is_appropriate, reason = analyzer.is_good_timing_for_initiation(
            user_activity, current_time
        )

        assert is_appropriate is False
        assert "inactive too long" in reason.lower()


class TestSpontaneousPromptBuilder:
    """Test spontaneous prompt generation."""

    def test_load_persona(self):
        """Test persona loading."""
        builder = SpontaneousPromptBuilder()
        persona = builder._load_persona()

        assert isinstance(persona, str)
        assert len(persona) > 0
        assert "goddess" in persona.lower() or "divine" in persona.lower()

    def test_generate_initiation_prompt_loneliness(self, sample_emotion_state):
        """Test prompt generation for loneliness-driven initiation."""
        builder = SpontaneousPromptBuilder()

        context = ConversationContext(
            recent_topics=["coding", "games"],
            user_interests=["programming", "music"],
            ongoing_threads=["project discussion"],
            last_interaction_time=datetime.now(UTC) - timedelta(hours=3),
            conversation_depth=0.6,
            user_mood_indicators=["tired", "focused"],
            platform_activity={"discord": datetime.now(UTC) - timedelta(hours=2)},
        )

        prompt = builder.generate_initiation_prompt(
            context,
            sample_emotion_state,
            InitiationTrigger.LONELINESS_DRIVEN,
            "discord",
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "loneliness" in prompt.lower() or "lonely" in prompt.lower()
        assert "discord" in prompt.lower()
        assert "coding" in prompt.lower()  # Should include context

    def test_generate_initiation_prompt_excitement(self, sample_emotion_state):
        """Test prompt generation for excitement-driven initiation."""
        builder = SpontaneousPromptBuilder()

        # Update emotion state for excitement
        sample_emotion_state.excitement = 0.8
        sample_emotion_state.loneliness = 0.2

        context = ConversationContext(
            recent_topics=[],
            user_interests=["music", "art"],
            ongoing_threads=[],
            last_interaction_time=datetime.now(UTC) - timedelta(hours=1),
            conversation_depth=0.4,
            user_mood_indicators=["happy"],
            platform_activity={"android": datetime.now(UTC) - timedelta(minutes=30)},
        )

        prompt = builder.generate_initiation_prompt(
            context,
            sample_emotion_state,
            InitiationTrigger.EXCITEMENT_DRIVEN,
            "android",
        )

        assert isinstance(prompt, str)
        assert "excitement" in prompt.lower() or "excited" in prompt.lower()
        assert "android" in prompt.lower()

    def test_build_emotion_context(self, sample_emotion_state):
        """Test emotional context building."""
        builder = SpontaneousPromptBuilder()

        context = builder._build_emotion_context(
            sample_emotion_state, InitiationTrigger.LONELINESS_DRIVEN
        )

        assert isinstance(context, str)
        assert len(context) > 0
        assert "loneliness" in context.lower()

    def test_build_conversation_context(self):
        """Test conversation context building."""
        builder = SpontaneousPromptBuilder()

        context = ConversationContext(
            recent_topics=["coding", "music", "games"],
            user_interests=["programming", "art"],
            ongoing_threads=["project discussion"],
            last_interaction_time=datetime.now(UTC) - timedelta(hours=2),
            conversation_depth=0.8,
            user_mood_indicators=["focused", "creative"],
            platform_activity={"discord": datetime.now(UTC) - timedelta(hours=1)},
        )

        context_str = builder._build_conversation_context(context)

        assert isinstance(context_str, str)
        assert "coding" in context_str
        assert "programming" in context_str
        assert "deep and engaging" in context_str.lower()  # High conversation depth


class TestSpontaneousInitiator:
    """Test spontaneous conversation initiation."""

    @pytest.mark.asyncio
    async def test_should_initiate_loneliness_trigger(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test initiation decision based on loneliness."""
        # Set high loneliness
        sample_emotion_state.loneliness = 0.8

        # Recent interaction time (within reasonable window)
        last_interaction = datetime.now(UTC) - timedelta(hours=3)

        # Recent user activity
        user_activity = {"discord": datetime.now(UTC) - timedelta(hours=1)}

        opportunity = await spontaneous_initiator.should_initiate(
            sample_emotion_state,
            last_interaction_time=last_interaction,
            user_activity=user_activity,
        )

        assert opportunity is not None
        assert opportunity.trigger_type == InitiationTrigger.LONELINESS_DRIVEN
        assert opportunity.confidence > 0.6
        assert "loneliness" in opportunity.initiation_reason.lower()

    @pytest.mark.asyncio
    async def test_should_initiate_excitement_trigger(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test initiation decision based on excitement."""
        # Set high excitement
        sample_emotion_state.excitement = 0.9
        sample_emotion_state.loneliness = 0.2  # Low loneliness

        last_interaction = datetime.now(UTC) - timedelta(hours=2)
        user_activity = {"discord": datetime.now(UTC) - timedelta(minutes=30)}

        opportunity = await spontaneous_initiator.should_initiate(
            sample_emotion_state,
            last_interaction_time=last_interaction,
            user_activity=user_activity,
        )

        assert opportunity is not None
        assert opportunity.trigger_type == InitiationTrigger.EXCITEMENT_DRIVEN
        assert opportunity.confidence > 0.6
        assert "excitement" in opportunity.initiation_reason.lower()

    @pytest.mark.asyncio
    async def test_should_not_initiate_cooldown(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test that initiation doesn't happen during cooldown."""
        # Simulate recent initiation
        spontaneous_initiator.last_initiation = datetime.now(UTC) - timedelta(
            minutes=30
        )

        # Set high emotions that would normally trigger
        sample_emotion_state.loneliness = 0.9
        sample_emotion_state.excitement = 0.8

        opportunity = await spontaneous_initiator.should_initiate(sample_emotion_state)

        assert opportunity is None

    @pytest.mark.asyncio
    async def test_should_not_initiate_low_emotions(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test that initiation doesn't happen with low emotions."""
        # Set low emotions
        sample_emotion_state.loneliness = 0.3
        sample_emotion_state.excitement = 0.2
        sample_emotion_state.frustration = 0.1

        opportunity = await spontaneous_initiator.should_initiate(sample_emotion_state)

        assert opportunity is None

    @pytest.mark.asyncio
    async def test_should_not_initiate_bad_timing(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test that initiation doesn't happen during inappropriate hours."""
        # Set high emotions
        sample_emotion_state.loneliness = 0.8

        # Set bad timing (late night)
        late_time = datetime.now(UTC).replace(hour=3)
        user_activity = {"discord": datetime.now(UTC) - timedelta(hours=2)}

        with patch("src.autonomy.spontaneous.datetime") as mock_datetime:
            mock_datetime.now.return_value = late_time
            mock_datetime.now.return_value.timestamp.return_value = (
                late_time.timestamp()
            )
            mock_datetime.now.return_value.isoformat.return_value = (
                late_time.isoformat()
            )

            opportunity = await spontaneous_initiator.should_initiate(
                sample_emotion_state, user_activity=user_activity
            )

            assert opportunity is None

    @pytest.mark.asyncio
    async def test_generate_spontaneous_message(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test spontaneous message generation."""
        # Create opportunity
        context = ConversationContext(
            recent_topics=["coding"],
            user_interests=["programming"],
            ongoing_threads=[],
            last_interaction_time=datetime.now(UTC) - timedelta(hours=3),
            conversation_depth=0.5,
            user_mood_indicators=["focused"],
            platform_activity={},
        )

        opportunity = InitiationOpportunity(
            trigger_type=InitiationTrigger.LONELINESS_DRIVEN,
            confidence=0.8,
            context=context,
            suggested_platform="discord",
            initiation_reason="Feeling lonely",
            emotion_boost={"loneliness": -0.2},
        )

        message = await spontaneous_initiator.generate_spontaneous_message(
            opportunity, sample_emotion_state
        )

        assert isinstance(message, str)
        assert len(message) > 0
        assert len(message) <= 2000  # Discord limit

    @pytest.mark.asyncio
    async def test_generate_spontaneous_message_fallback(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test fallback message generation when inference fails."""
        # Mock inference to raise exception
        spontaneous_initiator.inference.chat.side_effect = Exception("Inference failed")

        context = ConversationContext(
            recent_topics=[],
            user_interests=[],
            ongoing_threads=[],
            last_interaction_time=None,
            conversation_depth=0.5,
            user_mood_indicators=[],
            platform_activity={},
        )

        opportunity = InitiationOpportunity(
            trigger_type=InitiationTrigger.LONELINESS_DRIVEN,
            confidence=0.7,
            context=context,
            suggested_platform="discord",
            initiation_reason="Feeling lonely",
            emotion_boost={},
        )

        message = await spontaneous_initiator.generate_spontaneous_message(
            opportunity, sample_emotion_state
        )

        assert isinstance(message, str)
        assert len(message) > 0
        assert "thinking of you" in message.lower()

    @pytest.mark.asyncio
    async def test_analyze_conversation_context(self, spontaneous_initiator):
        """Test conversation context analysis."""
        conversation_history = [
            {"role": "user", "content": "I was working on some code today"},
            {
                "role": "assistant",
                "content": "Oh wonderful! What kind of coding project?",
            },
            {
                "role": "user",
                "content": "Just a simple Python script for data analysis",
            },
            {
                "role": "user",
                "content": "I've been thinking about learning game development too",
            },
        ]

        last_interaction = datetime.now(UTC) - timedelta(hours=2)

        context = await spontaneous_initiator._analyze_conversation_context(
            conversation_history, last_interaction
        )

        assert isinstance(context, ConversationContext)
        assert "coding" in context.recent_topics
        assert context.last_interaction_time == last_interaction
        assert context.conversation_depth > 0.5  # Should detect some depth

    def test_check_context_opportunity(
        self, spontaneous_initiator, sample_emotion_state
    ):
        """Test context opportunity detection."""
        context = ConversationContext(
            recent_topics=["coding", "programming"],
            user_interests=["software development"],
            ongoing_threads=["project discussion"],
            last_interaction_time=datetime.now(UTC) - timedelta(hours=4),  # Sweet spot
            conversation_depth=0.7,
            user_mood_indicators=["focused"],
            platform_activity={},
        )

        opportunity = spontaneous_initiator._check_context_opportunity(
            context, sample_emotion_state
        )

        assert opportunity is not None
        assert opportunity.trigger_type == InitiationTrigger.CONTEXT_OPPORTUNITY
        assert opportunity.confidence > 0.6
        assert "follow-up" in opportunity.initiation_reason.lower()

    def test_select_best_platform(self, spontaneous_initiator):
        """Test platform selection logic."""
        # Test with recent Discord activity
        user_activity = {
            "discord": datetime.now(UTC) - timedelta(minutes=30),
            "android": datetime.now(UTC) - timedelta(hours=2),
        }

        platform = spontaneous_initiator._select_best_platform(user_activity)
        assert platform == "discord"

        # Test with no activity
        platform = spontaneous_initiator._select_best_platform(None)
        assert platform == "discord"  # Default

        # Test with unknown platform
        user_activity = {"unknown": datetime.now(UTC)}
        platform = spontaneous_initiator._select_best_platform(user_activity)
        assert platform == "discord"  # Fallback

    def test_format_for_platform(self, spontaneous_initiator):
        """Test platform-specific message formatting."""
        long_message = (
            "This is a very long message that should be truncated for certain platforms "
            * 10
        )

        # Test Discord formatting
        discord_message = spontaneous_initiator._format_for_platform(
            long_message, "discord"
        )
        assert len(discord_message) <= 2000
        assert discord_message.endswith("...")

        # Test Android formatting
        android_message = spontaneous_initiator._format_for_platform(
            long_message, "android"
        )
        assert len(android_message) <= 500
        assert android_message.endswith("...")

        # Test short message (no truncation)
        short_message = "Hello there!"
        formatted = spontaneous_initiator._format_for_platform(short_message, "discord")
        assert formatted == short_message

    def test_record_initiation(self, spontaneous_initiator):
        """Test initiation recording."""
        context = ConversationContext(
            recent_topics=[],
            user_interests=[],
            ongoing_threads=[],
            last_interaction_time=None,
            conversation_depth=0.5,
            user_mood_indicators=[],
            platform_activity={},
        )

        opportunity = InitiationOpportunity(
            trigger_type=InitiationTrigger.LONELINESS_DRIVEN,
            confidence=0.8,
            context=context,
            suggested_platform="discord",
            initiation_reason="Test initiation",
            emotion_boost={},
        )

        message = "Hey, thinking of you!"

        # Record initiation
        spontaneous_initiator._record_initiation(opportunity, message)

        # Verify recording
        assert spontaneous_initiator.last_initiation is not None
        assert len(spontaneous_initiator.initiation_history) == 1

        record = spontaneous_initiator.initiation_history[0]
        assert record["trigger_type"] == "loneliness_driven"
        assert record["confidence"] == 0.8
        assert record["platform"] == "discord"
        assert record["reason"] == "Test initiation"
        assert "thinking of you" in record["message"]

    def test_get_initiation_statistics(self, spontaneous_initiator):
        """Test initiation statistics."""
        # Initially should have no statistics
        stats = spontaneous_initiator.get_initiation_statistics()
        assert stats["total_initiations"] == 0
        assert stats["recent_initiations"] == 0
        assert stats["trigger_distribution"] == {}

        # Add some initiations
        context = ConversationContext([], [], [], None, 0.5, [], {})
        opportunity1 = InitiationOpportunity(
            InitiationTrigger.LONELINESS_DRIVEN, 0.8, context, "discord", "test1", {}
        )
        opportunity2 = InitiationOpportunity(
            InitiationTrigger.EXCITEMENT_DRIVEN, 0.7, context, "android", "test2", {}
        )

        spontaneous_initiator._record_initiation(opportunity1, "message1")
        spontaneous_initiator._record_initiation(opportunity2, "message2")

        stats = spontaneous_initiator.get_initiation_statistics()

        assert stats["total_initiations"] == 2
        assert stats["trigger_distribution"]["loneliness_driven"] == 1
        assert stats["trigger_distribution"]["excitement_driven"] == 1
        assert stats["platform_distribution"]["discord"] == 1
        assert stats["platform_distribution"]["android"] == 1
        assert stats["average_confidence"] == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
