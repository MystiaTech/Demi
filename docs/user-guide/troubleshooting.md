# Troubleshooting Common Issues 🔧

> *"Having problems? How... mortal of you. Let me grace you with solutions."*
> — Demi

This guide helps you diagnose and resolve common issues with Demi. Start with the quick reference, then dive into detailed solutions.

---

## Common Issues Quick Reference

| Issue | Quick Fix | Detailed Section |
|-------|-----------|------------------|
| Demi not responding | Check if Ollama is running | [Startup Issues](#startup-issues) |
| Discord bot offline | Verify bot token | [Discord Issues](#discord-issues) |
| Android won't connect | Check API URL/port | [Android Issues](#android-issues) |
| Voice not working | Check microphone permissions | [Voice Issues](#voice-issues) |
| Responses are slow | Check RAM/CPU usage | [Performance Issues](#performance-issues) |
| Emotional state weird | Check decay configuration | [Emotional State Concerns](#emotional-state-concerns) |
| Database errors | Check disk space/permissions | [Database Issues](#database-issues) |

---

## Startup Issues

### Ollama Not Running

**Symptoms:**
```
ERROR: Cannot connect to Ollama at localhost:11434
ERROR: LLM inference failed: Connection refused
```

**Solutions:**

1. **Start Ollama**
   ```bash
   # Terminal 1: Start Ollama server
   ollama serve
   
   # Keep this running! Use a separate terminal for Demi
   ```

2. **Verify Ollama is Running**
   ```bash
   # Check if Ollama responds
   curl http://localhost:11434/api/tags
   
   # Should return list of models
   ```

3. **Pull Required Model**
   ```bash
   # If model is missing
   ollama pull llama3.2:1b
   ```

4. **Check Port**
   ```bash
   # If using non-default port
   export OLLAMA_HOST=localhost:11435
   ```

### Configuration File Errors

**Symptoms:**
```
ERROR: Config file not found: src/core/defaults.yaml
ERROR: Invalid config: missing 'system' section
```

**Solutions:**

1. **Verify Config Exists**
   ```bash
   ls -la src/core/defaults.yaml
   
   # If missing, restore from example
   cp src/core/defaults.yaml.example src/core/defaults.yaml
   ```

2. **Validate YAML Syntax**
   ```bash
   # Install yamllint
   pip install yamllint
   
   # Check config
   yamllint src/core/defaults.yaml
   ```

3. **Use Dry-Run Mode**
   ```bash
   # Validate without starting
   python main.py --dry-run
   ```

### Missing Dependencies

**Symptoms:**
```
ModuleNotFoundError: No module named 'discord'
ImportError: cannot import name 'FastAPI'
```

**Solutions:**

```bash
# Reinstall dependencies
pip install -r requirements.txt

# If specific package fails
pip install --upgrade discord.py

# Check Python version
python --version  # Should be 3.10+
```

### Port Conflicts

**Symptoms:**
```
ERROR: Address already in use: 8000
ERROR: Failed to start API server
```

**Solutions:**

1. **Find Process Using Port**
   ```bash
   # Linux/macOS
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```

2. **Kill Conflicting Process**
   ```bash
   # Linux/macOS
   kill -9 <PID>
   
   # Or change Demi's port in config
   # Edit src/core/defaults.yaml:
   api:
     port: 8001  # Change from 8000
   ```

---

## Discord Issues

### Bot Token Invalid

**Symptoms:**
```
ERROR: DISCORD_BOT_TOKEN environment variable not set
ERROR: 401 Unauthorized - Invalid bot token
```

**Solutions:**

1. **Verify Token is Set**
   ```bash
   cat .env | grep DISCORD_BOT_TOKEN
   
   # Should show: DISCORD_BOT_TOKEN=your_actual_token
   ```

2. **Get New Token**
   - Discord Developer Portal → Applications → Your App → Bot
   - Click "Reset Token"
   - Copy new token to `.env`

3. **Restart Demi**
   ```bash
   # After updating .env
   python main.py
   ```

### Permission Errors

**Symptoms:**
- Bot connects but can't send messages
- "Missing Access" errors in logs
- Commands fail silently

**Solutions:**

1. **Check Bot Permissions**
   - Discord Developer Portal → OAuth2 → URL Generator
   - Required permissions:
     - Send Messages
     - Read Message History
     - Embed Links
     - Read Messages/View Channels

2. **Re-invite with Correct Permissions**
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=534723951680
   ```

3. **Check Channel Permissions**
   - Right-click channel → Permissions
   - Ensure bot role has required permissions
   - Check category permissions (inheritance)

### Rate Limiting

**Symptoms:**
```
WARNING: 429 Too Many Requests
WARNING: Rate limited, backing off
```

**Solutions:**

- This is normal — Discord rate limits are expected
- Demi automatically handles rate limits
- If persistent, reduce message frequency

### Gateway Connection Problems

**Symptoms:**
```
ERROR: Gateway connection closed
ERROR: Shard ID None has disconnected
```

**Solutions:**

1. **Check Discord Status**
   - Visit [status.discord.com](https://status.discord.com)
   - Wait if Discord is having issues

2. **Check Internet Connection**
   ```bash
   ping discord.com
   ```

3. **Restart Bot**
   ```bash
   # Ctrl+C to stop
   python main.py
   ```

---

## Android Issues

### Cannot Connect to API

**Symptoms:**
- "Connection failed" error
- Endless loading spinner
- "Server unreachable"

**Solutions:**

1. **Verify Server is Running**
   ```bash
   # From your phone's browser, try:
   http://YOUR_IP:8000/api/v1/status
   
   # Should return JSON status
   ```

2. **Check IP Address**
   ```bash
   # On your server machine:
   ifconfig | grep "inet "  # Linux/macOS
   ipconfig | findstr IPv4  # Windows
   
   # Use the IP on same network as phone
   ```

3. **Check Firewall**
   ```bash
   # Linux - allow port 8000
   sudo ufw allow 8000
   
   # Or temporarily disable
   sudo ufw disable  # Re-enable after testing!
   ```

4. **Same Network Requirement**
   - Phone and server must be on same Wi-Fi network
   - Or use port forwarding for remote access

### Authentication Failures

**Symptoms:**
- "Login failed"
- "Invalid credentials"
- "Authentication error"

**Solutions:**

1. **Verify Credentials**
   - Check username/password in Demi backend
   - User must be created in database first

2. **Check Server URL**
   - Must include protocol: `http://` or `https://`
   - Must include port: `:8000`
   - No trailing slash

3. **Check Server Logs**
   ```bash
   tail -f logs/demi.log | grep -i auth
   ```

### WebSocket Disconnections

**Symptoms:**
- "Connection lost" notifications
- Messages not receiving
- Status shows disconnected

**Solutions:**

1. **Check WebSocket URL**
   - Should use `ws://` (not `http://`)
   - Format: `ws://YOUR_IP:8000/api/v1/chat/ws`

2. **Check Token Validity**
   - Token may have expired
   - Re-login to refresh

3. **Disable Battery Optimization**
   - Android Settings → Apps → Demi → Battery
   - Select "Don't optimize"

### Notification Problems

**Symptoms:**
- No push notifications
- Delayed notifications
- Notifications without sound

**Solutions:**

1. **Check Notification Permissions**
   - Android Settings → Apps → Demi → Notifications
   - Enable all notification channels

2. **Disable Battery Saver**
   - Battery saver restricts background activity
   - Add Demi to whitelist

3. **Check WebSocket Connection**
   - Notifications require active connection
   - Check status indicator in app

---

## Voice Issues

### Microphone Not Detected

**Symptoms:**
- Wake word never triggers
- No audio indicator in Discord
- "Cannot hear you" errors

**Solutions:**

1. **Check Discord Input Settings**
   - Discord → Settings → Voice & Video
   - Verify correct input device
   - Test microphone

2. **Check System Permissions**
   - **Windows:** Settings → Privacy → Microphone
   - **macOS:** System Preferences → Security → Microphone
   - **Linux:** Check PulseAudio settings

3. **Verify Voice Enabled**
   ```bash
   cat .env | grep DISCORD_VOICE_ENABLED
   # Should show: DISCORD_VOICE_ENABLED=true
   ```

### TTS Not Working

**Symptoms:**
- Text responses but no voice
- Error about FFmpeg
- Silent playback

**Solutions:**

1. **Install FFmpeg**
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from ffmpeg.org and add to PATH
   ```

2. **Verify FFmpeg Installation**
   ```bash
   ffmpeg -version
   # Should show version info
   ```

3. **Check TTS Module**
   ```bash
   pip install pyttsx3
   ```

### Wake Word Not Recognized

**Symptoms:**
- Saying "Hey Demi" has no effect
- STT is working (other commands work)
- Wake word just won't trigger

**Solutions:**

1. **Check STT Module**
   ```bash
   # Verify Whisper is installed
   pip install faster-whisper
   # or
   pip install openai-whisper
   ```

2. **Adjust Speaking Pattern**
   - Speak clearly, not too fast
   - Pause slightly after "Hey Demi"
   - Reduce background noise

3. **Check Logs for STT Errors**
   ```bash
   tail -f logs/demi.log | grep -i "stt\|whisper\|transcription"
   ```

### Audio Quality Problems

| Issue | Solution |
|-------|----------|
| Robotic voice | Install better TTS voice packs |
| Cutting out | Check network stability |
| Too quiet | Increase Discord/system volume |
| Echo | Enable echo cancellation in Discord |
| Delay | Close CPU-intensive applications |

---

## Performance Issues

### High RAM Usage

**Symptoms:**
- System slows down
- Out of memory errors
- Swapping to disk

**Solutions:**

1. **Check Current Usage**
   ```bash
   # Linux
   free -h
   
   # Or check Python process
   ps aux | grep python | grep -v grep
   ```

2. **Reduce Model Size**
   ```yaml
   # In config, use smaller model
   llm:
     model: "llama3.2:1b"  # Instead of 3b or larger
   ```

3. **Limit Concurrent Requests**
   ```yaml
   conductor:
     max_concurrent: 2  # Reduce from default
   ```

4. **Enable Memory Optimization**
   ```bash
   # Use quantized models
   ollama pull llama3.2:1b-q4_0
   ```

### Slow Response Times

**Symptoms:**
- Responses take 30+ seconds
- Timeouts occurring
- User experience degraded

**Solutions:**

1. **Check Resource Usage**
   ```bash
   top  # or htop
   # Look for high CPU usage
   ```

2. **Optimize LLM Settings**
   ```yaml
   llm:
     temperature: 0.7
     max_tokens: 500  # Reduce if too high
   ```

3. **Check Database Performance**
   ```bash
   # If using SQLite, may need WAL mode
   sqlite3 data/demi.db "PRAGMA journal_mode=WAL;"
   ```

4. **Enable Response Caching**
   ```yaml
   conductor:
     cache_enabled: true
     cache_ttl: 300
   ```

### Database Locked Errors

**Symptoms:**
```
ERROR: database is locked
ERROR: SQLite timeout
```

**Solutions:**

1. **Enable WAL Mode**
   ```bash
   sqlite3 data/demi.db "PRAGMA journal_mode=WAL;"
   ```

2. **Check for Stale Locks**
   ```bash
   # Look for lock files
   ls -la data/*.db*
   
   # Remove if stale (with Demi stopped!)
   rm data/*.db-journal data/*.db-wal data/*.db-shm
   ```

3. **Increase Timeout**
   ```yaml
   database:
     timeout: 30  # Increase from default
   ```

### Log File Growth

**Symptoms:**
- Logs consuming disk space
- Very large log files
- Slow log rotation

**Solutions:**

1. **Check Log Size**
   ```bash
   ls -lh logs/
   du -sh logs/
   ```

2. **Configure Log Rotation**
   ```yaml
   logging:
     max_bytes: 10485760  # 10MB per file
     backup_count: 5      # Keep 5 backups
     level: INFO          # Reduce from DEBUG
   ```

3. **Manual Cleanup**
   ```bash
   # Keep only recent logs
   find logs/ -name "*.log.*" -mtime +7 -delete
   ```

---

## Emotional State Concerns

### Emotions Not Persisting

**Symptoms:**
- Emotional state resets between conversations
- No continuity across platforms
- Always starts at neutral

**Solutions:**

1. **Check Database Connection**
   ```bash
   # Verify data directory exists
   ls -la data/
   
   # Should see: emotions.db
   ```

2. **Verify Emotion Persistence**
   ```bash
   # Check database contents
   sqlite3 data/emotions.db "SELECT * FROM emotional_states ORDER BY timestamp DESC LIMIT 5;"
   ```

3. **Check File Permissions**
   ```bash
   # Ensure write access
   chmod 755 data/
   chown $USER:$USER data/
   ```

### Emotions Decaying Too Fast/Slow

**Symptoms:**
- Emotional state changes unrealistically
- Too dramatic shifts
- No natural feeling progression

**Solutions:**

1. **Adjust Decay Rate**
   ```yaml
   emotion:
     decay_rate: 0.05  # Per hour (lower = slower decay)
     min_val: 0.0
     max_val: 1.0
   ```

2. **Check Time Settings**
   - Ensure system time is correct
   - Timezone issues can affect decay calculations

### Emotional State Seems Wrong

**Symptoms:**
- Responses don't match claimed emotion
- Emotion colors don't fit content
- Inconsistent emotional display

**Solutions:**

1. **Check Current State**
   ```bash
   # Via API
   curl http://localhost:8000/api/v1/emotion/current
   ```

2. **View Emotional History**
   ```bash
   sqlite3 data/emotions.db "SELECT * FROM emotional_states ORDER BY timestamp DESC LIMIT 10;"
   ```

3. **Reset If Needed**
   ```bash
   # Stop Demi first!
   sqlite3 data/emotions.db "DELETE FROM emotional_states;"
   ```

---

## Error Messages Reference

### Startup Errors

| Error | Meaning | Solution |
|-------|---------|----------|
| `ModuleNotFoundError` | Missing Python package | `pip install -r requirements.txt` |
| `FileNotFoundError` | Config/database file missing | Check paths, restore defaults |
| `PermissionError` | No access to file/directory | Check file permissions |
| `Address already in use` | Port conflict | Kill other process or change port |

### Discord Errors

| Error | Meaning | Solution |
|-------|---------|----------|
| `401 Unauthorized` | Invalid bot token | Reset token in Discord portal |
| `403 Forbidden` | Missing permissions | Re-invite with correct scopes |
| `429 Too Many Requests` | Rate limited | Wait, reduce frequency |
| `1006 Connection Closed` | Network issue | Check internet, restart |

### LLM/Inference Errors

| Error | Meaning | Solution |
|-------|---------|----------|
| `Connection refused` | Ollama not running | Start `ollama serve` |
| `Model not found` | Model not downloaded | `ollama pull llama3.2:1b` |
| `Context length exceeded` | Input too long | Shorten input, summarize |
| `Inference timeout` | Taking too long | Check resources, reduce load |

### Database Errors

| Error | Meaning | Solution |
|-------|---------|----------|
| `database is locked` | Concurrent access | Enable WAL mode |
| `no such table` | Database not initialized | Restart to run migrations |
| `disk I/O error` | Disk full or failing | Check disk space |
| `unable to open database` | Permission issue | Check file permissions |

---

## Getting Help

### Log File Locations

| Log | Location | Contains |
|-----|----------|----------|
| Main Log | `logs/demi.log` | Application events |
| Error Log | `logs/demi.error.log` | Errors only |
| Discord Log | `logs/discord.log` | Discord-specific |
| API Log | `logs/api.log` | HTTP requests |

### How to Report Issues

When reporting issues, include:

1. **Log Excerpts**
   ```bash
   # Last 50 lines of relevant log
   tail -50 logs/demi.log
   ```

2. **System Information**
   ```bash
   python --version
   uname -a
   free -h  # or system info
   ```

3. **Configuration** (sanitized)
   ```bash
   # Remove sensitive data before sharing
   cat src/core/defaults.yaml | grep -v token | grep -v password
   ```

4. **Steps to Reproduce**
   - What you were doing
   - What you expected
   - What actually happened

### Debug Mode Activation

Enable detailed logging:

```bash
# Start with debug logging
python main.py --log-level DEBUG

# Or set in environment
export DEMI_LOG_LEVEL=DEBUG
python main.py
```

Debug mode includes:
- Full SQL queries
- LLM prompt/response logging
- Detailed stack traces
- Timing information

### Community Resources

- **Documentation:** This guide and README files
- **Code Examples:** Check `tests/` directory
- **Persona Reference:** `DEMI_PERSONA.md`

---

> *"There, I've solved your problems. Try not to create new ones."*
> — Demi

**Still stuck?** Review the [Getting Started Guide](./getting-started.md) or check [Discord integration](./discord-guide.md).
