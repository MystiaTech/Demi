"""Integration Test Harness for Demi.

Provides full-system test orchestration with mock external services,
enabling comprehensive end-to-end testing without requiring live
Discord or Ollama connections.
"""

import asyncio
import tempfile
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from pathlib import Path

# Core imports
from src.core.logger import get_logger

logger = get_logger()


@dataclass
class TestEnvironment:
    """Container for test environment state."""

    conductor: Optional[Any] = None
    temp_dir: Optional[Path] = None
    mock_services: Dict[str, Any] = field(default_factory=dict)
    test_db_path: Optional[str] = None
    event_log: List[Dict] = field(default_factory=list)

    def record_event(self, event_type: str, data: Dict):
        """Record an event for test verification."""
        self.event_log.append(
            {"type": event_type, "data": data, "timestamp": time.time()}
        )

    def get_events(self, event_type: Optional[str] = None) -> List[Dict]:
        """Get recorded events, optionally filtered by type."""
        if event_type is None:
            return self.event_log.copy()
        return [e for e in self.event_log if e["type"] == event_type]

    def clear_events(self):
        """Clear all recorded events."""
        self.event_log.clear()


@dataclass
class TestConfig:
    """Configuration for integration tests."""

    use_mocks: bool = True
    mock_llm_latency_ms: float = 50.0
    mock_llm_error_rate: float = 0.0
    test_timeout_seconds: float = 30.0
    response_timeout_seconds: float = 5.0
    db_isolation: bool = True
    enable_voice_mocks: bool = False


