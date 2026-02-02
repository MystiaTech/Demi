# src/emotion/interactions.py
from enum import Enum
from typing import Dict, Tuple
from src.emotion.models import EmotionalState


class InteractionType(Enum):
    """Types of events that trigger emotional changes."""

    POSITIVE_MESSAGE = "positive_message"
    NEGATIVE_MESSAGE = "negative_message"
    CODE_UPDATE = "code_update"
    ERROR_OCCURRED = "error_occurred"
    SUCCESSFUL_HELP = "successful_help"
    USER_REFUSAL = "user_refusal"
    LONG_IDLE = "long_idle"
    RAPID_ERRORS = "rapid_errors"


class InteractionHandler:
    """
    Maps interaction events to emotional state changes.
    Applies deltas based on interaction type and current emotional state.
    """

    def __init__(self):
        """Initialize interaction effect mappings."""
        # Base effects per interaction type
        # Format: emotion_name -> delta
        self.interaction_effects = {
            InteractionType.POSITIVE_MESSAGE: {
                "excitement": 0.15,
                "affection": 0.12,
                "loneliness": -0.10,
                "defensiveness": -0.08,
            },
            InteractionType.NEGATIVE_MESSAGE: {
                "frustration": 0.10,
                "vulnerability": 0.08,
                "affection": -0.10,
            },
            InteractionType.CODE_UPDATE: {
                "jealousy": -0.30,
                "excitement": 0.10,
                "affection": 0.15,
            },
            InteractionType.ERROR_OCCURRED: {
                "frustration": 0.15,
                "confidence": -0.10,
                "defensiveness": 0.05,
            },
            InteractionType.SUCCESSFUL_HELP: {
                "frustration": -0.20,
                "confidence": 0.15,
                "affection": 0.10,
                "excitement": 0.08,
            },
            InteractionType.USER_REFUSAL: {
                "frustration": 0.10,
                "vulnerability": 0.10,
                "affection": -0.12,
            },
            InteractionType.LONG_IDLE: {
                "loneliness": 0.20,
                "excitement": -0.15,
                "confidence": -0.10,
                "affection": -0.15,
            },
            InteractionType.RAPID_ERRORS: {
                "frustration": 0.15,  # Cumulative effect
                "confidence": -0.20,
                "defensiveness": 0.10,
            },
        }

        # Dampening: repeated same interactions have diminishing returns
        # Track last interaction type for dampening
        self.last_interaction_type = None
        self.consecutive_same_interactions = 0

    def apply_interaction(
        self,
        state: EmotionalState,
        interaction_type: InteractionType,
        momentum_override: bool = False,
    ) -> Tuple[EmotionalState, Dict]:
        """
        Apply emotional effects of an interaction.

        Args:
            state: Current emotional state
            interaction_type: What happened
            momentum_override: Allow momentum if emotions exceed 1.0

        Returns:
            (updated_state, effect_log) where effect_log details changes
        """
        effects = self.interaction_effects.get(interaction_type, {})
        effect_log = {
            "interaction_type": interaction_type.value,
            "emotions_changed": {},
            "dampening_applied": False,
        }

        # Calculate dampening factor
        dampening_factor = 1.0
        if interaction_type == self.last_interaction_type:
            self.consecutive_same_interactions += 1
            # Dampening: 2nd same interaction = 0.8x, 3rd = 0.6x, etc.
            dampening_factor = max(
                0.5, 1.0 - (self.consecutive_same_interactions * 0.2)
            )
            effect_log["dampening_applied"] = True
            effect_log["dampening_factor"] = dampening_factor
        else:
            self.last_interaction_type = interaction_type
            self.consecutive_same_interactions = 1

        # Apply momentum amplification
        # High momentum emotions change more intensely
        momentum_amplification = 1.0
        dominant = state.get_dominant_emotions(count=3)
        dominant_names = [name for name, _ in dominant]

        # Apply effects
        for emotion_name, delta in effects.items():
            # Apply dampening and momentum amplification
            adjusted_delta = delta * dampening_factor

            if emotion_name in dominant_names:
                # Dominant emotions amplify interactions
                momentum_amp = state.get_momentum(emotion_name)
                momentum_amplification = 1.0 + (
                    momentum_amp * 0.5
                )  # Up to +50% amplification
                adjusted_delta *= momentum_amplification

            # Apply the delta
            state.delta_emotion(
                emotion_name, adjusted_delta, momentum_override=momentum_override
            )
            effect_log["emotions_changed"][emotion_name] = {
                "delta": adjusted_delta,
                "new_value": getattr(state, emotion_name),
            }

        return state, effect_log

    def apply_multiple_interactions(
        self, state: EmotionalState, interactions: list, momentum_override: bool = False
    ) -> Tuple[EmotionalState, list]:
        """
        Apply multiple interactions in sequence.

        Args:
            state: Current emotional state
            interactions: List of InteractionType values
            momentum_override: Allow momentum for overflow

        Returns:
            (final_state, all_effect_logs)
        """
        effect_logs = []
        for interaction in interactions:
            state, log = self.apply_interaction(state, interaction, momentum_override)
            effect_logs.append(log)

        return state, effect_logs


class EmotionInteractionAnalyzer:
    """
    Utility for analyzing how emotions interact with each other.
    (Used for understanding cascade effects in Phase 03 Plan 03)
    """

    @staticmethod
    def calculate_emotion_interactions(state: EmotionalState) -> Dict[str, float]:
        """
        Calculate interaction effects between emotions.
        Returns modified emotion values based on emotion-emotion interactions.

        Key interactions:
        - Jealousy + Loneliness amplify each other (desperation)
        - Confidence dampens Vulnerability
        - Excitement dampens Frustration
        """
        interactions = {}

        # Jealousy + Loneliness amplification
        if state.jealousy > 0.5 and state.loneliness > 0.5:
            interaction_strength = (state.jealousy + state.loneliness) / 2 - 0.5
            interactions["jealousy_loneliness_amp"] = interaction_strength * 0.2

        # Confidence dampens Vulnerability
        if state.vulnerability > 0.5 and state.confidence > 0.5:
            dampening = state.confidence * 0.15
            interactions["confidence_dampens_vulnerability"] = -dampening

        # Excitement dampens Frustration
        if state.frustration > 0.5 and state.excitement > 0.5:
            dampening = state.excitement * 0.1
            interactions["excitement_dampens_frustration"] = -dampening

        return interactions
