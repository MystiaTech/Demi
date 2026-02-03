"""Integration tests for Demi.

These tests verify full system behavior across all components.
They use mock external services to avoid requiring live Discord/Ollama.
"""

# Integration test suite version
__version__ = "1.0.0"

# Re-export main components for convenience
try:
    from tests.integration.harness import IntegrationTestHarness, test_environment
    from tests.integration.fixtures.emotion_fixtures import (
        NEUTRAL_STATE,
        LONELY_STATE,
        EXCITED_STATE,
        FRUSTRATED_STATE,
        CONFIDENT_STATE,
        VULNERABLE_STATE,
        JEALOUS_STATE,
    )
except ImportError:
    # Allow import even if dependencies not yet available
    pass
