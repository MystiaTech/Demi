# src/emotion/__init__.py
from .models import EmotionalState
from .decay import DecaySystem, DecayTuner
from .interactions import (
    InteractionType,
    InteractionHandler,
    EmotionInteractionAnalyzer,
)
from .modulation import PersonalityModulator, ModulationParameters
from .persistence import EmotionPersistence

__all__ = [
    "EmotionalState",
    "DecaySystem",
    "DecayTuner",
    "InteractionType",
    "InteractionHandler",
    "EmotionInteractionAnalyzer",
    "PersonalityModulator",
    "ModulationParameters",
    "EmotionPersistence",
]
