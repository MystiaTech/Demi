# Codebase Concerns

**Analysis Date:** 2026-02-02

## Tech Debt

### Duplicate Initialization in Conductor Constructor
- Issue: Multiple attributes are initialized twice with identical values, suggesting incomplete refactoring
- Files: `src/conductor/orchestrator.py` (lines 103-142)
- Impact: Code confusion, risk of inconsistent initialization order during future maintenance
- Fix approach: Remove duplicate initialization blocks (lines 107-135) and keep only final initialization sequence (lines 121-142)

### Global Singleton Pattern Without Thread Safety
- Issue: Multiple global singletons use simple flag-based initialization without synchronization
- Files:
  - `src/conductor/orchestrator.py` (get_conductor, get_conductor_instance)
  - `src/conductor/health.py` (get_health_monitor)
  - `src/conductor/circuit_breaker.py` (get_circuit_breaker_manager)
  - `src/conductor/metrics.py` (get_metrics)
- Impact: Race conditions in multi-threaded access; potential for multiple instances despite singleton intent
- Fix approach: Implement thread-safe singleton pattern using locks or use a more robust DI container

### Large Monolithic Files
- Issue: Several core files exceed safe complexity thresholds
- Files:
  - `src/conductor/orchestrator.py` (853 lines) - manages plugins, LLM, health, emotion, autonomy, shutdown
  - `src/autonomy/spontaneous.py` (665 lines) - timing analysis, context evaluation, initiation logic
  - `src/integrations/discord_bot.py` (592 lines) - bot lifecycle, message handling, embed formatting
  - `src/autonomy/coordinator.py` (578 lines) - action execution, platform routing, state tracking
  - `src/api/autonomy.py` (572 lines) - API endpoints, database operations, ramble management
- Impact: Testing difficulty, high cognitive load, increased bug risk, harder to locate issues
- Fix approach: Break into smaller, focused classes with single responsibility (e.g., separate LLMManager, PluginLifecycleManager from Conductor)

## Known Bugs

### Bare Exception Handler in Response Processor
- Symptoms: Silent failures in refusal interaction application without specific error context
- Files: `src/llm/response_processor.py` (line 316)
- Trigger: When `InteractionType.USER_REFUSAL` interaction fails or is not available
- Workaround: Falls back to manual emotion adjustments, but loses original error context
- Issue: `except:` clause catches all exceptions including system exits, making debugging impossible

### AttributeError Handling for Missing load_state Method
- Symptoms: Silent fallback when emotion persistence doesn't have expected methods
- Files: `src/autonomy/coordinator.py` (line 174)
- Trigger: During autonomy startup if EmotionPersistence lacks load_state method
- Workaround: Creates default EmotionalState, but suggests inconsistent interface contract
- Fix approach: Implement proper interface validation in __init__ or use ABC abstract base class

## Security Considerations

### Hardcoded Default JWT Secrets
- Risk: Production deployments could use default secrets if environment variables not properly set
- Files: `src/api/auth.py` (lines 28-29)
- Current mitigation: Comments suggest changing in production; .env.example shows requirement
- Recommendations:
  1. Validate secrets are NOT defaults at startup, raise fatal error if detected
  2. Require explicit setup script that generates and validates secrets
  3. Add tests that verify defaults are never used in production config

### Insecure Default Database Path
- Risk: Database path defaults to hardcoded `~/.demi/demi.db` which may be world-readable
- Files: `src/api/auth.py` (line 41), `src/emotion/persistence.py` (line 18)
- Current mitigation: Uses sqlite3 file permissions (OS-dependent)
- Recommendations:
  1. Set file permissions to 0600 (owner read/write only) after creation
  2. Validate database parent directory has proper permissions
  3. Document production deployment requirements for database security

### Unvalidated Direct Environment Variable Usage
- Risk: Discord bot token stored directly from environment without sanitization
- Files: `src/integrations/discord_bot.py` (lines 319-327)
- Current mitigation: Checks for empty string but doesn't validate format
- Recommendations: Add basic validation (length, character set) before use

