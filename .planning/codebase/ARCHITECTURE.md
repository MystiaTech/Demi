# Architecture

**Analysis Date:** 2026-02-02

## Pattern Overview

**Overall:** Modular conductor-orchestrated system with layered separation of concerns

**Key Characteristics:**
- Central orchestrator (Conductor) coordinates all subsystems
- Plugin-based platform integration with lifecycle management
- Emotion system as cross-cutting concern that influences all behavior
- Async-first design with task-based background processing
- Dual-mode operation: standalone conductor and FastAPI API server

## Layers

**Entry Point Layer:**
- Purpose: Application lifecycle management, configuration loading, graceful shutdown
- Location: `main.py`, `src/api/main.py`
- Contains: ApplicationManager, argument parsing, signal handling
- Depends on: Conductor, DemiConfig
- Used by: Shell/deployment systems

**API Layer (FastAPI):**
- Purpose: Android client communication via REST/WebSocket
- Location: `src/api/`
- Contains: Auth routes (`auth.py`), WebSocket handler (`websocket.py`), migrations (`migrations.py`)
- Depends on: Core layer for logging and config, models for data structures
- Used by: Android client applications
- Key Components:
  - `src/api/auth.py`: JWT token management, user authentication, session tracking
  - `src/api/websocket.py`: Real-time bidirectional messaging with ConnectionManager
  - `src/api/autonomy.py`: Autonomous behavior endpoints and background tasks
  - `src/api/models.py`: Pydantic request/response models

**Conductor/Orchestration Layer:**
- Purpose: Central nervous system coordinating all subsystems
- Location: `src/conductor/`
- Contains: Main orchestrator, health monitoring, resource scaling, request routing, metrics
- Depends on: All other subsystems
- Used by: Entry points, plugins
- Key Components:
  - `src/conductor/orchestrator.py`: Main Conductor class managing startup/shutdown sequence
  - `src/conductor/health.py`: HealthMonitor for platform health checks (5-second intervals)
  - `src/conductor/scaler.py`: PredictiveScaler for resource auto-scaling
  - `src/conductor/router.py`: RequestRouter for content-based request routing
  - `src/conductor/circuit_breaker.py`: Circuit breaker protection for platform integrations
  - `src/conductor/metrics.py`: MetricsRegistry for performance tracking
  - `src/conductor/resource_monitor.py`: System resource usage monitoring
  - `src/conductor/isolation.py`: Platform isolation and sandboxing

**Platform Integration Layer:**
- Purpose: Abstract interface for platform-specific plugins
- Location: `src/platforms/`, `src/integrations/`
- Contains: Base classes, concrete implementations
- Depends on: Core layer for logging
- Used by: Conductor for multi-platform communication
- Key Components:
  - `src/platforms/base.py`: BasePlatform abstract class defining plugin contract
  - `src/integrations/discord_bot.py`: Discord integration with message routing and ramble support
  - Additional platform implementations loaded via plugin system

**Plugin Management Layer:**
- Purpose: Plugin discovery, lifecycle management, state tracking
- Location: `src/plugins/`
- Contains: Plugin discovery, loading, state management
- Depends on: Platform base classes
- Used by: Conductor during startup
- Key Components:
  - `src/plugins/manager.py`: PluginManager handling discovery, loading, unloading
  - `src/plugins/discovery.py`: Plugin discovery via entry points
  - `src/plugins/base.py`: PluginMetadata and PluginState enums

**LLM/Inference Layer:**
- Purpose: LLM inference engine with context and personality
- Location: `src/llm/`
- Contains: Ollama inference, prompt building, response processing, conversation history
- Depends on: Core layer, emotion system
- Used by: Conductor for generating responses
- Key Components:
  - `src/llm/inference.py`: OllamaInference engine with token counting
  - `src/llm/prompt_builder.py`: PromptBuilder with codebase context injection
  - `src/llm/response_processor.py`: ResponseProcessor for structured LLM output parsing
  - `src/llm/history_manager.py`: ConversationHistory for multi-turn context
  - `src/llm/codebase_reader.py`: CodebaseReader for self-awareness capabilities
  - `src/llm/config.py`: LLMConfig for model and inference parameters

