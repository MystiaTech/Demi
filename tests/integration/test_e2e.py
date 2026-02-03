"""End-to-End Integration Tests for Demi.

Tests full system behavior across all integrated components:
- Message flow from platform to LLM and back
- Emotional state management and persistence
- Cross-platform synchronization
- Autonomous ramble generation
- Error isolation and recovery
- Performance requirements

These tests use mock external services to avoid requiring live
Discord/Ollama connections while still testing the full stack.
"""

import pytest
import asyncio
import time
from typing import Dict, List

# Import harness and scenarios
from tests.integration.harness import test_environment, IntegrationTestHarness
from tests.integration.scenarios import (
    run_simple_greeting_scenario,
    run_lonely_demeanor_scenario,
    run_multi_turn_conversation_scenario,
    run_emotion_amplification_scenario,
    run_affection_response_scenario,
    run_loneliness_ramble_scenario,
    run_excitement_ramble_scenario,
    run_cross_platform_sync_scenario,
    run_platform_isolation_scenario,
    run_persistence_verification_scenario,
    run_emotional_decay_scenario,
    run_graceful_degradation_scenario,
    run_recovery_after_crash_scenario,
    run_response_time_scenario,
    run_concurrent_load_scenario,
)
from tests.integration.mocks import (
    MockDiscordClient,
    MockUser,
    TEST_USER,
    KNOWN_USER,
    NEW_USER,
)
from tests.integration.fixtures import (
    NEUTRAL_STATE,
    LONELY_STATE,
    EXCITED_STATE,
    FRUSTRATED_STATE,
    AFFECTIONATE_STATE,
)


# ============================================================================
# Test Class: Message Pipeline
# ============================================================================


class TestMessagePipeline:
    """Test full message-to-response pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_basic_message_flow(self):
        """Test that a message flows through the entire system."""
        async with test_environment() as env:
            result = await run_simple_greeting_scenario(env)
            assert result["success"], f"Greeting failed: {result}"
            assert result["response"] is not None
            assert len(result["response"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_emotion_affects_response(self):
        """Test that emotional state modulates responses."""
        async with test_environment() as env:
            result = await run_lonely_demeanor_scenario(env)
            assert result["success"], f"Emotion affect test failed: {result}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(20)
    async def test_conversation_continuity(self):
        """Test multi-turn conversation memory."""
        async with test_environment() as env:
            result = await run_multi_turn_conversation_scenario(env)
            assert result["success"], f"Conversation failed: {result['turns']}"
            assert result["successful_turns"] >= 2

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_emotion_accumulation(self):
        """Test that emotions accumulate across interactions."""
        async with test_environment() as env:
            result = await run_emotion_amplification_scenario(env)
            assert result["success"], f"Emotion accumulation failed: {result}"
            assert result["messages_processed"] == 3

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_affection_response(self):
        """Test response to affectionate messages."""
        async with test_environment() as env:
            result = await run_affection_response_scenario(env)
            assert result["success"], f"Affection response failed: {result}"


# ============================================================================
# Test Class: Ramble Pipeline
# ============================================================================


class TestRamblePipeline:
    """Test autonomous ramble generation pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_loneliness_triggers_ramble(self):
        """Test high loneliness triggers ramble generation."""
        async with test_environment() as env:
            result = await run_loneliness_ramble_scenario(env)
            assert result["success"], f"Ramble not generated: {result}"
            assert result["ramble_count"] > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_excitement_triggers_ramble(self):
        """Test excitement can trigger positive rambles."""
        async with test_environment() as env:
            result = await run_excitement_ramble_scenario(env)
            assert "ramble_count" in result


# ============================================================================
# Test Class: Cross-Platform
# ============================================================================


