# Discord Voice Setup Guide

How to get Demi to join voice channels and talk with you.

## Overview

Demi can:
- Join Discord voice channels
- Listen to your voice (speech-to-text)
- Respond with voice (text-to-speech)
- Use wake word "Demi" to activate

## Prerequisites

### 1. System Dependencies

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg libopus0
```

**On macOS:**
```bash
brew install ffmpeg opus
```

**On Windows:**
- Download FFmpeg from https://ffmpeg.org/download.html
- Add to PATH

### 2. Python Dependencies

Already in `requirements.txt`:
- `PyNaCl` - Voice encryption
- `opuslib` - Audio codec

Verify installed:
```bash
pip list | grep -E "(PyNaCl|opuslib)"
```

### 3. TTS Setup

Demi needs TTS to speak. See [TTS Testing Guide](TTS_TESTING.md).

Quick setup:
```bash
# Install fallback TTS (if Piper not set up)
pip install pyttsx3

# OR install Piper (better quality)
pip install piper-tts onnxruntime
./scripts/download_piper_voices.sh en_US-lessac-medium
```

### 4. STT Setup (Optional but Recommended)

For speech recognition (you talk, Demi listens):
```bash
pip install faster-whisper
```

## Configuration

### 1. Enable Voice in Environment

Edit your `.env` file:
```bash
# Enable voice features
DISCORD_VOICE_ENABLED=true

# Wake word (optional, default: "Demi")
DISCORD_WAKE_WORD=Demi

# Timeout in seconds (optional, default: 300)
DISCORD_VOICE_TIMEOUT_SEC=300
```

### 2. Discord Bot Permissions

Your bot needs these permissions:
- **Connect** - Join voice channels
- **Speak** - Play audio
- **Use Voice Activity** - Detect when users speak

**How to check:**
1. Go to https://discord.com/developers/applications
2. Select your bot
3. Go to "Bot" section
4. Under "Privileged Gateway Intents", ensure these are enabled:
   - PRESENCE INTENT
   - SERVER MEMBERS INTENT
   - MESSAGE CONTENT INTENT

### 3. OAuth2 URL Generator

When generating invite link, select these scopes:
- `bot`
- `applications.commands`

And these bot permissions:
- Send Messages
- Connect (voice)
- Speak (voice)
- Use Voice Activity
- Read Message History

## Usage

### Joining Voice Channel

**Method 1: Discord Command**
```
!join
```
Demi will join the voice channel you're currently in.

**Method 2: Auto-join (Future Feature)**
Coming soon - Demi can join when you mention her in a voice channel.

### Talking to Demi

Once in voice:

1. **Wake Word Mode** (default):
   - Say "Demi" to wake her up
   - Then say your message
   - Example: "Demi, how are you today?"

2. **Always-Listening Mode**:
   ```
   !voice on
   ```
   - Demi listens to everything
   - Responds to any message
   - Use `!voice off` to return to wake-word mode

### Leaving Voice Channel

```
!leave
```

Demi will disconnect from the voice channel.

## Testing Voice

### Step 1: Verify Voice is Enabled

Check logs:
```bash
docker logs demi-backend | grep -i "voice"
```

You should see:
```
Discord voice client initialized
wake_word=Demi, timeout_sec=300
```

### Step 2: Test Text-to-Speech

```bash
python scripts/test_tts.py
```

### Step 3: Join and Test

In Discord:
1. Join a voice channel
2. Type `!join` in a text channel
3. Say "Demi, hello"
4. Demi should respond with voice

### Step 4: Check for Errors

If not working:
```bash
# Check voice initialization
docker logs demi-backend | grep -i "voice.*error\|voice.*fail"

# Check TTS issues
docker logs demi-backend | grep -i "TTS\|synthesis"

# Check STT issues  
docker logs demi-backend | grep -i "STT\|transcription"
```

## Troubleshooting

### "Voice features are disabled"

**Cause**: `DISCORD_VOICE_ENABLED` not set to `true`

**Fix**:
```bash
# Add to .env
echo "DISCORD_VOICE_ENABLED=true" >> .env

