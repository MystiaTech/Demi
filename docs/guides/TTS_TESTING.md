# TTS Testing Guide

How to check and test Demi's Text-to-Speech (TTS) functionality.

## Quick Check

Run the diagnostic script:

```bash
python scripts/test_tts.py
```

This will:
1. Check which TTS backends are installed
2. Check for Piper voice files
3. Test each available backend
4. Provide recommendations

## Understanding TTS Backends

Demi supports two TTS backends:

### 1. Piper TTS (Recommended)
- **Quality**: High-quality neural TTS
- **Latency**: ~500ms with GPU, ~2s with CPU
- **Requirements**: 
  - `piper-tts` Python package
  - `onnxruntime` or `onnxruntime-gpu`
  - Voice model files (~100-300MB)
- **Best for**: Production use, voice channels

### 2. pyttsx3 (Fallback)
- **Quality**: System TTS (robotic)
- **Latency**: ~1-2s
- **Requirements**: Just `pyttsx3` package
- **Best for**: Quick testing, development

## Installation

### Install Piper (Recommended)

```bash
# Install packages
pip install piper-tts onnxruntime

# Download a voice model
./scripts/download_piper_voices.sh en_US-lessac-medium
```

For GPU acceleration:
```bash
pip install onnxruntime-gpu
```

### Install pyttsx3 (Fallback)

```bash
pip install pyttsx3
```

## Testing Methods

### Method 1: Diagnostic Script (Recommended)

```bash
python scripts/test_tts.py
```

Expected output if working:
```
============================================================
TTS DEPENDENCY CHECK
============================================================
✅ piper-tts: INSTALLED
✅ pyttsx3: INSTALLED
✅ onnxruntime: INSTALLED (1.16.0)

============================================================
PIPER VOICE FILES CHECK
============================================================
✅ Found 1 voice model(s):
   - en_US-lessac-medium.onnx (95.2 MB)

...

✅ Main TTS test PASSED

🎉 TTS is working! Demi can speak.
```

### Method 2: Python Console Test

```python
import asyncio
from src.voice.tts import TextToSpeech, TTSConfig

async def test():
    # Initialize TTS
    tts = TextToSpeech()
    
    # Check which backend is active
    print(f"Backend: {tts.get_backend()}")
    
    # List available voices
    voices = tts.list_voices()
    print(f"Available voices: {len(voices)}")
    
    # Test synthesis
    await tts.speak(
        text="Hello, I am Demi.",
        save_path="/tmp/test.wav",
        play_immediately=False
    )
    print("Audio saved to /tmp/test.wav")

asyncio.run(test())
```

### Method 3: Direct Backend Test

**Test Piper directly:**
```python
import asyncio
from src.voice.piper_tts import PiperTTS, PiperTTSConfig

async def test_piper():
    config = PiperTTSConfig(
        voice_id="en_US-lessac-medium",
        use_gpu=False
    )
    engine = PiperTTS(config)
    
    if engine.voice is None:
        print("❌ No voice loaded - run download script")
        return
    
    result = await engine.speak(
        text="Hello, I am Demi.",
        save_path="/tmp/piper_test.wav",
        play_immediately=False
    )
    print(f"✅ Synthesis complete: {result}")

asyncio.run(test_piper())
```

**Test pyttsx3 directly:**
```python
import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty("voices")
print(f"Available voices: {len(voices)}")

for v in voices:
    print(f"  - {v.name}")

engine.save_to_file("Hello, I am Demi.", "/tmp/pyttsx3_test.wav")
engine.runAndWait()
print("✅ Audio saved")
```

## Checking Voice Files

Voice files are stored in:
```
~/.demi/voices/piper/
```

List installed voices:
```bash
./scripts/download_piper_voices.sh
```

Expected output:
```
Installed Voices:
-------------------
  ✓ en_US-lessac-medium (95M) - Lessac (Medium) - Female, Good quality...
  ✗ en_US-ryan-high - Ryan (High) - Male, High quality...
```

## Common Issues

### "No TTS backend available"

**Cause**: Neither Piper nor pyttsx3 is installed.