class IntegrationTestHarness:
    """
    Full-system test harness for Demi integration tests.

    Manages:
    - Test environment lifecycle (setup/teardown)
    - Mock external services (Discord, Ollama, Android)
    - Test database isolation
    - Performance tracking
    - Assertion helpers

    Example:
        async with test_environment() as env:
            # Test code here
            result = await run_scenario(env)
            assert result["success"]
    """

    def __init__(self, config: Optional[TestConfig] = None):
        """
        Initialize harness with configuration.

        Args:
            config: Test configuration, uses defaults if None
        """
        self.config = config or TestConfig()
        self._logger = logger
        self._mock_registry: Dict[str, Any] = {}
        self._timing: Dict[str, float] = {}

    async def setup(self, config_overrides: Optional[Dict] = None) -> TestEnvironment:
        """
        Set up test environment with isolated resources.

        Args:
            config_overrides: Optional config values to override defaults

        Returns:
            TestEnvironment ready for testing
        """
        start_time = time.time()
        self._timing["setup_start"] = start_time

        # Create temp directory for test isolation
        temp_dir = Path(tempfile.mkdtemp(prefix="demi_test_"))
        self._logger.info(f"Test temp directory: {temp_dir}")

        # Create test database path
        test_db_path = str(temp_dir / "test_emotions.db")

        env = TestEnvironment(
            temp_dir=temp_dir,
            test_db_path=test_db_path,
        )

        # Initialize mock services if enabled
        if self.config.use_mocks:
            await self._setup_mock_services(env)

        # Record setup time
        self._timing["setup_complete"] = time.time()
        setup_duration = self._timing["setup_complete"] - start_time
        self._logger.info(f"Test environment setup complete in {setup_duration:.2f}s")

        return env

    async def _setup_mock_services(self, env: TestEnvironment) -> None:
        """Initialize and register mock external services."""
        # Import mocks here to avoid circular imports
        from tests.integration.mocks import (
            MockDiscordClient,
            MockOllamaServer,
            MockAndroidClient,
            MockVoiceClient,
        )

        # Initialize mocks
        mock_discord = MockDiscordClient()
        mock_ollama = MockOllamaServer()
        mock_android = MockAndroidClient()
        mock_voice = MockVoiceClient()

        # Configure mock behaviors
        mock_ollama.latency_override = self.config.mock_llm_latency_ms
        mock_ollama.error_rate = self.config.mock_llm_error_rate

        # Register with environment
        env.mock_services["discord"] = mock_discord
        env.mock_services["ollama"] = mock_ollama
        env.mock_services["android"] = mock_android
        env.mock_services["voice"] = mock_voice

        self._mock_registry = env.mock_services.copy()

        self._logger.info(
            f"Mock services initialized: {list(env.mock_services.keys())}"
        )

    async def teardown(self, env: TestEnvironment) -> None:
        """
        Clean up test environment and release resources.

        Args:
            env: TestEnvironment to clean up
        """
        start_time = time.time()
        self._timing["teardown_start"] = start_time

        # Clean up mock services
        for name, service in env.mock_services.items():
            try:
                if hasattr(service, "cleanup"):
                    await service.cleanup()
                elif hasattr(service, "clear_history"):
                    service.clear_history()
            except Exception as e:
                self._logger.warning(f"Error cleaning up mock {name}: {e}")

        # Remove temp directory
        if env.temp_dir and env.temp_dir.exists():
            import shutil

            try:
                shutil.rmtree(env.temp_dir)
                self._logger.info(f"Removed temp directory: {env.temp_dir}")
            except Exception as e:
                self._logger.warning(f"Error removing temp dir: {e}")

        # Record teardown time
        self._timing["teardown_complete"] = time.time()
        teardown_duration = self._timing["teardown_complete"] - start_time
        self._logger.info(f"Test environment teardown complete in {teardown_duration:.2f}s")

    async def run_scenario(
        self, scenario_fn: Callable, env: TestEnvironment, **kwargs
    ) -> Dict:
        """
        Execute a test scenario and collect results.

        Args:
            scenario_fn: Async function to execute
            env: Test environment
            **kwargs: Additional arguments for scenario function

        Returns:
            Scenario results with timing metrics
        """
        start_time = time.time()

        try:
            result = await scenario_fn(env, **kwargs)
        except Exception as e:
            self._logger.error(f"Scenario execution failed: {e}")
            result = {"success": False, "error": str(e), "error_type": type(e).__name__}

        elapsed = time.time() - start_time

        # Add timing metrics
        if isinstance(result, dict):
            result["_timing"] = {"scenario_duration_sec": elapsed}

        return result

    def assert_emotion_state(
        self,
        actual: Dict[str, float],
        expected_emotions: Dict[str, float],
        tolerance: float = 0.1,
    ) -> bool:
        """
        Verify emotional state matches expectations.

        Args:
            actual: Actual emotion state dict
            expected_emotions: Expected values for specific emotions
            tolerance: Acceptable difference (default 0.1)

        Returns:
            True if all emotions within tolerance

        Raises:
            AssertionError: If any emotion outside tolerance
        """
        failures = []

        for emotion, expected in expected_emotions.items():
            actual_value = actual.get(emotion, 0.5)
            diff = abs(actual_value - expected)
            if diff > tolerance:
                failures.append(
                    f"  {emotion}: expected {expected:.2f}, got {actual_value:.2f} "
                    f"(diff: {diff:.2f})"
                )

        if failures:
            raise AssertionError("Emotion state mismatch:\n" + "\n".join(failures))

        return True

    def assert_response_quality(
        self, response: str, checks: List[str], case_sensitive: bool = False
    ) -> bool:
        """
        Verify response contains expected content.

        Args:
            response: Response text to check
            checks: List of strings that should be present
            case_sensitive: Whether checks are case sensitive

        Returns:
            True if all checks pass

        Raises:
            AssertionError: If any check fails
        """
        if not response:
            raise AssertionError("Response is empty or None")

        check_text = response if case_sensitive else response.lower()
        failures = []

        for check in checks:
            check_lower = check if case_sensitive else check.lower()
            if check_lower not in check_text:
                failures.append(f"  Missing: '{check}'")

        if failures:
            raise AssertionError(
                f"Response quality check failed:\n"
                + "\n".join(failures)
                + f"\nResponse: {response[:200]}..."
            )

        return True

    def assert_performance(
        self, operation_name: str, duration_sec: float, max_allowed_sec: float
    ) -> bool:
        """
        Verify operation completed within time limit.

        Args:
            operation_name: Name of operation for error message
            duration_sec: Actual duration
            max_allowed_sec: Maximum allowed duration

        Returns:
            True if within limit

        Raises:
            AssertionError: If operation too slow
        """
        if duration_sec > max_allowed_sec:
            raise AssertionError(
                f"Performance check failed for {operation_name}: "
                f"{duration_sec:.2f}s > {max_allowed_sec:.2f}s"
            )
        return True

    def get_timing_report(self) -> Dict[str, float]:
        """Get timing metrics for setup/teardown."""
        return self._timing.copy()


@asynccontextmanager
async def test_environment(
    config_overrides: Optional[Dict] = None, use_mocks: bool = True
):
    """
    Context manager for test environment lifecycle.

    Usage:
        async with test_environment() as env:
            # Your test code here
            discord = env.mock_services["discord"]
            # ... use discord mock

    Args:
        config_overrides: Optional config overrides
        use_mocks: Whether to use mock services

    Yields:
        Configured TestEnvironment
    """
    config = TestConfig(use_mocks=use_mocks)
    harness = IntegrationTestHarness(config)
    env = await harness.setup(config_overrides)
    try:
        yield env
    finally:
        await harness.teardown(env)


# Helper function for synchronous test setup
def create_test_harness(use_mocks: bool = True) -> IntegrationTestHarness:
    """
    Create a test harness for use in tests.

    Args:
        use_mocks: Whether to use mock services

    Returns:
        Configured IntegrationTestHarness
    """
    config = TestConfig(use_mocks=use_mocks)
    return IntegrationTestHarness(config)
