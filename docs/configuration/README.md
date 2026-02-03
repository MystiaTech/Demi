# Configuration Reference

Complete guide for configuring and customizing Demi.

## Overview

Demi uses a hierarchical configuration system that allows you to customize every aspect of her behavior. Configuration can be specified through:

1. **Environment Variables** - Runtime overrides (best for secrets and deployment-specific settings)
2. **YAML Config Files** - Persistent settings (best for behavior customization)
3. **Built-in Defaults** - Fallback values for all options

## Configuration Priority

When the same option is set in multiple places, the following priority order applies:

```
Environment Variables (highest priority)
    ↓
Custom YAML Config File
    ↓
defaults.yaml (lowest priority)
```

**Example:** If you set `DEMI_LOG_LEVEL=DEBUG` in your environment, it will override any log level setting in your YAML config files.

## Configuration Methods

### Method 1: Environment Variables

Best for:
- Secrets (tokens, API keys)
- Deployment-specific settings
- Quick testing
- Docker/containerized deployments

**File:** `.env` (in project root)

```bash
# Example .env file
DISCORD_BOT_TOKEN=your-token-here
DEMI_LOG_LEVEL=DEBUG
ANDROID_API_PORT=8080
```

See [Environment Variables Reference](./environment-variables.md) for complete documentation.

### Method 2: Config File

Best for:
- Behavior customization
- Emotional tuning
- Platform settings
- Persistent configuration

**File:** Custom YAML file (referenced in code) or modify `src/core/defaults.yaml`

```yaml
# Example custom config
system:
  log_level: DEBUG

emotional_system:
  decay_rates:
    loneliness: 0.05  # Slower decay = more emotional
```

See [Config File Reference](./config-file.md) for complete documentation.

## Quick Reference Table

| Category | Environment Variables | Config File Section |
|----------|----------------------|---------------------|
| **Core System** | `DEMI_DEBUG`, `DEMI_LOG_LEVEL`, `DEMI_DATA_DIR` | `system:` |
| **Discord** | `DISCORD_BOT_TOKEN`, `DISCORD_RAMBLE_CHANNEL_ID`, `DISCORD_PROGRESS_WEBHOOK_URL` | `platforms.discord:` |
| **Database** | `DEMI_DB_PATH`, `DATABASE_URL` | `database:` |
| **Authentication** | `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY` | - |
| **API Server** | `ANDROID_API_HOST`, `ANDROID_API_PORT` | `platforms.android:` |
| **CORS** | `ALLOWED_ORIGINS` | - |
| **LLM** | - | `llm:` |
| **Voice** | - | `voice:` |
| **Emotional** | - | `emotional_system:` |
| **Autonomy** | - | `autonomy:` |
| **Monitoring** | - | `monitoring:` |

## Configuration Files

| File | Purpose |
|------|---------|
| [Environment Variables](./environment-variables.md) | Complete reference for all environment variables |
| [Config File](./config-file.md) | Complete YAML configuration reference |
| [Tuning Guide](./tuning-guide.md) | Performance and behavior tuning recommendations |
| [Security](./security.md) | Security best practices |

## Security Warnings

> ⚠️ **WARNING: Secrets Management**
>
> Never commit sensitive configuration to version control:
> - Discord bot tokens
> - JWT secret keys
> - Database passwords
> - API keys
>
> **Always:**
> - Store secrets in `.env` file
> - Add `.env` to `.gitignore`
> - Use different secrets for production
> - Rotate secrets regularly

### Generating Secure Secrets

```bash
# Generate a secure JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### File Permissions

```bash
# Secure your .env file
chmod 600 .env

# Secure your data directory
chmod 700 ~/.demi
```

## Getting Started

### Minimal Configuration

For a basic Discord bot setup:

```bash
# .env
DISCORD_BOT_TOKEN=your-bot-token-from-discord-portal
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_REFRESH_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ALLOWED_ORIGINS=http://localhost:3000
```

### Production Configuration

For production deployments:

```bash
# .env
DISCORD_BOT_TOKEN=your-production-bot-token
JWT_SECRET_KEY=your-production-jwt-secret
JWT_REFRESH_SECRET_KEY=your-production-refresh-secret
ALLOWED_ORIGINS=https://yourdomain.com
ANDROID_API_HOST=127.0.0.1
DEMI_LOG_LEVEL=WARNING
```

```yaml
# config/production.yaml
system:
  log_level: WARNING
  max_log_size_mb: 500

emotional_system:
  persistence_interval: 600  # Save less frequently

platforms:
  discord:
    auto_reconnect: true
    reconnect_max_attempts: 10
```

## Troubleshooting

### Configuration Not Loading

1. Check file paths are correct
2. Verify environment variable names match exactly
3. Ensure YAML indentation uses spaces (not tabs)
4. Check file permissions

### Changes Not Taking Effect

1. Remember environment variables override config files
2. Restart Demi after changing configuration
3. Check for typos in variable names

### Secrets Exposed

1. Immediately regenerate any exposed tokens/keys
2. Check git history with `git log -p -- .env`
3. Consider using git-filter-repo to remove from history
4. Review access logs for unauthorized usage

## Need Help?

- See [Tuning Guide](./tuning-guide.md) for customization tips
- See [Security](./security.md) for security best practices
- Check the main [README](../../README.md) for setup instructions