**Fix**:
```bash
pip install pyttsx3  # Quick fix
# OR
pip install piper-tts onnxruntime  # Better quality
./scripts/download_piper_voices.sh en_US-lessac-medium
```

### "No voice loaded" / "No voice models found"

**Cause**: Piper is installed but voice files are missing.

**Fix**:
```bash
./scripts/download_piper_voices.sh en_US-lessac-medium
```

### "onnxruntime not installed"

**Cause**: Piper requires ONNX Runtime.

**Fix**:
```bash
# For CPU
pip install onnxruntime

# For GPU (CUDA)
pip install onnxruntime-gpu
```

### Audio plays but sounds robotic

**Cause**: Using pyttsx3 fallback instead of Piper.

**Fix**: Install Piper for higher quality:
```bash
pip install piper-tts onnxruntime
./scripts/download_piper_voices.sh en_US-lessac-medium
```

### TTS is slow (>2 seconds)

**Cause**: Using CPU instead of GPU, or using pyttsx3.

**Fix**:
1. Use Piper instead of pyttsx3
2. Enable GPU for Piper:
```python
from src.voice.tts import TTSConfig

config = TTSConfig(
    backend="piper",
    piper_use_gpu=True
)
```

## Testing in Discord Voice

To test TTS in Discord voice channels:

1. **Enable voice features**:
   ```bash
   # In .env
   DISCORD_VOICE_ENABLED=true
   ```

2. **Join a voice channel**:
   ```
   !join
   ```

3. **Say something** (with voice):
   Demi should respond with audio if TTS is working.

4. **Check logs**:
   ```bash
   docker logs demi-backend | grep -i "TTS\|voice"
   ```

## Configuration Options

### Environment Variables

```bash
# TTS Backend preference
TTS_BACKEND=piper  # or pyttsx3, auto

# Piper settings
PIPER_VOICE=en_US-lessac-medium
PIPER_USE_GPU=true
PIPER_VOICES_DIR=/app/voices/piper

# pyttsx3 settings
TTS_RATE=150  # Words per minute
TTS_VOLUME=1.0  # 0.0 to 1.0
```

### Docker Configuration

In `docker-compose.yml`:
```yaml
services:
  backend:
    volumes:
      - piper_voices:/app/voices/piper
    environment:
      - PIPER_VOICES_DIR=/app/voices/piper
      - DISCORD_VOICE_ENABLED=true
```

## Verifying in Production

Check TTS is working in production:

```bash
# Check backend initialized
docker logs demi-backend | grep -i "TTS backend initialized"

# Check voice loaded (Piper)
docker logs demi-backend | grep -i "voice loaded\|voice file"

# Check synthesis latency
docker logs demi-backend | grep -i "TTS synthesis completed"

# Check for errors
docker logs demi-backend | grep -i "TTS.*error\|synthesis failed"
```

## Performance Benchmarks

Expected synthesis times:

| Backend | Hardware | Latency | Quality |
|---------|----------|---------|---------|
| Piper | GPU (RTX 3060) | ~300-500ms | Excellent |
| Piper | CPU (8 cores) | ~1-2s | Excellent |
| pyttsx3 | Any | ~1-2s | Fair |

If latency is consistently higher, check:
1. GPU is being used (if available)
2. Model is cached after first use
3. No other processes consuming resources

## Troubleshooting Checklist

- [ ] Run `python scripts/test_tts.py`
- [ ] Check at least one backend shows "✅ INSTALLED"
- [ ] If using Piper, run `./scripts/download_piper_voices.sh`
- [ ] Verify voice files exist in `~/.demi/voices/piper/`
- [ ] Test synthesis saves audio file
- [ ] Check audio file plays correctly
- [ ] Test in Discord with `!join` command

## Getting Help

If TTS still doesn't work:

1. Run diagnostic: `python scripts/test_tts.py`
2. Check logs: `docker logs demi-backend | grep -i tts`
3. Verify voice files: `./scripts/download_piper_voices.sh`
4. Check GPU (if using): `nvidia-smi`
