# Codebase Structure

**Analysis Date:** 2026-02-02

## Directory Layout

```
/home/mystiatech/projects/Demi/
├── main.py                    # Entry point - application lifecycle management
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variable template
├── src/                      # Main source code
│   ├── __init__.py
│   ├── core/                 # Infrastructure layer
│   │   ├── __init__.py
│   │   ├── logger.py         # DemiLogger structured logging
│   │   ├── config.py         # DemiConfig YAML+env configuration
│   │   ├── database.py       # DatabaseManager SQLite singleton
│   │   ├── error_handler.py  # Error handling utilities
│   │   ├── system.py         # System information utilities
│   │   └── defaults.yaml     # Default configuration file
│   ├── api/                  # FastAPI layer (Android client)
│   │   ├── __init__.py       # create_app() FastAPI factory
│   │   ├── main.py           # Uvicorn entry point
│   │   ├── auth.py           # JWT authentication and sessions
│   │   ├── websocket.py      # WebSocket handler with ConnectionManager
│   │   ├── messages.py       # Message storage and retrieval
│   │   ├── models.py         # Pydantic request/response models
│   │   ├── autonomy.py       # Autonomy background task endpoints
│   │   └── migrations.py     # Database schema migrations
│   ├── conductor/            # Orchestration layer
│   │   ├── __init__.py       # Exports: Conductor, get_conductor()
│   │   ├── orchestrator.py   # Main Conductor class (853 lines)
│   │   ├── health.py         # HealthMonitor with 5-sec check interval
│   │   ├── circuit_breaker.py # Circuit breaker for platform protection
│   │   ├── scaler.py         # PredictiveScaler for resource auto-scaling
│   │   ├── router.py         # RequestRouter for content-based routing
│   │   ├── metrics.py        # MetricsRegistry and performance tracking
│   │   ├── resource_monitor.py # System resource usage monitoring
│   │   └── isolation.py      # Platform isolation and sandboxing
│   ├── llm/                  # LLM/Inference layer
│   │   ├── __init__.py       # Module exports
│   │   ├── inference.py      # OllamaInference engine with token counting
│   │   ├── config.py         # LLMConfig model parameters
│   │   ├── prompt_builder.py # PromptBuilder with codebase context
│   │   ├── response_processor.py # ResponseProcessor for output parsing (527 lines)
│   │   ├── history_manager.py # ConversationHistory for multi-turn context
│   │   └── codebase_reader.py # CodebaseReader for self-awareness
│   ├── emotion/              # Emotion/Personality layer
│   │   ├── __init__.py
│   │   ├── models.py         # EmotionalState 9-dimension vector model
│   │   ├── persistence.py    # EmotionPersistence SQLite storage (454 lines)
│   │   ├── decay.py          # DecaySystem for time-based degradation
│   │   ├── modulation.py     # PersonalityModulator for style adaptation
│   │   └── interactions.py   # InteractionType tracking
│   ├── autonomy/             # Autonomous Behavior layer
│   │   ├── __init__.py
│   │   ├── coordinator.py    # AutonomyCoordinator unified behavior manager (578 lines)
│   │   ├── triggers.py       # TriggerManager emotional threshold evaluation (414 lines)
│   │   ├── spontaneous.py    # SpontaneousInitiator random behavior (665 lines)
│   │   ├── refusals.py       # RefusalSystem content filtering (343 lines)
│   │   └── config.py         # AutonomyConfig settings and thresholds
│   ├── platforms/            # Platform integration abstraction
│   │   ├── __init__.py
│   │   └── base.py           # BasePlatform abstract contract
│   ├── plugins/              # Plugin management layer
│   │   ├── __init__.py
│   │   ├── manager.py        # PluginManager lifecycle management
│   │   ├── discovery.py      # Plugin discovery via entry points
│   │   └── base.py           # PluginMetadata and PluginState enums
│   ├── integrations/         # Platform implementations
│   │   ├── __init__.py
│   │   ├── discord_bot.py    # Discord integration with emotion visualization (592 lines)
│   │   └── stubs.py          # Stub implementations for testing
│   └── models/               # Data models
│       ├── __init__.py
│       ├── base.py           # SQLAlchemy ORM base models
│       └── rambles.py        # Ramble autonomous message storage
├── tests/                    # Test suite
│   ├── test_autonomy*.py     # Autonomy system tests
│   ├── test_emotion*.py      # Emotion system tests
│   ├── test_llm*.py          # LLM layer tests
│   ├── test_discord*.py      # Discord integration tests
│   └── test_history_manager.py
├── android/                  # Android client code
│   ├── app/
│   ├── build.gradle.kts
│   └── settings.gradle.kts
├── .planning/                # Planning and documentation
│   ├── phases/              # Phase completion summaries
│   └── codebase/            # Codebase analysis documents (this dir)
└── .github/                  # GitHub workflows and config
```