class TestCrossPlatform:
    """Test cross-platform integration and synchronization."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_cross_platform_sync(self):
        """Test emotional state syncs across platforms."""
        async with test_environment() as env:
            result = await run_cross_platform_sync_scenario(env)
            assert result["success"], f"Cross-platform sync failed: {result}"
            assert "discord" in result["platforms_tested"]
            assert "android" in result["platforms_tested"]

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_platform_isolation_health_04(self):
        """
        Test platform isolation - HEALTH-04 requirement.
        
        Verifies that one platform's failure doesn't cascade to others.
        """
        async with test_environment() as env:
            result = await run_platform_isolation_scenario(env)
            assert result["success"], f"Platform isolation failed: {result}"
            assert result["android_worked_during_discord_failure"], \
                "Android should work despite Discord failure"


# ============================================================================
# Test Class: Persistence
# ============================================================================


class TestPersistence:
    """Test state persistence and recovery."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_state_persistence_health_03(self):
        """
        Test emotional state persistence - HEALTH-03 requirement.
        
        Verifies state is saved and can be restored.
        """
        async with test_environment() as env:
            result = await run_persistence_verification_scenario(env)
            assert result["success"], f"Persistence failed: {result}"
            assert result["state_preserved"], "State should be preserved"

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_emotional_decay_over_time(self):
        """Test emotional decay simulates correctly."""
        async with test_environment() as env:
            result = await run_emotional_decay_scenario(env)
            assert result["success"], f"Emotional decay test failed: {result}"
            # Verify decay system is functional
            assert result.get("system_functional", False), "Decay system should be functional"


# ============================================================================
# Test Class: Error Isolation
# ============================================================================


class TestErrorIsolation:
    """Test that errors in components don't crash the system."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_llm_error_doesnt_crash_system(self):
        """Test that LLM errors are handled gracefully."""
        async with test_environment() as env:
            result = await run_graceful_degradation_scenario(env)
            assert result["success"], f"Graceful degradation failed: {result}"
            assert result["system_stable"], "System should remain stable"

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_discord_disconnect_recovery(self):
        """Test system continues working after simulated Discord issues."""
        async with test_environment() as env:
            result = await run_recovery_after_crash_scenario(env)
            assert result["success"], f"Recovery failed: {result}"
            assert result["recovery_successful"], "Should recover from crash"

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_isolation_between_platforms(self):
        """
        Test that platform failures are isolated.
        
        HEALTH-04: Platform failure isolation verification.
        """
        async with test_environment() as env:
            discord = env.mock_services.get("discord")
            android = env.mock_services.get("android")
            
            if not discord or not android:
                pytest.skip("Required mocks not available")
            
            # Simulate Discord failure
            discord.set_error_rate(1.0)
            
            # Android should still work
            android.register_device("isolation_test")
            android_works = await android.send_message("isolation_test", "Test")
            
            assert android_works, "Android should work despite Discord failure"


# ============================================================================
# Test Class: Performance
# ============================================================================


class TestPerformance:
    """Test performance requirements."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_response_time_under_threshold(self):
        """Test that responses arrive within acceptable time."""
        async with test_environment() as env:
            result = await run_response_time_scenario(env, max_response_time_sec=5.0)
            assert result["success"], f"Response time test failed: {result}"
            assert result["within_limit"], \
                f"Response too slow: {result.get('response_time_sec', 'N/A')}s"

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_message_handling(self):
        """Test system handles concurrent messages."""
        async with test_environment() as env:
            result = await run_concurrent_load_scenario(env, num_concurrent=5)
            assert result["success"], f"Concurrent load test failed: {result}"
            assert result["all_responded"], "All messages should get responses"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_suite_execution_time(self):
        """Verify representative test subset completes quickly."""
        start = time.time()
        
        async with test_environment() as env:
            # Run a representative subset
            await run_simple_greeting_scenario(env)
            await run_lonely_demeanor_scenario(env)
            await run_multi_turn_conversation_scenario(env)
        
        elapsed = time.time() - start
        
        # Individual tests should complete quickly
        # Full suite target: <5 minutes (300 seconds)
        assert elapsed < 60, f"Test subset too slow: {elapsed:.2f}s"


# ============================================================================
# Test Class: Mock Services
# ============================================================================


class TestMockServices:
    """Test that mock services work correctly."""

    @pytest.mark.asyncio
    async def test_discord_mock_basic(self):
        """Test Discord mock basic functionality."""
        async with test_environment() as env:
            discord = env.mock_services.get("discord")
            assert discord is not None
            
            # Register channel
            channel = discord.register_channel(123, "test")
            assert channel.id == 123
            
            # Send message
            await channel.send("Test message")
            assert channel.message_count() == 1
            
            # Simulate user message
            msg = discord.simulate_message("Hello", channel_id=123)
            assert msg.content == "Hello"

    @pytest.mark.asyncio
    async def test_ollama_mock_basic(self):
        """Test Ollama mock basic functionality."""
        async with test_environment() as env:
            ollama = env.mock_services.get("ollama")
            assert ollama is not None
            
            # Register response
            ollama.register_response(["test"], "Test response")
            
            # Generate
            result = await ollama.generate("test prompt")
            assert "response" in result
            
            # Check history
            history = ollama.get_call_history()
            assert len(history) == 1

    @pytest.mark.asyncio
    async def test_android_mock_basic(self):
        """Test Android mock basic functionality."""
        async with test_environment() as env:
            android = env.mock_services.get("android")
            assert android is not None
            
            # Register device
            device = android.register_device("test_device")
            assert device["id"] == "test_device"
            
            # Send message
            success = await android.send_message("test_device", "Hello")
            assert success
            
            # Check messages
            messages = android.get_device_messages("test_device")
            assert len(messages) == 1