**Emotion/Personality Layer:**
- Purpose: Emotional state tracking and personality modulation
- Location: `src/emotion/`
- Contains: Emotion models, persistence, decay, personality modulation, interaction tracking
- Depends on: Core database layer
- Used by: All layers for emotional context
- Key Components:
  - `src/emotion/models.py`: EmotionalState dataclass with 9 emotion dimensions
  - `src/emotion/persistence.py`: EmotionPersistence for SQLite storage and offline decay
  - `src/emotion/decay.py`: DecaySystem for time-based emotion degradation
  - `src/emotion/modulation.py`: PersonalityModulator for response style adaptation
  - `src/emotion/interactions.py`: InteractionType enum and interaction tracking

**Autonomy Layer:**
- Purpose: Autonomous behavior generation, emotional triggers, refusal system
- Location: `src/autonomy/`
- Contains: Coordinator, triggers, spontaneous initiator, refusal system
- Depends on: Emotion system, LLM layer, conductor
- Used by: Conductor and API for background autonomous actions
- Key Components:
  - `src/autonomy/coordinator.py`: AutonomyCoordinator managing background tasks and emotional triggers
  - `src/autonomy/triggers.py`: TriggerManager with emotional threshold evaluation
  - `src/autonomy/spontaneous.py`: SpontaneousInitiator for random autonomous behavior
  - `src/autonomy/refusals.py`: RefusalSystem for content filtering and request refusal
  - `src/autonomy/config.py`: AutonomyConfig with trigger thresholds and behavior settings

**Core Infrastructure Layer:**
- Purpose: Foundational services and utilities
- Location: `src/core/`
- Contains: Logging, configuration, database, error handling
- Depends on: Nothing (no upward dependencies)
- Used by: All layers
- Key Components:
  - `src/core/logger.py`: DemiLogger for structured logging
  - `src/core/config.py`: DemiConfig for YAML+environment configuration
  - `src/core/database.py`: DatabaseManager singleton for SQLite access
  - `src/core/error_handler.py`: Error handling utilities
  - `src/core/system.py`: System information and utilities
  - `src/core/defaults.yaml`: Default configuration file

**Models/Data Layer:**
- Purpose: Database ORM models and data structures
- Location: `src/models/`
- Contains: SQLAlchemy models, data serialization
- Depends on: Nothing
- Used by: Core database and API layers
- Key Components:
  - `src/models/base.py`: Base ORM models (EmotionalState, Interaction, PlatformStatus)
  - `src/models/rambles.py`: Ramble model for autonomous message storage

## Data Flow

**User Message → Response Flow:**

1. Client sends message via WebSocket to `src/api/websocket.py` with JWT token
2. ConnectionManager verifies token and routes to message handler
3. Message handler calls `conductor.request_inference()`
4. Conductor loads current emotional state from `EmotionPersistence`
5. PromptBuilder constructs prompt with:
   - Codebase context from CodebaseReader
   - Conversation history from ConversationHistory
   - Emotional state from persistence layer
   - Personality modulation from PersonalityModulator
6. OllamaInference generates response with token counting
7. ResponseProcessor parses response and extracts emotion updates
8. Emotion updates applied to EmotionalState via persistence layer
9. Response sent back to client via WebSocket
10. Interaction logged to audit trail in persistence layer

**Autonomous Behavior Flow:**

1. AutonomyCoordinator checks emotional triggers periodically (background task)
2. TriggerManager evaluates emotional state against thresholds
3. If trigger fires:
   - Spontaneous initiator generates appropriate content
   - RefusalSystem validates content against refusal rules
   - If approved, AutonomousAction queued
4. Conductor routes action to appropriate platform (Discord, Android, etc)
5. Platform executes action and returns result
6. Result logged to action history and emotion tracking

**State Management:**

- **Emotional State:** Persisted in SQLite via EmotionPersistence with timestamp-based UNIQUE constraint
- **Conversation History:** In-memory ConversationHistory instance in Conductor
- **Plugin State:** Tracked in PluginManager registry with PluginMetadata
- **Platform Health:** Maintained in HealthMonitor's check results dictionary
- **Background Tasks:** Stored as asyncio.Task references in Conductor and AutonomyCoordinator
- **Resource Metrics:** Cached in HealthMonitor's resource_metrics field

## Key Abstractions

