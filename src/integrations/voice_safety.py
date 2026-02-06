"""Voice Safety - Prevents feedback loops and runaway activations.

Safety mechanisms:
1. Self-voice detection - Ignores Demi's own TTS output
2. Rate limiting - Max responses per minute per user
3. Duplicate detection - Ignores repeated identical phrases
4. Cooldown periods - Minimum time between activations
5. Loop detection - Tracks recent interactions to prevent loops
"""

import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from src.core.logger import get_logger

logger = get_logger()


@dataclass
class UserVoiceStats:
    """Voice interaction statistics for a user."""
    user_id: int
    last_activation: Optional[datetime] = None
    activation_count: int = 0
    recent_phrases: deque = field(default_factory=lambda: deque(maxlen=10))
    
    # Rate limiting
    _activation_times: deque = field(default_factory=lambda: deque(maxlen=20))
    
    def record_activation(self):
        """Record a voice activation."""
        now = datetime.now()
        self.last_activation = now
        self.activation_count += 1
        self._activation_times.append(now)
    
    def check_rate_limit(self, max_per_minute: int = 10) -> tuple[bool, str]:
        """Check if user is within rate limits.
        
        Returns:
            (allowed, reason)
        """
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Count activations in last minute
        recent_activations = sum(
            1 for t in self._activation_times 
            if t > one_minute_ago
        )
        
        if recent_activations >= max_per_minute:
            return False, f"Rate limit exceeded ({recent_activations}/{max_per_minute} per minute)"
        
        return True, None
    
    def is_duplicate(self, phrase: str, similarity_threshold: float = 0.9) -> bool:
        """Check if phrase is a near-duplicate of recent phrases.
        
        Args:
            phrase: Text to check
            similarity_threshold: How similar is considered duplicate
            
        Returns:
            True if this is a duplicate phrase
        """
        phrase_lower = phrase.lower().strip()
        
        for recent in self.recent_phrases:
            # Simple exact match for now
            if phrase_lower == recent:
                return True
            
            # Check for containment (shorter phrase inside longer)
            if len(phrase_lower) > 10 and phrase_lower in recent:
                return True
            if len(recent) > 10 and recent in phrase_lower:
                return True
        
        self.recent_phrases.append(phrase_lower)
        return False
    
    def check_cooldown(self, cooldown_seconds: float = 3.0) -> tuple[bool, float]:
        """Check if cooldown period has passed.
        
        Returns:
            (passed, remaining_seconds)
        """
        if not self.last_activation:
            return True, 0.0
        
        elapsed = (datetime.now() - self.last_activation).total_seconds()
        remaining = max(0, cooldown_seconds - elapsed)
        
        return remaining <= 0, remaining


@dataclass 
class VoiceLoopDetector:
    """Detects and prevents conversation loops.
    
    A loop occurs when:
    - User says X -> Demi responds Y -> User responds to Y with similar X
    - Demi keeps activating on her own responses
    """
    
    recent_demis_responses: deque = field(default_factory=lambda: deque(maxlen=5))
    recent_user_inputs: deque = field(default_factory=lambda: deque(maxlen=5))
    
    def record_demi_response(self, text: str):
        """Record Demi's response to detect self-activation."""
        self.recent_demis_responses.append(text.lower().strip()[:100])
    
    def record_user_input(self, text: str):
        """Record user's input."""
        self.recent_user_inputs.append(text.lower().strip()[:100])
    
    def is_self_activation(self, user_text: str) -> bool:
        """Check if user is just repeating Demi's response (echo).
        
        Args:
            user_text: The text the user spoke
            
        Returns:
            True if this appears to be an echo of Demi's response
        """
        user_lower = user_text.lower().strip()
        
        # Check against recent Demi responses
        for demi_response in self.recent_demis_responses:
            # Direct match
            if user_lower == demi_response:
                logger.warning(f"Self-activation detected: user repeated Demi's response")
                return True
            
            # High similarity check (user says part of what Demi said)
            if len(demi_response) > 20:
                # Check if significant portion matches
                words_user = set(user_lower.split())
                words_demi = set(demi_response.split())
                
                if len(words_user) > 0 and len(words_demi) > 0:
                    overlap = len(words_user & words_demi)
                    similarity = overlap / len(words_user)
                    
                    if similarity > 0.8:
                        logger.warning(f"Self-activation detected: high similarity ({similarity:.2f})")
                        return True
        
        return False
    
    def is_ping_pong_loop(self) -> bool:
        """Detect ping-pong loops where user and Demi keep repeating.
        
        Returns:
            True if a loop pattern is detected
        """
        if len(self.recent_user_inputs) < 3:
            return False
        
        # Check for repeating pattern
        inputs_list = list(self.recent_user_inputs)
        
        # Check if last 3 inputs are very similar
        if len(inputs_list) >= 3:
            last = inputs_list[-1]
            prev = inputs_list[-2]
            prev2 = inputs_list[-3]
            
            # All three are very similar = potential loop
            if last == prev or last == prev2:
                logger.warning("Ping-pong loop detected: user repeating similar phrases")
                return True
        
        return False


