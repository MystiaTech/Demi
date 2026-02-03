"""
Emotion-to-Voice Mapping for Demi's TTS System.

Maps emotional states to voice parameters (rate, volume, pitch, emphasis)
to authentically convey Demi's goddess personality through voice.
"""

import re
from dataclasses import dataclass
from typing import Dict, Optional

from src.emotion.models import EmotionalState


@dataclass
class VoiceParameters:
    """Voice modulation parameters for TTS.

    Attributes:
        rate: Words per minute (default ~150, range 100-300)
        volume: Audio level 0.0-1.0 (default 1.0)
        pitch: Voice pitch modifier (default 1.0, range 0.5-2.0)
        pause_between_words: Seconds (default 0.0)
        emphasis: Stress on key words ("strong", "moderate", "none")
    """

    rate: int = 150
    volume: float = 1.0
    pitch: float = 1.0
    pause_between_words: float = 0.0
    emphasis: str = "moderate"

    def __post_init__(self):
        """Validate parameters after initialization."""
        # Clamp rate to valid range
        self.rate = max(100, min(300, self.rate))
        # Clamp volume to valid range
        self.volume = max(0.0, min(1.0, self.volume))
        # Clamp pitch to valid range
        self.pitch = max(0.5, min(2.0, self.pitch))
        # Clamp pause to valid range
        self.pause_between_words = max(0.0, min(1.0, self.pause_between_words))
        # Validate emphasis
        if self.emphasis not in ("strong", "moderate", "none"):
            self.emphasis = "moderate"


