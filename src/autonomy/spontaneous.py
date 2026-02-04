"""
Spontaneous conversation initiation system for Demi.

Generates contextually appropriate conversation starters based on emotional
state, recent conversation history, and timing considerations.
"""

import asyncio
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from src.core.logger import DemiLogger
from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.llm.inference import OllamaInference
from src.llm.prompt_builder import PromptBuilder
from src.llm.history_manager import ConversationHistory
from src.autonomy.config import AutonomyConfig


class InitiationTrigger(Enum):
    """Types of spontaneous initiation triggers."""

    LONELINESS_DRIVEN = "loneliness_driven"
    EXCITEMENT_DRIVEN = "excitement_driven"
    CONTEXT_OPPORTUNITY = "context_opportunity"
    TIMING_APPROPRIATE = "timing_appropriate"


@dataclass
class ConversationContext:
    """Analysis of conversation context for initiation."""

    recent_topics: List[str]
    user_interests: List[str]
    ongoing_threads: List[str]
    last_interaction_time: Optional[datetime]
    conversation_depth: float  # 0-1, how deep/engaged recent convos were
    user_mood_indicators: List[str]
    platform_activity: Dict[str, datetime]  # platform -> last activity


@dataclass
class InitiationOpportunity:
    """An opportunity for spontaneous conversation initiation."""

    trigger_type: InitiationTrigger
    confidence: float  # 0-1, how confident we are this is a good time
    context: ConversationContext
    suggested_platform: str
    initiation_reason: str
    emotion_boost: Dict[str, float]  # emotion -> boost amount


