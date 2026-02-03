"""Voice Activity Detection (VAD) module for Demi.

Uses webrtcvad to detect speech in audio streams with configurable
aggressiveness and frame-based processing.
"""

import collections
from dataclasses import dataclass
from typing import Optional, List
import logging

import numpy as np

try:
    import webrtcvad
    HAS_WEBRTCVAD = True
except ImportError:
    HAS_WEBRTCVAD = False
    webrtcvad = None

logger = logging.getLogger(__name__)


@dataclass
class VADConfig:
    """Configuration for Voice Activity Detection.
    
    Attributes:
        aggressiveness: VAD aggressiveness level (0-3), where 0 is least
            aggressive (more false positives) and 3 is most aggressive
            (more false negatives).
        frame_duration_ms: Frame duration in milliseconds. Must be 10, 20, or 30.
        padding_duration_ms: Duration of padding to add before/after speech
            segments for natural boundaries.
    """
    aggressiveness: int = 3
    frame_duration_ms: int = 30
    padding_duration_ms: int = 300

    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0 <= self.aggressiveness <= 3:
            raise ValueError(f"Aggressiveness must be 0-3, got {self.aggressiveness}")
        if self.frame_duration_ms not in (10, 20, 30):
            raise ValueError(
                f"Frame duration must be 10, 20, or 30 ms, got {self.frame_duration_ms}"
            )


class SpeechBuffer:
    """Ring buffer for streaming VAD with speech segment detection.
    
    Maintains a rolling buffer of audio frames and detects complete
    speech segments based on VAD results and silence detection.
    
    Attributes:
        padding_frames: Number of frames to keep as padding before/after speech.
        max_silence_frames: Maximum consecutive silence frames before segment ends.
        min_speech_frames: Minimum frames required to consider it speech.
    """

    def __init__(
        self,
        frame_duration_ms: int = 30,
        padding_duration_ms: int = 300,
        max_silence_ms: int = 500,
        min_speech_ms: int = 200,
    ):
        self.frame_duration_ms = frame_duration_ms
        self.padding_frames = padding_duration_ms // frame_duration_ms
        self.max_silence_frames = max_silence_ms // frame_duration_ms
        self.min_speech_frames = min_speech_ms // frame_duration_ms

        # Ring buffer: list of (frame_data, is_speech) tuples
        self._buffer: collections.deque = collections.deque(maxlen=1000)
        self._speech_started = False
        self._silence_counter = 0
        self._speech_frames = 0
        self._pending_segment: List[bytes] = []

    def add_frame(self, frame: bytes, is_speech: bool) -> Optional[bytes]:
        """Add an audio frame with its VAD result.
        
        Args:
            frame: Audio frame data (16-bit PCM).
            is_speech: True if frame contains speech according to VAD.
            
        Returns:
            Complete speech segment as bytes if speech ended, None otherwise.
        """
        self._buffer.append((frame, is_speech))

        if is_speech:
            self._speech_started = True
            self._silence_counter = 0
            self._speech_frames += 1
            self._pending_segment.append(frame)
        else:
            if self._speech_started:
                self._silence_counter += 1
                self._pending_segment.append(frame)

                # Check if speech segment should end
                if self._silence_counter >= self.max_silence_frames:
                    return self._finalize_segment()

        return None

    def _finalize_segment(self) -> Optional[bytes]:
        """Finalize current speech segment if long enough.
        
        Returns:
            Speech segment bytes if segment is valid, None otherwise.
        """
        if self._speech_frames >= self.min_speech_frames:
            # Include padding frames from before speech started
            result = b"".join(self._pending_segment)
            logger.debug(
                f"Speech segment finalized: {len(result)} bytes, "
                f"{self._speech_frames} speech frames"
            )
        else:
            result = None
            logger.debug(
                f"Speech segment too short ({self._speech_frames} frames), discarding"
            )

        # Reset state
        self._speech_started = False
        self._silence_counter = 0
        self._speech_frames = 0
        self._pending_segment = []

        return result

    def get_speech_segments(self) -> List[bytes]:
        """Extract all speech segments from buffer (legacy method).
        
        Returns:
            List of speech segment bytes.
        """
        segments = []
        current_segment = []
        silence_count = 0
        speech_count = 0

        for frame, is_speech in self._buffer:
            if is_speech:
                current_segment.append(frame)
                speech_count += 1
                silence_count = 0
            else:
                if current_segment:
                    silence_count += 1
                    current_segment.append(frame)

                    if silence_count >= self.max_silence_frames:
                        if speech_count >= self.min_speech_frames:
                            segments.append(b"".join(current_segment))
                        current_segment = []
                        speech_count = 0

        # Handle ongoing segment
        if speech_count >= self.min_speech_frames:
            segments.append(b"".join(current_segment))

        return segments

    def clear(self) -> None:
        """Reset the buffer and all state."""
        self._buffer.clear()
        self._speech_started = False
        self._silence_counter = 0
        self._speech_frames = 0
        self._pending_segment = []

    @property
    def is_speech_active(self) -> bool:
        """True if currently in an active speech segment."""
        return self._speech_started


