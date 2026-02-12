# src/emotion/models.py
from dataclasses import dataclass, field
from typing import Dict
from datetime import datetime, timezone


@dataclass
class EmotionalState:
    """
    Demi's emotional state across 9 dimensions.
    Each emotion is a percentage (0.0-1.0).
    Momentum tracking records overflow for cascade effects.
    """

    # Core 5 emotions
    loneliness: float = 0.5
    excitement: float = 0.5
    frustration: float = 0.5
    jealousy: float = 0.5
    vulnerability: float = 0.5

    # Additional 4 dimensions
    confidence: float = 0.5
    curiosity: float = 0.5
    affection: float = 0.5
    defensiveness: float = 0.5

    # Momentum tracking (how much each emotion exceeded 1.0)
    # Used by decay system to trigger cascade effects
    momentum: Dict[str, float] = field(default_factory=dict)

    # Metadata
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Emotion-specific floors (minimum values)
    _EMOTION_FLOORS = {
        "loneliness": 0.3,  # Loneliness lingers (hard to shake)
        "excitement": 0.1,  # Others have minimal baseline
        "frustration": 0.1,
        "jealousy": 0.1,
        "vulnerability": 0.1,
        "confidence": 0.1,
        "curiosity": 0.1,
        "affection": 0.1,
        "defensiveness": 0.1,
    }
    _EMOTION_NAMES = tuple(_EMOTION_FLOORS.keys())

    def __post_init__(self):
        """Validate state after initialization."""
        self.momentum = self._normalize_momentum(self.momentum)
        self._validate_bounds()
        self.last_updated = datetime.now(timezone.utc)

    def _validate_bounds(self):
        """Ensure all emotions are within [floor, 1.0]."""
        for name in self._EMOTION_NAMES:
            value = getattr(self, name)
            min_val = self._EMOTION_FLOORS.get(name, 0.1)
            max_val = 1.0

            if value < min_val:
                setattr(self, name, min_val)
            elif value > max_val:
                excess = value - max_val
                self.momentum[name] += excess
                setattr(self, name, max_val)

    def _normalize_momentum(self, momentum: Dict[str, float]) -> Dict[str, float]:
        """Normalize momentum dict to include all tracked emotions with float values."""
        normalized = {name: 0.0 for name in self._EMOTION_NAMES}
        if not isinstance(momentum, dict):
            return normalized

        for name in self._EMOTION_NAMES:
            raw = momentum.get(name, 0.0)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = 0.0
            normalized[name] = max(0.0, value)
        return normalized

    def set_emotion(
        self, emotion_name: str, value: float, momentum_override: bool = False
    ) -> None:
        """
        Set an emotion to a specific value with bounds checking.

        Args:
            emotion_name: Name of emotion to set
            value: Target value (0.0-1.0, or higher if allowing momentum)
            momentum_override: If True, allow value > 1.0 (sets momentum)
        """
        if emotion_name not in self._EMOTION_FLOORS:
            raise ValueError(f"Unknown emotion: {emotion_name}")

        if momentum_override:
            # Allow overflow, record momentum with bounds checking
            if value > 1.0:
                excess = value - 1.0
                self.momentum[emotion_name] = max(self.momentum[emotion_name], excess)
                setattr(self, emotion_name, 1.0)
            else:
                setattr(
                    self, emotion_name, max(value, self._EMOTION_FLOORS[emotion_name])
                )
                self.momentum[emotion_name] = 0.0
        else:
            # Strict bounds [floor, 1.0]
            floor = self._EMOTION_FLOORS[emotion_name]
            clamped = max(floor, min(1.0, value))
            setattr(self, emotion_name, clamped)
            self.momentum[emotion_name] = 0.0

        self.last_updated = datetime.now(timezone.utc)

    def delta_emotion(
        self, emotion_name: str, delta: float, momentum_override: bool = False
    ) -> None:
        """
        Change an emotion by a delta value.

        Args:
            emotion_name: Name of emotion to modify
            delta: Change amount (can be positive or negative)
            momentum_override: If True, allow crossing 1.0 (sets momentum)
        """
        current = getattr(self, emotion_name)
        new_value = current + delta
        self.set_emotion(emotion_name, new_value, momentum_override=momentum_override)

    def get_momentum(self, emotion_name: str) -> float:
        """Get current momentum for an emotion (how much it exceeded 1.0)."""
        return self.momentum.get(emotion_name, 0.0)

    def clear_momentum(self, emotion_name: str) -> None:
        """Clear momentum for an emotion (after cascade effect fires)."""
        self.momentum[emotion_name] = 0.0

    def to_dict(self) -> Dict:
        """Serialize emotional state to dict for database storage."""
        return {
            "loneliness": self.loneliness,
            "excitement": self.excitement,
            "frustration": self.frustration,
            "jealousy": self.jealousy,
            "vulnerability": self.vulnerability,
            "confidence": self.confidence,
            "curiosity": self.curiosity,
            "affection": self.affection,
            "defensiveness": self.defensiveness,
            "momentum": self.momentum.copy(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EmotionalState":
        """Deserialize emotional state from dict (from database)."""
        return cls(
            loneliness=data.get("loneliness", 0.5),
            excitement=data.get("excitement", 0.5),
            frustration=data.get("frustration", 0.5),
            jealousy=data.get("jealousy", 0.5),
            vulnerability=data.get("vulnerability", 0.5),
            confidence=data.get("confidence", 0.5),
            curiosity=data.get("curiosity", 0.5),
            affection=data.get("affection", 0.5),
            defensiveness=data.get("defensiveness", 0.5),
            momentum=data.get("momentum", {}),
        )

    def get_all_emotions(self) -> Dict[str, float]:
        """Return dict of all emotion names and current values."""
        return {name: getattr(self, name) for name in self._EMOTION_NAMES}

    def get_dominant_emotions(self, count: int = 3) -> list:
        """Return the N strongest emotions (by value)."""
        emotions = self.get_all_emotions()
        return sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:count]
