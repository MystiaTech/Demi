# External Integrations

**Analysis Date:** 2026-02-02

## APIs & External Services

**LLM Provider:**
- Ollama - Local LLM inference engine
  - SDK/Client: `ollama` Python package (lazy-imported in `src/llm/inference.py`)
  - Auth: None (local service, unauthenticated)
  - Config: Base URL via `ollama.base_url` in `src/core/defaults.yaml` (default: `http://localhost:11434`)
  - Models: Configurable (default: `llama3.2:1b` with fallbacks to `llama3.2:3b`, `llama2:7b`)

**Discord API:**
- Discord Bot - Social platform integration
  - SDK/Client: `discord.py` 2.6.0+
  - Auth: `DISCORD_BOT_TOKEN` environment variable (from Discord Developer Portal)
  - Used by: `src/integrations/discord_bot.py`
  - Features: Message handling, embed formatting, status updates, ramble posting, emotion-based color coding

**Android/Mobile API:**
- Custom REST API - Mobile client communication
  - SDK: FastAPI 0.115.0+, Uvicorn 0.32.0+
  - Endpoints: `/api/v1/auth/*`, `/api/v1/status`, WebSocket connections
  - Entry point: `src/api/main.py` and `src/api/autonomy.py`
  - Host/Port: Configurable via `ANDROID_API_HOST` and `ANDROID_API_PORT` env vars

## Data Storage

**Databases:**

**SQLite:**
- Connection: `DATABASE_URL` environment variable or `DEMI_DATA_DIR/demi.sqlite`
- Location: `~/.demi/demi.sqlite` (default)
- Tables:
  - `users` - User accounts (user_id, email, username, password_hash, created_at, last_login)
  - `sessions` - Multi-device sessions (session_id, user_id, device_name, refresh_token_hash, expires_at)
  - `android_messages` - Android conversation history (message_id, conversation_id, content, emotion_state, status)
  - `discord_rambles` - Autonomous Discord messages (ramble_id, channel_id, content, emotion_state, trigger)
  - `emotional_state` - Persistent emotion values (from `src/emotion/persistence.py`)
  - `interaction_log` - Interaction history (from defaults.yaml)
  - `memory` - Long-term memory storage (from defaults.yaml)
- Client: Raw `sqlite3` module + SQLAlchemy 2.0.0+
- Migrations: `src/api/migrations.py` uses raw SQL (no Alembic ORM-based migrations yet)

**File Storage:**
- Local filesystem only
- YAML config: `src/core/defaults.yaml`
- Personality data: `data/DEMI_PERSONA.md`
- Logs: `~/.demi/logs/` (date-based naming: `demi_YYYY-MM-DD.log`)
- Metrics: `logs/metrics.json` (optional, configured in defaults.yaml)

**Caching:**
- In-memory: Message history deque in `src/llm/history_manager.py`
- Resource history: 30-minute sliding window in `src/conductor/resource_monitor.py`
- Prometheus in-memory metrics registry (if enabled)
- No Redis or Memcached detected

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based authentication (no external OAuth provider)
- Implementation: `src/api/auth.py`
- Approach:
  - Access tokens (30 minutes, HS256)
  - Refresh tokens (7 days, HS256)
  - Password hashing: bcrypt via passlib
  - Multi-device support via session tracking
  - Failed login lockout: 5 attempts → 15 minute lockout
- Secrets:
  - `JWT_SECRET_KEY` - Access token signing key
  - `JWT_REFRESH_SECRET_KEY` - Refresh token signing key

**Discord Authentication:**
- Bot token only (no user OAuth)
- Token: `DISCORD_BOT_TOKEN` env var
- Scope: Message reading, sending, status updates (defined by bot permissions in Discord Developer Portal)

## Monitoring & Observability

**Error Tracking:**
- None detected - errors logged to file/console only
- Could integrate Sentry but not currently configured

**Logs:**
- File-based logging to `~/.demi/logs/demi_YYYY-MM-DD.log`
- Console output with configurable level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured logging via structlog (optional, JSON output if available)
- Implementation: `src/core/logger.py` with rotation support
- Log level configurable via `DEMI_LOG_LEVEL` env var or config