## Directory Purposes

**`src/core/`:**
- Purpose: Infrastructure services required by all layers
- Contains: Logging, configuration management, database access, error handling
- Key files: `logger.py` (DemiLogger), `config.py` (DemiConfig), `database.py` (DatabaseManager)

**`src/api/`:**
- Purpose: FastAPI REST/WebSocket API for Android client communication
- Contains: Auth routes, WebSocket handler, message storage, Pydantic models
- Key files: `auth.py` (JWT + sessions), `websocket.py` (real-time messaging), `autonomy.py` (background tasks)

**`src/conductor/`:**
- Purpose: Central orchestrator coordinating all subsystems
- Contains: Lifecycle management, health monitoring, resource scaling, circuit breakers
- Key files: `orchestrator.py` (main Conductor), `health.py` (health checks), `scaler.py` (auto-scaling)

**`src/llm/`:**
- Purpose: LLM inference engine with context management and personality
- Contains: Ollama inference, prompt building, response processing, conversation history
- Key files: `inference.py` (OllamaInference), `prompt_builder.py` (context injection), `response_processor.py` (output parsing)

**`src/emotion/`:**
- Purpose: Emotional state tracking, persistence, and personality adaptation
- Contains: 9-dimensional emotion models, SQLite storage, decay system, personality modulation
- Key files: `models.py` (EmotionalState), `persistence.py` (storage), `decay.py` (time-based degradation)

**`src/autonomy/`:**
- Purpose: Autonomous behavior generation and emotional trigger-based actions
- Contains: Coordinator, emotional triggers, spontaneous behavior, refusal system
- Key files: `coordinator.py` (unified manager), `triggers.py` (threshold evaluation), `spontaneous.py` (random generation)

**`src/platforms/`:**
- Purpose: Abstract interface for platform plugins
- Contains: BasePlatform abstract class defining lifecycle contract
- Key files: `base.py` (PluginHealth, BasePlatform)

**`src/plugins/`:**
- Purpose: Plugin discovery and lifecycle management
- Contains: Plugin manager, discovery mechanism, state tracking
- Key files: `manager.py` (PluginManager), `discovery.py` (entry point scanning), `base.py` (PluginMetadata)

**`src/integrations/`:**
- Purpose: Concrete platform implementations
- Contains: Discord bot with emotion visualization, stub implementations
- Key files: `discord_bot.py` (Discord integration), `stubs.py` (testing stubs)

**`src/models/`:**
- Purpose: Database ORM models and data structures
- Contains: SQLAlchemy declarative base models
- Key files: `base.py` (EmotionalState, Interaction, PlatformStatus), `rambles.py` (Ramble storage)

**`tests/`:**
- Purpose: Unit and integration tests
- Contains: Test suites for emotion, autonomy, LLM, Discord integration
- Key files: `test_emotion_*.py`, `test_autonomy_*.py`, `test_llm_*.py`

**`android/`:**
- Purpose: Android client application (Kotlin/Gradle)
- Contains: Android app source, build configuration
- Key files: `app/`, `build.gradle.kts`

## Key File Locations

**Entry Points:**
- `main.py`: Main CLI entry point for standalone conductor
- `src/api/main.py`: Uvicorn entry point for FastAPI server
- `src/plugins/discovery.py`: Plugin discovery entry point during startup

**Configuration:**
- `src/core/defaults.yaml`: Default system configuration
- `src/core/config.py`: Configuration loader with env override support
- `.env.example`: Environment variable template

**Core Logic:**
- `src/conductor/orchestrator.py`: Central orchestrator (853 lines) - defines startup sequence, plugin loading, autonomy coordination
- `src/autonomy/coordinator.py`: Autonomy system (578 lines) - manages autonomous behavior and emotional triggers
- `src/llm/inference.py`: LLM inference engine (317 lines) - Ollama integration with token counting
- `src/emotion/persistence.py`: Emotion storage (454 lines) - SQLite persistence with decay system