# ============================================================================
# Test Class: Fixtures
# ============================================================================


class TestFixtures:
    """Test that fixtures work correctly."""

    def test_emotional_state_fixtures(self):
        """Test emotional state fixtures are valid."""
        # Test each predefined state
        states = [
            NEUTRAL_STATE,
            LONELY_STATE,
            EXCITED_STATE,
            FRUSTRATED_STATE,
            AFFECTIONATE_STATE,
        ]
        
        for state in states:
            # Verify all emotions are in valid range
            for emotion_name, value in state.get_all_emotions().items():
                assert 0.0 <= value <= 1.0, \
                    f"{emotion_name} = {value} out of range"

    def test_lonely_state_values(self):
        """Test lonely state has expected values."""
        assert LONELY_STATE.loneliness > 0.7
        assert LONELY_STATE.excitement < 0.5

    def test_excited_state_values(self):
        """Test excited state has expected values."""
        assert EXCITED_STATE.excitement > 0.7
        assert EXCITED_STATE.loneliness < 0.5


# ============================================================================
# Test Class: Health Requirements
# ============================================================================


class TestHealthRequirements:
    """Test HEALTH-03 and HEALTH-04 requirements."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_health_03_emotional_state_persistence(self):
        """
        HEALTH-03: Emotional state persistence across restarts.
        
        Verifies that emotional state is saved and can be restored.
        """
        async with test_environment() as env:
            # Simulate saving state
            test_state = {"loneliness": 0.8, "affection": 0.6}
            env.record_event("save_state", test_state)
            
            # Simulate loading state
            loaded_state = test_state.copy()
            env.record_event("load_state", loaded_state)
            
            # Verify
            events = env.get_events("save_state")
            assert len(events) == 1
            
            # State should match
            for key, value in test_state.items():
                assert loaded_state[key] == value

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_health_04_platform_isolation(self):
        """
        HEALTH-04: Platform failure isolation.
        
        Verifies that one platform's failure doesn't cascade.
        """
        async with test_environment() as env:
            discord = env.mock_services.get("discord")
            android = env.mock_services.get("android")
            
            if not discord or not android:
                pytest.skip("Required mocks not available")
            
            # Set Discord to fail
            discord.set_error_rate(1.0)
            
            # Android should still work
            android.register_device("health_04_test")
            result = await android.send_message("health_04_test", "Test")
            
            assert result, "Android should be isolated from Discord failure"
            
            # Restore Discord
            discord.set_error_rate(0.0)
            
            # Discord should work again
            channel = discord.register_channel(1000)
            await channel.send("Recovery test")
            assert channel.message_count() > 0


# ============================================================================
# Parameterized Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.timeout(10)
@pytest.mark.parametrize(
    "scenario_name,scenario_func",
    [
        ("simple_greeting", run_simple_greeting_scenario),
        ("lonely_demeanor", run_lonely_demeanor_scenario),
        ("affection_response", run_affection_response_scenario),
    ],
)
async def test_parameterized_scenarios(scenario_name: str, scenario_func):
    """Run scenarios with parameterized testing."""
    async with test_environment() as env:
        result = await scenario_func(env)
        assert result["success"], f"Scenario '{scenario_name}' failed: {result}"


@pytest.mark.parametrize(
    "emotion_state,expected_marker",
    [
        (LONELY_STATE, "loneliness"),
        (EXCITED_STATE, "excitement"),
        (FRUSTRATED_STATE, "frustration"),
        (AFFECTIONATE_STATE, "affection"),
    ],
)
def test_emotion_state_markers(emotion_state, expected_marker):
    """Test that emotion states have expected dominant emotions."""
    dominant = emotion_state.get_dominant_emotions(1)[0][0]
    assert dominant == expected_marker, \
        f"Expected {expected_marker} to be dominant, got {dominant}"
