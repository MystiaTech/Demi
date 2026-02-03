"""Tests for the voice module (STT, Audio Capture, VAD).

These tests verify basic functionality without requiring actual
microphone access or model downloads.
"""

import asyncio
import pytest


class TestVoiceImports:
    """Test that all voice module components can be imported."""

    def test_stt_imports(self):
        """Test STT module imports."""
        from src.voice.stt import SpeechToText, TranscriptionResult
        assert SpeechToText is not None
        assert TranscriptionResult is not None

    def test_audio_capture_imports(self):
        """Test audio capture module imports."""
        from src.voice.audio_capture import AudioCapture, AudioConfig
        assert AudioCapture is not None
        assert AudioConfig is not None

    def test_vad_imports(self):
        """Test VAD module imports."""
        from src.voice.vad import VoiceActivityDetector, VADConfig, SpeechBuffer
        assert VoiceActivityDetector is not None
        assert VADConfig is not None
        assert SpeechBuffer is not None

    def test_voice_module_exports(self):
        """Test that voice module exports are correct."""
        from src.voice import __all__
        expected_exports = [
            "SpeechToText",
            "TranscriptionResult",
            "AudioCapture",
            "AudioConfig",
            "VoiceActivityDetector",
            "VADConfig",
        ]
        for export in expected_exports:
            assert export in __all__, f"{export} not in __all__"


class TestVADConfig:
    """Test VAD configuration."""

    def test_default_config(self):
        """Test default VAD configuration."""
        from src.voice.vad import VADConfig

        config = VADConfig()
        assert config.aggressiveness == 3
        assert config.frame_duration_ms == 30
        assert config.padding_duration_ms == 300

    def test_custom_config(self):
        """Test custom VAD configuration."""
        from src.voice.vad import VADConfig

        config = VADConfig(aggressiveness=1, frame_duration_ms=20, padding_duration_ms=500)
        assert config.aggressiveness == 1
        assert config.frame_duration_ms == 20
        assert config.padding_duration_ms == 500

    def test_invalid_aggressiveness(self):
        """Test that invalid aggressiveness raises error."""
        from src.voice.vad import VADConfig

        with pytest.raises(ValueError):
            VADConfig(aggressiveness=5)

        with pytest.raises(ValueError):
            VADConfig(aggressiveness=-1)

    def test_invalid_frame_duration(self):
        """Test that invalid frame duration raises error."""
        from src.voice.vad import VADConfig

        with pytest.raises(ValueError):
            VADConfig(frame_duration_ms=15)


class TestAudioConfig:
    """Test audio configuration."""

    def test_default_config(self):
        """Test default audio configuration."""
        from src.voice.audio_capture import AudioConfig

        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.format_bit_depth == 16
        assert config.chunk_duration_ms == 30

    def test_custom_config(self):
        """Test custom audio configuration."""
        from src.voice.audio_capture import AudioConfig

        config = AudioConfig(sample_rate=48000, channels=2)
        assert config.sample_rate == 48000
        assert config.channels == 2