**Testing:**
- `tests/test_emotion_*.py`: Emotion system unit tests
- `tests/test_autonomy_*.py`: Autonomy behavior tests
- `tests/test_llm_*.py`: LLM inference and processing tests
- `tests/test_discord_rambles.py`: Discord integration tests

## Naming Conventions

**Files:**
- `*.py`: Python source files
- `*_test.py` or `test_*.py`: Unit/integration tests
- `*.yaml`: Configuration files
- `*_processor.py`: Classes that parse/transform data (e.g., response_processor.py)
- `*_manager.py`: Classes managing lifecycle/collections (e.g., plugin_manager.py)
- `*_coordinator.py`: Orchestration classes (e.g., autonomy_coordinator.py)

**Directories:**
- `src/`: Main source code
- `tests/`: Test suite
- `src/[domain]/`: Domain-specific modules (llm, emotion, autonomy, etc)
- `src/core/`: Infrastructure/cross-cutting concerns
- `.planning/`: Planning documents and analysis

**Classes:**
- PascalCase for all classes: `Conductor`, `AutonomyCoordinator`, `EmotionalState`
- Abstract base classes prefixed with "Base": `BasePlatform`
- Manager/coordinator classes: `PluginManager`, `TriggerManager`, `AutonomyCoordinator`
- Configuration classes end with "Config": `DemiConfig`, `AutonomyConfig`, `LLMConfig`
- Singleton getters use `get_*()`: `get_conductor()`, `get_logger()`

**Functions/Methods:**
- snake_case for all functions: `request_inference()`, `discover_plugins()`, `initialize()`
- Async functions are regular async functions, not prefixed: `async def startup()`, `async def load_plugin()`
- Private methods prefixed with underscore: `_init_schema()`, `_create_default_triggers()`

**Constants:**
- UPPER_SNAKE_CASE: `SECRET_KEY`, `MAX_FAILED_LOGIN_ATTEMPTS`, `EMOTION_COLORS`

## Where to Add New Code

**New Feature (End-to-End):**
- Primary feature code: Feature-specific directory under appropriate domain
  - Behavior feature: `src/autonomy/[feature].py`
  - LLM feature: `src/llm/[feature].py`
  - Emotion feature: `src/emotion/[feature].py`
- API endpoints: Add router to `src/api/` or extend existing routers
- Tests: Create `tests/test_[feature].py` mirroring feature structure
- Configuration: Add section to `src/core/defaults.yaml` and `DemiConfig` class

**New Platform/Plugin:**
- Implementation: Create `src/integrations/[platform]_bot.py` extending `BasePlatform`
- Registration: Add entry point to `pyproject.toml` or `setup.py` in "demi.platforms" group
- Configuration: Add platform config section to `defaults.yaml`
- Plugin manager: No changes needed - auto-discovered via entry points

**New Component/Module:**
- Implementation: Create file in appropriate `src/[domain]/` directory
- Exports: Add to `__init__.py` in domain directory if public API
- Dependencies: Import from core layer, not upward dependencies
- Logging: Use `get_logger()` or inject `logger` instance

**Utilities/Helpers:**
- Shared helpers across modules: `src/core/[util_name].py`
- Domain-specific utilities: `src/[domain]/[util_name].py`
- Do not create top-level utility files unless used across 3+ domains

## Special Directories

**`src/core/`:**
- Purpose: Infrastructure services
- Generated: No
- Committed: Yes
- Notes: No business logic, only cross-cutting utilities. All modules should be importable without circular dependencies.

**`.planning/`:**
- Purpose: Planning documents and analysis
- Generated: Yes (by /gsd commands)
- Committed: Yes (except drafts)
- Notes: Created by `/gsd:map-codebase`, populated by `/gsd:plan-phase`, referenced by `/gsd:execute-phase`

**`tests/`:**
- Purpose: Test suite
- Generated: No
- Committed: Yes
- Notes: Pytest config in `pyproject.toml`. Run with `pytest` or `pytest -v`.

**`__pycache__/` and `.pytest_cache/`:**
- Purpose: Python bytecode and test cache
- Generated: Yes
- Committed: No (.gitignore)
- Notes: Auto-cleaned by Python runtime and pytest

**`android/`:**
- Purpose: Android client application
- Generated: Partially (compiled APKs)
- Committed: Source code yes, build artifacts no
- Notes: Separate Kotlin/Gradle project. Build with `./gradlew build`

---

*Structure analysis: 2026-02-02*