**BasePlatform:**
- Purpose: Abstract contract for all platform integrations
- Examples: `src/integrations/discord_bot.py`, future Android/Telegram implementations
- Pattern: Each platform inherits and implements initialize(), shutdown(), send_message(), health_check()

**PluginMetadata:**
- Purpose: Represents plugin state and lifecycle
- Examples: `src/plugins/base.py`
- Pattern: Tracks plugin through states (UNREGISTERED → REGISTERED → LOADING → ACTIVE)

**EmotionalState:**
- Purpose: Represents Demi's current emotional condition
- Examples: `src/emotion/models.py`, used throughout LLM and autonomy layers
- Pattern: 9-dimensional vector with momentum tracking and decay application

**AutonomousAction:**
- Purpose: Represents a single autonomous action to execute
- Examples: `src/autonomy/coordinator.py`
- Pattern: Contains action_type, platform, content, context, priority, timestamp

**ProcessedResponse:**
- Purpose: Structured output from ResponseProcessor
- Examples: `src/llm/response_processor.py`
- Pattern: Parses LLM raw output into content, emotion updates, confidence scores

## Entry Points

**Main Application (Conductor):**
- Location: `main.py`
- Triggers: `python main.py` with optional --config, --log-level, --dry-run flags
- Responsibilities:
  - Parse CLI arguments
  - Validate configuration
  - Initialize ApplicationManager
  - Execute Conductor startup sequence
  - Run main event loop until shutdown signal

**FastAPI API Server:**
- Location: `src/api/main.py`
- Triggers: `uvicorn src.api.main:app` or via deployment
- Responsibilities:
  - Create FastAPI app with CORS middleware
  - Initialize database and autonomy tasks on startup
  - Route incoming requests to auth/websocket/health handlers
  - Clean up resources on shutdown

**Plugin Discovery:**
- Location: `src/plugins/discovery.py`
- Triggers: Called during Conductor startup sequence
- Responsibilities:
  - Scan for entry points named "demi.platforms"
  - Return mapping of platform names to classes
  - Log discovered plugins

## Error Handling

**Strategy:** Layered error handling with graceful degradation

**Patterns:**

**LLM Errors (Inference Layer):**
- `InferenceError`: Raised on Ollama connection/timeout issues
- `ContextOverflowError`: Raised when prompt exceeds token limit
- Handled by: Conductor returns error response to client, logs incident

**Plugin Errors (Integration Layer):**
- Platform initialization failures: Plugin marked as ERROR, circuit breaker activated
- Platform health check failures: HealthMonitor counts failures, may trigger isolation
- Handled by: PluginManager catches during load, logs and continues

**Database Errors (Core Layer):**
- Transaction failures: Caught in DatabaseManager.session_scope(), rolled back automatically
- Schema errors: Logged and require manual intervention
- Handled by: Context manager ensures rollback/cleanup

**Autonomy Errors (Behavior Layer):**
- Trigger evaluation failures: Logged, autonomy continues with other triggers
- Action execution failures: Logged to action_history with error context
- Handled by: AutonomyCoordinator continues despite individual failures

## Cross-Cutting Concerns

**Logging:**
- Framework: `src/core/logger.py` with DemiLogger class
- Pattern: Structured logging with context tags (e.g., "conductor_initialized", "plugin_loaded")
- Used throughout all layers for observability

**Validation:**
- Approach: Pydantic models in API layer, dataclass validation in core layer
- Examples: LoginRequest validation, token verification in auth.py
- Location: `src/api/models.py`, `src/api/auth.py`

**Authentication:**
- Approach: JWT token-based with short-lived access tokens (30 min) and refresh tokens (7 days)
- Implementation: `src/api/auth.py` with bcrypt password hashing
- Used by: WebSocket and API endpoints for user verification

**Resource Management:**
- Approach: Circuit breakers prevent cascade failures, predictive scaler adjusts resources
- Implementations: `src/conductor/circuit_breaker.py`, `src/conductor/scaler.py`
- Monitors: RAM, CPU, disk usage via psutil

**Task Lifecycle:**
- Approach: Async task management with explicit cleanup in shutdown handlers
- Pattern: Background tasks stored in task lists, cancelled during shutdown
- Used by: AutonomyCoordinator (autonomy tasks), Conductor (health/scaling/routing tasks)

---

*Architecture analysis: 2026-02-02*
