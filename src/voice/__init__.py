"""Voice I/O module for Demi.

Provides Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities
for voice channel interactions.
"""

# STT components (Phase 08-01)
from src.voice.stt import (
    SpeechToText,
    TranscriptionResult,
    FasterWhisperSTT,
    FasterWhisperWord,
    FasterWhisperSegment,
    STTStats,
)
from src.voice.audio_capture import AudioCapture, AudioConfig
from src.voice.vad import VoiceActivityDetector, VADConfig

# TTS components
from src.voice.tts import TextToSpeech, TTSConfig
from src.voice.emotion_voice import EmotionVoiceMapper, VoiceParameters

# Piper TTS (optional)
try:
    from src.voice.piper_tts import PiperTTS, PiperTTSConfig, PIPER_AVAILABLE, PIPER_VOICE_REGISTRY, download_voice
except ImportError:
    PIPER_AVAILABLE = False
    PiperTTS = None
    PiperTTSConfig = None
    PIPER_VOICE_REGISTRY = None
    download_voice = None

__all__ = [
    # Original STT
    "SpeechToText",
    "TranscriptionResult",
    # Faster-whisper optimized STT
    "FasterWhisperSTT",
    "FasterWhisperWord",
    "FasterWhisperSegment",
    "STTStats",
    # Audio
    "AudioCapture",
    "AudioConfig",
    # VAD
    "VoiceActivityDetector",
    "VADConfig",
    # TTS
    "TextToSpeech",
    "TTSConfig",
    "EmotionVoiceMapper",
    "VoiceParameters",
    # Piper
    "PiperTTS",
    "PiperTTSConfig",
    "PIPER_AVAILABLE",
    "PIPER_VOICE_REGISTRY",
    "download_voice",
]
