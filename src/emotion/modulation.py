# src/emotion/modulation.py
import yaml
import os
from typing import Dict, Optional
from dataclasses import dataclass, field
from src.emotion.models import EmotionalState


@dataclass
class ModulationParameters:
    """
    Response modulation parameters derived from emotional state.
    These are injected into LLM prompts in Phase 4.
    """

    sarcasm_level: float  # 0-1: how sarcastic/snark
    formality: float  # 0-1: how formal
    warmth: float  # 0-1: how warm/supportive
    response_length: int  # word count target
    humor_frequency: float  # 0-1: how often to be funny
    self_deprecation: float  # 0-1: how self-critical
    emoji_frequency: float  # 0-1: how many emojis
    nickname_frequency: float  # 0-1: use pet names

    # Tone flags (for LLM context)
    tone_flags: Dict[str, bool] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Generate prompt injection text for LLM."""
        lines = [
            f"Sarcasm level: {int(self.sarcasm_level * 100)}% (0=straight, 1=very sarcastic)",
            f"Formality: {int(self.formality * 100)}% (0=casual, 1=formal)",
            f"Warmth: {int(self.warmth * 100)}% (0=cold, 1=very warm)",
            f"Response length: ~{self.response_length} words",
            f"Humor frequency: {int(self.humor_frequency * 100)}%",
            f"Self-deprecation: {int(self.self_deprecation * 100)}%",
            f"Emoji frequency: {int(self.emoji_frequency * 100)}%",
            f"Nickname usage: {int(self.nickname_frequency * 100)}%",
        ]

        if self.tone_flags:
            lines.append("\nCommunication style:")
            for flag, value in self.tone_flags.items():
                if value:
                    lines.append(f"  - {flag.replace('_', ' ').title()}")

        return "\n".join(lines)


class PersonalityModulator:
    """
    Applies emotional state to produce personality modulation parameters.
    Bridges EmotionalState → response generation in LLM.
    """

    def __init__(self, traits_file: Optional[str] = None, logger=None):
        """
        Initialize modulator with personality traits.

        Args:
            traits_file: Path to personality_traits.yaml
                        (defaults to src/emotion/personality_traits.yaml)
            logger: Optional logger instance
        """
        self.logger = logger
        if traits_file is None:
            base_dir = os.path.dirname(__file__)
            traits_file = os.path.join(base_dir, "personality_traits.yaml")

        with open(traits_file, "r") as f:
            self.traits = yaml.safe_load(f)

        self.baseline = self.traits["baseline"]
        self.modulation = self.traits["modulation"]
        self.variance = self.traits["acceptable_variance"]

    def modulate(
        self,
        state: EmotionalState,
        situational_context: Optional[str] = None,
        force_serious: bool = False,
    ) -> ModulationParameters:
        """
        Apply emotional state to generate modulation parameters.

        Args:
            state: Current emotional state
            situational_context: Context like "death", "loss", "crisis" for override
            force_serious: If True, ignore emotion modulation (serious mode)

        Returns:
            ModulationParameters ready for LLM injection
        """
        # Check if serious context overrides emotional modulation
        serious_contexts = [
            "death",
            "died",
            "dying",
            "loss",
            "crisis",
            "emergency",
            "injury",
            "hospital",
        ]
        if situational_context:
            is_serious = any(
                ctx in situational_context.lower() for ctx in serious_contexts
            )
            if is_serious:
                force_serious = True

        # If serious, return baseline (neutral emotional mode)
        if force_serious:
            return self._create_parameters_from_baseline()

        # Otherwise, modulate based on emotional state
        params = {}

        # Get emotional state as dict for easy iteration
        emotions = state.get_all_emotions()

        # Start with baseline
        for key in [
            "sarcasm",
            "formality",
            "warmth",
            "humor_frequency",
            "self_deprecation",
            "emoji_frequency",
            "nickname_frequency",
        ]:
            params[key] = self.baseline[key]

        # Apply modulation for each emotion (weighted by deviation from neutral)
        tone_flags = {}

        for emotion_name, emotion_value in emotions.items():
            if emotion_name not in self.modulation:
                continue

            mods = self.modulation[emotion_name]

            # Apply modulation weighted by how far from neutral (0.5)
            # 0.5 = neutral (no modulation)
            # 0.0 or 1.0 = maximum modulation
            # This prevents all-neutral states from accumulating modulations
            deviation = abs(emotion_value - 0.5)

            for param_name, delta in mods.items():
                if param_name == "tone_flags" or not isinstance(delta, (int, float)):
                    # Collect tone flags separately
                    if param_name.endswith("_tone"):
                        tone_flags[param_name] = (
                            bool(delta) if isinstance(delta, bool) else delta
                        )
                    elif param_name == "can_refuse":
                        tone_flags["can_refuse"] = delta
                    continue

                if param_name in params:
                    # Add weighted modulation (only applies if emotion deviates from neutral)
                    # At 0.5: no change. At 0.0 or 1.0: full change
                    params[param_name] += (
                        delta * deviation * 2
                    )  # *2 because deviation is 0-0.5, we want weight 0-1

        # Clamp all values to [0, 1]
        for key in params:
            if key != "tone_flags":
                params[key] = max(0.0, min(1.0, params[key]))

        # Calculate response length based on curiosity
        base_length = self.baseline["typical_length"]
        response_length = int(
            base_length * (1.0 + (emotions.get("curiosity", 0.5) * 0.3))
        )
        response_length = max(
            self.baseline["min_length"],
            min(self.baseline["max_length"], response_length),
        )

        return ModulationParameters(
            sarcasm_level=params["sarcasm"],
            formality=params["formality"],
            warmth=params["warmth"],
            response_length=response_length,
            humor_frequency=params["humor_frequency"],
            self_deprecation=params["self_deprecation"],
            emoji_frequency=params["emoji_frequency"],
            nickname_frequency=params["nickname_frequency"],
            tone_flags=tone_flags,
        )

    def _create_parameters_from_baseline(self) -> ModulationParameters:
        """Create parameters directly from baseline (for serious mode)."""
        base = self.baseline
        return ModulationParameters(
            sarcasm_level=base["sarcasm"],
            formality=base["formality"],
            warmth=base["warmth"],
            response_length=base["typical_length"],
            humor_frequency=base["humor_frequency"],
            self_deprecation=base["self_deprecation"],
            emoji_frequency=base["emoji_frequency"],
            nickname_frequency=base["nickname_frequency"],
            tone_flags={"serious_mode": True},
        )

    def validate_variance(self, params: ModulationParameters) -> Dict[str, bool]:
        """
        Validate that modulation stays within acceptable variance.
        Used for personality consistency checks.

        Returns:
            Dict mapping parameter names to validity (True = within bounds)
        """
        base = self.baseline
        variance_min = self.variance["min_factor"]
        variance_max = self.variance["max_factor"]

        validation = {}
        validation["sarcasm"] = (
            base["sarcasm"] * variance_min
            <= params.sarcasm_level
            <= base["sarcasm"] * variance_max
        )
        validation["formality"] = (
            base["formality"] * variance_min
            <= params.formality
            <= base["formality"] * variance_max
        )
        validation["warmth"] = (
            base["warmth"] * variance_min
            <= params.warmth
            <= base["warmth"] * variance_max
        )

        return validation

    def get_self_awareness_comment(self, state: EmotionalState) -> Optional[str]:
        """
        Generate optional self-aware comment about emotional state.
        Returns None most of the time (don't force it).
        Returns text when emotional state is dramatic enough to acknowledge.

        Probability based on how different from neutral state Demi is.
        """
        emotions = state.get_all_emotions()

        # Get dominant emotion
        dominant = state.get_dominant_emotions(count=1)
        dominant_emotion_name = dominant[0][0]
        dominant_emotion_value = dominant[0][1]

        # Only generate commentary if dominant emotion is far enough from neutral
        # 0.5 = neutral, so deviation should be > 0.15
        deviation = abs(dominant_emotion_value - 0.5)
        if deviation < 0.15:
            return None  # Too neutral, nothing to say

        # Generate contextual comment based on dominant emotion
        if dominant_emotion_name == "loneliness" and dominant_emotion_value > 0.65:
            return "I've been pretty lonely lately, if I'm being honest."
        elif dominant_emotion_name == "excitement" and dominant_emotion_value > 0.7:
            return "Okay, I'm genuinely excited about this one!"
        elif dominant_emotion_name == "frustration" and dominant_emotion_value > 0.65:
            return "Fair warning: I'm in a bit of a mood right now."
        elif dominant_emotion_name == "vulnerability" and dominant_emotion_value > 0.55:
            return "I might be more honest than usual today."
        elif dominant_emotion_name == "confidence" and dominant_emotion_value > 0.7:
            return "I'm feeling pretty good about my abilities right now."
        elif dominant_emotion_name == "affection" and dominant_emotion_value > 0.65:
            return "You've been making me feel pretty cared-for lately."

        return None  # Default: don't force commentary
