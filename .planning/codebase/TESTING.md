# Testing Patterns

**Analysis Date:** 2026-02-02

## Test Framework

**Runner:** pytest 7.4.0+
- Config location: No `pytest.ini` or `pyproject.toml` found - using pytest defaults
- Tests discovered from `tests/` directory using standard naming patterns

**Async Support:**
- `pytest-asyncio` 0.21.0+ for async test support
- Uses `@pytest.mark.asyncio` decorator for async test functions

**Mocking:**
- `unittest.mock` module: `Mock`, `AsyncMock`, `MagicMock`, `patch`
- Mocks imported directly: `from unittest.mock import Mock, AsyncMock, patch`

**Assertion Library:**
- Standard Python `assert` statements
- Floating-point assertions use epsilon tolerance: `assert abs(value - expected) < 1e-9`

**Coverage:**
- `pytest-cov` 4.1.0+ available but no coverage configuration detected
- Run command not yet standardized (no pytest.ini config)

## Test Organization

**File Location:** `tests/` directory at project root
- Pattern: `test_*.py` files
- File naming matches module under test: `test_llm_inference.py` tests `src/llm/inference.py`

**Total Tests:** 310+ test functions across ~20 test files
- Largest test files: `test_spontaneous_initiator.py` (566 lines), `test_emotion_modulation.py` (485 lines)

**Structure Example from `test_emotion_models.py`:**
```
tests/
├── test_llm_inference.py              (333 lines)
├── test_emotion_models.py             (198 lines)
├── test_llm_response_processor.py     (401 lines)
├── test_spontaneous_initiator.py      (566 lines)
├── test_unified_autonomy.py           (371 lines)
├── test_emotion_modulation.py         (485 lines)
├── test_llm_prompt_builder.py         (278 lines)
├── test_emotion_integration.py        (209 lines)
├── test_history_manager.py            (308 lines)
├── test_discord_rambles.py            (103 lines)
└── [11 more test modules]
```

## Test Structure

**Class Organization:**
- Tests grouped in classes by functionality
- Class naming: `Test{ComponentName}` or `Test{Functionality}`
- Example from `test_emotion_models.py`:
  ```python
  class TestEmotionalStateInstantiation:
      """Test EmotionalState creation and initialization."""

  class TestBoundsClamping:
      """Test that emotions stay within [floor, 1.0]."""

  class TestMomentumTracking:
      """Test momentum accumulation and clearing."""
  ```

**Test Method Naming:**
- Method naming: `test_{what_is_being_tested}_{expected_outcome}`
- Docstrings describe the test in plain English
- Example from `test_emotion_models.py`:
  ```python
  def test_default_neutral_state(self):
      """All emotions should default to 0.5 (neutral)."""

  def test_emotion_below_floor_clamped_to_floor(self):
      """Emotions below their floor should be clamped up."""
  ```

**Test Module Docstring:**
- Each test file has a module-level docstring
- Example from `test_llm_inference.py`:
  ```python
  """
  Unit tests for LLM inference engine.

  Tests OllamaInference class with:
  - Configuration validation
  - Health check
  - Message validation
  - Context overflow detection
  - Context trimming
  - Token counting (with fallback)
  """
  ```

## Fixtures

**Pattern:** pytest fixtures with `@pytest.fixture` decorator at module level or in class
- Fixtures return test data or mock objects
- Fixtures used as function parameters

**Fixture Examples from `test_llm_response_processor.py`:**
```python
@pytest.fixture
def logger():
    """Create a test logger."""
    return DemiLogger()

@pytest.fixture
def interaction_handler():
    """Create an interaction handler."""
    return InteractionHandler()

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock()

@pytest.fixture
def response_processor(logger, mock_db_session, interaction_handler):
    """Create a ResponseProcessor instance."""
    return ResponseProcessor(
        logger=logger,
        db_session=mock_db_session,
        interaction_handler=interaction_handler,
    )

@pytest.fixture
def baseline_emotional_state():
    """Create a baseline emotional state."""
    return EmotionalState(
        loneliness=0.5,
        excitement=0.5,
        frustration=0.5,
        # ... other emotions
    )
```

