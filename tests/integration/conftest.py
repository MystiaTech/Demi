"""Pytest configuration for integration tests."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator

# Import test harness
from tests.integration.harness import IntegrationTestHarness, TestEnvironment, TestConfig


# ============================================================================
# Event Loop Fixture
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Environment Fixtures
# ============================================================================


@pytest.fixture
async def test_env() -> AsyncGenerator[TestEnvironment, None]:
    """Provide a fresh test environment for each test."""
    harness = IntegrationTestHarness(use_mocks=True)
    env = await harness.setup()
    try:
        yield env
    finally:
        await harness.teardown(env)


@pytest.fixture
async def test_env_with_latency() -> AsyncGenerator[TestEnvironment, None]:
    """Provide test environment with simulated latency."""
    config = TestConfig(use_mocks=True, mock_llm_latency_ms=100.0)
    harness = IntegrationTestHarness(config)
    env = await harness.setup()
    try:
        yield env
    finally:
        await harness.teardown(env)


@pytest.fixture
async def test_env_with_errors() -> AsyncGenerator[TestEnvironment, None]:
    """Provide test environment with simulated errors."""
    config = TestConfig(use_mocks=True, mock_llm_error_rate=0.3)
    harness = IntegrationTestHarness(config)
    env = await harness.setup()
    try:
        yield env
    finally:
        await harness.teardown(env)


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_discord(test_env: TestEnvironment):
    """Get Discord mock from test environment."""
    return test_env.mock_services.get("discord")


@pytest.fixture
def mock_ollama(test_env: TestEnvironment):
    """Get Ollama mock from test environment."""
    return test_env.mock_services.get("ollama")


@pytest.fixture
def mock_android(test_env: TestEnvironment):
    """Get Android mock from test environment."""
    return test_env.mock_services.get("android")


@pytest.fixture
def mock_voice(test_env: TestEnvironment):
    """Get Voice mock from test environment."""
    return test_env.mock_services.get("voice")


# ============================================================================
# Harness Fixture
# ============================================================================


@pytest.fixture
def harness():
    """Provide a fresh test harness."""
    return IntegrationTestHarness(use_mocks=True)


# ============================================================================
# Test Constants
# ============================================================================


# Test timeouts
INTEGRATION_TEST_TIMEOUT = 30  # seconds
RESPONSE_TIMEOUT = 5.0  # seconds

# Performance thresholds
MAX_RESPONSE_TIME_SEC = 3.0
MAX_SUITE_EXECUTION_TIME_SEC = 300  # 5 minutes

# Test user IDs
TEST_USER_ID = 123456789
KNOWN_USER_ID = 987654321
NEW_USER_ID = 111222333

# Test channel IDs
TEST_CHANNEL_ID = 987654321
RAMBLE_CHANNEL_ID = 888