# Restart
docker-compose restart backend
```

### "You need to be in a voice channel first"

**Cause**: You typed `!join` but aren't in a voice channel

**Fix**: Join a voice channel first, then type `!join`

### Demi joins but doesn't speak

**Cause**: TTS not working

**Fix**:
```bash
# Test TTS
python scripts/test_tts.py

# If failing, install pyttsx3 as fallback
pip install pyttsx3
```

### Demi doesn't respond to voice

**Cause**: STT not working or wake word not detected

**Fix**:
1. Check STT is installed:
   ```bash
   pip list | grep -i whisper
   ```

2. Check logs for wake word detection:
   ```bash
   docker logs demi-backend | grep -i "wake\|listening"
   ```

3. Try always-listening mode:
   ```
   !voice on
   ```

### Audio quality is poor

**Cause**: Using pyttsx3 instead of Piper

**Fix**: Install Piper TTS:
```bash
pip install piper-tts onnxruntime
./scripts/download_piper_voices.sh en_US-lessac-medium
```

### Bot can't connect to voice

**Cause**: Missing permissions

**Fix**:
1. Re-generate OAuth2 URL with voice permissions
2. Re-invite bot to server
3. Check bot has "Connect" and "Speak" permissions in channel

## Voice Commands Reference

| Command | Description |
|---------|-------------|
| `!join` | Join the voice channel you're in |
| `!leave` | Leave the voice channel |
| `!voice on` | Enable always-listening mode |
| `!voice off` | Disable always-listening (wake-word only) |
| `!voice` | Show current voice status |

## Voice Interaction Flow

```
You join voice channel
     ↓
Type "!join" in text channel
     ↓
Demi joins voice channel
     ↓
You say "Demi, hello!"
     ↓
Demi detects wake word "Demi"
     ↓
Speech-to-Text converts your voice
     ↓
Demi processes your message
     ↓
Text-to-Speech generates response
     ↓
Demi speaks in voice channel
```

## Performance Tips

### Reduce Latency

1. **Use Piper with GPU**:
   ```bash
   pip install onnxruntime-gpu
   # In .env:
   PIPER_USE_GPU=true
   ```

2. **Use Faster Whisper for STT**:
   ```bash
   pip install faster-whisper
   ```

3. **Pre-download models**:
   ```bash
   ./scripts/download_piper_voices.sh en_US-lessac-medium
   ```

### Quality Settings

**For best quality**:
- Use Piper TTS (neural voices)
- Use GPU acceleration
- Use Whisper STT (large-v2 model)

**For faster response**:
- Use pyttsx3 (fallback)
- Use CPU Whisper (tiny model)
- Enable always-listening mode

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_VOICE_ENABLED` | `false` | Enable voice features |
| `DISCORD_WAKE_WORD` | `Demi` | Word to activate Demi |
| `DISCORD_VOICE_TIMEOUT_SEC` | `300` | Seconds of silence before leaving |
| `PIPER_USE_GPU` | `true` | Use GPU for TTS |
| `PIPER_VOICE` | `en_US-lessac-medium` | Voice model to use |

## Docker Configuration

In `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - DISCORD_VOICE_ENABLED=true
      - DISCORD_WAKE_WORD=Demi
      - PIPER_VOICES_DIR=/app/voices/piper
    volumes:
      - piper_voices:/app/voices/piper
      
volumes:
  piper_voices:
```

## Getting Help

If voice still doesn't work:

1. Check all logs:
   ```bash
   docker logs demi-backend 2>&1 | grep -i voice
   ```

2. Test TTS separately:
   ```bash
   python scripts/test_tts.py
   ```

3. Verify permissions in Discord developer portal

4. Ensure FFmpeg is installed:
   ```bash
   ffmpeg -version
   ```