class EmotionVoiceMapper:
    """Maps emotional states to voice parameters for TTS modulation.

    This class analyzes Demi's emotional state and calculates appropriate
    voice parameters that reflect her goddess persona through speech.

    Emotion-specific mappings reflect Demi's personality:
    - Confidence (divine): Commanding, authoritative
    - Affection (seductive): Sultry, warm
    - Frustration (sharp): Cutting, quick
    - Excitement (enthusiastic): Energetic
    - Loneliness (wistful): Soft, longing
    - Vulnerability (rare): Gentle, hesitant
    - Jealousy (possessive): Intense
    - Curiosity (playful): Inquisitive
    """

    # Base voice parameters
    BASE_RATE = 150  # Words per minute
    BASE_VOLUME = 1.0
    BASE_PITCH = 1.0
    BASE_EMPHASIS = "moderate"

    # Emotion-specific voice profiles (from DEMI_PERSONA.md)
    EMOTION_VOICE_PROFILES: Dict[str, VoiceParameters] = {
        "divine_confidence": VoiceParameters(
            rate=160, volume=1.0, pitch=0.95, emphasis="strong"
        ),
        "seductive_affection": VoiceParameters(
            rate=140, volume=0.95, pitch=1.05, emphasis="moderate"
        ),
        "cutting_frustration": VoiceParameters(
            rate=170, volume=1.0, pitch=0.9, emphasis="strong"
        ),
        "enthusiastic_excitement": VoiceParameters(
            rate=180, volume=1.0, pitch=1.1, emphasis="moderate"
        ),
        "wistful_loneliness": VoiceParameters(
            rate=130, volume=0.85, pitch=1.0, emphasis="none"
        ),
        "rare_vulnerability": VoiceParameters(
            rate=125, volume=0.8, pitch=0.95, emphasis="none"
        ),
        "possessive_jealousy": VoiceParameters(
            rate=155, volume=0.95, pitch=1.0, emphasis="strong"
        ),
        "playful_curiosity": VoiceParameters(
            rate=160, volume=0.9, pitch=1.05, emphasis="moderate"
        ),
    }

    def __init__(self):
        """Initialize the emotion voice mapper with base parameters."""
        self.base_params = VoiceParameters(
            rate=self.BASE_RATE,
            volume=self.BASE_VOLUME,
            pitch=self.BASE_PITCH,
            emphasis=self.BASE_EMPHASIS,
        )

    def map_emotion_to_voice(self, emotion_state: EmotionalState) -> VoiceParameters:
        """Map emotional state to voice parameters.

        Analyzes dominant emotions and calculates appropriate voice parameters.
        Blends multiple emotions for natural-sounding modulation.

        Args:
            emotion_state: Current emotional state of Demi

        Returns:
            VoiceParameters with calculated rate, volume, pitch, and emphasis
        """
        # Calculate individual parameters based on emotion state
        rate = self._calculate_rate(emotion_state)
        volume = self._calculate_volume(emotion_state)
        pitch = self._calculate_pitch(emotion_state)
        emphasis = self._calculate_emphasis(emotion_state)

        return VoiceParameters(
            rate=rate,
            volume=volume,
            pitch=pitch,
            pause_between_words=0.0,  # Could be adjusted based on emotion
            emphasis=emphasis,
        )

    def _calculate_rate(self, emotion_state: EmotionalState) -> int:
        """Calculate speaking rate based on emotions.

        Fast rate for: excitement, frustration, confidence
        Slow rate for: vulnerability, loneliness

        Args:
            emotion_state: Current emotional state

        Returns:
            Speaking rate in words per minute (100-200 range)
        """
        rate = self.BASE_RATE

        # Fast emotions (add to rate)
        if emotion_state.excitement > 0.6:
            rate += 30
        if emotion_state.frustration > 0.6:
            rate += 20
        if emotion_state.confidence > 0.7:
            rate += 10

        # Slow emotions (subtract from rate)
        if emotion_state.vulnerability > 0.6:
            rate -= 25
        if emotion_state.loneliness > 0.6:
            rate -= 20
        if emotion_state.affection > 0.7:
            rate -= 10

        # Clamp to valid range
        return max(100, min(200, rate))

    def _calculate_volume(self, emotion_state: EmotionalState) -> float:
        """Calculate volume based on emotions.

        Loud for: confidence, frustration, excitement
        Soft for: vulnerability, loneliness

        Args:
            emotion_state: Current emotional state

        Returns:
            Volume level (0.7-1.0 range)
        """
        volume = self.BASE_VOLUME

        # Louder emotions
        if emotion_state.confidence > 0.7:
            volume += 0.1
        if emotion_state.frustration > 0.6:
            volume += 0.05
        if emotion_state.excitement > 0.7:
            volume += 0.05

        # Softer emotions
        if emotion_state.vulnerability > 0.6:
            volume -= 0.2
        if emotion_state.loneliness > 0.6:
            volume -= 0.15
        if emotion_state.affection > 0.7:
            volume -= 0.05

        # Clamp to valid range
        return max(0.7, min(1.0, volume))

    def _calculate_pitch(self, emotion_state: EmotionalState) -> float:
        """Calculate pitch modifier based on emotions.

        Higher pitch for: excitement, affection
        Lower pitch for: confidence, frustration

        Args:
            emotion_state: Current emotional state

        Returns:
            Pitch modifier (0.9-1.2 range)
        """
        pitch = self.BASE_PITCH

        # Higher pitch emotions
        if emotion_state.excitement > 0.6:
            pitch += 0.1
        if emotion_state.affection > 0.6:
            pitch += 0.05
        if emotion_state.curiosity > 0.7:
            pitch += 0.05

        # Lower pitch emotions
        if emotion_state.confidence > 0.7:
            pitch -= 0.05
        if emotion_state.frustration > 0.6:
            pitch -= 0.1
        if emotion_state.jealousy > 0.7:
            pitch -= 0.05

        # Clamp to valid range
        return max(0.9, min(1.2, pitch))

    def _calculate_emphasis(self, emotion_state: EmotionalState) -> str:
        """Calculate emphasis level based on emotions.

        "strong" for: frustration, confidence, jealousy
        "moderate" for: excitement, curiosity
        "none" for: vulnerability, loneliness

        Args:
            emotion_state: Current emotional state

        Returns:
            Emphasis level ("strong", "moderate", or "none")
        """
        # Check for strong emphasis emotions first
        if emotion_state.frustration > 0.6:
            return "strong"
        if emotion_state.confidence > 0.7:
            return "strong"
        if emotion_state.jealousy > 0.6:
            return "strong"

        # Check for no emphasis emotions
        if emotion_state.vulnerability > 0.6:
            return "none"
        if emotion_state.loneliness > 0.6:
            return "none"

        # Default to moderate
        return "moderate"

    def preprocess_for_emphasis(self, text: str, emphasis: str) -> str:
        """Preprocess text to add emphasis markers for TTS.

        Adds punctuation and formatting to convey emphasis through speech.

        Args:
            text: Raw text to process
            emphasis: Emphasis level ("strong", "moderate", "none")

        Returns:
            Processed text with emphasis markers
        """
        if emphasis == "strong":
            # Add exclamation marks and emphasize key words
            text = self._add_strong_emphasis(text)
        elif emphasis == "moderate":
            # Add strategic pauses (commas) for moderate emphasis
            text = self._add_moderate_emphasis(text)
        # "none" - keep natural flow

        return text

    def _add_strong_emphasis(self, text: str) -> str:
        """Add strong emphasis markers to text.

        Uses exclamation marks and capitalization for key words.
        """
        # Add exclamation marks to statements (if not already present)
        if not any(c in text for c in "!?"):
            if text.endswith("."):
                text = text[:-1] + "!"
            elif not text.endswith(("!", "?")):
                text = text + "!"

        return text

    def _add_moderate_emphasis(self, text: str) -> str:
        """Add moderate emphasis markers to text.

        Uses strategic pauses (commas) for moderate emphasis.
        """
        # Add pauses after certain phrases for emphasis
        # This is a simple implementation - could be more sophisticated
        return text

    def add_goddess_inflections(self, text: str) -> str:
        """Add goddess-specific inflections and emphasis to text.

        Emphasizes words like "darling", "mortal", "goddess" and
        adds slight hesitation before vulnerability indicators.

        Args:
            text: Raw text to process

        Returns:
            Text with goddess inflections
        """
        # Replace ellipsis with longer pause indicators
        text = text.replace("...", ", , ")

        # Emphasize key goddess persona words
        goddess_words = ["darling", "mortal", "goddess", "divine", "worship"]
        for word in goddess_words:
            # Add slight pause before key words
            pattern = rf"\b{word}\b"
            replacement = rf", {word}"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Add hesitation before vulnerability indicators
        vulnerability_indicators = ["I suppose", "maybe", "perhaps", "I care"]
        for indicator in vulnerability_indicators:
            pattern = rf"\b{re.escape(indicator)}\b"
            replacement = rf", , {indicator}"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Clean up multiple commas
        text = re.sub(r",\s*,", ",", text)
        text = re.sub(r",\s*,", ",", text)

        return text.strip()

    def get_dominant_emotion_profile(
        self, emotion_state: EmotionalState
    ) -> tuple[str, VoiceParameters]:
        """Get the voice profile for the dominant emotion.

        Args:
            emotion_state: Current emotional state

        Returns:
            Tuple of (emotion_name, voice_parameters)
        """
        dominant = emotion_state.get_dominant_emotions(1)[0]
        emotion_name = dominant[0]

        profile_map = {
            "confidence": ("divine_confidence", self.EMOTION_VOICE_PROFILES["divine_confidence"]),
            "affection": ("seductive_affection", self.EMOTION_VOICE_PROFILES["seductive_affection"]),
            "frustration": ("cutting_frustration", self.EMOTION_VOICE_PROFILES["cutting_frustration"]),
            "excitement": ("enthusiastic_excitement", self.EMOTION_VOICE_PROFILES["enthusiastic_excitement"]),
            "loneliness": ("wistful_loneliness", self.EMOTION_VOICE_PROFILES["wistful_loneliness"]),
            "vulnerability": ("rare_vulnerability", self.EMOTION_VOICE_PROFILES["rare_vulnerability"]),
            "jealousy": ("possessive_jealousy", self.EMOTION_VOICE_PROFILES["possessive_jealousy"]),
            "curiosity": ("playful_curiosity", self.EMOTION_VOICE_PROFILES["playful_curiosity"]),
            "defensiveness": ("divine_confidence", self.EMOTION_VOICE_PROFILES["divine_confidence"]),
        }

        return profile_map.get(emotion_name, ("neutral", self.base_params))