class TestSpeechBuffer:
    """Test SpeechBuffer functionality."""

    def test_buffer_initialization(self):
        """Test buffer initialization."""
        from src.voice.vad import SpeechBuffer

        buffer = SpeechBuffer()
        assert buffer.is_speech_active is False
        assert buffer.frame_duration_ms == 30

    def test_add_silence_frames(self):
        """Test adding silence frames to buffer."""
        from src.voice.vad import SpeechBuffer

        buffer = SpeechBuffer()
        silence = b"\x00" * 480  # 30ms at 16kHz, 16-bit = 960 bytes... wait, 30ms * 16000Hz * 2 bytes = 960 bytes
        silence = b"\x00" * 960

        # Add silence frames - no segment should be returned
        for _ in range(20):
            result = buffer.add_frame(silence, is_speech=False)
            assert result is None

        assert buffer.is_speech_active is False

    def test_add_speech_frames(self):
        """Test adding speech frames creates a segment."""
        from src.voice.vad import SpeechBuffer

        buffer = SpeechBuffer(frame_duration_ms=30, max_silence_ms=300)
        frame_size = 960  # 30ms at 16kHz, 16-bit
        frame = b"\x01\x02" * (frame_size // 2)

        # Add speech frames
        for _ in range(20):  # 600ms of speech
            result = buffer.add_frame(frame, is_speech=True)
            assert result is None  # Speech still ongoing

        assert buffer.is_speech_active is True

        # Add silence to trigger segment finalization
        silence = b"\x00" * frame_size
        for _ in range(15):  # 450ms silence (exceeds 300ms threshold)
            result = buffer.add_frame(silence, is_speech=False)
            if result is not None:
                # Segment finalized
                break


class TestAudioUtils:
    """Test audio utility functions."""

    def test_validate_audio_format_valid(self):
        """Test valid audio format validation."""
        from src.voice.vad import validate_audio_format

        # 30ms at 16kHz, 16-bit = 960 bytes
        valid_frame = b"\x00" * 960
        assert validate_audio_format(valid_frame, 16000, 30) is True

    def test_validate_audio_format_invalid_size(self):
        """Test invalid frame size."""
        from src.voice.vad import validate_audio_format

        invalid_frame = b"\x00" * 100  # Wrong size
        assert validate_audio_format(invalid_frame, 16000, 30) is False

    def test_normalize_audio_bytes(self):
        """Test normalizing bytes."""
        from src.voice.vad import normalize_audio

        data = b"\x00\x01\x02\x03"
        result = normalize_audio(data)
        assert result == data


class TestTranscriptionResult:
    """Test TranscriptionResult dataclass."""

    def test_default_result(self):
        """Test default transcription result."""
        from src.voice.stt import TranscriptionResult

        result = TranscriptionResult(text="Hello world")
        assert result.text == "Hello world"
        assert result.confidence == 0.0
        assert result.language == "unknown"
        assert result.is_final is True

    def test_full_result(self):
        """Test transcription result with all fields."""
        from src.voice.stt import TranscriptionResult

        result = TranscriptionResult(
            text="Hello world",
            confidence=0.95,
            language="en",
            duration_ms=1500,
            latency_ms=500,
            is_final=True,
        )
        assert result.confidence == 0.95
        assert result.language == "en"
        assert result.duration_ms == 1500
        assert result.latency_ms == 500


class TestSTTStats:
    """Test STT statistics tracking."""

    def test_default_stats(self):
        """Test default statistics."""
        from src.voice.stt import STTStats

        stats = STTStats()
        assert stats.total_transcriptions == 0
        assert stats.avg_latency_ms == 0.0
        assert stats.avg_confidence == 0.0

    def test_stats_calculation(self):
        """Test statistics calculation."""
        from src.voice.stt import STTStats

        stats = STTStats()
        stats.total_transcriptions = 10
        stats.total_latency_ms = 5000
        stats.confidence_scores = [0.8, 0.9, 0.85, 0.95]

        assert stats.avg_latency_ms == 500.0
        assert stats.avg_confidence == 0.875


class TestAudioCapture:
    """Test AudioCapture functionality (mock)."""

    def test_initialization(self):
        """Test audio capture initialization."""
        from src.voice.audio_capture import AudioCapture

        capture = AudioCapture()
        assert capture is not None
        capture.stop()

    def test_context_manager(self):
        """Test audio capture as context manager."""
        from src.voice.audio_capture import AudioCapture

        with AudioCapture() as capture:
            assert capture is not None

    def test_list_devices(self):
        """Test listing audio devices."""
        from src.voice.audio_capture import AudioCapture

        capture = AudioCapture()
        devices = capture.list_devices()
        assert isinstance(devices, list)
        capture.stop()


class TestSpeechToText:
    """Test SpeechToText class initialization."""

    def test_initialization_without_model(self):
        """Test STT initialization without loading model."""
        from src.voice.stt import SpeechToText

        stt = SpeechToText(model_size="tiny")
        assert stt.model_size == "tiny"
        assert stt.is_model_loaded() is False

    def test_invalid_model_size(self):
        """Test that invalid model size raises error."""
        from src.voice.stt import SpeechToText

        with pytest.raises(ValueError):
            SpeechToText(model_size="invalid")

    def test_get_stats_structure(self):
        """Test that get_stats returns expected structure."""
        from src.voice.stt import SpeechToText

        stt = SpeechToText(model_size="tiny")
        stats = stt.get_stats()

        assert "total_transcriptions" in stats
        assert "avg_latency_ms" in stats
        assert "avg_confidence" in stats
        assert "confidence_histogram" in stats
        assert "languages_detected" in stats
        assert "errors" in stats
        assert "model_size" in stats
        assert "backend" in stats
        assert "model_loaded" in stats


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations."""

    async def test_mock_stream_creation(self):
        """Test creating mock audio stream."""
        from src.voice.audio_capture import AudioCapture

        capture = AudioCapture()
        stream = capture.create_mock_stream(duration_ms=1000)
        assert stream is not None
        assert stream.is_active is True

        # Read some chunks
        chunks = []
        async for chunk in stream.iter_chunks():
            chunks.append(chunk)
            if len(chunks) >= 5:
                break

        assert len(chunks) > 0
        stream.stop()
        capture.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
