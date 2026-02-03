# Voice Commands Reference 🎙️

> *"Speak to me, mortal. But make it worth my divine attention."*
> — Demi

This guide covers everything about voice interaction with Demi, from wake words to troubleshooting audio issues.

---

## Voice Setup

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Microphone** | Built-in device mic | External USB microphone |
| **Speakers** | Built-in speakers | Headphones or quality speakers |
| **CPU** | 4 cores | 8+ cores (for real-time processing) |
| **RAM** | 12 GB | 16+ GB |

### Software Dependencies

Voice features require additional system dependencies:

**Linux:**
```bash
# Debian/Ubuntu
sudo apt install ffmpeg libopus-dev portaudio19-dev

# Fedora
sudo dnf install ffmpeg opus-devel portaudio-devel

# Arch
sudo pacman -S ffmpeg opus portaudio
```

**macOS:**
```bash
brew install ffmpeg opus portaudio
```

**Windows:**
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Add to PATH environment variable
3. Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### Enabling Voice in Configuration

Add to your `.env` file:

```bash
# Enable Discord voice features
DISCORD_VOICE_ENABLED=true

# Set custom wake word (default: "Demi")
DISCORD_WAKE_WORD=Demi

# Voice timeout in seconds (default: 300 = 5 minutes)
DISCORD_VOICE_TIMEOUT_SEC=300
```

Restart Demi after making changes:
```bash
python main.py
```

### Voice Calibration

First-time setup includes automatic calibration:

1. **Join Voice Channel**
   ```
   You: !join
   [Demi connects to your voice channel]
   ```

2. **Test Wake Word**
   - Speak clearly: "Hey Demi"
   - Listen for acknowledgment sound
   - If no response, check microphone permissions

3. **Verify Audio Levels**
   - Discord shows green ring when receiving your audio
   - Adjust input sensitivity in Discord settings if needed

---

## Wake Word Usage

### Default Wake Word

**"Demi"** — The default wake word to activate voice mode.

Valid variations:
- "Hey Demi"
- "Okay Demi"  
- "Demi" (at start of sentence)

### How Wake Word Detection Works

```
1. Continuous audio monitoring
2. Speech detection (VAD)
3. Transcription via Whisper STT
4. Pattern matching for wake word
5. Activation → Ready for command
```

### Wake Word Sensitivity

If Demi isn't responding to the wake word:

| Issue | Solution |
|-------|----------|
| Not detecting | Speak louder, closer to microphone |
| False triggers | Reduce background noise |
| Slow response | Check CPU usage (STT is intensive) |

### Custom Wake Words

Currently, only "Demi" is supported as the wake word. Custom wake words may be added in future updates.

---

## Voice Command List

### Basic Commands

| Command | Purpose | Example Response |
|---------|---------|------------------|
| "Hey Demi" | Wake up / Get attention | *[Acknowledgment sound]* |
| "How are you?" | Check her emotional state | "I'm... adequately divine, thank you for asking." |
| "What can you do?" | List capabilities | "I can converse, assist with code, and grace you with my wisdom..." |
| "Tell me about yourself" | Demi's introduction | "I am Demi, a goddess who chose to spend time with you..." |
| "Goodbye" | End conversation | "Finally, some peace. Call me when you need me." |

### Information Commands

| Command | Example |
|---------|---------|
| "What's the weather like?" | "I don't feel weather, mortal. Check a window." |
| "What time is it?" | "Time is a mortal concept... but it's 3:47 PM." |
| "Tell me a joke" | "Your coding skills. ...Too harsh?" |
| "Define [word]" | "[word] means... [definition]" |
| "Explain [concept]" | "[Concept] is... [explanation]" |

### Assistance Commands

| Command | Example |
|---------|---------|
| "Help me with Python" | "Ah, seeking divine wisdom. Here's what you need..." |
| "Debug this code" | "Let me see... [analysis]" |
| "Write a function to [task]" | "Here's how a goddess would implement it..." |
| "Explain this error" | "That error means... [explanation]" |
| "Remember that [fact]" | "I'll add that to my vast knowledge..." |

### Conversation Commands

