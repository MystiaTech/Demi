# Environment Variables Reference

Complete reference for all environment variables supported by Demi.

## Overview

Environment variables provide the highest priority configuration and are the recommended way to store secrets and deployment-specific settings. Variables are typically set in a `.env` file in the project root.

## Quick Reference

| Variable | Required | Default | Category |
|----------|----------|---------|----------|
| `DISCORD_BOT_TOKEN` | Yes* | - | Discord |
| `DISCORD_RAMBLE_CHANNEL_ID` | No | - | Discord |
| `DISCORD_PROGRESS_WEBHOOK_URL` | No | - | Discord |
| `JWT_SECRET_KEY` | Yes | - | Authentication |
| `JWT_REFRESH_SECRET_KEY` | Yes | - | Authentication |
| `ALLOWED_ORIGINS` | Yes | `http://localhost:3000` | Security |
| `DEMI_DB_PATH` | No | `~/.demi/emotions.db` | Database |
| `DATABASE_URL` | No | `sqlite:////home/user/.demi/demi.db` | Database |
| `ANDROID_API_HOST` | No | `127.0.0.1` | API Server |
| `ANDROID_API_PORT` | No | `8000` | API Server |
| `DEMI_DEBUG` | No | `false` | Core System |
| `DEMI_LOG_LEVEL` | No | `INFO` | Core System |
| `DEMI_DATA_DIR` | No | `~/.demi` | Core System |
| `DEMI_RAM_THRESHOLD` | No | `80` | Core System |
| `DEMI_MAX_ERRORS` | No | `5` | Core System |
| `DEMI_AUTO_RECOVER` | No | `false` | Core System |

\* Required only if using Discord integration

---

## Discord Configuration

### DISCORD_BOT_TOKEN

| Property | Value |
|----------|-------|
| **Required** | Yes (for Discord integration) |
| **Default** | None |
| **Sensitive** | 🔴 High |

**Description:**  
Discord bot authentication token from the Discord Developer Portal.

**How to obtain:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create or select your application
3. Go to "Bot" section
4. Click "Reset Token" or "Copy Token"

**Example:**
```bash
DISCORD_BOT_TOKEN=your_bot_token_placeholder
```

**Security Notes:**
- Never share or commit this token
- Regenerate immediately if exposed
- Bot will be automatically disabled if token leaks

---

### DISCORD_RAMBLE_CHANNEL_ID

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | None |
| **Sensitive** | 🟢 None |

**Description:**  
Discord channel ID where Demi will send spontaneous rambles when autonomy is enabled.

**How to obtain:**
1. Enable Developer Mode in Discord (Settings → Advanced)
2. Right-click the channel
3. Select "Copy Channel ID"

**Example:**
```bash
DISCORD_RAMBLE_CHANNEL_ID=123456789012345678
```