### SQL Injection Risk in Parameterized Queries
- Status: **LOW RISK** - All observed database queries use parameterized format correctly
- Files: `src/api/auth.py`, `src/emotion/persistence.py`, `src/api/autonomy.py`
- Details: Code properly uses `?` placeholders and passes parameters separately
- Confidence: No f-string or format-string interpolation in SQL queries found

## Performance Bottlenecks

### Blocking Codebase Reader Initialization
- Problem: CodebaseReader loads entire codebase into memory during Conductor init, blocking startup
- Files: `src/llm/codebase_reader.py` (lines 58-100)
- Cause: Synchronous file walking and parsing on all Python files in `src/` directory
- Impact: Startup latency increases with codebase size; blocks all other initialization
- Improvement path:
  1. Make codebase loading async
  2. Implement lazy loading - only load files on first query
  3. Add caching layer with TTL for frequently accessed files

### Naive Emotion Decay System
- Problem: Decay calculations performed on every access without batching
- Files: `src/emotion/decay.py`
- Cause: Linear iteration through emotions for each access
- Impact: With 9 emotions and frequent access, causes cumulative overhead
- Improvement path:
  1. Batch decay calculations at fixed intervals (every 5 minutes)
  2. Use vectorized operations if emotion state becomes larger

### Health Check Loop Polling
- Problem: Health monitor polls all platforms synchronously every 5 seconds
- Files: `src/conductor/health.py` (lines 56-100+)
- Cause: Sequential health checks rather than concurrent execution
- Impact: As platform count grows, health check duration exceeds interval
- Improvement path:
  1. Use asyncio.gather() for concurrent health checks
  2. Implement timeout per platform to prevent slow checks blocking others
  3. Add circuit breaker backoff to reduce check frequency for unhealthy platforms

## Fragile Areas

### Autonomy System Initialization Order Dependencies
- Files: `src/autonomy/coordinator.py`, `src/conductor/orchestrator.py`
- Why fragile: Multiple subsystems (conductor, emotion_persistence, spontaneous_initiator) must be initialized in specific order with circular dependency potential
- Safe modification:
  1. Document exact initialization sequence in coordinator
  2. Add assertions validating all dependencies exist before use
  3. Implement defensive checks: `if self.conductor is None: raise RuntimeError("Not initialized")`
- Test coverage gaps: No tests verify initialization with missing dependencies

### Discord Embed Formatting with Dynamic Content
- Files: `src/integrations/discord_bot.py` (lines 58-100+)
- Why fragile: 2000-character limit enforced but exception handling for overflow is absent
- Safe modification:
  1. Truncate content before passing to format function
  2. Add unit tests with boundary conditions (1999, 2000, 2001 chars)
  3. Log truncation events for debugging
- Test coverage: `test_discord_embed_formatting.py` exists but may lack edge cases

### Plugin Discovery and Dynamic Loading
- Files: `src/plugins/manager.py`, `src/conductor/orchestrator.py` (lines 257-276)
- Why fragile: Failed plugin loads continue silently, but system may expect them to exist
- Safe modification:
  1. Distinguish between optional and critical plugins
  2. Add pre-flight validation that critical plugins load successfully
  3. Implement rollback if critical plugin fails
- Test coverage: Assumes all plugins load; no tests for partial failures

### LLM Fallback Chain
- Files: `src/conductor/orchestrator.py` (lines 509-518)
- Why fragile: Generic error response returned without analyzing error cause
- Safe modification:
  1. Distinguish inference errors from system errors
  2. Return different messages based on error type (timeout vs OOM vs model error)
  3. Add detailed logging of all error paths
- Test coverage: Generic error handling tested but not specific error paths

## Scaling Limits

### In-Memory Codebase Index
- Current capacity: ~383 lines per largest file; entire `src/` indexed in memory
- Limit: Breaks when codebase exceeds available RAM (unlikely but possible)
- Scaling path:
  1. Implement disk-based cache (SQLite or similar)
  2. Use bloom filters for quick file exclusion
  3. Lazy-load files on demand with LRU eviction