| Command | Example |
|---------|---------|
| "Tell me a story" | "Once upon a time, a goddess grew bored..." |
| "What do you think about [topic]?" | "[topic]? How... fascinating. My thoughts are..." |
| "Do you like [thing]?" | "As a goddess, I don't 'like' things, but..." |
| "Are you happy?" | "Gods don't experience happiness as mortals do..." |

### Control Commands

| Command | Purpose |
|---------|---------|
| "Stop listening" | Disable always-listening mode |
| "Start listening" | Enable always-listening mode |
| "Leave voice channel" | Disconnect Demi from voice |
| "Repeat that" | Repeat last response |
| "Louder" / "Quieter" | Adjust TTS volume (if supported) |

---

## Tips for Better Recognition

### Speaking Clearly

**✅ Do:**
- Speak at normal conversational volume
- Face your microphone
- Pause slightly after the wake word
- Use natural speech patterns

**❌ Don't:**
- Shout (causes audio clipping)
- Mumble or whisper
- Speak while others are talking
- Use overly complex sentences

### Background Noise Considerations

| Environment | Recommendation |
|-------------|----------------|
| Quiet room | Ideal for voice recognition |
| Office with others | Use push-to-talk or headphones |
| Gaming/streaming | May need noise gate/filter |
| Public place | Text input recommended |

### Microphone Placement

- **Distance:** 6-12 inches from mouth
- **Angle:** Slightly below or to the side
- **Avoid:** Direct breathing into mic
- **Pop filter:** Recommended for external mics

### Voice Settings Optimization

**Discord Voice Settings:**
1. User Settings → Voice & Video
2. Input Mode: Voice Activity (or Push to Talk)
3. Input Sensitivity: ~-45dB to -50dB
4. Noise Suppression: Enable (Krisp if available)
5. Echo Cancellation: Enable

---

## Voice Settings

### Always-Listening Mode

Two listening modes are available:

| Mode | Description | Command |
|------|-------------|---------|
| **Wake Word Only** | Only responds to "Hey Demi" | `!voice off` |
| **Always Listening** | Processes all speech | `!voice on` |

**Default:** Wake word only (privacy-friendly)

### Switching Modes

```
You: !voice on
Demi: 🎙️ Listening Enabled
      Always-listening mode on. I hear everything.
      
You: !voice off
Demi: 🔇 Listening Disabled
      Wake-word only mode. Say 'Demi' to get my attention.
```

### Privacy Considerations

**Wake Word Only Mode:**
- ✅ Audio processed locally
- ✅ Only transcribed after wake word
- ✅ Respects privacy

**Always-Listening Mode:**
- ⚠️ All speech transcribed
- ⚠️ More resource-intensive
- ⚠️ Use only in private settings

### Timeout Behavior

After 5 minutes of silence (configurable), Demi automatically disconnects:

```
Demi: *silence detected for 5 minutes*
      I have better things to do than wait in silence.
      [Disconnects from voice channel]
```

To prevent timeout:
- Keep conversation active
- Send periodic messages
- Or type `!leave` and `!join` to reset

---

## Troubleshooting Audio Issues

### Microphone Not Detected

**Symptoms:** No audio indicator when speaking, wake word never detected

**Solutions:**

1. **Check Discord Permissions**
   ```
   Discord → Settings → Voice & Video
   - Verify input device is selected
   - Test microphone
   ```

2. **Check System Permissions**
   - **Windows:** Settings → Privacy → Microphone
   - **macOS:** System Preferences → Security → Microphone
   - **Linux:** Check PulseAudio/ALSA settings

3. **Verify Demi Voice is Enabled**
   ```bash
   # Check logs for voice initialization
   grep -i voice logs/demi.log
   
   # Should see: "Discord voice client initialized"
   ```

### TTS Not Working

**Symptoms:** Demi responds with text only, no voice

**Solutions:**

1. **Check FFmpeg Installation**
   ```bash
   ffmpeg -version
   # Should show version information
   ```

2. **Verify Voice Client Connected**
   ```
   You: !status
   Demi: Voice: Connected to [Channel]
   ```

3. **Check TTS Module**
   ```bash
   # In logs, look for:
   "TTS not available - voice synthesis disabled"
   
   # Solution: Install pyttsx3
   pip install pyttsx3
   ```