**Usage Pattern:**
- Fixtures passed as parameters to test methods
- Multiple fixtures can be composed together
- Example: `response_processor` fixture depends on `logger`, `mock_db_session`, and `interaction_handler`

**Fixture Location:**
- No `conftest.py` found - fixtures defined in each test module
- Fixtures scoped to individual test modules

## Mocking Patterns

**Mock Framework:** `unittest.mock` from Python standard library

**Mock Types Used:**
- `Mock()`: Basic mock for any object
- `AsyncMock()`: For async functions/methods
- `MagicMock()`: For objects with special methods
- `patch()`: Context manager for replacing objects

**Mocking Examples:**

**1. Basic Mock Creation:**
```python
# From test_spontaneous_initiator.py
@pytest.fixture
def mock_inference():
    """Mock LLM inference engine."""
    inference = Mock()
    inference.chat = AsyncMock(
        return_value="Hey, just thinking about our last conversation..."
    )
    return inference
```

**2. Mock with `spec` Parameter:**
```python
# From test_unified_autonomy.py
conductor = Mock(spec=Conductor)
conductor.logger = Mock()
conductor.request_inference = AsyncMock(return_value="Test response")
```

**3. Mock Configuration Methods:**
```python
# From test_unified_autonomy.py
conductor._plugin_manager = Mock()
discord_plugin = Mock()
discord_plugin.send_message = Mock(return_value=True)
conductor._plugin_manager.get_loaded_plugin = Mock(
    side_effect=lambda name: {
        "discord": discord_plugin,
        "android": android_plugin,
    }.get(name)
)
```

**4. Using `patch` Context Manager:**
```python
# From test_spontaneous_initiator.py
with patch("src.autonomy.spontaneous.datetime") as mock_datetime:
    # Test code using mocked datetime
    pass

# From test_unified_autonomy.py
with patch("src.autonomy.coordinator.TriggerManager") as mock_trigger_manager:
    mock_manager_instance = Mock()
    # Configure mock
    mock_trigger_manager.return_value = mock_manager_instance
```

**What to Mock:**
- External services: Ollama inference, Discord bot, database
- Time-dependent functions: `datetime.now()`, timers
- Random/non-deterministic behavior
- Slow I/O operations

**What NOT to Mock:**
- Pure business logic functions (emotion calculations)
- Data model classes (test the real implementations)
- Custom exceptions
- Internal helper methods unless they have side effects

## Async Testing

**Pattern:** Use `@pytest.mark.asyncio` decorator on async test methods

**Example from `test_unified_autonomy.py`:**
```python
@pytest.mark.asyncio
async def test_autonomy_coordinator_initialization(self, mock_conductor):
    """Test autonomy coordinator initialization."""
    coordinator = AutonomyCoordinator(mock_conductor)

    assert coordinator.conductor == mock_conductor
    assert coordinator.is_running is False
    assert coordinator.current_status.active is False
    assert len(coordinator.background_tasks) == 0
```

**Async Mock Usage:**
```python
# Create AsyncMock for coroutines
inference.chat = AsyncMock(return_value="response")

# Can await AsyncMock
result = await inference.chat()
```

**Number of Async Tests:** 21+ tests marked with `@pytest.mark.asyncio`

## Assertions

**Pattern:** Simple Python `assert` statements with descriptive failure messages

**Standard Assertions:**
```python
# Equality
assert state.loneliness == 0.5

# Inequality
assert output != "hello"

# Membership
assert "<|end|>" not in output
assert "response" in output

# Boolean
assert coordinator.is_running is True
assert result is False

# Comparisons
assert len(coordinator.background_tasks) == 0
assert state.excitement > 0.5
```

**Floating-Point Assertions:**
- Use epsilon tolerance for float comparisons
- Example from `test_emotion_models.py`:
  ```python
  assert abs(state.momentum["loneliness"] - 0.2) < 1e-9
  ```

**Exception Assertions:**
- Using `pytest.raises` context manager
- Example from `test_llm_inference.py`:
  ```python
  with pytest.raises(ValueError, match="temperature must be in range"):
      LLMConfig(temperature=1.5)
  ```

## Test Data & Factories

**Pattern:** Fixtures provide test data

