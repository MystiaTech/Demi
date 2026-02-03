# Security Best Practices

Comprehensive security guidelines for deploying and operating Demi safely.

## Overview

This guide covers security best practices for all aspects of Demi's configuration and deployment. Following these guidelines helps protect your data, prevent unauthorized access, and ensure safe operation.

---

## JWT Secret Management

### Generating Secure Secrets

JWT secrets must be cryptographically secure random strings. Never use:
- Simple passwords
- Dictionary words
- Short strings (< 32 characters)
- The same secret for development and production

**Correct way to generate:**

```bash
# Generate secure 32-byte URL-safe token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output:
# Zm9vYmFyYmF6cXV4aWdkYXRhc3RyaW5nMTIzNDU2Nzg5
```

**For both secrets:**

```bash
# Generate both secrets at once
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export JWT_REFRESH_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Verify they're different
echo "Access: $JWT_SECRET_KEY"
echo "Refresh: $JWT_REFRESH_SECRET_KEY"
```

---

### Secure Storage

#### Environment Variables (Recommended)

```bash
# .env file - add to .gitignore!
JWT_SECRET_KEY=your-generated-secret-here
JWT_REFRESH_SECRET_KEY=your-generated-refresh-secret-here
```

**File permissions:**

```bash
# Set restrictive permissions
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw------- (owner read/write only)
```

#### Secret Management Systems

For production deployments, use a secret manager:

**Docker Secrets:**
```yaml
# docker-compose.yml
secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  jwt_refresh_secret:
    file: ./secrets/jwt_refresh_secret.txt

services:
  demi:
    secrets:
      - jwt_secret
      - jwt_refresh_secret
    environment:
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret
      JWT_REFRESH_SECRET_KEY_FILE: /run/secrets/jwt_refresh_secret
```

**HashiCorp Vault:**
```bash
# Retrieve from Vault
export JWT_SECRET_KEY=$(vault kv get -field=secret demi/jwt)
export JWT_REFRESH_SECRET_KEY=$(vault kv get -field=refresh demi/jwt)
```

**AWS Secrets Manager:**
```bash
# Retrieve from AWS
export JWT_SECRET_KEY=$(aws secretsmanager get-secret-value \
  --secret-id demi/jwt-secret \
  --query SecretString \
  --output text)
```

---

### Secret Rotation

**When to rotate:**
- Every 90 days (recommended)
- Immediately if compromised
- After team member departures
- When switching environments

**Rotation process:**

1. Generate new secrets:
```bash
export NEW_JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export NEW_JWT_REFRESH_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

2. Update configuration (graceful deployment):
```bash
# Set both old and new secrets temporarily
export JWT_SECRET_KEY="$OLD_SECRET,$NEW_SECRET"
```

3. Wait for existing tokens to expire (typically 15-30 minutes)

4. Remove old secret:
```bash
export JWT_SECRET_KEY="$NEW_SECRET"
```

---

## Network Security

### API Server Binding

#### Localhost Only (Recommended for Most Cases)

```bash
# .env
ANDROID_API_HOST=127.0.0.1
ANDROID_API_PORT=8000
```

**When to use:**
- Single-machine deployment
- Behind reverse proxy (nginx, Apache)
- Development environments

**Benefits:**
- Not accessible from network
- Immune to external scanning
- Requires local access or proxy

---

#### All Interfaces (Use with Caution)

```bash
# .env
ANDROID_API_HOST=0.0.0.0
ANDROID_API_PORT=8000
```

**When to use:**
- Docker containers
- Internal networks only
- Behind firewall with strict rules

**Required additional security:**

1. **Firewall rules:**
```bash
# UFW (Ubuntu)
ufw default deny incoming
ufw allow from 192.168.1.0/24 to any port 8000
ufw enable

# iptables
iptables -A INPUT -p tcp --dport 8000 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
```

2. **CORS restrictions:**
```bash
# .env
ALLOWED_ORIGINS=https://yourdomain.com
```

3. **HTTPS/TLS termination:**
Use a reverse proxy with TLS:

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### CORS Configuration

#### Development

```bash
# .env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000
```

#### Production

```bash
# .env - NEVER use wildcard in production!
ALLOWED_ORIGINS=https://yourdomain.com