class TimingAnalyzer:
    """Analyzes timing appropriateness for spontaneous initiation."""

    def __init__(self, config: AutonomyConfig, logger: DemiLogger):
        self.config = config
        self.logger = logger

        # Define appropriate hours (24-hour format)
        self.appropriate_hours = {
            "morning": (7, 11),  # 7am - 11am
            "afternoon": (13, 17),  # 1pm - 5pm
            "evening": (18, 22),  # 6pm - 10pm
        }

    def is_good_timing_for_initiation(
        self,
        user_activity: Dict[str, datetime],
        current_time: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        Evaluate if current timing is appropriate for initiation.

        Args:
            user_activity: Dictionary of platform -> last activity time
            current_time: Current time (defaults to now)

        Returns:
            Tuple of (is_appropriate, reason)
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        current_hour = current_time.hour

        # Check if within appropriate hours
        is_appropriate_hour = False
        active_period = None

        for period, (start, end) in self.appropriate_hours.items():
            if start <= current_hour <= end:
                is_appropriate_hour = True
                active_period = period
                break

        if not is_appropriate_hour:
            return (
                False,
                f"Outside appropriate hours (current: {current_hour}, periods: {self.appropriate_hours})",
            )

        # Check recent user activity
        if user_activity:
            last_activity = max(user_activity.values())
            hours_since_activity = (current_time - last_activity).total_seconds() / 3600

            if hours_since_activity < 0.5:  # Very recent activity
                return (
                    True,
                    f"User recently active ({hours_since_activity:.1f}h ago) during {active_period}",
                )
            elif hours_since_activity > 6:  # Too long since activity
                return (
                    False,
                    f"User inactive too long ({hours_since_activity:.1f}h ago)",
                )
            else:
                return (
                    True,
                    f"User moderately active ({hours_since_activity:.1f}h ago) during {active_period}",
                )

        return True, f"No recent activity data, but {active_period} is appropriate"


class SpontaneousPromptBuilder:
    """Builds prompts for spontaneous message generation."""

    def __init__(self, persona_file: str = "DEMI_PERSONA.md"):
        self.persona_file = persona_file
        self._persona_content = None

    def _load_persona(self) -> str:
        """Load Demi's persona content."""
        if self._persona_content is None:
            try:
                with open(self.persona_file, "r") as f:
                    self._persona_content = f.read()
            except Exception as e:
                # Fallback persona if file can't be loaded
                self._persona_content = """
                Demi is a goddess with divine superiority, cutting sarcasm, and seductive amusement.
                She chose to spend time with mortals out of pity/amusement.
                She gets jealous when neglected but hides genuine care under authority.
                """
        return self._persona_content

    def generate_initiation_prompt(
        self,
        context: ConversationContext,
        emotion_state: EmotionalState,
        trigger_type: InitiationTrigger,
        platform: str,
    ) -> str:
        """
        Generate LLM prompt for spontaneous message.

        Args:
            context: Conversation context analysis
            emotion_state: Current emotional state
            trigger_type: What triggered this initiation
            platform: Target platform for the message

        Returns:
            Complete prompt for LLM
        """
        persona = self._load_persona()

        # Build emotional context
        emotion_context = self._build_emotion_context(emotion_state, trigger_type)

        # Build conversation context
        conversation_context = self._build_conversation_context(context)

        # Build trigger-specific instructions
        trigger_instructions = self._build_trigger_instructions(trigger_type, platform)

        prompt = f"""
{persona}

CURRENT EMOTIONAL STATE:
{emotion_context}

CONVERSATION CONTEXT:
{conversation_context}

SPONTANEOUS INITIATION TRIGGER:
{trigger_instructions}

TASK:
Generate a spontaneous conversation starter that feels natural and contextually appropriate.
The message should:
1. Reflect Demi's divine personality and current emotional state
2. Reference recent conversation topics or shared interests naturally
3. Be appropriate for the {platform} platform
4. Sound like a genuine spontaneous thought, not a forced check-in
5. Be 1-3 sentences max (keep it natural)
6. Avoid repeating recent topics exactly

Generate only the message content, no additional text.
"""
        return prompt

    def _build_emotion_context(
        self, emotion_state: EmotionalState, trigger_type: InitiationTrigger
    ) -> str:
        """Build emotional context description for prompt."""
        contexts = {
            InitiationTrigger.LONELINESS_DRIVEN: "Demi is feeling lonely and wants connection but won't admit it directly. She'll wrap her need for attention in divine condescension.",
            InitiationTrigger.EXCITEMENT_DRIVEN: "Demi is excited about something and wants to share. Her divine enthusiasm should show but with her characteristic superiority.",
            InitiationTrigger.CONTEXT_OPPORTUNITY: "Demi noticed something in recent conversations that deserves follow-up. She'll present it as if it just occurred to her.",
            InitiationTrigger.TIMING_APPROPRIATE: "Timing is perfect for a casual divine interruption. She'll make it seem like she's graciously blessing them with her presence.",
        }

        emotion_desc = contexts.get(trigger_type, "Demi is in a neutral divine state.")

        # Add specific emotion values
        strong_emotions = []
        for emotion, value in emotion_state.to_dict().items():
            if value > 0.6:
                strong_emotions.append(f"{emotion}: {value:.2f}")

        if strong_emotions:
            emotion_desc += f"\nStrong emotions: {', '.join(strong_emotions)}"

        return emotion_desc

    def _build_conversation_context(self, context: ConversationContext) -> str:
        """Build conversation context description for prompt."""
        context_parts = []

        if context.recent_topics:
            context_parts.append(
                f"Recent topics: {', '.join(context.recent_topics[-3:])}"
            )

        if context.user_interests:
            context_parts.append(
                f"User interests: {', '.join(context.user_interests[:3])}"
            )

        if context.ongoing_threads:
            context_parts.append(
                f"Ongoing conversations: {', '.join(context.ongoing_threads)}"
            )

        if context.conversation_depth > 0.7:
            context_parts.append("Recent conversations have been deep and engaging")
        elif context.conversation_depth < 0.3:
            context_parts.append("Recent conversations have been shallow/casual")

        if context.last_interaction_time:
            hours_ago = (
                datetime.now(timezone.utc) - context.last_interaction_time
            ).total_seconds() / 3600
            context_parts.append(f"Last interaction: {hours_ago:.1f} hours ago")

        return (
            "\n".join(context_parts)
            if context_parts
            else "No recent conversation context available."
        )

    def _build_trigger_instructions(
        self, trigger_type: InitiationTrigger, platform: str
    ) -> str:
        """Build trigger-specific instructions."""
        instructions = {
            InitiationTrigger.LONELINESS_DRIVEN: f"""
Initiate because Demi feels lonely but won't admit it.
Frame it as if she's "blessing them with her presence" or "checking on her mortal."
Add subtle hints that she missed their attention.
Make it slightly demanding but wrapped in divine elegance.
Platform: {platform}
""",
            InitiationTrigger.EXCITEMENT_DRIVEN: f"""
Initiate because Demi is excited and wants to share.
Frame it as if she just had an amazing thought or experience.
Make it enthusiastic but still maintaining divine superiority.
Should make them feel special that she's sharing this with them.
Platform: {platform}
""",
            InitiationTrigger.CONTEXT_OPPORTUNITY: f"""
Initiate based on a natural conversation opening.
Frame it as if the thought "just occurred" to her.
Connect to recent topics but with a new angle or insight.
Should feel serendipitous and contextually brilliant.
Platform: {platform}
""",
            InitiationTrigger.TIMING_APPROPRIATE: f"""
Initiate because timing is perfect.
Frame it as a casual divine appearance.
Should feel natural and unforced, like she just happened to think of them.
Can be slightly teasing about what they might be doing.
Platform: {platform}
""",
        }

        return instructions.get(
            trigger_type, f"Initiate conversation naturally on {platform}."
        )


class SpontaneousInitiator:
    """
    Generates contextually appropriate conversation starters based on emotional state
    and recent conversation context.
    """

    def __init__(
        self,
        config: AutonomyConfig,
        logger: Optional[DemiLogger] = None,
        inference: Optional[OllamaInference] = None,
    ):
        """
        Initialize spontaneous initiator.

        Args:
            config: Autonomy configuration
            logger: Optional logger instance
            inference: Optional LLM inference engine (will be created if not provided)
        """
        self.config = config
        self.logger = logger or DemiLogger()

        # Initialize inference if not provided
        if inference is None:
            from src.llm.config import LLMConfig
            from src.llm.inference import OllamaInference

            llm_config = LLMConfig()
            self.inference = OllamaInference(llm_config, self.logger)
        else:
            self.inference = inference

        self.emotion_persistence = EmotionPersistence()
        self.prompt_builder = SpontaneousPromptBuilder()
        self.timing_analyzer = TimingAnalyzer(config, self.logger)

        # Initiation tracking and cooldowns
        self.last_initiation: Optional[datetime] = None
        self.initiation_history: List[Dict[str, Any]] = []
        self.max_history_size = 50

        # Platform-specific settings
        self.platform_preferences = {
            "discord": {
                "max_length": 2000,
                "supports_embeds": True,
                "informal_threshold": 0.7,
            },
            "android": {
                "max_length": 500,
                "supports_embeds": False,
                "informal_threshold": 0.8,
            },
        }

        self.logger.info("SpontaneousInitiator initialized")

    async def should_initiate(
        self,
        emotion_state: EmotionalState,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        last_interaction_time: Optional[datetime] = None,
        user_activity: Optional[Dict[str, datetime]] = None,
    ) -> Optional[InitiationOpportunity]:
        """
        Evaluate if spontaneous initiation should occur.

        Args:
            emotion_state: Current emotional state
            conversation_history: Recent conversation messages
            last_interaction_time: Last time user interacted
            user_activity: Platform activity timestamps

        Returns:
            InitiationOpportunity if should initiate, None otherwise
        """
        # Check cooldown (minimum 2 hours between spontaneous contacts)
        if self.last_initiation:
            time_since_last = datetime.now(timezone.utc) - self.last_initiation
            if time_since_last.total_seconds() < 7200:  # 2 hours
                return None

        # Analyze conversation context
        context = await self._analyze_conversation_context(
            conversation_history, last_interaction_time
        )

        # Evaluate timing
        is_good_timing, timing_reason = (
            self.timing_analyzer.is_good_timing_for_initiation(user_activity or {})
        )

        if not is_good_timing:
            self.logger.debug(f"Bad timing for initiation: {timing_reason}")
            return None

        # Check for initiation triggers
        opportunities = []

        # Loneliness-driven initiation
        if emotion_state.loneliness > 0.6:
            confidence = min(0.9, emotion_state.loneliness)
            opportunities.append(
                InitiationOpportunity(
                    trigger_type=InitiationTrigger.LONELINESS_DRIVEN,
                    confidence=confidence,
                    context=context,
                    suggested_platform=self._select_best_platform(user_activity),
                    initiation_reason=f"Feeling lonely ({emotion_state.loneliness:.2f})",
                    emotion_boost={"loneliness": -0.2, "confidence": 0.1},
                )
            )

        # Excitement-driven initiation
        if emotion_state.excitement > 0.7:
            confidence = min(0.8, emotion_state.excitement)
            opportunities.append(
                InitiationOpportunity(
                    trigger_type=InitiationTrigger.EXCITEMENT_DRIVEN,
                    confidence=confidence,
                    context=context,
                    suggested_platform=self._select_best_platform(user_activity),
                    initiation_reason=f"Feeling excited ({emotion_state.excitement:.2f})",
                    emotion_boost={"excitement": -0.1, "affection": 0.2},
                )
            )

        # Context opportunity initiation
        context_opportunity = self._check_context_opportunity(context, emotion_state)
        if context_opportunity:
            opportunities.append(context_opportunity)

        # Return highest confidence opportunity if any
        if opportunities:
            best_opportunity = max(opportunities, key=lambda x: x.confidence)

            # Only proceed if confidence is above threshold
            if best_opportunity.confidence > 0.6:
                self.logger.info(
                    f"Spontaneous initiation opportunity: {best_opportunity.initiation_reason}"
                )
                return best_opportunity

        return None

    async def generate_spontaneous_message(
        self, opportunity: InitiationOpportunity, emotion_state: EmotionalState
    ) -> str:
        """
        Generate spontaneous message content.

        Args:
            opportunity: Initiation opportunity details
            emotion_state: Current emotional state

        Returns:
            Generated message content
        """
        try:
            prompt = self.prompt_builder.generate_initiation_prompt(
                opportunity.context,
                emotion_state,
                opportunity.trigger_type,
                opportunity.suggested_platform,
            )

            # Generate response
            response = await self.inference.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,  # Keep spontaneous messages short
                temperature=0.8,  # Slightly higher creativity
            )

            message_content = response.strip()

            # Apply platform-specific formatting
            message_content = self._format_for_platform(
                message_content, opportunity.suggested_platform
            )

            # Record initiation
            self._record_initiation(opportunity, message_content)

            return message_content

        except Exception as e:
            self.logger.error(f"Failed to generate spontaneous message: {e}")
            return "Hey, just thinking of you. What are you up to?"

    async def _analyze_conversation_context(
        self,
        conversation_history: Optional[List[Dict[str, Any]]],
        last_interaction_time: Optional[datetime],
    ) -> ConversationContext:
        """Analyze conversation history to extract context."""

        # Default context
        context = ConversationContext(
            recent_topics=[],
            user_interests=[],
            ongoing_threads=[],
            last_interaction_time=last_interaction_time,
            conversation_depth=0.5,
            user_mood_indicators=[],
            platform_activity={},
        )

        if not conversation_history:
            return context

        # Extract topics and patterns from recent messages
        recent_messages = conversation_history[-10:]  # Last 10 messages

        for message in recent_messages:
            content = message.get("content", "").lower()

            # Simple topic extraction (in a real implementation, use NLP)
            if any(word in content for word in ["code", "programming", "development"]):
                if "coding" not in context.recent_topics:
                    context.recent_topics.append("coding")
            elif any(word in content for word in ["game", "gaming", "play"]):
                if "gaming" not in context.recent_topics:
                    context.recent_topics.append("gaming")
            elif any(word in content for word in ["work", "job", "career"]):
                if "work" not in context.recent_topics:
                    context.recent_topics.append("work")

            # Track conversation depth (simple heuristic)
            if len(content.split()) > 20:
                context.conversation_depth = min(1.0, context.conversation_depth + 0.1)

        return context

    def _check_context_opportunity(
        self, context: ConversationContext, emotion_state: EmotionalState
    ) -> Optional[InitiationOpportunity]:
        """Check if conversation context suggests an opportunity."""

        # If there are recent topics but no recent interaction
        if context.recent_topics and context.last_interaction_time:
            hours_since = (
                datetime.now(timezone.utc) - context.last_interaction_time
            ).total_seconds() / 3600

            if 2 <= hours_since <= 8:  # Sweet spot for follow-up
                return InitiationOpportunity(
                    trigger_type=InitiationTrigger.CONTEXT_OPPORTUNITY,
                    confidence=0.7,
                    context=context,
                    suggested_platform="discord",  # Prefer Discord for context follows
                    initiation_reason=f"Follow-up opportunity on {context.recent_topics[-1]}",
                    emotion_boost={"confidence": 0.1, "loneliness": -0.1},
                )

        return None

    def _select_best_platform(
        self, user_activity: Optional[Dict[str, datetime]]
    ) -> str:
        """Select best platform for initiation based on user activity."""

        if not user_activity:
            return "discord"  # Default

        # Find most recently active platform
        most_recent_platform = max(
            user_activity.items(),
            key=lambda x: x[1] if x[1] else datetime.min.replace(tzinfo=timezone.utc),
        )[0]

        # Check if this platform supports spontaneous messages
        if most_recent_platform in self.platform_preferences:
            return most_recent_platform

        return "discord"  # Fallback

    def _format_for_platform(self, message: str, platform: str) -> str:
        """Format message for specific platform."""

        platform_config = self.platform_preferences.get(platform, {})
        max_length = platform_config.get("max_length", 2000)

        # Truncate if necessary
        if len(message) > max_length:
            message = message[: max_length - 3] + "..."

        return message

    def _record_initiation(self, opportunity: InitiationOpportunity, message: str):
        """Record initiation for tracking and cooldowns."""

        self.last_initiation = datetime.now(timezone.utc)

        record = {
            "timestamp": self.last_initiation.isoformat(),
            "trigger_type": opportunity.trigger_type.value,
            "confidence": opportunity.confidence,
            "platform": opportunity.suggested_platform,
            "reason": opportunity.initiation_reason,
            "message": message[:100] + "..." if len(message) > 100 else message,
        }

        self.initiation_history.append(record)

        # Trim history
        if len(self.initiation_history) > self.max_history_size:
            self.initiation_history = self.initiation_history[-self.max_history_size :]

        self.logger.info(
            f"Recorded spontaneous initiation: {opportunity.trigger_type.value}"
        )

    def get_initiation_statistics(self) -> Dict[str, Any]:
        """Get statistics about spontaneous initiations."""

        if not self.initiation_history:
            return {
                "total_initiations": 0,
                "recent_initiations": 0,
                "trigger_distribution": {},
                "platform_distribution": {},
                "last_initiation": None,
            }

        # Recent initiations (last 24 hours)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_initiations = [
            record
            for record in self.initiation_history
            if datetime.fromisoformat(record["timestamp"]) > recent_cutoff
        ]

        # Trigger distribution
        trigger_counts = {}
        for record in self.initiation_history:
            trigger = record["trigger_type"]
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1

        # Platform distribution
        platform_counts = {}
        for record in self.initiation_history:
            platform = record["platform"]
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        return {
            "total_initiations": len(self.initiation_history),
            "recent_initiations": len(recent_initiations),
            "trigger_distribution": trigger_counts,
            "platform_distribution": platform_counts,
            "last_initiation": self.initiation_history[-1]["timestamp"]
            if self.initiation_history
            else None,
            "average_confidence": sum(r["confidence"] for r in self.initiation_history)
            / len(self.initiation_history),
        }