### Singular Discord Connection Per Bot
- Current capacity: One Discord.py client per bot instance
- Limit: Cannot distribute across multiple processes; bottleneck at 10k concurrent connections per process
- Scaling path:
  1. Implement bot sharding for multiple servers
  2. Use Discord.py's built-in sharding support
  3. Add load balancing across multiple bot instances

### SQLite Database Single Writer
- Current capacity: Works for small user bases (<1000 concurrent)
- Limit: SQLite default locking becomes contention bottleneck above ~100 concurrent writes
- Scaling path:
  1. Migrate to PostgreSQL with connection pooling
  2. Implement WAL (Write-Ahead Logging) mode for SQLite as interim
  3. Add query batching to reduce write frequency

### Autonomy Action Queue
- Current capacity: `self.pending_actions` is unbounded list (line 83 of coordinator.py)
- Limit: No eviction policy; old actions remain in memory forever if not executed
- Scaling path:
  1. Implement bounded queue with configurable max size
  2. Add TTL for pending actions (expire after 24 hours)
  3. Implement priority-based eviction (remove lowest priority actions first)

## Dependencies at Risk

### Ollama Service Dependency
- Risk: Hard dependency on external Ollama service at localhost:11434 with no fallback
- Impact: If Ollama crashes, all LLM inference disabled; autonomy stops
- Current mitigation: Health checks report unavailability but don't switch modes
- Migration plan:
  1. Implement local-mode with pre-generated responses for offline operation
  2. Add secondary LLM provider (e.g., local llama.cpp) as failover
  3. Queue requests during Ollama downtime for batch processing when restored

### psutil Conditional Import
- Risk: Health monitoring silently degrades if psutil not installed
- Files: `src/conductor/health.py` (lines 12-17)
- Impact: Resource metrics unavailable; health checks incomplete
- Current mitigation: Checks `HAS_PSUTIL` flag
- Migration plan: Make psutil required dependency (add to requirements.txt with version pins)

### Discord.py Event Loop Lifecycle
- Risk: Bot event loop conflicts with asyncio.run() in Conductor startup
- Files: `src/integrations/discord_bot.py` (lines 462+), `src/conductor/orchestrator.py`
- Impact: If not carefully managed, event loop ownership errors crash application
- Current mitigation: Creates task and manages lifecycle
- Migration plan: Implement centralized event loop manager shared across all async components

## Test Coverage Gaps

### Conductor Initialization Paths
- What's not tested: Partial failures during startup (e.g., plugins fail but LLM succeeds)
- Files: `src/conductor/orchestrator.py` (lines 161-305)
- Risk: Undefined system state after partial failures; no tests verify graceful degradation
- Priority: HIGH - startup failures should not leave system in zombie state

### Error Recovery in Autonomy System
- What's not tested: Graceful recovery when conductor becomes unavailable mid-execution
- Files: `src/autonomy/coordinator.py`, `src/autonomy/spontaneous.py`
- Risk: Pending actions orphaned; resource leaks; system hang
- Priority: HIGH - autonomy runs in background; failures may go unnoticed

### Edge Cases in Emotion State Calculations
- What's not tested: Emotion values at exactly 0.0 and 1.0 boundaries; negative momentum values
- Files: `src/emotion/models.py`, `src/emotion/persistence.py`
- Risk: Boundary conditions cause unexpected behavior (clamping issues, division by zero)
- Priority: MEDIUM - affects avatar personality authenticity

### Discord Message Content Validation
- What's not tested: Messages with special characters (zero-width, RTL, emoji edge cases), very long messages
- Files: `src/integrations/discord_bot.py`, `test_discord_embed_formatting.py`
- Risk: Malformed embeds crash bot; messages fail to send
- Priority: MEDIUM - affects user experience but not system stability

### Database Consistency After Crashes
- What's not tested: Database state recovery after process termination during write
- Files: `src/emotion/persistence.py`, `src/api/auth.py`
- Risk: Corrupted emotion history; duplicate session records; orphaned user data
- Priority: HIGH - affects long-term reliability and data integrity

---

*Concerns audit: 2026-02-02*