**Related Configuration:**
- See [autonomy.rambles](./config-file.md#autonomy) in config file

---

### DISCORD_PROGRESS_WEBHOOK_URL

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | None |
| **Sensitive** | 🟡 Medium |

**Description:**  
Discord webhook URL for sending progress reports and status updates.

**How to obtain:**
1. In Discord, go to Server Settings → Integrations → Webhooks
2. Click "New Webhook"
3. Select channel and copy webhook URL

**Example:**
```bash
DISCORD_PROGRESS_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefgh-ijklmnop
```

---

## Authentication

### JWT_SECRET_KEY

| Property | Value |
|----------|-------|
| **Required** | Yes |
| **Default** | None |
| **Sensitive** | 🔴 Critical |

**Description:**  
Secret key used for signing JWT access tokens. This key validates all API authentication.

**Generation:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example:**
```bash
JWT_SECRET_KEY=Zm9vYmFyYmF6cXV4aWdkYXRhc3RyaW5nMTIz
```

**Security Notes:**
- Use a different key for each environment
- Minimum 32 characters recommended
- Changing this invalidates all existing tokens
- Store in environment only, never in code

---

### JWT_REFRESH_SECRET_KEY

| Property | Value |
|----------|-------|
| **Required** | Yes |
| **Default** | None |
| **Sensitive** | 🔴 Critical |

**Description:**  
Secret key used for signing JWT refresh tokens. Must be different from `JWT_SECRET_KEY`.

**Generation:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example:**
```bash
JWT_REFRESH_SECRET_KEY=YmFyZm9vYmF6cXV4aWdkYXRhc3RyaW5nNDU2
```

**Security Notes:**
- Must be different from `JWT_SECRET_KEY`
- Compromise allows indefinite token refresh
- Rotate periodically for enhanced security

---

## CORS Configuration

### ALLOWED_ORIGINS

| Property | Value |
|----------|-------|
| **Required** | Yes |
| **Default** | `http://localhost:3000` |
| **Sensitive** | 🟢 None |

**Description:**  
Comma-separated list of origins allowed to make CORS requests to the API.

**Format:**
- Multiple origins: comma-separated, no spaces
- No trailing slashes on URLs

**Examples:**
```bash
# Development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Production
ALLOWED_ORIGINS=https://myapp.com

# Multiple production domains
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

**Security Notes:**
- Never use `*` in production
- Restrict to your actual domains only
- Includes protocol (http/https) and port if non-standard

---

## Database Configuration

### DEMI_DB_PATH

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `~/.demi/emotions.db` |
| **Sensitive** | 🟢 None |

**Description:**  
Path to the SQLite database file for storing emotions, memories, and interaction history.

**Examples:**
```bash
# Default location
DEMI_DB_PATH=~/.demi/emotions.db

# Custom location
DEMI_DB_PATH=/var/lib/demi/data.db

# Relative to project
DEMI_DB_PATH=./data/demi.db
```

**Notes:**
- Path is expanded (`~` becomes home directory)
- Parent directory must exist
- Use absolute paths in production

---

### DATABASE_URL

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `sqlite:////home/user/.demi/demi.db` |
| **Sensitive** | 🟡 Low (may contain password) |

**Description:**  
Full database connection URL following SQLAlchemy format.

**Format:**
```
sqlite:///absolute/path/to/database.db
```

**Examples:**
```bash
# SQLite (default)
DATABASE_URL=sqlite:////home/user/.demi/demi.db

# SQLite relative path
DATABASE_URL=sqlite:///./data/demi.db
```

**Note:** Currently only SQLite is supported. This format allows for future database backends.

---

## API Server Configuration

### ANDROID_API_HOST

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `127.0.0.1` |
| **Sensitive** | 🟡 Medium |

**Description:**  
Network interface for the Android API server to bind to.

**Options:**

| Value | Description | Use Case |
|-------|-------------|----------|
| `127.0.0.1` | Localhost only (default) | Development, single machine |
| `0.0.0.0` | All interfaces | Docker, behind reverse proxy |
| `192.168.x.x` | Specific LAN IP | Local network access |

**Examples:**
```bash
# Local only (recommended for most setups)
ANDROID_API_HOST=127.0.0.1

# All interfaces (use with caution)
ANDROID_API_HOST=0.0.0.0

# Specific interface
ANDROID_API_HOST=192.168.1.100
```

**Security Notes:**
- Use `127.0.0.1` unless you need external access
- When using `0.0.0.0`, implement firewall rules
- Always use HTTPS when exposed to network

---

### ANDROID_API_PORT

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `8000` |
| **Sensitive** | 🟢 None |

**Description:**  
TCP port for the Android API server.

**Range:** 1-65535

**Examples:**
```bash
# Default port
ANDROID_API_PORT=8000

# Alternative ports
ANDROID_API_PORT=8080
ANDROID_API_PORT=3000
```

**Notes:**
- Ports below 1024 require root/admin privileges
- Check for port conflicts with other services
- Update firewall rules when changing

---

## Core System Configuration

### DEMI_DEBUG

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `false` |
| **Sensitive** | 🟢 None |

**Description:**  
Enable debug mode for verbose logging and additional diagnostics.

**Values:**
- `true`, `1`, `yes` - Enable debug mode
- `false`, `0`, `no` - Disable debug mode

**Examples:**
```bash
# Enable debug
DEMI_DEBUG=true

# Disable debug (default)
DEMI_DEBUG=false
```

**Impact:**
- Increases log verbosity significantly
- May affect performance
- Shows detailed error traces
- Useful for troubleshooting only

---

### DEMI_LOG_LEVEL

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `INFO` |
| **Sensitive** | 🟢 None |

**Description:**  
Minimum severity level for log messages to be recorded.

**Valid Options:**

| Level | Description | Use Case |
|-------|-------------|----------|
| `DEBUG` | Detailed diagnostic information | Development, debugging |
| `INFO` | General operational events | Normal operation |
| `WARNING` | Potential issues, not errors | Production monitoring |
| `ERROR` | Errors that don't stop operation | Minimal production |
| `CRITICAL` | Serious errors requiring attention | Alerts only |

**Examples:**
```bash
# Development
DEMI_LOG_LEVEL=DEBUG

# Normal operation (default)
DEMI_LOG_LEVEL=INFO

# Production
DEMI_LOG_LEVEL=WARNING
```

---

### DEMI_DATA_DIR

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `~/.demi` |
| **Sensitive** | 🟢 None |

**Description:**  
Base directory for all persistent data (database, logs, cache).

**Examples:**
```bash
# Default
DEMI_DATA_DIR=~/.demi

# Custom location
DEMI_DATA_DIR=/var/lib/demi

# Relative path
DEMI_DATA_DIR=./data
```

**Contents:**
- SQLite database files
- Log files
- Emotional state persistence
- Cached data

---

### DEMI_RAM_THRESHOLD

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `80` |
| **Sensitive** | 🟢 None |

**Description:**  
RAM usage percentage threshold for triggering resource management.

**Range:** 0-100

**Examples:**
```bash
# Default (80%)
DEMI_RAM_THRESHOLD=80

# Lower threshold for systems with less RAM
DEMI_RAM_THRESHOLD=70

# Higher threshold for systems with plenty of RAM
DEMI_RAM_THRESHOLD=90
```

**Behavior:**
- When RAM usage exceeds this threshold, Demi may:
  - Reduce message cache size
  - Pause non-essential background tasks
  - Trigger garbage collection

---

### DEMI_MAX_ERRORS

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `5` |
| **Sensitive** | 🟢 None |

**Description:**  
Maximum number of consecutive errors before triggering recovery procedures.

**Examples:**
```bash
# Default
DEMI_MAX_ERRORS=5

# More tolerant
DEMI_MAX_ERRORS=10

# Stricter
DEMI_MAX_ERRORS=3
```

---

### DEMI_AUTO_RECOVER

| Property | Value |
|----------|-------|
| **Required** | No |
| **Default** | `false` |
| **Sensitive** | 🟢 None |

**Description:**  
Enable automatic recovery when error threshold is exceeded.

**Values:**
- `true`, `1`, `yes` - Enable auto-recovery
- `false`, `0`, `no` - Disable auto-recovery

**Examples:**
```bash
# Enable auto-recovery
DEMI_AUTO_RECOVER=true

# Disable (default - manual intervention)
DEMI_AUTO_RECOVER=false
```

---

## Environment-Specific Examples

### Development Environment

```bash
# .env.development
DEMI_DEBUG=true
DEMI_LOG_LEVEL=DEBUG

DISCORD_BOT_TOKEN=your-dev-bot-token
DISCORD_RAMBLE_CHANNEL_ID=123456789

JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_REFRESH_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

ANDROID_API_HOST=127.0.0.1
ANDROID_API_PORT=8000

DEMI_DB_PATH=./data/dev.db
```

### Production Environment

```bash
# .env.production
DEMI_DEBUG=false
DEMI_LOG_LEVEL=WARNING

DISCORD_BOT_TOKEN=your-production-bot-token
DISCORD_RAMBLE_CHANNEL_ID=987654321
DISCORD_PROGRESS_WEBHOOK_URL=https://discord.com/api/webhooks/...

JWT_SECRET_KEY=your-secure-production-secret
JWT_REFRESH_SECRET_KEY=your-secure-production-refresh-secret

ALLOWED_ORIGINS=https://yourdomain.com

ANDROID_API_HOST=127.0.0.1
ANDROID_API_PORT=8000

DEMI_DB_PATH=/var/lib/demi/demi.db
DEMI_DATA_DIR=/var/lib/demi
```

### Docker Environment

```bash
# .env.docker
DEMI_LOG_LEVEL=INFO

DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}

JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET_KEY}

ALLOWED_ORIGINS=http://localhost:3000

ANDROID_API_HOST=0.0.0.0
ANDROID_API_PORT=8000

DEMI_DB_PATH=/app/data/demi.db
DEMI_DATA_DIR=/app/data
```

## Validation

### Checking Environment Variables

You can verify your environment configuration using Python:

```python
from src.core.config import DemiConfig

# Load and display configuration
config = DemiConfig.load()
print(f"Log Level: {config.system['log_level']}")
print(f"Debug Mode: {config.system['debug']}")
print(f"Data Directory: {config.system['data_dir']}")
```

### Required Variables Checklist

Before starting Demi, ensure you have:

- [ ] `DISCORD_BOT_TOKEN` (if using Discord)
- [ ] `JWT_SECRET_KEY`
- [ ] `JWT_REFRESH_SECRET_KEY`
- [ ] `ALLOWED_ORIGINS`

---

## See Also

- [Config File Reference](./config-file.md) - YAML configuration options
- [Tuning Guide](./tuning-guide.md) - Performance and behavior tuning
- [Security Best Practices](./security.md) - Security recommendations