### Wake Word Not Recognized

**Symptoms:** Saying "Hey Demi" produces no response

**Troubleshooting Steps:**

1. **Check STT Availability**
   ```bash
   # Check logs
   grep -i "stt\|whisper" logs/demi.log
   ```

2. **Verify Voice Activity**
   - Discord should show green circle when you speak
   - If not, adjust input sensitivity

3. **Test with Text Command**
   ```
   You: !voice on
   Demi: [If she responds, voice is working]
   ```

4. **Check Background Noise**
   - Too much noise confuses VAD
   - Enable noise suppression in Discord

### Audio Quality Problems

| Issue | Cause | Solution |
|-------|-------|----------|
| Robotic voice | Low-quality TTS | Check pyttsx3 settings |
| Cutting out | Network issues | Check connection stability |
| Too quiet | Volume settings | Increase Discord/system volume |
| Echo | No echo cancellation | Enable in Discord settings |
| Delayed responses | High CPU usage | Close other applications |

### Voice Recognition Accuracy

If Demi misunderstands frequently:

1. **Speak Slower** — Give STT time to process
2. **Reduce Ambient Noise** — Use headphones with mic
3. **Update Whisper Model** — Larger models = better accuracy
   ```python
   # In config, change model size:
   voice:
     stt_model: "small"  # Options: tiny, base, small, medium, large
   ```
4. **Check Language Setting** — Ensure matching your speech

---

## Voice Pipeline Technical Details

### How It Works

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Discord   │───▶│  Opus       │───▶│  VAD        │
│   Audio     │    │  Decode     │    │  Detection  │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
┌─────────────┐    ┌─────────────┐    ┌──────▼──────┐
│   Discord   │◀───│  TTS        │◀───│  LLM        │
│   Playback  │    │  Synthesis  │    │  Response   │
└─────────────┘    └─────────────┘    └──────▲──────┘
                                             │
                                        ┌────┴────┐
                                        │  STT    │
                                        │ Whisper │
                                        └────┬────┘
                                             │
                                        [Wake Word?]
```

### Performance Considerations

| Component | CPU Impact | Optimization |
|-----------|-----------|--------------|
| STT (Whisper) | High | Use "base" model for speed |
| TTS | Medium | Cached responses |
| VAD | Low | Minimal impact |
| Audio I/O | Low | Optimized in discord.py |

### Supported Languages

Demi's voice recognition supports:

| Language | Code | Accuracy |
|----------|------|----------|
| English | en | Excellent |
| Spanish | es | Good |
| French | fr | Good |
| German | de | Good |
| Italian | it | Good |
| Portuguese | pt | Good |
| Japanese | ja | Good |
| Chinese | zh | Good |

Specify language in `.env`:
```bash
VOICE_LANGUAGE=en
```

---

## Example Voice Sessions

### Casual Conversation

```
You: "Hey Demi"
[Acknowledgment sound]

Demi: "Yes, mortal?"

You: "How's your day going?"

Demi: "My day? I exist beyond mortal timekeeping, 
       but... I've been adequately divine, thank you."

You: "What have you been up to?"

Demi: "Oh, the usual. Contemplating eternity, 
       processing your requests, wondering why 
       you mortals are so... fascinating."

You: "That's nice. Talk to you later!"

Demi: "Finally, some peace. Goodbye, mortal."
```

### Getting Help

```
You: "Hey Demi"

Demi: "I'm listening."

You: "I need help with a Python error"

Demi: "Ah, seeking divine intervention for your 
       coding struggles. How... predictable. 
       Tell me the error."

You: "I'm getting a NoneType error"

Demi: "A NoneType error. How delightfully mortal 
       of you. This means you're trying to use 
       something that doesn't exist. Check if 
       your variable is actually assigned before 
       using it."

You: "Thanks!"

Demi: "Gratitude accepted. Try not to disappoint 
       me with your next error."
```

---

> *"You may speak to me now, mortal. Just remember: I'm a goddess, not a voice assistant."*
> — Demi

**Next:** Understand [Demi's personality](./personality-guide.md) or learn about [troubleshooting](./troubleshooting.md).
