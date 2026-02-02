"""
Integration tests for unified autonomy system.

Tests cross-platform emotional state synchronization, consistent autonomous behavior,
and platform-specific message delivery with unified content.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, UTC

from src.autonomy.coordinator import AutonomyCoordinator, AutonomousAction
from src.emotion.models import EmotionalState
from src.conductor.orchestrator import Conductor
from src.integrations.discord_bot import DiscordBot
from src.api.autonomy import AutonomyManager


class TestUnifiedAutonomyIntegration:
    """Test suite for unified autonomy system integration."""

    @pytest.fixture
    def mock_conductor(self):
        """Mock conductor instance."""
        conductor = Mock(spec=Conductor)
        conductor.logger = Mock()
        conductor.autonomy_coordinator = None

        # Mock LLM methods
        conductor.request_inference = AsyncMock(return_value="Test response")
        conductor.request_inference_for_platform = AsyncMock(
            return_value={"content": "Test response", "emotion_state": {}}
        )

        # Mock platform methods
        conductor.send_discord_message = Mock(return_value=True)
        conductor.send_android_websocket_message = Mock(return_value=True)

        # Mock plugin manager
        conductor._plugin_manager = Mock()
        discord_plugin = Mock()
        discord_plugin.send_message = Mock(return_value=True)
        android_plugin = Mock()
        android_plugin.send_websocket_message = Mock(return_value=True)
        conductor._plugin_manager.get_loaded_plugin = Mock(
            side_effect=lambda name: {
                "discord": discord_plugin,
                "android": android_plugin,
            }.get(name)
        )

        return conductor

    @pytest.fixture
    def autonomy_coordinator(self, mock_conductor):
        """Create autonomy coordinator for testing."""
        return AutonomyCoordinator(mock_conductor)

    @pytest.fixture
    def emotional_state(self):
        """Create test emotional state."""
        state = EmotionalState()
        state.loneliness = 0.8
        state.excitement = 0.3
        state.frustration = 0.2
        state.affection = 0.5
        return state

    @pytest.mark.asyncio
    async def test_autonomy_coordinator_initialization(self, mock_conductor):
        """Test autonomy coordinator initialization."""
        coordinator = AutonomyCoordinator(mock_conductor)

        assert coordinator.conductor == mock_conductor
        assert coordinator.is_running is False
        assert coordinator.current_status.active is False
        assert len(coordinator.background_tasks) == 0

    @pytest.mark.asyncio
    async def test_autonomy_system_startup(self, autonomy_coordinator):
        """Test autonomy system startup sequence."""
        # Start autonomy system
        result = autonomy_coordinator.start_autonomy()

        assert result is True
        assert autonomy_coordinator.is_running is True
        assert autonomy_coordinator.current_status.active is True
        assert len(autonomy_coordinator.background_tasks) == 2  # monitor + processor

        # Stop autonomy system
        result = autonomy_coordinator.stop_autonomy()
        assert result is True
        assert autonomy_coordinator.is_running is False

    @pytest.mark.asyncio
    async def test_discord_autonomous_action_execution(
        self, autonomy_coordinator, mock_conductor
    ):
        """Test Discord autonomous action execution."""
        context = {
            "content": "Test autonomous message",
            "channel_id": "123456789",
            "platform": "discord",
        }

        # Execute action
        result = await autonomy_coordinator.execute_autonomous_action("ramble", context)

        assert result is True
        mock_conductor.send_discord_message.assert_called_once_with(
            "Test autonomous message", "123456789"
        )

    @pytest.mark.asyncio
    async def test_android_autonomous_action_execution(
        self, autonomy_coordinator, mock_conductor
    ):
        """Test Android autonomous action execution."""
        context = {
            "content": "Test check-in message",
            "device_id": "test_device",
            "platform": "android",
        }

        # Execute action
        result = await autonomy_coordinator.execute_autonomous_action(
            "check_in", context
        )

        assert result is True
        mock_conductor.send_android_websocket_message.assert_called_once_with(
            "Test check-in message", "test_device"
        )

    @pytest.mark.asyncio
    async def test_emotional_trigger_evaluation(
        self, autonomy_coordinator, emotional_state
    ):
        """Test emotional trigger evaluation."""
        # Mock trigger manager
        with patch("src.autonomy.coordinator.TriggerManager") as mock_trigger_manager:
            mock_manager_instance = Mock()
            mock_trigger_manager.return_value = mock_manager_instance
            mock_manager_instance.evaluate_triggers.return_value = [
                {
                    "type": "ramble",
                    "platform": "discord",
                    "content": "Spontaneous ramble content",
                    "priority": 1,
                }
            ]

            # Evaluate triggers
            await autonomy_coordinator._evaluate_emotional_triggers(emotional_state)

            # Check that action was created
            assert len(autonomy_coordinator.pending_actions) == 1
            action = autonomy_coordinator.pending_actions[0]
            assert action.action_type == "ramble"
            assert action.platform == "discord"
            assert action.content == "Spontaneous ramble content"

    @pytest.mark.asyncio
    async def test_refusal_system_integration(self, autonomy_coordinator):
        """Test refusal system integration."""
        # Mock refusal system to refuse request
        autonomy_coordinator.refusal_system.should_refuse = Mock(
            return_value=Mock(
                should_refuse=True, reason="Test refusal", category=Mock(value="spam")
            )
        )

        context = {"content": "Spam content", "platform": "discord"}

        # Execute action (should be refused)
        result = await autonomy_coordinator.execute_autonomous_action("ramble", context)

        assert result is False
        assert len(autonomy_coordinator.refused_requests) == 1

    def test_autonomy_status_tracking(self, autonomy_coordinator):
        """Test autonomy status tracking."""
        status = autonomy_coordinator.get_autonomy_status()

        assert status.active is False
        assert status.tasks_running == 0
        assert status.error_count == 0

    def test_refusal_statistics(self, autonomy_coordinator):
        """Test refusal statistics tracking."""
        # Add some refused requests
        autonomy_coordinator.refused_requests = [
            {"refusal_category": "spam", "timestamp": datetime.now(UTC).isoformat()},
            {
                "refusal_category": "inappropriate",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]

        stats = autonomy_coordinator.get_refusal_statistics()

        assert stats["total_refused_requests"] == 2
        assert "refusal_system_stats" in stats
        assert "refusal_rate" in stats

    @pytest.mark.asyncio
    async def test_discord_bot_unified_autonomy_integration(self, mock_conductor):
        """Test Discord bot integration with unified autonomy."""
        # Create Discord bot
        bot = DiscordBot()

        # Mock conductor with autonomy coordinator
        mock_conductor.autonomy_coordinator = AutonomyCoordinator(mock_conductor)

        # Test initialization
        with patch(
            "os.getenv",
            side_effect=lambda key, default=None: {
                "DISCORD_BOT_TOKEN": "test_token",
                "DEMI_DB_PATH": "~/.demi/emotions.db",
            }.get(key),
        ):
            with patch("discord.ext.commands.Bot"):
                result = await bot.initialize(mock_conductor)

                assert bot.autonomy_coordinator is not None
                assert bot.autonomy_coordinator == mock_conductor.autonomy_coordinator

    @pytest.mark.asyncio
    async def test_android_autonomy_manager_integration(self, mock_conductor):
        """Test Android autonomy manager integration."""
        # Mock conductor with autonomy coordinator
        mock_conductor.autonomy_coordinator = AutonomyCoordinator(mock_conductor)

        # Create autonomy manager
        manager = AutonomyManager(mock_conductor)

        # Test initialization
        result = await manager.initialize()
        assert result is True
        assert manager.autonomy_coordinator is not None

    @pytest.mark.asyncio
    async def test_cross_platform_emotional_state_synchronization(self, mock_conductor):
        """Test cross-platform emotional state synchronization."""
        # Create autonomy coordinator
        coordinator = AutonomyCoordinator(mock_conductor)

        # Mock emotion persistence
        with patch("src.autonomy.coordinator.EmotionPersistence") as mock_persistence:
            mock_state = EmotionalState()
            mock_state.loneliness = 0.8
            mock_persistence.return_value.load_state.return_value = mock_state

            # Monitor emotional state
            await coordinator._monitor_emotional_state()

            # Verify emotional state was loaded
            mock_persistence.return_value.load_state.assert_called()

    @pytest.mark.asyncio
    async def test_rate_limiting_for_autonomous_actions(self, autonomy_coordinator):
        """Test rate limiting for autonomous actions."""
        # Fill action history to exceed rate limit
        for _ in range(100):  # Exceed default max per hour
            autonomy_coordinator.action_history.append(
                {"timestamp": datetime.now(UTC).timestamp(), "status": "executed"}
            )

        # Test should execute action
        result = autonomy_coordinator._should_execute_action()
        assert result is False

    @pytest.mark.asyncio
    async def test_background_task_cleanup_on_shutdown(self, autonomy_coordinator):
        """Test background task cleanup on shutdown."""
        # Start autonomy system
        autonomy_coordinator.start_autonomy()

        # Verify tasks are running
        assert len(autonomy_coordinator.background_tasks) == 2

        # Stop autonomy system
        result = autonomy_coordinator.stop_autonomy()

        assert result is True
        assert len(autonomy_coordinator.background_tasks) == 0
        assert autonomy_coordinator.is_running is False

    def test_platform_adapter_discord_formatting(self, mock_conductor):
        """Test Discord platform adapter maintains formatting."""
        discord_plugin = Mock()
        discord_plugin.send_message = Mock(return_value=True)
        mock_conductor._plugin_manager.get_loaded_plugin.return_value = discord_plugin

        # Send Discord message
        result = mock_conductor.send_discord_message("Test content", "123456789")

        assert result is True
        discord_plugin.send_message.assert_called_once_with("Test content", "123456789")

    def test_platform_adapter_android_websocket_delivery(self, mock_conductor):
        """Test Android platform adapter WebSocket delivery."""
        android_plugin = Mock()
        android_plugin.send_websocket_message = Mock(return_value=True)
        mock_conductor._plugin_manager.get_loaded_plugin.return_value = android_plugin

        # Send Android message
        result = mock_conductor.send_android_websocket_message(
            "Test content", "test_device"
        )

        assert result is True
        android_plugin.send_websocket_message.assert_called_once_with(
            "Test content", "test_device"
        )


class TestUnifiedAutonomyPerformance:
    """Performance tests for unified autonomy system."""

    @pytest.mark.asyncio
    async def test_concurrent_autonomous_actions(self, autonomy_coordinator):
        """Test handling multiple concurrent autonomous actions."""
        # Create multiple actions
        actions = []
        for i in range(10):
            context = {
                "content": f"Test message {i}",
                "platform": "discord" if i % 2 == 0 else "android",
                "channel_id" if i % 2 == 0 else "device_id": f"target_{i}",
            }
            actions.append(
                autonomy_coordinator.execute_autonomous_action("ramble", context)
            )

        # Execute all actions concurrently
        results = await asyncio.gather(*actions, return_exceptions=True)

        # Verify all executed successfully
        assert all(isinstance(result, bool) for result in results)
        assert sum(1 for r in results if r is True) >= 8  # Allow for some rate limiting

    @pytest.mark.asyncio
    async def test_memory_usage_during_extended_operation(self, autonomy_coordinator):
        """Test memory usage during extended operation."""
        # Start autonomy system
        autonomy_coordinator.start_autonomy()

        # Simulate extended operation
        initial_history_size = len(autonomy_coordinator.action_history)

        # Add many actions to history
        for _ in range(200):  # Exceed max history size
            autonomy_coordinator.action_history.append(
                {"timestamp": datetime.now(UTC).timestamp(), "status": "executed"}
            )

        # Check history was trimmed
        assert (
            len(autonomy_coordinator.action_history)
            <= autonomy_coordinator.max_history_size
        )

        # Stop autonomy system
        autonomy_coordinator.stop_autonomy()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
