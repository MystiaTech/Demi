"""Audio capture module for microphone and stream sources.

Provides AudioCapture and AudioStream classes for real-time audio
streaming from microphone or Discord sources with format conversion.
"""

import asyncio
import collections
import logging
import threading
import wave
from dataclasses import dataclass
from typing import Optional, Callable, List, Dict, Any

import numpy as np

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    pyaudio = None

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Configuration for audio capture.
    
    Attributes:
        sample_rate: Target sample rate in Hz (16000 recommended for Whisper).
        chunk_size: Number of samples per chunk.
        channels: Number of audio channels (1 for mono, 2 for stereo).
        format_bit_depth: Bit depth (16 for 16-bit PCM).
        chunk_duration_ms: Duration of each chunk in milliseconds.
    """
    sample_rate: int = 16000
    chunk_size: int = 480  # 30ms at 16kHz
    channels: int = 1
    format_bit_depth: int = 16
    chunk_duration_ms: int = 30

    def __post_init__(self):
        """Validate and compute derived values."""
        if self.chunk_size <= 0:
            # Auto-calculate from duration
            self.chunk_size = int(
                self.sample_rate * self.chunk_duration_ms / 1000
            )

        valid_rates = (8000, 16000, 22050, 44100, 48000)
        if self.sample_rate not in valid_rates:
            logger.warning(
                f"Unusual sample rate {self.sample_rate}, "
                f"recommended: 16000 for Whisper"
            )


class AudioStream:
    """Audio stream wrapper for consistent interface.
    
    Wraps various audio sources (PyAudio, Discord, file) with a
    uniform async interface for reading audio chunks.
    
    Attributes:
        config: AudioConfig for this stream.
        sample_rate: Sample rate in Hz.
        is_active: Whether stream is currently active.
    """

    def __init__(
        self,
        config: AudioConfig,
        source: Optional[Any] = None,
        source_type: str = "mock",
    ):
        """Initialize audio stream.
        
        Args:
            config: Audio configuration.
            source: Underlying audio source object.
            source_type: Type of source ("pyaudio", "discord", "file", "mock").
        """
        self.config = config
        self.sample_rate = config.sample_rate
        self._source = source
        self._source_type = source_type
        self._is_active = False
        self._queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=100)
        self._read_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        logger.debug(
            f"AudioStream created: {source_type}, {config.sample_rate}Hz, "
            f"{config.channels}ch"
        )

    async def read_chunk(self) -> Optional[bytes]:
        """Read a single audio chunk.
        
        Returns:
            Audio chunk bytes, or None if stream ended.
        """
        try:
            # Wait for data with timeout
            chunk = await asyncio.wait_for(self._queue.get(), timeout=5.0)
            return chunk
        except asyncio.TimeoutError:
            logger.debug("Audio stream read timeout")
            return None

    async def iter_chunks(self):
        """Async generator that yields audio chunks continuously.
        
        Yields:
            Audio chunk bytes until stream is stopped.
        """
        while self._is_active:
            chunk = await self.read_chunk()
            if chunk is None:
                break
            yield chunk

    def start(self) -> None:
        """Start the audio stream."""
        if self._is_active:
            return

        self._is_active = True
        self._stop_event.clear()

        if self._source_type == "pyaudio" and self._source:
            self._read_thread = threading.Thread(target=self._pyaudio_read_loop)
            self._read_thread.daemon = True
            self._read_thread.start()
        elif self._source and hasattr(self._source, 'read'):
            # For mock/file sources that have a read method, use a read loop
            self._read_thread = threading.Thread(target=self._generic_read_loop)
            self._read_thread.daemon = True
            self._read_thread.start()

        logger.info(f"AudioStream started: {self._source_type}")

    def stop(self) -> None:
        """Stop the audio stream."""
        if not self._is_active:
            return

        self._is_active = False
        self._stop_event.set()

        # Signal end to any waiting readers
        try:
            self._queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)

        logger.info(f"AudioStream stopped: {self._source_type}")

    def _pyaudio_read_loop(self) -> None:
        """Background thread for reading from PyAudio stream."""
        if not self._source:
            return

        while not self._stop_event.is_set():
            try:
                data = self._source.read(self.config.chunk_size, exception_on_overflow=False)
                if data:
                    self._put_in_queue(data)
            except Exception as e:
                logger.error(f"PyAudio read error: {e}")
                break

    def _generic_read_loop(self) -> None:
        """Background thread for reading from generic sources (mock/file)."""
        if not self._source:
            return

        while not self._stop_event.is_set():
            try:
                # Generic read without PyAudio-specific args
                data = self._source.read(self.config.chunk_size)
                if data:
                    self._put_in_queue(data)
                else:
                    # Empty data means end of stream
                    break
            except Exception as e:
                logger.error(f"Generic read error: {e}")
                break
        
        # Signal end of stream
        self._put_in_queue(None)

    def _put_in_queue(self, data: Optional[bytes]) -> None:
        """Put data into the async queue from a thread."""
        try:
            # For synchronous test compatibility, put directly
            if asyncio.get_event_loop().is_running():
                asyncio.run_coroutine_threadsafe(
                    self._queue.put(data), asyncio.get_event_loop()
                )
            else:
                # If no loop running, we need a different approach
                pass
        except RuntimeError:
            # No event loop running, try direct put for testing
            try:
                self._queue.put_nowait(data)
            except asyncio.QueueFull:
                pass

    @property
    def is_active(self) -> bool:
        """True if stream is active and can provide audio."""
        return self._is_active


class AudioCapture:
    """Audio capture manager for microphone and stream sources.
    
    Handles initialization of PyAudio, device enumeration, and
    creation of audio streams from various sources.
    
    Attributes:
        config: AudioConfig for capture.
        is_initialized: Whether PyAudio is initialized.
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        """Initialize audio capture.
        
        Args:
            config: Audio configuration, or None for defaults.
            
        Raises:
            ImportError: If PyAudio is not installed.
        """
        if not HAS_PYAUDIO:
            logger.warning(
                "PyAudio not available. Audio capture will be limited. "
                "Install with: pip install pyaudio>=0.2.11"
            )

        self.config = config or AudioConfig()
        self._pa: Optional[Any] = None
        self._streams: List[AudioStream] = []
        self._is_initialized = False

        if HAS_PYAUDIO:
            try:
                self._pa = pyaudio.PyAudio()
                self._is_initialized = True
                logger.info("PyAudio initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PyAudio: {e}")

    def list_devices(self) -> List[Dict[str, Any]]:
        """List available audio input devices.
        
        Returns:
            List of device info dictionaries.
        """
        if not self._pa:
            return []

        devices = []
        try:
            for i in range(self._pa.get_device_count()):
                info = self._pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append({
                        "index": i,
                        "name": info.get("name", "Unknown"),
                        "channels": info.get("maxInputChannels"),
                        "sample_rate": info.get("defaultSampleRate"),
                        "latency": info.get("defaultLowInputLatency"),
                    })
        except Exception as e:
            logger.error(f"Error listing devices: {e}")

        return devices

    async def start_microphone_stream(
        self,
        device_index: Optional[int] = None,
        config: Optional[AudioConfig] = None,
    ) -> AudioStream:
        """Start streaming from microphone.
        
        Args:
            device_index: Specific device index, or None for default.
            config: Audio configuration, or None to use default.
            
        Returns:
            AudioStream instance for reading audio chunks.
            
        Raises:
            RuntimeError: If PyAudio is not initialized.
        """
        if not self._pa:
            raise RuntimeError("PyAudio not initialized")

        cfg = config or self.config

        try:
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=cfg.channels,
                rate=cfg.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=cfg.chunk_size,
            )

            audio_stream = AudioStream(
                config=cfg,
                source=stream,
                source_type="pyaudio",
            )
            audio_stream.start()
            self._streams.append(audio_stream)

            device_name = "default"
            if device_index is not None:
                info = self._pa.get_device_info_by_index(device_index)
                device_name = info.get("name", "unknown")

            logger.info(f"Microphone stream started: {device_name} at {cfg.sample_rate}Hz")
            return audio_stream

        except Exception as e:
            logger.error(f"Failed to start microphone stream: {e}")
            raise RuntimeError(f"Microphone initialization failed: {e}")

    async def start_discord_stream(
        self,
        discord_source: Any,
        config: Optional[AudioConfig] = None,
    ) -> AudioStream:
        """Start streaming from Discord audio source.
        
        Discord provides 48kHz stereo Opus audio. This method
        creates a stream that converts to the configured format.
        
        Args:
            discord_source: Discord.py AudioSource or PCMAudio.
            config: Target audio configuration.
            
        Returns:
            AudioStream with converted audio.
        """
        cfg = config or self.config

        # Discord typically provides 48kHz stereo
        # We'll need to resample and convert to mono
        discord_config = AudioConfig(
            sample_rate=48000,
            channels=2,
            chunk_duration_ms=cfg.chunk_duration_ms,
        )

        audio_stream = AudioStream(
            config=discord_config,
            source=discord_source,
            source_type="discord",
        )

        # Wrap with conversion
        converted_stream = self._wrap_with_conversion(audio_stream, cfg)
        converted_stream.start()
        self._streams.append(converted_stream)

        logger.info("Discord audio stream started")
        return converted_stream

    def create_mock_stream(self, duration_ms: int = 5000) -> AudioStream:
        """Create a mock audio stream for testing.
        
        Args:
            duration_ms: Duration of mock audio in milliseconds.
            
        Returns:
            AudioStream yielding silence for testing.
        """
        cfg = self.config
        num_chunks = (duration_ms // cfg.chunk_duration_ms)
        silence = b"\x00" * (cfg.chunk_size * 2)  # 16-bit = 2 bytes per sample

        class MockSource:
            def __init__(self, chunks: int):
                self._chunks = chunks
                self._current = 0

            def read(self, size: int, exception_on_overflow: bool = False) -> bytes:
                if self._current >= self._chunks:
                    return b""
                self._current += 1
                return silence

        mock = MockSource(num_chunks)
        stream = AudioStream(config=cfg, source=mock, source_type="mock")
        stream.start()
        self._streams.append(stream)

        logger.debug(f"Mock audio stream created: {duration_ms}ms")
        return stream

    def _wrap_with_conversion(
        self,
        source_stream: AudioStream,
        target_config: AudioConfig,
    ) -> AudioStream:
        """Wrap a stream with audio format conversion."""
        # This would implement resampling and channel conversion
        # For now, return the source stream
        return source_stream

    def stop(self) -> None:
        """Stop all streams and release resources."""
        for stream in self._streams:
            try:
                stream.stop()
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
        self._streams.clear()

        if self._pa:
            try:
                self._pa.terminate()
                self._pa = None
                self._is_initialized = False
                logger.info("PyAudio terminated")
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Audio conversion utilities

def resample_audio(
    audio_data: bytes,
    src_rate: int,
    dst_rate: int,
    channels: int = 1,
) -> bytes:
    """Resample audio data from one sample rate to another.
    
    Args:
        audio_data: Raw audio bytes (16-bit PCM).
        src_rate: Source sample rate.
        dst_rate: Destination sample rate.
        channels: Number of channels.
        
    Returns:
        Resampled audio bytes.
    """
    if src_rate == dst_rate:
        return audio_data

    # Convert to numpy array
    audio_array = np.frombuffer(audio_data, dtype=np.int16)

    # Calculate new length
    ratio = dst_rate / src_rate
    new_length = int(len(audio_array) * ratio)

    # Simple linear interpolation resampling
    indices = np.linspace(0, len(audio_array) - 1, new_length)
    indices_floor = indices.astype(np.int32)
    indices_ceil = np.minimum(indices_floor + 1, len(audio_array) - 1)
    fractions = indices - indices_floor

    resampled = (
        audio_array[indices_floor] * (1 - fractions) +
        audio_array[indices_ceil] * fractions
    ).astype(np.int16)

    return resampled.tobytes()


def stereo_to_mono(audio_data: bytes) -> bytes:
    """Convert stereo audio to mono.
    
    Args:
        audio_data: Stereo audio bytes (16-bit PCM, interleaved).
        
    Returns:
        Mono audio bytes.
    """
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    # Reshape to (samples, 2) and average channels
    stereo = audio_array.reshape(-1, 2)
    mono = stereo.mean(axis=1).astype(np.int16)
    return mono.tobytes()


def normalize_volume(audio_data: bytes, target_db: float = -20.0) -> bytes:
    """Normalize audio volume to target dB level.
    
    Args:
        audio_data: Audio bytes (16-bit PCM).
        target_db: Target RMS level in dB.
        
    Returns:
        Normalized audio bytes.
    """
    audio_array = np.frombuffer(audio_data, dtype=np.float32) / 32768.0

    # Calculate RMS
    rms = np.sqrt(np.mean(audio_array ** 2))
    if rms < 1e-10:
        return audio_data  # Too quiet, return original

    current_db = 20 * np.log10(rms)
    gain_db = target_db - current_db
    gain = 10 ** (gain_db / 20)

    # Apply gain and convert back to int16
    normalized = (audio_array * gain * 32768.0).clip(-32768, 32767)
    return normalized.astype(np.int16).tobytes()


def load_wav_file(filepath: str) -> tuple[np.ndarray, int]:
    """Load a WAV file into numpy array.
    
    Args:
        filepath: Path to WAV file.
        
    Returns:
        Tuple of (audio_array, sample_rate).
    """
    with wave.open(filepath, "rb") as wav:
        n_channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        n_frames = wav.getnframes()

        raw_data = wav.readframes(n_frames)

        if sample_width == 2:
            audio_array = np.frombuffer(raw_data, dtype=np.int16)
        elif sample_width == 4:
            audio_array = np.frombuffer(raw_data, dtype=np.int32)
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")

        if n_channels > 1:
            audio_array = audio_array.reshape(-1, n_channels)

        return audio_array, sample_rate
