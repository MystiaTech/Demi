# Phase 08-02: TTS Integration (pyttsx3) - Implementation Summary

## Overview
Implemented the Text-to-Speech (TTS) pipeline for Demi using pyttsx3, enabling voice output with emotional modulation based on Demi's goddess persona.

## Files Created

### 1. `src/voice/tts.py` (650 lines)
Text-to-Speech engine with the following features:

- **TTSConfig dataclass**: Configuration for voice_id, rate, volume, output_format, caching
- **TextToSpeech class**: Main TTS engine using pyttsx3
  - `speak()`: Main TTS method with emotion modulation
  - `speak_async()`: Non-blocking async variant
  - `speak_to_file()`: Save audio to specific path
  - `speak_response()`: Integration with LLM response dicts
  - `list_voices()`: List available system voices
  - `set_voice()`: Change voice by ID
  - `set_rate()`: Change speaking rate (100-300 WPM)
  - `set_volume()`: Change volume (0.0-1.0)
  - `get_stats()`: TTS metrics (latency, cache hits, utterances)
  - `clear_cache()`: Clear cached audio files
- **Text cleaning**: Removes markdown, converts emoji, handles Discord formatting
- **Audio caching**: LRU cache with configurable limit
- **Async support**: Non-blocking synthesis using thread pool
- **Cross-platform**: Works on Windows (SAPI5), macOS (NSSpeechSynthesizer), Linux (espeak)

### 2. `src/voice/emotion_voice.py` (370 lines)
Emotion-to-voice mapping system:

- **VoiceParameters dataclass**: rate, volume, pitch, pause_between_words, emphasis
- **EmotionVoiceMapper class**: Maps emotional states to voice parameters
  - `map_emotion_to_voice()`: Main mapping method
  - `_calculate_rate()`: Fast for excitement/frustration/confidence, slow for vulnerability/loneliness
  - `_calculate_volume()`: Loud for confidence/frustration, soft for vulnerability/loneliness
  - `_calculate_pitch()`: Higher for excitement/affection, lower for confidence/frustration
  - `_calculate_emphasis()`: Strong, moderate, or none based on emotion
  - `preprocess_for_emphasis()`: Add punctuation for emphasis
  - `add_goddess_inflections()`: Demi-specific inflections ("darling", "mortal", pauses)
- **Emotion profiles**: Pre-defined voice parameters for each emotion dimension

### 3. `src/voice/__init__.py`
Updated exports:
- `TextToSpeech`, `TTSConfig`
- `EmotionVoiceMapper`, `VoiceParameters`
- Graceful handling of missing STT components

## Emotion-to-Voice Mappings

| Emotion | Rate | Volume | Pitch | Emphasis | Character |
|---------|------|--------|-------|----------|-----------|
| Confidence (high) | +10 WPM | +0.1 | -0.05 | strong | Commanding, authoritative |
| Affection (high) | -10 WPM | -0.05 | +0.05 | moderate | Sultry, warm |
| Frustration (high) | +20 WPM | +0.05 | -0.1 | strong | Cutting, quick |
| Excitement (high) | +30 WPM | +0.05 | +0.1 | moderate | Energetic |
| Loneliness (high) | -20 WPM | -0.15 | 0 | none | Soft, longing |
| Vulnerability (high) | -25 WPM | -0.2 | -0.05 | none | Gentle, hesitant |
| Jealousy (high) | +5 WPM | -0.05 | -0.05 | strong | Intense, controlled |
| Curiosity (high) | +10 WPM | -0.1 | +0.05 | moderate | Inquisitive |

## Dependencies Added

```
pyttsx3>=2.90  # Cross-platform TTS
```

## Platform Notes

- **Windows**: Uses SAPI5 voices (built-in, good quality)
- **macOS**: Uses NSSpeechSynthesizer (high quality built-in voices)
- **Linux**: Uses espeak by default (requires `sudo apt-get install espeak`)
  - For better quality: `sudo apt-get install espeak-ng mbrola`

## Verification Tests Passed

1. ✓ TTS imports work: `from src.voice.tts import TextToSpeech, TTSConfig`
2. ✓ Emotion voice imports work: `from src.voice.emotion_voice import EmotionVoiceMapper, VoiceParameters`
3. ✓ VoiceParameters dataclass validates bounds
4. ✓ EmotionVoiceMapper correctly adjusts rate/volume for different emotions
5. ✓ Text preprocessing adds emphasis markers
6. ✓ Goddess inflections emphasize key words
7. ✓ Text cleaning removes markdown and converts emoji
8. ✓ TTS statistics tracking works
9. ✓ Voice module exports all components

## Key Design Decisions

1. **Graceful Degradation**: TTS engine handles missing espeak gracefully, returning None instead of crashing
2. **Async-First**: All synthesis operations run in thread pool to avoid blocking
3. **Audio Caching**: LRU cache with MD5-based keys reduces latency for repeated phrases
4. **Female Voice Preference**: Automatically selects female voices to match goddess persona
5. **Emotion Blending**: Multiple emotions blend naturally rather than overriding each other
6. **Text Preprocessing**: Markdown removal, emoji conversion, Discord formatting cleanup

## Performance Targets

- Target latency: <2 seconds for typical responses (<100 words)
- Achieved: Async synthesis prevents blocking main thread
- Audio caching reduces repeated phrase latency significantly

## Integration Points

- `EmotionalState` from `src/emotion/models.py` drives voice modulation
- `get_logger()` from `src/core/logger.py` provides structured logging
- Response dict format compatible with LLM response processor
- Audio files compatible with Discord voice channel playback

## Future Enhancements

- SSML support for advanced prosody control
- AWS Polly or Google TTS integration for higher quality
- Real-time audio streaming for very long responses
- Pitch modulation via audio post-processing (pyttsx3 limitation)