# Multiple production domains
ALLOWED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
```

**CORS Security Checklist:**
- [ ] No wildcards (`*`) in production
- [ ] HTTPS only in production
- [ ] Exact domain matching (no subdomains unless intended)
- [ ] Regular review of allowed origins

---

## Discord Bot Security

### Token Protection

**Critical rules:**
1. Never commit tokens to version control
2. Never share tokens in chat/email
3. Regenerate immediately if exposed
4. Use separate bots for development/production

**If token is exposed:**

1. **Immediately regenerate:**
   - Discord Developer Portal → Bot → Reset Token
   - Update your `.env` file
   - Restart Demi

2. **Check for unauthorized access:**
   - Review Discord audit logs
   - Check for unknown applications in your server
   - Look for unusual message activity

3. **Consider server impacts:**
   - If bot has admin privileges, check for unauthorized changes
   - Review webhook configurations
   - Check for added/removed roles

---

### Minimal Permissions

Grant only necessary permissions to your bot:

**Recommended minimum:**
- ✅ Read Messages/View Channels
- ✅ Send Messages
- ✅ Read Message History
- ✅ Embed Links
- ✅ Attach Files
- ✅ Use External Emojis

**Avoid unless specifically needed:**
- ❌ Administrator
- ❌ Manage Server
- ❌ Manage Channels
- ❅ Manage Roles
- ❌ Manage Webhooks
- ❌ Kick/Ban Members

**Permission calculator:**
Use [Discord Permission Calculator](https://discordapi.com/permissions.html) to generate invite links with exact permissions.

---

### Account Security

1. **Enable 2FA** on your Discord account
2. **Use a dedicated bot account** (not your personal account)
3. **Regularly review** authorized apps at [Discord Settings](https://discord.com/channels/@me/settings/authorized-apps)
4. **Monitor bot activity** in audit logs

---

## Database Security

### SQLite Security

#### File Permissions

```bash
# Create data directory with proper permissions
mkdir -p ~/.demi
chmod 700 ~/.demi

# Database file should be owner-only
chmod 600 ~/.demi/emotions.db

# Verify
ls -la ~/.demi/
# drwx------  user user  .demi/
# -rw-------  user user  emotions.db
```

#### Secure Location

```bash
# .env - Keep database outside web root
DEMI_DB_PATH=/var/lib/demi/demi.db
# NOT: /var/www/html/demi.db
```

**Never place the database:**
- In web-accessible directories
- In version control
- In shared/network drives without encryption

---

### Backup Security

#### Encrypted Backups

```bash
# Create encrypted backup
gpg --symmetric --cipher-algo AES256 \
    --output demi-backup-$(date +%Y%m%d).db.gpg \
    ~/.demi/emotions.db

# Restore from encrypted backup
gpg --decrypt demi-backup-20240101.db.gpg > ~/.demi/emotions.db
```

#### Automated Backup Script

```bash
#!/bin/bash
# backup-demi.sh

BACKUP_DIR="/secure/backups/demi"
DB_PATH="$HOME/.demi/emotions.db"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Copy with timestamp
cp "$DB_PATH" "$BACKUP_DIR/emotions_$DATE.db"

# Encrypt
gpg --symmetric --cipher-algo AES256 \
    --output "$BACKUP_DIR/emotions_$DATE.db.gpg" \
    "$BACKUP_DIR/emotions_$DATE.db"

# Remove unencrypted
rm "$BACKUP_DIR/emotions_$DATE.db"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/emotions_*.gpg | tail -n +8 | xargs rm -f
```

---

## Dependency Security

### Regular Updates

```bash
# Check for outdated packages
pip list --outdated

# Update all dependencies
pip install -r requirements.txt --upgrade

# Test after updates
pytest tests/
```

### Vulnerability Scanning

```bash
# Install safety
pip install safety

# Scan dependencies
safety check

