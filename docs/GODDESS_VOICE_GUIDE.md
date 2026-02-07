# 🔮 Demi's Goddess Voice Setup Guide

## Overview

Demi uses **Coqui XTTS-v2** TTS backend with **Goddess Voice Enhancement** to create a divine, ethereal voice perfect for an emotional AI companion.

## Architecture

```
Text → Coqui TTS (XTTS-v2) → Goddess Voice Processor → Audio Output
                                   ↓
                        - Reverb (cathedral-like)
                        - Pitch shift (ethereal)
                        - Compression (presence)
                        - EQ enhancement (warmth/clarity)
                        - Loudness normalization
```

## Quick Start

### 1. Install Dependencies

```bash
./scripts/setup_goddess_voice.sh
```

Or manually:
```bash
# Coqui TTS (best quality)
pip install TTS torch torchaudio

# Audio enhancement
pip install librosa soundfile scipy pyloudnorm

# Optional: GPU acceleration
pip install accelerate
```

### 2. Configure in `.env`

```env
# Use Coqui for best quality
TTS_BACKEND=coqui

# Use GPU if available (faster synthesis, ~1-2s per utterance)
TTS_DEVICE=cuda  # or 'cpu', 'mps'

# Optional: Reference voice for voice cloning
# COQUI_SPEAKER_WAV=/path/to/reference.wav
```

### 3. Enable Goddess Voice Enhancements

Default enabled. Customize in `.env`:

```env
# Goddess voice settings
# GODDESS_VOICE_ENABLED=true (default)
# GODDESS_VOICE_REVERB_WETNESS=0.3 (0.0-1.0, increase for more reverb)
# GODDESS_VOICE_PITCH_SHIFT=1.5 (semitones, higher = more feminine)
# GODDESS_VOICE_PRESENCE_DB=4.0 (dB boost for clarity)
```

### 4. Start Demi

```bash
docker-compose up -d
# OR
python -m src.main
```

## Voice Cloning (Advanced)

For the best "goddess" effect, provide a reference voice:

### Option A: Find a Free Sample
- Search for "ethereal feminine voice" audio samples
- Download from royalty-free sites (FreePD, Freesound, YouTube)
- Use `youtube-dl` to extract audio from YouTube

### Option B: Create Your Own
1. Record 10-30 seconds of voice
2. Use a feminine, breathy, emotionally expressive tone
3. Quiet background
4. Export as WAV

### Option C: Character Voice
- Download character voice samples from anime/games
- Ensure licensing allows personal use
- Convert to WAV

### Setup Reference Voice

```bash
# Convert audio to WAV (required format)
ffmpeg -i input.mp3 -ar 22050 -ac 1 reference.wav

# Set in .env
echo "COQUI_SPEAKER_WAV=/path/to/reference.wav" >> .env

# Restart Demi
docker-compose restart demi
```

## Performance Tuning

### Latency

- **First load**: ~10-15 seconds (model downloads ~2GB)
- **Subsequent syntheses**:
  - GPU (CUDA): ~1-2 seconds per utterance
  - CPU: ~3-5 seconds per utterance

### Reduce Latency

```env
# Use GPU
TTS_DEVICE=cuda

# Enable model caching
TTS_CACHE_ENABLED=true

# Use Kokoro as fallback (faster but lower quality)
TTS_BACKEND=auto  # Will auto-select Coqui, fallback to Kokoro
```

### Reduce Memory Usage

```env
# Use CPU instead of GPU
TTS_DEVICE=cpu

# Or use Kokoro (80MB vs 2GB model)
TTS_BACKEND=kokoro
```

## Customization

### Reverb Amount

```python
# In .env or code
goddess_voice_reverb_wetness=0.3  # Subtle (default)
goddess_voice_reverb_wetness=0.5  # Moderate
goddess_voice_reverb_wetness=0.7  # Heavy (very ethereal)
```

### Pitch Shift

```python
goddess_voice_pitch_shift=0.0    # Keep original
goddess_voice_pitch_shift=1.5    # Slightly higher (default)
goddess_voice_pitch_shift=3.0    # Much higher (more feminine)
goddess_voice_pitch_shift=-1.0   # Lower (more masculine)
```

### Presence/Clarity

```python
goddess_voice_presence_db=2.0   # Subtle
goddess_voice_presence_db=4.0   # Moderate (default)
goddess_voice_presence_db=6.0   # Bright/clear
```

## Emotion Integration

The goddess voice processor works with Demi's emotion system:

```python
# Emotion affects voice modulation
emotional_state = demi.get_emotion()

# High emotion → more reverb/ethereal
if emotional_state.energy > 0.8:
    goddess_processor.config.reverb_wetness = 0.4
else:
    goddess_processor.config.reverb_wetness = 0.2
```

## Troubleshooting

### "Coqui TTS not installed"
```bash
pip install TTS
```

### "No module named librosa"
```bash
pip install librosa soundfile scipy pyloudnorm
```

### Slow synthesis (>5 seconds)
- You're using CPU. Use GPU: `TTS_DEVICE=cuda`
- Or switch to Kokoro: `TTS_BACKEND=kokoro` (faster, lower quality)

### Audio sounds robotic/unnatural
- This is normal for TTS. Try:
  1. Provide a reference voice (voice cloning)
  2. Increase reverb: `goddess_voice_reverb_wetness=0.5`
  3. Add more emotion to text (exclamation marks, etc.)

### Model won't download
- Check internet connection
- Check disk space (needs ~3GB free)
- Set model cache dir: `export HF_HOME=/path/with/space`

### Reference voice sounds wrong
- Reference must be in WAV format (not MP3)
- Sample rate: 22050 Hz recommended
- No background music/noise
- 10-30 seconds duration

```bash
# Check/fix audio format
ffmpeg -i reference.wav -acodec pcm_s16le -ar 22050 -ac 1 reference_fixed.wav
```

## Backends Comparison

| Backend | Quality | Speed | Size | Voice Clone | Emotion |
|---------|---------|-------|------|-------------|---------|
| **Coqui** | ⭐⭐⭐⭐⭐ | 1-2s | 2GB | ✅ Yes | Partial |
| **LuxTTS** | ⭐⭐⭐⭐⭐ | 2-3s | 500MB | ✅ Yes | No |
| **Kokoro** | ⭐⭐⭐⭐ | <500ms | 80MB | ❌ No | ✅ Yes |
| **MeloTTS** | ⭐⭐⭐⭐ | 1-2s | 300MB | ❌ No | ✅ Yes |
| **Piper** | ⭐⭐⭐ | <500ms | 100MB | ❌ No | No |

**Recommended**: **Coqui** (best quality) + **Goddess Voice** enhancement

## Future Enhancements

Planned additions:
- [ ] RVC voice conversion layer (real-time voice morphing)
- [ ] Emotional prosody control (happiness, sadness affects delivery)
- [ ] Voice model fine-tuning on Demi's personality
- [ ] Multi-voice support (different voices for different moods)

## References

- [Coqui TTS Docs](https://github.com/coqui-ai/TTS)
- [XTTS-v2 Model Card](https://huggingface.co/coqui/XTTS-v2)
- [Audio Processing with Librosa](https://librosa.org/)
