# Coding Conventions

**Analysis Date:** 2026-02-02

## Language & Tools

**Primary Language:** Python 3.9+

**Type Hints:** Used throughout codebase with type annotations on function signatures and variable declarations
- Example: `def chat(self, messages: List[Dict[str, str]], max_context_tokens: int = 8000) -> str:`

**Code Formatter:** Not detected (no `.black`, `.flake8`, or linter config files)
- No enforced formatting tool found in project root
- Code style appears manually maintained

## Naming Patterns

**Classes:**
- PascalCase for all classes
- Examples: `ApplicationManager`, `OllamaInference`, `EmotionalState`, `AutonomyCoordinator`
- Dataclasses: Use `@dataclass` decorator with PascalCase names
  - Example: `@dataclass class LLMConfig:`

**Functions and Methods:**
- snake_case for all functions and methods
- Private methods prefixed with underscore: `_validate_bounds()`, `_attempt_recovery()`
- Async functions use `async def` keyword
- Example: `async def health_check(self) -> bool:`, `def _validate(self):`

**Variables and Constants:**
- snake_case for variable names: `max_consecutive_errors`, `token_count`, `emotional_state`
- Module-level constants in UPPER_SNAKE_CASE when appropriate
- Dictionary keys use snake_case: `{"model_name": "...", "temperature": 0.7}`

**Type Names:**
- Enum classes: PascalCase
  - Examples: `class PluginState(Enum):`, `class InitiationTrigger(Enum):`

**Module Names:**
- snake_case for module files: `inference.py`, `logger.py`, `error_handler.py`
- Directories use snake_case: `src/llm/`, `src/emotion/`, `src/autonomy/`

## Import Organization

**Order (from actual code patterns):**
1. Standard library imports: `import asyncio`, `import sys`, `from typing import ...`
2. Third-party imports: `import ollama`, `import pytest`, `from pydantic import ...`
3. Local imports: `from src.llm.config import LLMConfig`, `from src.core.logger import DemiLogger`

**Examples from codebase:**
```python
# src/llm/inference.py
import asyncio
import time
from typing import Optional, List, Dict
from src.llm.config import LLMConfig
from src.core.logger import DemiLogger

# src/conductor/orchestrator.py
import asyncio
import signal
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.core.logger import get_logger
from src.core.config import DemiConfig
```

**Path Convention:**
- Always use absolute imports from `src/` root: `from src.llm.config import ...`
- Never use relative imports
- Organize by domain: `src/llm/`, `src/emotion/`, `src/api/`, `src/conductor/`, `src/integrations/`

## Code Structure

**Module Organization:**
- Each module has docstring at top describing purpose
- Example from `src/llm/inference.py`:
  ```python
  """
  LLM inference engine for Demi with Ollama backend.

  Provides async interface to Ollama for response generation,
  with context window management, token counting, and error handling.
  """
  ```

**Class Structure:**
- Docstrings on class definition
- Methods ordered: `__init__`, public methods, private methods
- Type hints on all method signatures

**Dataclass Pattern:**
- Use `@dataclass` for simple data models
- Include field defaults where appropriate
- Use `field(default_factory=...)` for mutable defaults
- Example from `src/emotion/models.py`:
  ```python
  @dataclass
  class EmotionalState:
      loneliness: float = 0.5
      excitement: float = 0.5
      momentum: Dict[str, float] = field(default_factory=lambda: {...})
      last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
  ```

## Error Handling

**Pattern:** Custom exception hierarchy with descriptive names

**Examples from codebase:**
```python
# src/llm/inference.py
class InferenceError(Exception):
    """Generic LLM inference error."""
    pass

class ContextOverflowError(InferenceError):
    """Context window exceeded maximum allowed tokens."""
    pass
```

**Exception Handling Strategy:**
- Catch specific exceptions, not bare `except:`
- Log exceptions with full context when caught
- Example from `src/llm/inference.py`:
  ```python
  except asyncio.TimeoutError:
      self.logger.warning("Ollama health check: timeout")
      return False
  except Exception as e:
      self.logger.warning(f"Ollama health check: {type(e).__name__}")
      return False
  ```

**Fallback Patterns:**
- Try/except with graceful fallbacks for optional dependencies
- Example: `try: import structlog` then `HAS_STRUCTLOG = True` flag for conditional use

## Logging

**Framework:** `DemiLogger` custom class wrapping Python's standard `logging` module
- Location: `src/core/logger.py`
- Supports structured logging with optional `structlog` integration
- Uses `get_logger()` function to retrieve singleton instance

