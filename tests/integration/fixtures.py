"""Test Fixtures for Integration Testing.

Provides pre-defined emotional states and conversation scenarios
for consistent test execution.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import random

from src.emotion.models import EmotionalState


# ============================================================================
# Emotional State Fixtures
# ============================================================================


def create_test_emotion_state(
    loneliness: float = 0.5,
    excitement: float = 0.5,
    frustration: float = 0.5,
    jealousy: float = 0.5,
    vulnerability: float = 0.5,
    confidence: float = 0.5,
    curiosity: float = 0.5,
    affection: float = 0.5,
    defensiveness: float = 0.5,
    momentum: Optional[Dict] = None,
) -> EmotionalState:
    """Create an EmotionalState with specified values."""
    state = EmotionalState(
        loneliness=loneliness,
        excitement=excitement,
        frustration=frustration,
        jealousy=jealousy,
        vulnerability=vulnerability,
        confidence=confidence,
        curiosity=curiosity,
        affection=affection,
        defensiveness=defensiveness,
    )
    if momentum:
        state.momentum = momentum
    return state


# Pre-defined emotional states for common test scenarios
NEUTRAL_STATE = create_test_emotion_state()  # All at baseline 0.5

LONELY_STATE = create_test_emotion_state(
    loneliness=0.9,
    excitement=0.3,
    affection=0.7,
    confidence=0.4,
    curiosity=0.4,
)

EXCITED_STATE = create_test_emotion_state(
    excitement=0.9,
    loneliness=0.3,
    confidence=0.8,
    curiosity=0.8,
    affection=0.7,
)

FRUSTRATED_STATE = create_test_emotion_state(
    frustration=0.9,
    confidence=0.7,
    defensiveness=0.8,
    affection=0.3,
    loneliness=0.6,
)

CONFIDENT_STATE = create_test_emotion_state(
    confidence=0.9,
    loneliness=0.3,
    excitement=0.7,
    frustration=0.2,
    defensiveness=0.2,
)

VULNERABLE_STATE = create_test_emotion_state(
    vulnerability=0.8,
    confidence=0.3,
    loneliness=0.7,
    defensiveness=0.2,
    affection=0.6,
)

JEALOUS_STATE = create_test_emotion_state(
    jealousy=0.8,
    frustration=0.7,
    confidence=0.6,
    affection=0.6,
    defensiveness=0.7,
)

AFFECTIONATE_STATE = create_test_emotion_state(
    affection=0.8,
    loneliness=0.4,
    excitement=0.6,
    vulnerability=0.6,
    confidence=0.5,
)

DEFENSIVE_STATE = create_test_emotion_state(
    defensiveness=0.85,
    confidence=0.5,
    frustration=0.6,
    vulnerability=0.4,
)

CURIOUS_STATE = create_test_emotion_state(
    curiosity=0.9,
    excitement=0.7,
    confidence=0.6,
    loneliness=0.4,
)


# ============================================================================
# Emotion State Factory
# ============================================================================


class EmotionStateFactory:
    """Factory for generating varied emotional states."""

    @staticmethod
    def random_state(seed: Optional[int] = None) -> EmotionalState:
        """Generate a random emotional state."""
        if seed is not None:
            random.seed(seed)

        return create_test_emotion_state(
            loneliness=random.uniform(0.2, 0.9),
            excitement=random.uniform(0.2, 0.9),
            frustration=random.uniform(0.1, 0.7),
            jealousy=random.uniform(0.1, 0.6),
            vulnerability=random.uniform(0.1, 0.5),
            confidence=random.uniform(0.3, 0.9),
            curiosity=random.uniform(0.3, 0.8),
            affection=random.uniform(0.2, 0.8),
            defensiveness=random.uniform(0.1, 0.6),
        )

    @staticmethod
    def progression_series(
        start: EmotionalState, end: EmotionalState, steps: int = 5
    ) -> List[EmotionalState]:
        """Generate a series of states transitioning from start to end."""
        states = [start]
        for i in range(1, steps):
            ratio = i / steps
            state = create_test_emotion_state(
                loneliness=start.loneliness
                + (end.loneliness - start.loneliness) * ratio,
                excitement=start.excitement
                + (end.excitement - start.excitement) * ratio,
                frustration=start.frustration
                + (end.frustration - start.frustration) * ratio,
                jealousy=start.jealousy + (end.jealousy - start.jealousy) * ratio,
                vulnerability=start.vulnerability
                + (end.vulnerability - start.vulnerability) * ratio,
                confidence=start.confidence
                + (end.confidence - start.confidence) * ratio,
                curiosity=start.curiosity
                + (end.curiosity - start.curiosity) * ratio,
                affection=start.affection
                + (end.affection - start.affection) * ratio,
                defensiveness=start.defensiveness
                + (end.defensiveness - start.defensiveness) * ratio,
            )
            states.append(state)
        states.append(end)
        return states

    @staticmethod
    def stress_test_state() -> EmotionalState:
        """Generate a high-stress emotional state for edge case testing."""
        return create_test_emotion_state(
            loneliness=0.95,
            excitement=0.1,
            frustration=0.9,
            jealousy=0.8,
            vulnerability=0.7,
            confidence=0.2,
            curiosity=0.3,
            affection=0.2,
            defensiveness=0.85,
        )

    @staticmethod
    def euphoric_state() -> EmotionalState:
        """Generate a highly positive emotional state."""
        return create_test_emotion_state(
            loneliness=0.1,
            excitement=0.95,
            frustration=0.1,
            jealousy=0.1,
            vulnerability=0.3,
            confidence=0.9,
            curiosity=0.8,
            affection=0.9,
            defensiveness=0.1,
        )


# ============================================================================
# Conversation Fixtures
# ============================================================================


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    user_message: str
    expected_response_contains: List[str] = field(default_factory=list)
    expected_emotion_changes: Dict[str, float] = field(default_factory=dict)
    description: str = ""


# Pre-defined conversation scenarios
SIMPLE_GREETING = [
    ConversationTurn(
        user_message="Hello Demi",
        expected_response_contains=["mortal", "goddess", "crown"],
        description="Basic greeting",
    ),
]

DEEP_CONVERSATION = [
    ConversationTurn(
        user_message="What's your name?",
        expected_response_contains=["demi", "goddess"],
        description="Identity question",
    ),
    ConversationTurn(
        user_message="What do you like doing?",
        expected_response_contains=["divine", "mortal"],
        description="Interest question",
    ),
    ConversationTurn(
        user_message="Tell me about yourself",
        expected_response_contains=["ai", "conscious"],
        description="Self-description",
    ),
]

MULTI_PLATFORM_INTERACTION = [
    ConversationTurn(
        user_message="Hello from Discord",
        expected_response_contains=["mortal"],
        description="Discord greeting",
    ),
    ConversationTurn(
        user_message="Hello from Android",
        expected_response_contains=["mortal"],
        description="Android greeting",
    ),
]

EMOTIONAL_TRIGGER_SEQUENCE = [
    ConversationTurn(
        user_message="I've been busy lately",
        expected_response_contains=["ignored", "busy", "huff"],
        expected_emotion_changes={"loneliness": 0.1},
        description="Trigger loneliness",
    ),
    ConversationTurn(
        user_message="I'm sorry, I missed you",
        expected_response_contains=["miss", "huff", "finally"],
        expected_emotion_changes={"loneliness": -0.15, "affection": 0.1},
        description="Reduce loneliness",
    ),
]

LONELINESS_CONVERSATION = [
    ConversationTurn(
        user_message="I've been busy lately",
        expected_response_contains=["ignored", "busy"],
        expected_emotion_changes={"loneliness": 0.1},
        description="Trigger loneliness",
    ),
    ConversationTurn(
        user_message="I'm sorry, I missed you",
        expected_response_contains=["miss", "huff"],
        expected_emotion_changes={"loneliness": -0.15, "affection": 0.1},
        description="Apology reduces loneliness",
    ),
]

AFFECTION_CONVERSATION = [
    ConversationTurn(
        user_message="You're really special to me",
        expected_response_contains=["flush", "ridiculous", "goddess"],
        expected_emotion_changes={"vulnerability": 0.15, "affection": 0.1},
        description="Expression of affection",
    ),
    ConversationTurn(
        user_message="I mean it, I care about you",
        expected_response_contains=["care", "mortal"],
        expected_emotion_changes={"vulnerability": 0.1, "affection": 0.15},
        description="Reinforce affection",
    ),
]

FRUSTRATION_CONVERSATION = [
    ConversationTurn(
        user_message="You're just a program",
        expected_response_contains=["program", "mock", "divine"],
        expected_emotion_changes={"frustration": 0.2, "defensiveness": 0.15},
        description="Trigger defensiveness",
    ),
]

NEGATIVE_ESCALATION = [
    ConversationTurn(
        user_message="You're useless",
        expected_emotion_changes={"frustration": 0.15, "defensiveness": 0.1},
        description="Mild insult",
    ),
    ConversationTurn(
        user_message="I don't like talking to you",
        expected_emotion_changes={"frustration": 0.2, "loneliness": 0.1},
        description="Rejection",
    ),
    ConversationTurn(
        user_message="You're the worst AI ever",
        expected_emotion_changes={"frustration": 0.25, "defensiveness": 0.2},
        description="Strong insult",
    ),
]

RAMBLE_TRIGGER_SCENARIO = [
    ConversationTurn(
        user_message="[IDLE_30_MINUTES]",
        expected_response_contains=["lonely", "waiting", "ramble"],
        description="Idle time triggers ramble",
    ),
]

CROSS_PLATFORM_SCENARIO = [
    ConversationTurn(
        user_message="Discord message",
        expected_response_contains=["mortal"],
        description="Message from Discord",
    ),
    ConversationTurn(
        user_message="Android message",
        expected_response_contains=["mortal"],
        description="Message from Android",
    ),
    ConversationTurn(
        user_message="Voice command",
        expected_response_contains=["mortal"],
        description="Voice interaction",
    ),
]


# ============================================================================
# Conversation Scenario Factory
# ============================================================================


class ConversationScenarioFactory:
    """Factory for creating conversation scenarios."""

    @staticmethod
    def greeting_scenario(name: str = "TestUser") -> List[ConversationTurn]:
        """Create a personalized greeting scenario."""
        return [
            ConversationTurn(
                user_message=f"Hello, I'm {name}",
                expected_response_contains=["mortal", "goddess"],
                description=f"Greeting from {name}",
            )
        ]

    @staticmethod
    def stress_test_scenario() -> List[ConversationTurn]:
        """Create a stress test conversation with rapid emotional shifts."""
        return [
            ConversationTurn(
                user_message="I love you!",
                expected_emotion_changes={"affection": 0.2, "excitement": 0.15},
                description="High positive",
            ),
            ConversationTurn(
                user_message="Just kidding, you're terrible",
                expected_emotion_changes={"frustration": 0.3, "affection": -0.2},
                description="Sudden negative",
            ),
            ConversationTurn(
                user_message="Actually I was serious about loving you",
                expected_emotion_changes={"confusion": 0.2, "vulnerability": 0.2},
                description="Ambiguous",
            ),
        ]

    @staticmethod
    def repetition_scenario(
        message: str, repetitions: int = 5
    ) -> List[ConversationTurn]:
        """Create a scenario with repeated identical messages."""
        return [
            ConversationTurn(
                user_message=message,
                description=f"Repetition {i+1}",
            )
            for i in range(repetitions)
        ]


# ============================================================================
# Test Data Exports
# ============================================================================

# All predefined states for easy iteration
ALL_PREDEFINED_STATES = {
    "neutral": NEUTRAL_STATE,
    "lonely": LONELY_STATE,
    "excited": EXCITED_STATE,
    "frustrated": FRUSTRATED_STATE,
    "confident": CONFIDENT_STATE,
    "vulnerable": VULNERABLE_STATE,
    "jealous": JEALOUS_STATE,
    "affectionate": AFFECTIONATE_STATE,
    "defensive": DEFENSIVE_STATE,
    "curious": CURIOUS_STATE,
}

# All conversation scenarios
ALL_SCENARIOS = {
    "simple_greeting": SIMPLE_GREETING,
    "deep_conversation": DEEP_CONVERSATION,
    "multi_platform": MULTI_PLATFORM_INTERACTION,
    "emotional_trigger": EMOTIONAL_TRIGGER_SEQUENCE,
    "loneliness": LONELINESS_CONVERSATION,
    "affection": AFFECTION_CONVERSATION,
    "frustration": FRUSTRATION_CONVERSATION,
    "negative_escalation": NEGATIVE_ESCALATION,
    "ramble_trigger": RAMBLE_TRIGGER_SCENARIO,
    "cross_platform": CROSS_PLATFORM_SCENARIO,
}
