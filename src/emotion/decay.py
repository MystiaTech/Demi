# src/emotion/decay.py
import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, Optional, Callable
import math
from src.emotion.models import EmotionalState


class DecaySystem:
    """
    Background system that applies continuous emotional decay.
    Runs on 5-minute ticks (configurable).
    Different emotions decay at different rates.
    """

    def __init__(self, tick_interval_seconds: int = 300):
        """
        Initialize decay system.

        Args:
            tick_interval_seconds: How often to apply decay (default 300 = 5 min)
        """
        self.tick_interval = tick_interval_seconds
        self.is_running = False
        self._task = None
        self.last_tick = datetime.now(UTC)

        # Decay rates per emotion (percentage per 5-minute tick)
        # These are tuned based on research (CONTEXT.md)
        self.base_decay_rates = {
            "loneliness": 0.02,  # Slow decay (inertia, lingers)
            "excitement": 0.06,  # Fast decay (fleeting emotion)
            "frustration": 0.04,  # Medium decay
            "jealousy": 0.03,  # Slow-medium decay
            "vulnerability": 0.08,  # Very fast (temporary state)
            "confidence": 0.03,  # Slow-medium decay
            "curiosity": 0.05,  # Medium-fast decay
            "affection": 0.04,  # Medium decay
            "defensiveness": 0.05,  # Medium-fast decay
        }

        # Idle effects: applied every tick when no interaction recently
        # (tracked by calling code; DecaySystem just applies them)
        self.idle_effects = {
            "loneliness": 0.01,  # +0.01 per tick (~1% per 5 min)
            "excitement": -0.02,  # -0.02 per tick
            "affection": -0.015,  # Slight decay on warmth
            "confidence": -0.01,  # Slight decay on self-assurance
        }

        # Callbacks for testing
        self.on_decay_applied: Optional[Callable] = None

    async def start(self):
        """Start the background decay loop."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._decay_loop())

    async def stop(self):
        """Stop the background decay loop gracefully."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _decay_loop(self):
        """Background loop: apply decay every tick_interval seconds."""
        while self.is_running:
            try:
                await asyncio.sleep(self.tick_interval)
                # Tick happens in apply_decay() when called
            except asyncio.CancelledError:
                break

    def apply_decay(
        self,
        state: EmotionalState,
        idle_time_seconds: int = 0,
        force_idle: bool = False,
    ) -> EmotionalState:
        """
        Apply one tick of emotional decay to the state.

        Args:
            state: Current emotional state
            idle_time_seconds: Time since last interaction (for idle effects)
            force_idle: If True, apply idle effects regardless

        Returns:
            Updated emotional state
        """
        now = datetime.now(UTC)
        time_delta = (now - self.last_tick).total_seconds()
        self.last_tick = now

        # Clamp time delta to tick interval (prevent big jumps)
        time_delta = min(time_delta, self.tick_interval * 2)
        tick_multiplier = time_delta / self.tick_interval

        # Apply base decay to all emotions
        for emotion_name, base_rate in self.base_decay_rates.items():
            current = getattr(state, emotion_name)

            # Decay rate varies by current emotion level
            # High emotions (>0.8) decay 50% slower
            if current > 0.8:
                adjusted_rate = base_rate * 0.5
            else:
                adjusted_rate = base_rate

            # Apply logarithmic decay (fast at high values, slow at low)
            # Formula: emotion -= (adjusted_rate * current) * tick_multiplier
            decay_amount = adjusted_rate * current * tick_multiplier

            new_value = current - decay_amount
            state.set_emotion(emotion_name, new_value)

        # Apply idle effects if idle_time_seconds threshold exceeded
        idle_threshold_seconds = 300  # 5 minutes of no interaction = idle
        is_idle = (idle_time_seconds > idle_threshold_seconds) or force_idle

        if is_idle:
            for emotion_name, idle_delta in self.idle_effects.items():
                current = getattr(state, emotion_name)

                # Idle effects grow with idle time
                # More idle = stronger effect
                idle_multiplier = min(
                    idle_time_seconds / (3600 * 12), 3.0
                )  # Max 3x after 12 hours

                idle_effect = idle_delta * idle_multiplier * tick_multiplier
                new_value = current + idle_effect

                # Loneliness can go higher (with momentum if needed)
                if emotion_name == "loneliness" and new_value > 1.0:
                    state.set_emotion(emotion_name, new_value, momentum_override=True)
                else:
                    state.set_emotion(emotion_name, new_value)

        if self.on_decay_applied:
            self.on_decay_applied(state)

        return state

    def simulate_offline_decay(
        self, state: EmotionalState, offline_duration_seconds: int
    ) -> EmotionalState:
        """
        Simulate emotion decay for a period of offline time.
        Called when Demi restarts to "age" the emotions appropriately.

        Args:
            state: State from last shutdown (with timestamp)
            offline_duration_seconds: How long Demi was offline

        Returns:
            Decayed state as if she was idle the whole time
        """
        # Calculate how many ticks occurred during offline time
        num_ticks = offline_duration_seconds / self.tick_interval

        # Apply decay incrementally over the offline period
        for _ in range(int(num_ticks)):
            state = self.apply_decay(
                state,
                idle_time_seconds=self.tick_interval,  # Each tick treats as idle
                force_idle=True,  # Force idle effects
            )

        # Handle fractional tick
        remaining_seconds = offline_duration_seconds % self.tick_interval
        if remaining_seconds > 0:
            state = self.apply_decay(
                state, idle_time_seconds=remaining_seconds, force_idle=True
            )

        return state


class DecayTuner:
    """
    Utility class for testing and tuning decay rates.
    Allows simulation of various time periods.
    """

    def __init__(self, decay_system: DecaySystem):
        self.decay_system = decay_system

    def simulate_hours(
        self, state: EmotionalState, hours: int, idle: bool = False
    ) -> EmotionalState:
        """Simulate decay over N hours."""
        seconds = hours * 3600
        if idle:
            return self.decay_system.simulate_offline_decay(state, seconds)
        else:
            # Apply decay in ticks without idle effects
            num_ticks = seconds // self.decay_system.tick_interval
            for _ in range(num_ticks):
                state = self.decay_system.apply_decay(state, idle_time_seconds=0)
            return state

    def simulate_days(
        self, state: EmotionalState, days: int, idle: bool = False
    ) -> EmotionalState:
        """Simulate decay over N days."""
        return self.simulate_hours(state, days * 24, idle=idle)
