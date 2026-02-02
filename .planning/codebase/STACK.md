# Technology Stack

**Analysis Date:** 2026-02-02

## Languages

**Primary:**
- Python 3.x - Core application logic, LLM integration, emotional system, conductor, autonomy

**Secondary:**
- Kotlin - Android client (see `android/` directory for mobile implementation)

## Runtime

**Environment:**
- Python 3.10+ (inferred from asyncio/dataclass usage patterns)
- Ollama server (external dependency, not included in requirements.txt)

**Package Manager:**
- pip (Python dependencies in `requirements.txt`)
- Lockfile: Not detected (uses requirements.txt directly)

## Frameworks

**Core:**
- FastAPI 0.115.0+ - REST API server for Android client communication
- Uvicorn 0.32.0+ - ASGI application server (runs FastAPI)
- Discord.py 2.6.0+ - Discord bot integration

**Database:**
- SQLite 3 - Local persistent storage (default, configured via `DATABASE_URL`)
- SQLAlchemy 2.0.0+ - ORM layer (imported but raw sqlite3 also used)
- Alembic 1.13.0+ - Database migrations

**Authentication & Security:**
- Passlib 1.7.4+ with bcrypt - Password hashing
- PyJWT 2.9.0+ - JWT token generation/verification (HS256 algorithm)
- python-multipart 0.0.12+ - Form data parsing for FastAPI

**Validation:**
- Pydantic 2.9.0+ with EmailStr validator - Request/response models

**Monitoring & Observability:**
- psutil 5.9.0+ - System resource monitoring (CPU, memory, disk)
- prometheus-client 0.20.0+ - Optional Prometheus metrics integration (graceful fallback if unavailable)
- structlog 24.1.0+ - Optional structured logging to JSON (graceful fallback if unavailable)

**Machine Learning (Optional):**
- scikit-learn 1.3.0+ - Predictive resource scaling (optional, graceful fallback)

**Testing:**
- pytest 7.4.0+ - Test runner
- pytest-asyncio 0.21.0+ - Async test support
- pytest-cov 4.1.0+ - Coverage reporting

**Code Quality:**
- Black 23.0.0+ - Code formatting

## Key Dependencies

**Critical:**
- discord.py 2.6.0 - Discord bot presence, message handling, embed formatting
- FastAPI 0.115.0 - Android REST API, authentication endpoints, WebSocket support
- Pydantic 2.9.0 - Request/response validation, type safety
- PyJWT 2.9.0 - JWT token handling for Android multi-device authentication
- Passlib[bcrypt] 1.7.4 - Secure password hashing for user accounts

**LLM Integration:**
- ollama (external package, installed separately) - Async client for local LLM inference

**Infrastructure:**
- psutil 5.9.0 - Real-time CPU, memory, disk monitoring for resource awareness
- prometheus-client 0.20.0 - Optional metrics collection for system observability
- structlog 24.1.0 - Optional structured logging for JSON output

## Configuration

**Environment:**
- Configuration loaded from `src/core/defaults.yaml` (YAML)
- Environment variable overrides with `DEMI_` prefix
- Supports runtime configuration updates via `DemiConfig.update()` method

**Key Environment Variables:**
- `DISCORD_BOT_TOKEN` - Discord bot authentication token
- `DISCORD_RAMBLE_CHANNEL_ID` - Channel ID for autonomous messages
- `JWT_SECRET_KEY` - Access token secret
- `JWT_REFRESH_SECRET_KEY` - Refresh token secret
- `ANDROID_API_HOST` - API server bind address (default: 0.0.0.0)
- `ANDROID_API_PORT` - API server port (default: 8000)
- `DATABASE_URL` - SQLite connection string (format: `sqlite:////path/to/db`)
- `DEMI_DB_PATH` - Legacy database path for emotions
- `DEMI_DEBUG` - Enable debug mode
- `DEMI_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `DEMI_DATA_DIR` - Data directory for logs, databases (default: ~/.demi)
- `DEMI_RAM_THRESHOLD` - RAM usage threshold percentage for alerts
- `DEMI_MAX_ERRORS` - Maximum error count before degradation
- `DEMI_AUTO_RECOVER` - Enable automatic recovery from failures

**Build:**
- No build configuration files detected (pure Python, no compilation)
- Direct execution via `python main.py` or `uvicorn`

## Platform Requirements

**Development:**
- Python 3.10+
- Virtual environment (venv detected in project)
- Ollama server running locally on `http://localhost:11434` (default)

**Production:**
- Python 3.10+
- Linux/macOS/Windows with WSL2 support
- 12GB+ RAM recommended (per README)
- SQLite database writable to disk
- Ollama server accessible (local or remote)
- Discord bot token from Discord Developer Portal
- Network access for Discord/Android communication

**Deployment Target:**
- Local machine (primary)
- Android devices via FastAPI endpoint
- Discord via discord.py bot
- Potentially containerized (no Dockerfile detected yet)

---

*Stack analysis: 2026-02-02*
