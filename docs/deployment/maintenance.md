# Demi Maintenance Guide

This guide covers ongoing maintenance tasks for your Demi installation, including backups, updates, monitoring, and troubleshooting.

## Table of Contents

- [Backups](#backups)
- [Updates](#updates)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Backups

### What to Backup

| Path | Description | Backup Frequency | Priority |
|------|-------------|------------------|----------|
| `~/.demi/emotions.db` | Emotional state & history | Daily | 🔴 Critical |
| `~/.demi/demi.db` | Messages & user data | Daily | 🔴 Critical |
| `.env` | Configuration secrets | After changes | 🔴 Critical |
| `logs/` | Log files | Weekly | 🟡 Medium |
| `src/core/defaults.yaml` | Custom configuration | After changes | 🟡 Medium |

### Automated Backup Script

Create `/home/youruser/demi/scripts/backup.sh`:

```bash
#!/bin/bash
#
# Demi Backup Script
# Run via cron for automated backups

set -e

# Configuration
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-/backups/demi}"
DATA_DIR="${DATA_DIR:-$HOME/.demi}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/demi}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/$DATE"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[BACKUP]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop Demi temporarily (if running via systemd)
if systemctl is-active --quiet demi 2>/dev/null; then
    log "Stopping Demi service..."
    sudo systemctl stop demi
    WAS_RUNNING=true
else
    WAS_RUNNING=false
fi

# Backup database files
log "Backing up database files..."
if [[ -f "$DATA_DIR/emotions.db" ]]; then
    cp "$DATA_DIR/emotions.db" "$BACKUP_DIR/"
    log "✓ emotions.db backed up"
else
    warn "emotions.db not found"
fi

if [[ -f "$DATA_DIR/demi.db" ]]; then
    cp "$DATA_DIR/demi.db" "$BACKUP_DIR/"
    log "✓ demi.db backed up"
else
    warn "demi.db not found"
fi

# Backup configuration
log "Backing up configuration..."
if [[ -f "$INSTALL_DIR/.env" ]]; then
    cp "$INSTALL_DIR/.env" "$BACKUP_DIR/"
    log "✓ .env backed up"
else
    warn ".env not found"
fi

if [[ -f "$INSTALL_DIR/src/core/defaults.yaml" ]]; then
    cp "$INSTALL_DIR/src/core/defaults.yaml" "$BACKUP_DIR/"
    log "✓ defaults.yaml backed up"
fi

# Backup logs (optional)
if [[ -d "$INSTALL_DIR/logs" ]]; then
    log "Backing up logs..."
    tar -czf "$BACKUP_DIR/logs.tar.gz" -C "$INSTALL_DIR" logs/
    log "✓ Logs backed up"
fi

# Create manifest
cat > "$BACKUP_DIR/MANIFEST.txt" <<EOF
Demi Backup
Date: $(date)
Host: $(hostname)
User: $(whoami)
Files:
$(ls -la "$BACKUP_DIR/")
EOF

# Compress backup
log "Compressing backup..."
cd "$BACKUP_BASE_DIR"
tar -czf "$DATE.tar.gz" "$DATE"
rm -rf "$DATE"

# Calculate size
BACKUP_SIZE=$(du -h "$DATE.tar.gz" | cut -f1)
log "Backup created: $DATE.tar.gz ($BACKUP_SIZE)"

# Clean old backups
log "Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_BASE_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Restart Demi if it was running
if [[ "$WAS_RUNNING" == true ]]; then
    log "Restarting Demi service..."
    sudo systemctl start demi
fi

log "Backup complete!"
```

Make it executable:

```bash
chmod +x ~/demi/scripts/backup.sh
```

### Setting Up Automated Backups

#### Using cron (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/youruser/demi/scripts/backup.sh >> /home/youruser/demi/logs/backup.log 2>&1

# Add weekly backup on Sundays at 3 AM
0 3 * * 0 /home/youruser/demi/scripts/backup.sh >> /home/youruser/demi/logs/backup-weekly.log 2>&1
```

#### Using systemd Timer (Linux)

Create `/etc/systemd/system/demi-backup.service`:

```ini
[Unit]
Description=Demi Backup Service

[Service]
Type=oneshot
User=youruser
ExecStart=/home/youruser/demi/scripts/backup.sh
```

Create `/etc/systemd/system/demi-backup.timer`:

```ini
[Unit]
Description=Run Demi backup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable demi-backup.timer
sudo systemctl start demi-backup.timer

# Check status
systemctl list-timers demi-backup.timer
```

### Restore from Backup

#### Full Restore

```bash
# 1. Stop Demi
sudo systemctl stop demi
# or if running manually: pkill -f "python main.py"

# 2. Extract backup
cd /backups/demi
tar -xzf 20260201_020000.tar.gz

# 3. Restore databases
cp 20260201_020000/emotions.db ~/.demi/
cp 20260201_020000/demi.db ~/.demi/

# 4. Restore configuration (optional)
cp 20260201_020000/.env ~/demi/

# 5. Restart Demi
sudo systemctl start demi
# or: cd ~/demi && source venv/bin/activate && python main.py
```

#### Partial Restore (Single Table)

```bash
# Extract specific emotional state from backup
sqlite3 ~/.demi/emotions.db ".dump emotional_state" > emotional_state_backup.sql

# Restore to another database
sqlite3 ~/.demi/emotions.db ".read emotional_state_backup.sql"
```

### Remote Backup (rsync)

```bash
# Sync to remote server
rsync -avz --delete /backups/demi/ user@backup-server:/backups/demi/

# Or use rclone for cloud storage
rclone sync /backups/demi/ remote:demi-backups
```

---

## Updates

### Updating Demi Code

```bash
cd ~/demi

# Stop Demi
sudo systemctl stop demi

# Pull latest code
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart Demi
sudo systemctl start demi
```

### Database Migrations

If updates include database schema changes:

```bash
# Check for migration scripts
ls scripts/migrations/

# Run migrations (if provided)
python scripts/migrations/migrate_v1_to_v2.py

# Or manually with sqlite3
sqlite3 ~/.demi/emotions.db < scripts/migrations/v2_schema.sql
```

### Updating Ollama and Models

```bash
# Update Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Update Ollama (macOS)
brew upgrade ollama

# Pull latest model version
ollama pull llama3.2:1b

# List available models
ollama list
```

### Rollback Procedure

If an update causes issues:

```bash
# 1. Stop Demi
sudo systemctl stop demi

# 2. Restore from backup (see above)

# 3. Or rollback git
git log --oneline -10  # Find previous working commit
git checkout <commit-hash>

# 4. Restart Demi
sudo systemctl start demi
```

---

## Monitoring

### Log Rotation

Demi can generate large log files. Set up log rotation:

Create `/etc/logrotate.d/demi`:

```
/home/youruser/demi/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 youruser youruser
    sharedscripts
    postrotate
        # Reload Demi to reopen log files
        systemctl reload demi 2>/dev/null || true
    endscript
}
```

Test logrotate:

```bash
sudo logrotate -d /etc/logrotate.d/demi  # Debug mode
sudo logrotate -f /etc/logrotate.d/demi   # Force rotation
```

### Health Checks

#### Built-in Health Endpoint

```bash
# Check API health
curl http://localhost:8000/api/v1/status

# Check specific components
curl http://localhost:8000/api/v1/health/discord
curl http://localhost:8000/api/v1/health/ollama
```

#### System Resource Monitoring

```bash
# Monitor Demi process
ps aux | grep demi

# Check resource usage
htop -p $(pgrep -f "python main.py")

# Monitor disk usage
df -h ~/.demi

# Check database size
ls -lh ~/.demi/*.db
```

#### Custom Health Check Script

Create `~/demi/scripts/health-check.sh`:

```bash
#!/bin/bash
# Health check script for monitoring

API_URL="http://localhost:8000"
WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"  # Optional: for alerts

# Check API
curl -sf "$API_URL/api/v1/status" > /dev/null
if [[ $? -ne 0 ]]; then
    echo "$(date): ALERT - Demi API not responding"
    
    # Send alert to Discord webhook if configured
    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -X POST -H "Content-Type: application/json" \
            -d '{"content":"🚨 Demi health check failed!"}' \
            "$WEBHOOK_URL"
    fi
    
    exit 1
fi

echo "$(date): OK - Demi is healthy"
exit 0
```

### Setting Up Alerts

#### Using systemd

Monitor service status:

```bash
# Check if service is running
systemctl is-active demi

# View recent status
systemctl status demi

# View logs
journalctl -u demi -f
```

#### Using a Monitoring Service (e.g., Uptime Kuma)

1. Install Uptime Kuma or similar
2. Add health check URL: `http://your-server:8000/api/v1/status`
3. Configure notifications (Discord, email, etc.)

### Performance Monitoring

```bash
# Monitor response times
while true; do
    time curl -s http://localhost:8000/api/v1/status > /dev/null
    sleep 60
done

# Check database performance
sqlite3 ~/.demi/emotions.db "PRAGMA integrity_check;"
sqlite3 ~/.demi/emotions.db "ANALYZE;"
```

---

## Troubleshooting

### Common Startup Issues

#### "Configuration validation failed"

```bash
# Check .env file exists
ls -la ~/demi/.env

# Validate syntax
cat ~/demi/.env | grep -v "^#" | grep -v "^$"

# Run dry-run to see specific error
cd ~/demi && python main.py --dry-run
```

#### "Ollama connection refused"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check Ollama logs
journalctl -u ollama -f
```

#### "Port 8000 already in use"

```bash
# Find what's using the port
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>

# Or change port in .env
# ANDROID_API_PORT=8001
```

#### "Permission denied" errors

```bash
# Fix permissions on data directory
chmod 755 ~/.demi
chown -R $USER:$USER ~/.demi

# Fix permissions on install directory
chown -R $USER:$USER ~/demi
```

### Performance Degradation

#### High Memory Usage

```bash
# Check memory usage
ps aux | grep python

# Restart Demi
sudo systemctl restart demi

# Consider using a smaller model
ollama pull llama3.2:1b  # Instead of 3b or larger
```

#### Slow Response Times

```bash
# Check system load
uptime

# Check disk I/O
iotop

# Optimize database
sqlite3 ~/.demi/emotions.db "VACUUM;"

# Check Ollama performance
curl http://localhost:11434/api/generate -d '{
    "model": "llama3.2:1b",
    "prompt": "Hello"
}'
```

#### Database Locked Errors

```bash
# Check for concurrent access
lsof ~/.demi/*.db

# Backup and rebuild database
cp ~/.demi/emotions.db ~/.demi/emotions.db.backup
sqlite3 ~/.demi/emotions.db ".dump" > /tmp/emotions.sql
rm ~/.demi/emotions.db
sqlite3 ~/.demi/emotions.db < /tmp/emotions.sql
```

### Recovery Procedures

#### Complete Reset (Keep Configuration)

```bash
# Stop Demi
sudo systemctl stop demi

# Backup and clear databases
mv ~/.demi/emotions.db ~/.demi/emotions.db.old
mv ~/.demi/demi.db ~/.demi/demi.db.old

# Restart Demi (will create fresh databases)
sudo systemctl start demi
```

#### Clean Reinstall (Keep Data)

```bash
# Stop Demi
sudo systemctl stop demi

# Backup data
cp -r ~/.demi ~/.demi-backup-$(date +%Y%m%d)

# Reinstall code
cd ~/demi
git pull
source venv/bin/activate
pip install -r requirements.txt --force-reinstall

# Restart
sudo systemctl start demi
```

#### Emergency Recovery

```bash
# Last resort: complete wipe and reinstall
# 1. Backup everything
tar -czf demi-emergency-backup.tar.gz ~/demi ~/.demi

# 2. Remove and reinstall
rm -rf ~/demi ~/.demi

# 3. Run install script again
curl -fsSL ... | bash

# 4. Restore only the databases from backup
cp demi-emergency-backup.tar.gz ~/.demi-backup/
cd ~/.demi-backup && tar -xzf demi-emergency-backup.tar.gz
```

### Discord Integration Issues

#### Bot not responding to mentions

1. Check bot token in `.env`
2. Verify bot has "Message Content Intent" enabled
3. Check bot permissions in Discord server
4. Review logs: `grep -i discord logs/demi.log`

#### Ramble channel not working

1. Verify channel ID is correct
2. Check bot has permission to post in that channel
3. Ensure `DISCORD_RAMBLE_CHANNEL_ID` is set in `.env`

### Getting Help

If issues persist:

1. **Check logs**: `tail -n 100 ~/demi/logs/demi.log`
2. **Run with debug**: `python main.py --log-level DEBUG`
3. **Check system resources**: `htop`, `free -h`, `df -h`
4. **Open an issue** with:
   - Demi version (`git log --oneline -1`)
   - OS and version
   - Python version
   - Relevant log excerpts
   - Steps to reproduce

---

## Maintenance Checklist

### Daily
- [ ] Check that Demi is running
- [ ] Review error logs
- [ ] Verify Discord bot is responsive

### Weekly
- [ ] Review log file sizes
- [ ] Check disk space
- [ ] Test backup restoration process
- [ ] Review system resource usage

### Monthly
- [ ] Update dependencies
- [ ] Check for Ollama updates
- [ ] Review and rotate logs
- [ ] Test full backup/restore cycle
- [ ] Security review (check for exposed secrets)

### Quarterly
- [ ] Performance benchmark
- [ ] Dependency audit
- [ ] Documentation review
- [ ] Disaster recovery drill
