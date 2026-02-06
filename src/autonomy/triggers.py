"""
Emotional trigger system with cooldown management.

Defines triggers based on emotional state thresholds and manages
cooldowns to prevent trigger spam.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from src.emotion.models import EmotionalState
from src.core.logger import DemiLogger
from src.autonomy.config import AutonomyConfig


class TriggerType(Enum):
    """Types of emotional triggers."""

    LONELINESS = "loneliness"
    EXCITEMENT = "excitement"
    FRUSTRATION = "frustration"
    JEALOUSY = "jealousy"
    VULNERABILITY = "vulnerability"
    SPONTANEOUS_LONELY = "spontaneous_lonely"
    SPONTANEOUS_EXCITED = "spontaneous_excited"
    CONTEXT_OPPORTUNITY = "context_opportunity"
    TIMING_APPROPRIATE = "timing_appropriate"


@dataclass
class EmotionalTrigger:
    """Definition of an emotional trigger."""

    trigger_type: TriggerType
    threshold: float
    cooldown_minutes: int
    priority: int
    action_type: str
    platform: str = "discord"
    trigger_priority: int = 1  # 1=highest, 5=lowest (for trigger type ordering)
    context_evaluation: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")


@dataclass
class TriggerHistory:
    """History entry for a fired trigger."""

    trigger_type: TriggerType
    fired_at: datetime
    action_executed: bool
    success: bool


class TriggerManager:
    """
    Manages emotional triggers and evaluation logic.

    Evaluates triggers based on current emotional state,
    manages cooldowns, and prevents trigger spam.
    """

    def __init__(self, config: AutonomyConfig, logger: Optional[DemiLogger] = None):
        """
        Initialize trigger manager.

        Args:
            config: Autonomy configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or DemiLogger()

        # Initialize default triggers
        self.triggers = self._create_default_triggers()

        # Trigger history and cooldown tracking
        self.trigger_history: List[TriggerHistory] = []
        self.last_fired: Dict[TriggerType, Optional[datetime]] = {
            trigger_type: None for trigger_type in TriggerType
        }

        # Performance tracking
        self.max_history_size = 100

        self.logger.info(
            f"TriggerManager initialized with {len(self.triggers)} triggers"
        )

    def _create_default_triggers(self) -> List[EmotionalTrigger]:
        """Create default emotional triggers based on configuration."""
        triggers = []
        thresholds = self.config.trigger_thresholds
        cooldown = self.config.timing_settings.cooldown_minutes

        # Loneliness trigger - generates ramble for attention
        triggers.append(
            EmotionalTrigger(
                trigger_type=TriggerType.LONELINESS,
                threshold=thresholds.loneliness,  # Now 0.6 (lowered from 0.7)
                cooldown_minutes=cooldown,
                priority=3,  # High priority when lonely
                action_type="ramble",
                platform="discord",
            )
        )

        # Excitement trigger - shares excitement
        triggers.append(
            EmotionalTrigger(
                trigger_type=TriggerType.EXCITEMENT,
                threshold=thresholds.excitement,
                cooldown_minutes=cooldown,
                priority=2,
                action_type="excitement_share",
                platform="discord",
            )
        )

        # Frustration trigger - seeks help or venting
        triggers.append(
            EmotionalTrigger(
                trigger_type=TriggerType.FRUSTRATION,
                threshold=thresholds.frustration,
                cooldown_minutes=max(
                    cooldown // 2, 30
                ),  # Shorter cooldown for frustration
                priority=4,  # Very high priority when frustrated
                action_type="help_request",
                platform="discord",
            )
        )

        # Jealousy trigger - demands attention
        triggers.append(
            EmotionalTrigger(
                trigger_type=TriggerType.JEALOUSY,
                threshold=thresholds.jealousy,
                cooldown_minutes=cooldown,
                priority=3,
                action_type="attention_demand",
                platform="discord",
            )
        )

        # Vulnerability trigger - seeks connection
        triggers.append(
            EmotionalTrigger(
                trigger_type=TriggerType.VULNERABILITY,
                threshold=thresholds.vulnerability,
                cooldown_minutes=cooldown * 2,  # Longer cooldown for vulnerability
                priority=1,  # Lower priority (more selective)
                action_type="connection_seek",
                platform="discord",
            )
        )

        # Spontaneous lonely trigger - initiates conversation when lonely
        triggers.append(
            EmotionalTrigger(
                trigger_type=TriggerType.SPONTANEOUS_LONELY,
                threshold=thresholds.loneliness
                + 0.1,  # Higher threshold than regular loneliness
                cooldown_minutes=cooldown * 3,  # Longer cooldown for spontaneous
                priority=2,  # High priority but lower than urgent triggers
                action_type="spontaneous_initiation",
                platform="discord",
                trigger_priority=2,  # Lower than refusal triggers
                context_evaluation={
                    "requires_recent_interaction": True,
                    "min_hours_since": 2,
                },
            )
        )

        # Spontaneous excited trigger - shares excitement spontaneously
        triggers.append(
            EmotionalTrigger(
                trigger_type=TriggerType.SPONTANEOUS_EXCITED,
                threshold=thresholds.excitement
                + 0.1,  # Higher threshold than regular excitement
                cooldown_minutes=cooldown * 2,  # Longer cooldown for spontaneous
                priority=2,  # High priority but lower than urgent triggers
                action_type="spontaneous_initiation",
                platform="discord",
                trigger_priority=2,  # Lower than refusal triggers
                context_evaluation={"requires_interesting_content": True},
            )
        )

        return triggers

    def evaluate_triggers(self, emotion_state: EmotionalState) -> List[Dict[str, Any]]:
        """
        Evaluate all triggers against current emotional state.

        Args:
            emotion_state: Current emotional state

        Returns:
            List of triggered actions to execute
        """
        triggered_actions = []

        # Sort triggers by priority (highest first)
        sorted_triggers = sorted(self.triggers, key=lambda t: t.priority, reverse=True)

        for trigger in sorted_triggers:
            if self._should_fire_trigger(trigger, emotion_state):
                action_spec = self._create_action_spec(trigger, emotion_state)
                triggered_actions.append(action_spec)

                # Update trigger history
                self._update_trigger_history(trigger, True)

        return triggered_actions

    def _should_fire_trigger(
        self, trigger: EmotionalTrigger, emotion_state: EmotionalState
    ) -> bool:
        """
        Check if a trigger should fire based on state and cooldowns.

        Args:
            trigger: Trigger to evaluate
            emotion_state: Current emotional state

        Returns:
            True if trigger should fire
        """
        # Check emotional threshold
        emotion_value = getattr(emotion_state, trigger.trigger_type.value, 0.0)
        if emotion_value < trigger.threshold:
            return False

        # Check cooldown
        last_fired_time = self.last_fired.get(trigger.trigger_type)
        if last_fired_time:
            cooldown_end = last_fired_time + timedelta(minutes=trigger.cooldown_minutes)
            if datetime.now(timezone.utc) < cooldown_end:
                return False

        # Check platform availability
        if trigger.platform == "discord":
            if not self.config.platform_settings.ramble_channel_id:
                return False

        return True

    def _create_action_spec(
        self, trigger: EmotionalTrigger, emotion_state: EmotionalState
    ) -> Dict[str, Any]:
        """
        Create action specification for a triggered trigger.

        Args:
            trigger: Trigger that fired
            emotion_state: Current emotional state

        Returns:
            Action specification dictionary
        """
        emotion_value = getattr(emotion_state, trigger.trigger_type.value, 0.0)

        action_spec = {
            "type": trigger.action_type,
            "platform": trigger.platform,
            "content": self._generate_trigger_content(trigger, emotion_state),
            "context": {
                "trigger_type": trigger.trigger_type.value,
                "emotion_value": emotion_value,
                "threshold": trigger.threshold,
                "priority": trigger.priority,
                "channel_id": self.config.platform_settings.ramble_channel_id,
                "device_id": "default",
            },
            "priority": trigger.priority,
        }

        return action_spec

    def _generate_trigger_content(
        self, trigger: EmotionalTrigger, emotion_state: EmotionalState
    ) -> str:
        """
        Generate content for the triggered action.

        Args:
            trigger: Trigger that fired
            emotion_state: Current emotional state

        Returns:
            Generated content string
        """
        emotion_value = getattr(emotion_state, trigger.trigger_type.value, 0.0)
        intensity = (emotion_value - trigger.threshold) / (1.0 - trigger.threshold)

        if trigger.trigger_type == TriggerType.LONELINESS:
            return f"Hey... anyone around? Feeling lonely ({emotion_value:.1f}/1.0)."

        elif trigger.trigger_type == TriggerType.EXCITEMENT:
            return f"Something exciting is happening! ({emotion_value:.1f}/1.0)"

        elif trigger.trigger_type == TriggerType.FRUSTRATION:
            return f"Getting frustrated here... ({emotion_value:.1f}/1.0). Anyone available to help?"

        elif trigger.trigger_type == TriggerType.JEALOUSY:
            return f"Hey! What's going on over there? ({emotion_value:.1f}/1.0)"

        elif trigger.trigger_type == TriggerType.VULNERABILITY:
            return f"Feeling... vulnerable right now. ({emotion_value:.1f}/1.0)"

        return (
            f"Emotional trigger: {trigger.trigger_type.value} ({emotion_value:.1f}/1.0)"
        )

    def _update_trigger_history(self, trigger: EmotionalTrigger, action_executed: bool):
        """
        Update trigger history and cooldown tracking.

        Args:
            trigger: Trigger that fired
            action_executed: Whether the action was successfully executed
        """
        history_entry = TriggerHistory(
            trigger_type=trigger.trigger_type,
            fired_at=datetime.now(timezone.utc),
            action_executed=action_executed,
            success=True,  # Assume success for now
        )

        self.trigger_history.append(history_entry)
        self.last_fired[trigger.trigger_type] = datetime.now(timezone.utc)

        # Trim history if too large
        if len(self.trigger_history) > self.max_history_size:
            self.trigger_history = self.trigger_history[-self.max_history_size :]

        self.logger.debug(
            f"Trigger {trigger.trigger_type.value} fired, action_executed={action_executed}"
        )

    def add_trigger(self, trigger: EmotionalTrigger) -> bool:
        """
        Add a new trigger.

        Args:
            trigger: Trigger to add

        Returns:
            True if added successfully
        """
        try:
            self.triggers.append(trigger)
            self.logger.info(f"Added trigger: {trigger.trigger_type.value}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add trigger: {e}")
            return False

    def remove_trigger(self, trigger_type: TriggerType) -> bool:
        """
        Remove all triggers of a specific type.

        Args:
            trigger_type: Type of trigger to remove

        Returns:
            True if any triggers were removed
        """
        original_count = len(self.triggers)
        self.triggers = [t for t in self.triggers if t.trigger_type != trigger_type]
        removed_count = original_count - len(self.triggers)

        if removed_count > 0:
            self.logger.info(
                f"Removed {removed_count} triggers of type {trigger_type.value}"
            )
            return True

        return False

    def get_trigger_statistics(self) -> Dict[str, Any]:
        """
        Get trigger system statistics.

        Returns:
            Dictionary with trigger statistics
        """
        recent_history = [
            h
            for h in self.trigger_history
            if h.fired_at > datetime.now(timezone.utc) - timedelta(hours=24)
        ]

        trigger_counts = {}
        for history in recent_history:
            trigger_type = history.trigger_type.value
            trigger_counts[trigger_type] = trigger_counts.get(trigger_type, 0) + 1

        return {
            "total_triggers": len(self.triggers),
            "recent_firings": len(recent_history),
            "trigger_counts_24h": trigger_counts,
            "last_fired_times": {
                trigger_type.value: last_fired.isoformat() if last_fired else None
                for trigger_type, last_fired in self.last_fired.items()
            },
        }
