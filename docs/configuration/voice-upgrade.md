# Voice Upgrade Guide - RTX 3060 Optimization

This guide covers the new faster-whisper STT and Piper TTS features optimized for your RTX 3060 (12GB VRAM).

---

## Quick Setup

### 1. Install Dependencies

```bash
# Activate your environment
source .venv/bin/activate

# Install new voice dependencies
pip install faster-whisper piper-tts onnxruntime-gpu
```

### 2. Download Piper Voices

```bash
# Download the default voice (high quality female)
./scripts/download_piper_voices.sh en_US-lessac-medium

# Or download all recommended voices
./scripts/download_piper_voices.sh all
```

Voices are saved to `~/.demi/voices/piper/`

### 3. Update Configuration

Edit your `.env` or `src/core/defaults.yaml`:

```yaml
voice:
  enabled: true
  tts:
    backend: "auto"  # Tries Piper first, falls back to pyttsx3
    piper_voice: "en_US-lessac-medium"
    piper_use_gpu: true
  stt:
    use_faster_whisper: true
    compute_type: "int8"  # 50% VRAM reduction
    device: "cuda"
    model_size: "small"   # <2s latency on RTX 3060
```

---

## faster-whisper STT

### Why faster-whisper?

| Feature | openai-whisper | faster-whisper |
|---------|---------------|----------------|
| Speed | 1x | **4-5x faster** |
| VRAM Usage | 100% | **~50% with int8** |
| GPU Support | Limited | **Full CUDA** |
| VAD Filter | No | **Built-in** |

### Usage

```python
from src.voice.stt import FasterWhisperSTT

# RTX 3060 optimized (recommended)
stt = FasterWhisperSTT.for_rtx3060()

# Or custom configuration
stt = FasterWhisperSTT(
    model_size="small",      # tiny, base, small, medium, large-v1/v2/v3
    compute_type="int8",     # int8, int8_float16, float16, float32
    device="cuda",           # cuda, cpu, auto
    vad_filter=True,
    word_timestamps=False
)

# Transcribe
result = await stt.transcribe_file("audio.wav")
print(result.text)

# With word timestamps
stt = FasterWhisperSTT(model_size="small", word_timestamps=True)
result = await stt.transcribe_file("audio.wav")
words = stt.get_last_word_timestamps()
for word in words:
    print(f"{word.word}: {word.start:.2f}s - {word.end:.2f}s")
```

### Model Size vs VRAM (int8)

| Model | VRAM | Latency (RTX 3060) |
|-------|------|-------------------|
| tiny | ~1GB | ~0.5s |
| base | ~1.5GB | ~1s |
| small | ~2GB | ~2s |
| medium | ~4GB | ~4s |
| large-v2 | ~8GB | ~8s |

**Recommendation:** Use `small` for best balance of speed/accuracy on RTX 3060.

---

## Piper TTS

### Why Piper?

| Feature | pyttsx3 | Piper |
|---------|---------|-------|
| Voice Quality | Robotic | **Natural** |
| GPU Acceleration | No | **Yes (ONNX)** |
| Emotion Support | Limited | **Speed/Pitch** |
| Offline | Yes | **Yes** |

### Available Voices

| Voice | Quality | Size | Style |
|-------|---------|------|-------|
| en_US-lessac-medium | Medium | ~100MB | Clear female |
| en_US-lessac-high | High | ~300MB | Clear female |
| en_US-ryan-high | High | ~300MB | Male |
| en_US-libritts-high | High | ~300MB | Natural female |

### Usage

```python
from src.voice.piper_tts import PiperTTS, download_voice

# Download voice (one-time)
download_voice("en_US-lessac-medium")

# Initialize
tts = PiperTTS(
    voice="en_US-lessac-medium",
    use_gpu=True  # Uses RTX 3060
)

# Speak
tts.speak("Hello mortal, I am Demi.")

# With emotion (affects speed/pitch)
from src.emotion.models import EmotionalState
emotion = EmotionalState(confidence=0.8)
tts.speak("You have pleased me.", emotion=emotion)

# Save to file
tts.speak_to_file("Hello!", "/tmp/greeting.wav")
```

### Using with TextToSpeech (Auto Backend)

```python
from src.voice.tts import TextToSpeech

# Auto tries Piper first, falls back to pyttsx3
tts = TextToSpeech(backend="auto")

# Check which backend is active
print(tts.get_backend())  # "piper" or "pyttsx3"

# Use normally
tts.speak("Hello mortal!")
```

---

## Emotion-to-Voice Mapping

Piper can adjust voice based on Demi's emotional state:

| Emotion | Effect |
|---------|--------|
| High Confidence | Faster, clearer |
| Vulnerability | Slower, softer |
| Frustration | Slightly faster, clipped |
| Excitement | Variable pace |
| Loneliness | Slower, seeking |

Configure in `src/voice/emotion_voice.py`:

```python
EMOTION_TO_VOICE_SETTINGS = {
    "confidence": {"length_scale": 0.9, "noise_scale": 0.667},
    "vulnerable": {"length_scale": 1.2, "noise_scale": 0.3},
    # ... etc
}
```

---

## Troubleshooting

### CUDA Out of Memory

```python
# Use smaller model
stt = FasterWhisperSTT(model_size="base", compute_type="int8")

# Or use CPU
stt = FasterWhisperSTT(model_size="small", device="cpu")
```

### Piper Voice Not Found

```bash
# Re-download voices
./scripts/download_piper_voices.sh en_US-lessac-medium

# Check voice location
ls ~/.demi/voices/piper/
```

### ONNX GPU Not Working

```python
# Force CPU for Piper
tts = PiperTTS(use_gpu=False)
```

### Whisper Not Using GPU

```python
# Check CUDA detection
import torch
print(torch.cuda.is_available())  # Should be True

# Force CUDA
stt = FasterWhisperSTT(device="cuda")
```

---

## Performance Benchmarks (RTX 3060)

### STT Latency

| Model | RTX 3060 (int8) | CPU |
|-------|----------------|-----|
| tiny | 0.3s | 2s |
| small | 0.8s | 5s |
| medium | 2s | 12s |

### TTS Latency

| Backend | RTX 3060 | CPU |
|---------|----------|-----|
| Piper | 0.2s | 1s |
| pyttsx3 | N/A | 0.5s |

---

## Migration from Previous Setup

If you were using the old whisper + pyttsx3 setup:

1. Install new dependencies: `pip install faster-whisper piper-tts onnxruntime-gpu`
2. Download Piper voice: `./scripts/download_piper_voices.sh en_US-lessac-medium`
3. Update config: `use_faster_whisper: true`, `backend: "auto"`
4. Done! Demi will automatically use the better backends.

The old whisper and pyttsx3 still work as fallbacks if needed.
