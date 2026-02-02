"""Tests for Discord ramble decision logic and generation.

Tests the should_generate_ramble function that determines when Demi posts
autonomous rambles based on emotional state.
"""

import pytest
from datetime import datetime, timedelta, UTC
from src.integrations.discord_bot import should_generate_ramble


class TestRambleDecision:
    """Test suite for ramble decision logic"""

    def test_should_ramble_empty_emotion(self):
        """Empty emotion state should not trigger ramble"""
        result, trigger = should_generate_ramble({}, None)
        assert result is False
        assert trigger is None

    def test_should_ramble_loneliness_trigger(self):
        """Loneliness > 0.7 should trigger ramble"""
        emotion_state = {"loneliness": 0.8, "excitement": 0.1}
        result, trigger = should_generate_ramble(emotion_state, None)
        assert result is True
        assert trigger == "loneliness"

    def test_should_ramble_excitement_trigger(self):
        """Excitement > 0.8 should trigger ramble"""
        emotion_state = {"excitement": 0.9, "loneliness": 0.1}
        result, trigger = should_generate_ramble(emotion_state, None)
        assert result is True
        assert trigger == "excitement"

    def test_should_ramble_frustration_trigger(self):
        """Frustration > 0.6 should trigger ramble"""
        emotion_state = {"frustration": 0.7}
        result, trigger = should_generate_ramble(emotion_state, None)
        assert result is True
        assert trigger == "frustration"

    def test_should_not_ramble_below_threshold(self):
        """Emotions below thresholds should not trigger ramble"""
        emotion_state = {"loneliness": 0.5, "excitement": 0.4}
        result, trigger = should_generate_ramble(emotion_state, None)
        assert result is False

    def test_should_not_ramble_recent_ramble(self):
        """Should not ramble if last ramble was too recent"""
        emotion_state = {"loneliness": 0.9}
        last_ramble = datetime.now(UTC) - timedelta(minutes=30)
        result, trigger = should_generate_ramble(
            emotion_state,
            last_ramble,
            min_interval_minutes=60
        )
        assert result is False  # Interval not met yet

    def test_should_ramble_after_interval(self):
        """Should ramble after minimum interval has passed"""
        emotion_state = {"excitement": 0.9}
        last_ramble = datetime.now(UTC) - timedelta(hours=2)
        result, trigger = should_generate_ramble(
            emotion_state,
            last_ramble,
            min_interval_minutes=60
        )
        assert result is True

    def test_loneliness_priority_over_lower_triggers(self):
        """Loneliness should be detected even with other emotions present"""
        emotion_state = {
            "loneliness": 0.75,
            "excitement": 0.85,  # Excitement is higher but loneliness checks first
        }
        result, trigger = should_generate_ramble(emotion_state, None)
        assert result is True
        # Note: Current implementation checks loneliness first, so it wins
        assert trigger == "loneliness"

    def test_excitement_boundary(self):
        """Test excitement at exact threshold boundary"""
        emotion_state = {"excitement": 0.8}  # Exactly at threshold
        result, trigger = should_generate_ramble(emotion_state, None)
        # 0.8 is NOT > 0.8, so should not trigger
        assert result is False

    def test_frustration_boundary(self):
        """Test frustration at exact threshold boundary"""
        emotion_state = {"frustration": 0.6}  # Exactly at threshold
        result, trigger = should_generate_ramble(emotion_state, None)
        # 0.6 is NOT > 0.6, so should not trigger
        assert result is False

    def test_none_emotion_state(self):
        """None emotion state should not trigger ramble"""
        result, trigger = should_generate_ramble(None, None)
        assert result is False
        assert trigger is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