class VoiceSafetyGuard:
    """Main safety guard for voice interactions.
    
    Coordinates all safety checks to prevent:
    - Self-activation loops
    - Rate limit abuse
    - Duplicate spam
    - Echo feedback
    """
    
    def __init__(
        self,
        rate_limit_per_minute: int = 10,
        cooldown_seconds: float = 3.0,
        bot_user_id: Optional[int] = None
    ):
        """Initialize voice safety guard.
        
        Args:
            rate_limit_per_minute: Max voice activations per user per minute
            cooldown_seconds: Minimum seconds between activations
            bot_user_id: Demi's Discord user ID (to ignore self)
        """
        self.rate_limit = rate_limit_per_minute
        self.cooldown = cooldown_seconds
        self.bot_user_id = bot_user_id
        
        # Per-user stats
        self._user_stats: Dict[int, UserVoiceStats] = {}
        
        # Loop detection per guild
        self._loop_detectors: Dict[int, VoiceLoopDetector] = {}
        
        # Global state
        self._last_response_time: Optional[datetime] = None
        self._is_speaking: bool = False
        
        logger.info(
            f"VoiceSafetyGuard initialized: "
            f"rate_limit={rate_limit_per_minute}/min, cooldown={cooldown_seconds}s"
        )
    
    def _get_user_stats(self, user_id: int) -> UserVoiceStats:
        """Get or create user stats."""
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserVoiceStats(user_id=user_id)
        return self._user_stats[user_id]
    
    def _get_loop_detector(self, guild_id: int) -> VoiceLoopDetector:
        """Get or create loop detector for guild."""
        if guild_id not in self._loop_detectors:
            self._loop_detectors[guild_id] = VoiceLoopDetector()
        return self._loop_detectors[guild_id]
    
    def check_safety(
        self,
        user_id: int,
        username: str,
        text: str,
        guild_id: int,
        is_bot: bool = False
    ) -> tuple[bool, str]:
        """Run all safety checks on voice input.
        
        Args:
            user_id: Discord user ID
            username: Username
            text: Transcribed text
            guild_id: Discord guild ID
            is_bot: Whether this is the bot's own voice
            
        Returns:
            (allowed, reason)
        """
        # 1. Ignore bot's own voice
        if is_bot or (self.bot_user_id and user_id == self.bot_user_id):
            return False, "Ignoring bot's own voice"
        
        stats = self._get_user_stats(user_id)
        loop_detector = self._get_loop_detector(guild_id)
        
        # 2. Rate limit check
        allowed, reason = stats.check_rate_limit(self.rate_limit)
        if not allowed:
            logger.warning(f"Voice rate limit for {username}: {reason}")
            return False, reason
        
        # 3. Cooldown check
        passed, remaining = stats.check_cooldown(self.cooldown)
        if not passed:
            logger.debug(f"Voice cooldown for {username}: {remaining:.1f}s remaining")
            return False, f"Cooldown active ({remaining:.1f}s)"
        
        # 4. Duplicate detection
        if stats.is_duplicate(text):
            logger.warning(f"Duplicate phrase detected from {username}")
            return False, "Duplicate phrase detected"
        
        # 5. Self-activation check (user echoing Demi's response)
        if loop_detector.is_self_activation(text):
            return False, "Self-activation loop prevented"
        
        # 6. Ping-pong loop detection
        if loop_detector.is_ping_pong_loop():
            return False, "Ping-pong loop detected - taking a break"
        
        # Record the input for loop detection
        loop_detector.record_user_input(text)
        
        # All checks passed
        return True, None
    
    def record_activation(self, user_id: int):
        """Record a successful voice activation."""
        stats = self._get_user_stats(user_id)
        stats.record_activation()
    
    def record_demi_response(self, guild_id: int, text: str):
        """Record Demi's response for loop detection."""
        loop_detector = self._get_loop_detector(guild_id)
        loop_detector.record_demi_response(text)
        self._last_response_time = datetime.now()
    
    def set_speaking_state(self, speaking: bool):
        """Update whether Demi is currently speaking."""
        self._is_speaking = speaking
        if speaking:
            self._last_response_time = datetime.now()
    
    def is_speaking(self) -> bool:
        """Check if Demi is currently speaking."""
        return self._is_speaking
    
    def get_stats(self) -> dict:
        """Get safety guard statistics."""
        return {
            "total_users": len(self._user_stats),
            "total_activations": sum(s.activation_count for s in self._user_stats.values()),
            "monitored_guilds": len(self._loop_detectors),
            "is_speaking": self._is_speaking,
        }


# Global instance (singleton)
_safety_guard: Optional[VoiceSafetyGuard] = None


def get_voice_safety_guard(bot_user_id: Optional[int] = None) -> VoiceSafetyGuard:
    """Get global voice safety guard instance."""
    global _safety_guard
    if _safety_guard is None:
        _safety_guard = VoiceSafetyGuard(bot_user_id=bot_user_id)
    elif bot_user_id and _safety_guard.bot_user_id != bot_user_id:
        _safety_guard.bot_user_id = bot_user_id
    return _safety_guard