class VoiceActivityDetector:
    """Voice Activity Detection using webrtcvad.
    
    Detects speech in audio frames with configurable aggressiveness.
    Supports streaming audio processing with speech buffer management.
    
    Attributes:
        config: VADConfig instance with detection parameters.
        vad: Underlying webrtcvad.Vad instance.
    """

    # Valid sample rates for webrtcvad
    VALID_SAMPLE_RATES = (8000, 16000, 32000, 48000)

    def __init__(self, config: Optional[VADConfig] = None):
        """Initialize VAD with configuration.
        
        Args:
            config: VADConfig instance, or None for defaults.
            
        Raises:
            ImportError: If webrtcvad is not installed.
            ValueError: If VAD initialization fails.
        """
        if not HAS_WEBRTCVAD:
            raise ImportError(
                "webrtcvad is required for voice activity detection. "
                "Install with: pip install webrtcvad>=2.0.10"
            )

        self.config = config or VADConfig()
        self.vad = webrtcvad.Vad(self.config.aggressiveness)

        logger.debug(
            f"VAD initialized with aggressiveness={self.config.aggressiveness}, "
            f"frame_duration={self.config.frame_duration_ms}ms"
        )

    def is_speech(self, audio_frame: bytes, sample_rate: int) -> bool:
        """Check if audio frame contains speech.
        
        Args:
            audio_frame: Audio data in 16-bit PCM format.
            sample_rate: Sample rate in Hz (8000, 16000, 32000, or 48000).
            
        Returns:
            True if frame contains speech, False otherwise.
            
        Raises:
            ValueError: If audio format is invalid.
        """
        self._validate_audio_format(audio_frame, sample_rate)

        try:
            is_speech = self.vad.is_speech(audio_frame, sample_rate)
            logger.debug(f"VAD decision: {is_speech} (frame size: {len(audio_frame)} bytes)")
            return is_speech
        except Exception as e:
            logger.warning(f"VAD processing error: {e}")
            return False

    def process_stream(
        self,
        audio_frames: List[bytes],
        sample_rate: int,
    ) -> List[tuple[bytes, bool]]:
        """Process multiple frames and return VAD results.
        
        Args:
            audio_frames: List of audio frame bytes.
            sample_rate: Sample rate in Hz.
            
        Returns:
            List of (frame, is_speech) tuples.
        """
        results = []
        for frame in audio_frames:
            try:
                is_speech = self.is_speech(frame, sample_rate)
                results.append((frame, is_speech))
            except ValueError as e:
                logger.warning(f"Skipping invalid frame: {e}")
                results.append((frame, False))
        return results

    def create_buffer(
        self,
        padding_duration_ms: Optional[int] = None,
        max_silence_ms: int = 500,
        min_speech_ms: int = 200,
    ) -> SpeechBuffer:
        """Create a new speech buffer for streaming VAD.
        
        Args:
            padding_duration_ms: Padding in ms, or None to use config default.
            max_silence_ms: Maximum silence before segment ends.
            min_speech_ms: Minimum speech duration for valid segment.
            
        Returns:
            Configured SpeechBuffer instance.
        """
        padding = padding_duration_ms or self.config.padding_duration_ms
        return SpeechBuffer(
            frame_duration_ms=self.config.frame_duration_ms,
            padding_duration_ms=padding,
            max_silence_ms=max_silence_ms,
            min_speech_ms=min_speech_ms,
        )

    def _validate_audio_format(self, audio_data: bytes, sample_rate: int) -> None:
        """Validate audio format meets webrtcvad requirements.
        
        Args:
            audio_data: Audio frame bytes.
            sample_rate: Sample rate in Hz.
            
        Raises:
            ValueError: If format is invalid.
        """
        if sample_rate not in self.VALID_SAMPLE_RATES:
            raise ValueError(
                f"Invalid sample rate {sample_rate}. "
                f"Must be one of {self.VALID_SAMPLE_RATES}"
            )

        # Calculate expected frame size: sample_rate * duration_ms / 1000 * 2 bytes (16-bit)
        expected_size = int(
            sample_rate * self.config.frame_duration_ms / 1000 * 2
        )

        if len(audio_data) != expected_size:
            raise ValueError(
                f"Invalid frame size: {len(audio_data)} bytes. "
                f"Expected {expected_size} bytes for {sample_rate}Hz, "
                f"{self.config.frame_duration_ms}ms frame."
            )


def validate_audio_format(audio_data: bytes, sample_rate: int, frame_duration_ms: int = 30) -> bool:
    """Validate audio format for VAD processing.
    
    Args:
        audio_data: Audio frame bytes.
        sample_rate: Sample rate in Hz.
        frame_duration_ms: Frame duration in ms (10, 20, or 30).
        
    Returns:
        True if format is valid, False otherwise.
    """
    if sample_rate not in VoiceActivityDetector.VALID_SAMPLE_RATES:
        return False
    if frame_duration_ms not in (10, 20, 30):
        return False

    expected_size = int(sample_rate * frame_duration_ms / 1000 * 2)
    return len(audio_data) == expected_size


def normalize_audio(audio_data: bytes) -> bytes:
    """Normalize audio data to 16-bit PCM format.
    
    Args:
        audio_data: Input audio bytes (any format).
        
    Returns:
        16-bit PCM audio bytes.
    """
    # If already bytes, assume it's 16-bit PCM
    if isinstance(audio_data, bytes):
        return audio_data

    # Convert numpy array to 16-bit PCM bytes
    if isinstance(audio_data, np.ndarray):
        # Ensure int16 format
        if audio_data.dtype != np.int16:
            # Normalize to int16 range
            if audio_data.dtype in (np.float32, np.float64):
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                audio_data = audio_data.astype(np.int16)
        return audio_data.tobytes()

    raise ValueError(f"Unsupported audio data type: {type(audio_data)}")
