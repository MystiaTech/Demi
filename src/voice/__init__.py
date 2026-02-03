"""Voice I/O module for Demi.

Provides Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities
for voice channel interactions.
"""

# STT components (Phase 08-01)
from src.voice.stt import SpeechToText, TranscriptionResult
from src.voice.audio_capture import AudioCapture, AudioConfig
from src.voice.vad import VoiceActivityDetector, VADConfig

__all__ = [
    "SpeechToText",
    "TranscriptionResult",
    "AudioCapture",
    "AudioConfig",
    "VoiceActivityDetector",
    "VADConfig",
]