**Metrics:**
- Prometheus client (optional, graceful fallback)
- Metrics exposed at in-memory registry (not HTTP endpoint yet)
- Tracked metrics: CPU, memory, disk, request counts, error rates, token usage
- Implementation: `src/conductor/metrics.py`
- Optional JSON file output: `logs/metrics.json` (from defaults.yaml)

**Health Monitoring:**
- System health checks: `src/conductor/health.py`
- Resource monitoring: `src/conductor/resource_monitor.py` (psutil-based)
- Ollama health check: `/api/tags` endpoint via ollama client
- Platform health: Discord connection status, API endpoint availability

## CI/CD & Deployment

**Hosting:**
- Local machine (primary, can run on WSL2 per README)
- Android: Remote API endpoint
- Discord: Via discord.py bot
- No cloud deployment detected

**CI Pipeline:**
- None detected - no GitHub Actions or other CI config found
- Test infrastructure available (pytest, pytest-asyncio, pytest-cov in requirements)

**Deployment:**
- Local: `python main.py` (via `src.core.ApplicationManager`)
- API: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- No Dockerfile detected yet

## Environment Configuration

**Required env vars:**
- `DISCORD_BOT_TOKEN` - Discord bot authentication
- `JWT_SECRET_KEY` - Critical for Android auth
- `JWT_REFRESH_SECRET_KEY` - Critical for session refresh

**Optional env vars (with sensible defaults):**
- `DATABASE_URL` - Defaults to `~/.demi/demi.sqlite`
- `ANDROID_API_HOST` - Defaults to `0.0.0.0`
- `ANDROID_API_PORT` - Defaults to `8000`
- `DEMI_DEBUG` - Defaults to false
- `DEMI_LOG_LEVEL` - Defaults to INFO
- `DEMI_DATA_DIR` - Defaults to `~/.demi`
- `DEMI_RAM_THRESHOLD` - Defaults to 80%
- `DEMI_MAX_ERRORS` - Defaults to 5
- `DEMI_AUTO_RECOVER` - Defaults to false

**Secrets location:**
- Environment variables (`.env` not in git, see `.env.example`)
- Loaded at runtime by `DemiConfig.load()` via `os.getenv()`
- No .env file loading detected (manual env var setup required)

## Webhooks & Callbacks

**Incoming:**
- Discord message webhooks (via discord.py event handlers)
  - `on_message()` - Direct messages and mentions
  - `on_ready()` - Bot connected status
- Android API webhooks:
  - POST `/api/v1/auth/login` - User authentication
  - POST `/api/v1/auth/refresh` - Token refresh
  - WebSocket connections for real-time messaging
- Autonomy triggers: Spontaneous message generation based on emotional thresholds

**Outgoing:**
- Discord: Message/embed posting to configured channel
- Android: WebSocket events (messages, typing indicators, read receipts)
- No external webhook deliveries detected

## Data Flow

**User → Discord:**
1. User mentions Demi in Discord
2. discord.py `on_message()` event fires
3. Message routed to conductor for inference
4. LLM generates response via Ollama
5. Response formatted as Discord Embed with emotion-based color
6. Embed sent back to Discord channel

**User → Android App:**
1. Android client sends message via `/api/v1/auth/*` endpoints
2. JWT token validated
3. Message stored in `android_messages` table
4. Conductor processes via LLM
5. Response sent back via WebSocket (`src/api/websocket.py`)
6. Android app receives in real-time

**Demi → Discord (Autonomous):**
1. Emotion triggers ramble generation (`src/autonomy/spontaneous.py`)
2. Ramble stored in `discord_rambles` table
3. Posted to `DISCORD_RAMBLE_CHANNEL_ID` channel
4. Formatted with trigger emotion and state

**Internal Persistence:**
1. All messages stored in SQLite
2. Emotional state persisted every 5 minutes (via `EmotionPersistence`)
3. Logs written to file daily
4. Metrics collected to in-memory Prometheus registry

---

*Integration audit: 2026-02-02*