**Usage Pattern:**
```python
from src.core.logger import get_logger
logger = get_logger()

# Debug level
logger.debug(f"OllamaInference initialized with model: {config.model_name}")

# Info level
logger.info("Configuration valid")

# Warning level
logger.warning("Ollama health check: timeout")

# Error level with exception info
logger.error(f"Configuration validation failed: {str(e)}")
logger.exception(f"Unhandled exception: {exc_type.__name__}")
```

**Log Levels Used:**
- `DEBUG`: Detailed initialization and internal state
- `INFO`: Startup, shutdown, successful operations
- `WARNING`: Recoverable issues, timeouts
- `ERROR`: Failures, validation errors
- `CRITICAL`: System shutdown

## Comments & Documentation

**Docstrings:**
- Triple-quoted docstrings on all classes and functions
- Format: One-line summary, blank line, detailed description if needed
- Include Args, Returns sections for methods
- Example from `src/llm/inference.py`:
  ```python
  async def health_check(self) -> bool:
      """
      Check if Ollama server is responding.

      Calls Ollama /api/tags endpoint to verify server availability.

      Returns:
          True if Ollama is online and responding, False otherwise
      """
  ```

**Inline Comments:**
- Minimal inline comments - code should be self-documenting
- When comments exist, they explain "why" not "what"
- Example from `src/emotion/models.py`:
  ```python
  # Clamp to [floor, 1.0]
  if current < floor:
      setattr(self, name, floor)
  ```

**File Headers:**
- All modules start with docstring describing module purpose and contents
- Example from `main.py`:
  ```python
  """
  Demi main entry point - Application startup and lifecycle management.

  Handles:
  - Command-line argument parsing
  - Configuration validation
  - Conductor initialization and startup
  - Graceful shutdown with signal handling
  - Exit codes for different failure scenarios
  """
  ```

## Function & Method Design

**Function Size:** Most functions 10-40 lines
- Larger functions break complex logic into helper methods
- Example: `ApplicationManager.startup()` is 25 lines of clear steps

**Parameters:**
- Use type hints on all parameters
- Default values for optional parameters
- Prefer multiple parameters over dictionaries when <5 parameters
- Example: `def __init__(self, config_path: str = None, log_level: str = None):`

**Return Values:**
- Always include type hints: `-> bool:`, `-> str:`, `-> Optional[Dict[str, Any]]:`
- Return values named in docstring Args/Returns section
- Consistent return types across related methods

**Async/Await:**
- Use `async def` for functions that perform I/O or await other async functions
- Use `await` for calling async functions
- Wrap non-async operations in `asyncio.wait_for()` for timeout control
- Example from `src/llm/inference.py`:
  ```python
  async def health_check(self) -> bool:
      response = await asyncio.wait_for(
          client.list(), timeout=self.config.timeout_sec
      )
  ```

## Validation Patterns

**Input Validation in `__post_init__` for Dataclasses:**
- Used on pydantic models and dataclasses
- Validates bounds, types, and required fields
- Raises `ValueError` with descriptive messages
- Example from `src/llm/config.py`:
  ```python
  def _validate(self):
      """Validate all configuration parameters."""
      if not self.model_name or not isinstance(self.model_name, str):
          raise ValueError("model_name must be non-empty string")
      if not (0.0 <= self.temperature <= 1.0):
          raise ValueError("temperature must be in range [0.0, 1.0]")
  ```

## State Management

**Dataclass Use:**
- Immutable state represented as frozen dataclasses when possible
- Mutable state in regular classes with methods
- Status tracking with Enums: `class PluginState(Enum):`

**Method Naming for State Changes:**
- Setter methods: `set_emotion()`, `start_autonomy()`, `stop_autonomy()`
- Checker methods: `is_running()`, `is_active()`, `is_loaded()`
- Example from `src/emotion/models.py`:
  ```python
  def set_emotion(self, emotion_name: str, value: float, momentum_override: bool = False) -> None:
  ```

## Pydantic Models

**Location:** `src/api/models.py`

**Pattern:**
- Inherit from `pydantic.BaseModel` for API validation
- Use dataclasses for internal domain models
- Example from `src/api/models.py`:
  ```python
  from pydantic import BaseModel, EmailStr

  class User(BaseModel):
      user_id: str
      email: EmailStr  # Built-in validation
      username: str
  ```

---

*Convention analysis: 2026-02-02*