**Data Creation Pattern:**
```python
# From test_unified_autonomy.py
@pytest.fixture
def emotional_state(self):
    """Create test emotional state."""
    state = EmotionalState()
    state.loneliness = 0.8
    state.excitement = 0.3
    state.frustration = 0.2
    state.affection = 0.5
    return state
```

**Real Object Instantiation:**
- Use real model classes in tests: `EmotionalState()`, `LLMConfig()`
- Only mock external dependencies (I/O, services, slow operations)

**Fixture Composition:**
- Complex fixtures depend on simpler fixtures
- Example: `response_processor` fixture uses `logger`, `mock_db_session`, `interaction_handler` fixtures

## Test Coverage

**Requirements:** No enforced minimum coverage detected

**Coverage Tool:** `pytest-cov` 4.1.0+ available but not configured

**Likely Coverage Areas:**
- Core emotion system: Very well covered (198+ lines in emotion tests)
- LLM inference: Well covered (333+ lines)
- Autonomy system: Well covered (566+ lines in spontaneous initiator tests)
- Response processing: Comprehensive (401+ lines)

**Commands Not Yet Standardized:**
```bash
# No pytest.ini means standard commands:
pytest                    # Run all tests
pytest -v               # Verbose output
pytest -x               # Stop on first failure
pytest tests/test_emotion_models.py  # Run specific file
```

## Test Types

**Unit Tests:** Majority of tests
- Test individual functions/methods in isolation
- Mock external dependencies
- Example: `test_clean_text_strips_whitespace()` tests `ResponseProcessor._clean_text()`

**Integration Tests:** ~25% of tests
- Test multiple components working together
- Examples: `test_unified_autonomy.py`, `test_llm_full_integration.py`
- Still mock external services (Ollama, Discord)

**E2E Tests:** Minimal
- File `test_llm_e2e.py` (416 lines) exists but appears to be integration rather than true end-to-end
- Would require real Ollama instance

**Async Integration Tests:** 21+ tests
- Test async code paths and concurrent operations
- Example: `test_autonomy_system_startup()` tests startup and shutdown sequences

## Common Test Patterns

**1. Happy Path Testing:**
```python
def test_valid_config_creation(self):
    """Should create config with valid parameters."""
    config = LLMConfig(
        model_name="llama3.2:1b",
        temperature=0.7,
        max_tokens=256,
        timeout_sec=10,
    )
    assert config.model_name == "llama3.2:1b"
    assert config.temperature == 0.7
```

**2. Validation/Error Testing:**
```python
def test_invalid_temperature_high(self):
    """Should reject temperature > 1.0."""
    with pytest.raises(ValueError, match="temperature must be in range"):
        LLMConfig(temperature=1.5)
```

**3. State Transition Testing:**
```python
@pytest.mark.asyncio
async def test_autonomy_system_startup(self, autonomy_coordinator):
    """Test autonomy system startup sequence."""
    # Start autonomy system
    result = autonomy_coordinator.start_autonomy()
    assert result is True
    assert autonomy_coordinator.is_running is True

    # Stop autonomy system
    result = autonomy_coordinator.stop_autonomy()
    assert result is True
    assert autonomy_coordinator.is_running is False
```

**4. Data Transformation Testing:**
```python
def test_clean_text_removes_special_tokens(self, response_processor):
    """Special tokens should be removed."""
    input_text = "hello <|end|> world"
    output = response_processor._clean_text(input_text)
    assert output == "hello world"
    assert "<|end|>" not in output
```

**5. Empty/Edge Case Testing:**
```python
def test_clean_text_empty_returns_fallback(self, response_processor):
    """Empty text should return fallback."""
    output = response_processor._clean_text("")
    assert output == "I forgot what I was thinking... try again?"
```

## Test Quality Observations

**Strengths:**
- Clear test names describing what is tested
- Good use of docstrings on test methods
- Comprehensive fixture setup pattern
- Module-level docstrings explaining test scope
- Good separation of test concerns into classes

**Areas for Standardization:**
- No shared `conftest.py` - each module defines its own fixtures
- No explicit pytest configuration (pytest.ini/pyproject.toml)
- No coverage configuration enforced
- Some placeholder tests with `pass` statements (e.g., `test_android_autonomy.py`)

---

*Testing analysis: 2026-02-02*