# Scan requirements file
safety check -r requirements.txt
```

### Pinning Dependencies

```txt
# requirements.txt - Pin exact versions
requests==2.31.0
discord.py==2.3.2
pyyaml==6.0.1
```

---

## Monitoring for Anomalies

### Log Monitoring

**Watch for:**
- Failed authentication attempts
- Unusual API request patterns
- Database errors
- Permission denied errors

**Example log watch script:**

```bash
#!/bin/bash
# monitor-logs.sh

LOG_FILE="logs/demi.log"
ALERT_FILE="logs/security-alerts.log"

# Check for suspicious patterns
tail -f "$LOG_FILE" | while read line; do
    # Multiple failed auth attempts
    if echo "$line" | grep -q "authentication failed"; then
        echo "$(date): Auth failure - $line" >> "$ALERT_FILE"
    fi
    
    # Unusual access patterns
    if echo "$line" | grep -q "404"; then
        echo "$(date): Not found - $line" >> "$ALERT_FILE"
    fi
    
    # Errors
    if echo "$line" | grep -q "ERROR"; then
        echo "$(date): Error - $line" >> "$ALERT_FILE"
    fi
done
```

### Rate Limiting

Implement rate limiting to prevent abuse:

```python
# Example: Add to API server
from functools import wraps
import time

rate_limits = {}

def rate_limit(max_requests=10, window=60):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            client = request.remote_addr
            now = time.time()
            
            # Clean old entries
            if client in rate_limits:
                rate_limits[client] = [
                    t for t in rate_limits[client] 
                    if now - t < window
                ]
            else:
                rate_limits[client] = []
            
            # Check limit
            if len(rate_limits.get(client, [])) >= max_requests:
                return {"error": "Rate limit exceeded"}, 429
            
            rate_limits[client].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Generate unique JWT secrets for production
- [ ] Verify `.env` is in `.gitignore`
- [ ] Set restrictive file permissions on `.env`
- [ ] Configure CORS for production domains only
- [ ] Set `DEMI_DEBUG=false`
- [ ] Set `DEMI_LOG_LEVEL=WARNING` or `ERROR`
- [ ] Use `ANDROID_API_HOST=127.0.0.1` with reverse proxy
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Configure automated backups
- [ ] Enable HTTPS/TLS

### Post-Deployment

- [ ] Verify no secrets in environment logs
- [ ] Test CORS from allowed origins only
- [ ] Confirm API not accessible directly from external network
- [ ] Verify database file permissions
- [ ] Test backup and restore procedure
- [ ] Set up log monitoring
- [ ] Document incident response procedure

---

## Incident Response

### If Secrets Are Exposed

1. **Immediate (within 5 minutes):**
   - Regenerate all exposed secrets/tokens
   - Revoke old Discord bot token
   - Update environment variables

2. **Short-term (within 1 hour):**
   - Review access logs for unauthorized activity
   - Check for unauthorized Discord messages/changes
   - Restart all services with new secrets

3. **Follow-up (within 24 hours):**
   - Audit all connected systems
   - Review who had access to exposed secrets
   - Update secret rotation schedule
   - Document incident

### If Unauthorized Access Detected

1. **Isolate:** Stop affected services
2. **Assess:** Determine scope of access
3. **Revoke:** Reset all credentials
4. **Investigate:** Check logs for impact
5. **Restore:** From known-good backups if needed
6. **Harden:** Implement additional security measures

---

## Security Tools

### Recommended Scanning Tools

```bash
# Python dependency vulnerabilities
pip install safety
safety check

# Code security scan
pip install bandit
bandit -r src/

# Secret scanning in git history
pip install truffleHog
truffleHog --regex --entropy=False .

# Check for secrets in current files
pip install detect-secrets
detect-secrets scan
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', 'src/']
```

---

## See Also

- [Environment Variables](./environment-variables.md) - Environment variable reference
- [Config File Reference](./config-file.md) - Complete configuration options
- [Tuning Guide](./tuning-guide.md) - Performance and behavior tuning
- [Discord Developer Portal](https://discord.com/developers/applications) - Bot management
