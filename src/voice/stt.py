"""Speech-to-Text engine with Whisper backend for Demi.

Provides real-time speech recognition using faster-whisper or openai-whisper
with Voice Activity Detection (VAD) integration for efficient processing.
"""

import asyncio
import io
import time
import wave
from dataclasses import dataclass, field
from typing import Optional, Callable, AsyncGenerator, Dict, List, Any, Tuple
import logging

import numpy as np

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False
    WhisperModel = None

try:
    import whisper
    HAS_OPENAI_WHISPER = True
except ImportError:
    HAS_OPENAI_WHISPER = False
    whisper = None

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None

from src.voice.vad import VoiceActivityDetector, VADConfig, SpeechBuffer
from src.voice.audio_capture import AudioCapture, AudioConfig, AudioStream

logger = logging.getLogger(__name__)


def _detect_cuda_device() -> Tuple[str, int]:
    """Detect CUDA device and return (device, num_workers).
    
    Returns:
        Tuple of (device_str, num_workers)
    """
    if HAS_TORCH and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0).lower()
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        logger.info(f"CUDA detected: {gpu_name} ({vram_gb:.1f}GB VRAM)")
        return "cuda", 1
    return "cpu", 1


@dataclass
class TranscriptionResult:
    """Result of a speech transcription.
    
    Attributes:
        text: Transcribed text.
        confidence: Confidence score (0.0-1.0).
        language: Detected language code (e.g., "en", "es").
        duration_ms: Audio duration in milliseconds.
        latency_ms: End-to-end processing latency in milliseconds.
        is_final: True if this is a complete utterance.
    """
    text: str
    confidence: float = 0.0
    language: str = "unknown"
    duration_ms: int = 0
    latency_ms: int = 0
    is_final: bool = True


@dataclass
class STTStats:
    """Statistics for STT performance tracking.
    
    Attributes:
        total_transcriptions: Total number of transcriptions processed.
        total_latency_ms: Cumulative latency for average calculation.
        confidence_scores: List of confidence scores for histogram.
        languages_detected: Dict of language codes to count.
        errors: Number of errors encountered.
    """
    total_transcriptions: int = 0
    total_latency_ms: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    languages_detected: Dict[str, int] = field(default_factory=dict)
    errors: int = 0

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        if self.total_transcriptions == 0:
            return 0.0
        return self.total_latency_ms / self.total_transcriptions

    @property
    def avg_confidence(self) -> float:
        """Average confidence score."""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores) / len(self.confidence_scores)


class SpeechToText:
    """Speech-to-Text engine using Whisper backend.
    
    Integrates VAD for efficient speech detection and provides both
    file-based and streaming transcription capabilities.
    
    Attributes:
        model: Loaded Whisper model.
        vad: VoiceActivityDetector instance.
        capture: AudioCapture instance.
        stats: STTStats for performance tracking.
    """

    # Model size options: tiny, base, small, medium, large
    MODEL_SIZES = ("tiny", "base", "small", "medium", "large")

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        language: Optional[str] = None,
        vad_aggressiveness: int = 3,
    ):
        """Initialize SpeechToText engine.
        
        Args:
            model_size: Whisper model size (tiny/base/small/medium/large).
            device: Device to use ("cpu", "cuda", or "auto").
            compute_type: Computation type ("int8", "int16", "float16", "float32").
            language: Language code for transcription (None for auto-detect).
            vad_aggressiveness: VAD aggressiveness (0-3).
            
        Raises:
            ImportError: If neither faster-whisper nor openai-whisper is installed.
            ValueError: If model_size is invalid.
        """
        if model_size not in self.MODEL_SIZES:
            raise ValueError(
                f"Invalid model size: {model_size}. "
                f"Choose from {self.MODEL_SIZES}"
            )

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: Optional[Any] = None
        self._model_loaded = False
        self._backend: Optional[str] = None

        # Initialize VAD (optional - graceful degradation if not available)
        try:
            vad_config = VADConfig(aggressiveness=vad_aggressiveness)
            self.vad = VoiceActivityDetector(config=vad_config)
        except (ImportError, Exception) as e:
            logger.warning(f"VAD not available: {e}")
            self.vad = None

        # Initialize audio capture
        self.capture = AudioCapture()

        # Statistics
        self.stats = STTStats()

        logger.info(
            f"SpeechToText initialized (model={model_size}, "
            f"device={device}, backend=not_loaded)"
        )

    def load_model(self) -> bool:
        """Load the Whisper model into memory.
        
        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self._model_loaded:
            return True

        start_time = time.time()

        # Try faster-whisper first (preferred for speed)
        if HAS_FASTER_WHISPER:
            try:
                logger.info(f"Loading faster-whisper model: {self.model_size}")
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                self._backend = "faster-whisper"
                self._model_loaded = True
                load_time = (time.time() - start_time) * 1000
                logger.info(f"faster-whisper model loaded in {load_time:.0f}ms")
                return True
            except Exception as e:
                logger.error(f"Failed to load faster-whisper: {e}")

        # Fallback to openai-whisper
        if HAS_OPENAI_WHISPER:
            try:
                logger.info(f"Loading openai-whisper model: {self.model_size}")
                self._model = whisper.load_model(self.model_size)
                self._backend = "openai-whisper"
                self._model_loaded = True
                load_time = (time.time() - start_time) * 1000
                logger.info(f"openai-whisper model loaded in {load_time:.0f}ms")
                return True
            except Exception as e:
                logger.error(f"Failed to load openai-whisper: {e}")

        logger.error("No Whisper backend available. Install faster-whisper or openai-whisper.")
        return False

    def is_model_loaded(self) -> bool:
        """Check if the model is loaded and ready.
        
        Returns:
            True if model is loaded.
        """
        return self._model_loaded and self._model is not None

    async def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """Transcribe an audio file.
        
        Args:
            audio_path: Path to audio file (wav, mp3, etc.).
            
        Returns:
            TranscriptionResult with text and metadata.
        """
        if not self.is_model_loaded():
            if not self.load_model():
                return TranscriptionResult(
                    text="",
                    confidence=0.0,
                    language="error",
                    is_final=True,
                )

        start_time = time.time()

        try:
            if self._backend == "faster-whisper":
                result = await self._transcribe_faster_whisper(audio_path)
            elif self._backend == "openai-whisper":
                result = await self._transcribe_openai_whisper(audio_path)
            else:
                raise RuntimeError("No backend available")

            latency_ms = int((time.time() - start_time) * 1000)
            result.latency_ms = latency_ms

            # Update stats
            self.stats.total_transcriptions += 1
            self.stats.total_latency_ms += latency_ms
            self.stats.confidence_scores.append(result.confidence)
            self.stats.languages_detected[result.language] = \
                self.stats.languages_detected.get(result.language, 0) + 1

            logger.info(
                f"Transcribed: '{result.text[:50]}...' "
                f"({result.language}, conf={result.confidence:.2f}, "
                f"latency={latency_ms}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.stats.errors += 1
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="error",
                is_final=True,
            )

    async def transcribe_stream(
        self,
        audio_stream: AudioStream,
        callback: Optional[Callable[[TranscriptionResult], None]] = None,
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Transcribe audio stream in real-time.
        
        Uses VAD to detect speech segments and transcribes them as they complete.
        
        Args:
            audio_stream: AudioStream providing audio chunks.
            callback: Optional callback for each final transcription.
            
        Yields:
            TranscriptionResult for each detected speech segment.
        """
        if not self.is_model_loaded():
            if not self.load_model():
                logger.error("Cannot start stream transcription: model not loaded")
                return

        logger.info("Starting stream transcription")

        # Create speech buffer for VAD
        if self.vad is None:
            logger.error("Cannot start stream transcription: VAD not available")
            return
        speech_buffer = self.vad.create_buffer()

        # Process audio chunks
        async for chunk in audio_stream.iter_chunks():
            if chunk is None:
                break

            # Run VAD on chunk
            try:
                is_speech = self.vad.is_speech(chunk, audio_stream.sample_rate)
            except ValueError as e:
                logger.warning(f"VAD error: {e}")
                continue

            # Add to buffer
            segment = speech_buffer.add_frame(chunk, is_speech)

            if segment:
                # Speech segment complete, transcribe it
                result = await self._transcribe_audio_bytes(segment, audio_stream.sample_rate)

                if callback:
                    callback(result)

                if result.text.strip():  # Only yield non-empty results
                    yield result

        # Handle any remaining speech in buffer
        if speech_buffer.is_speech_active:
            remaining = speech_buffer._finalize_segment()
            if remaining:
                result = await self._transcribe_audio_bytes(remaining, audio_stream.sample_rate)
                if callback:
                    callback(result)
                if result.text.strip():
                    yield result

        logger.info("Stream transcription ended")

    async def _transcribe_faster_whisper(self, audio_path: str) -> TranscriptionResult:
        """Transcribe using faster-whisper backend."""
        segments, info = self._model.transcribe(
            audio_path,
            language=self.language,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=False,
        )

        # Collect all segments
        texts = []
        confidences = []
        for segment in segments:
            texts.append(segment.text)
            # Use avg_logprob as confidence proxy
            confidences.append(getattr(segment, "avg_logprob", -1.0))

        full_text = " ".join(texts).strip()

        # Calculate confidence from logprobs (convert to 0-1 scale)
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            # Convert logprob to confidence: sigmoid-like transformation
            confidence = 1.0 / (1.0 + np.exp(-avg_conf * 2))
        else:
            confidence = 0.0

        return TranscriptionResult(
            text=full_text,
            confidence=confidence,
            language=info.language if info else self.language or "unknown",
            is_final=True,
        )

    async def _transcribe_openai_whisper(self, audio_path: str) -> TranscriptionResult:
        """Transcribe using openai-whisper backend."""
        result = self._model.transcribe(
            audio_path,
            language=self.language,
            temperature=0.0,
            condition_on_previous_text=False,
        )

        text = result.get("text", "").strip()
        detected_language = result.get("language", self.language or "unknown")

        # Estimate confidence from no_speech_prob if available
        segments = result.get("segments", [])
        if segments:
            avg_no_speech = sum(
                seg.get("no_speech_prob", 0.5) for seg in segments
            ) / len(segments)
            confidence = 1.0 - avg_no_speech
        else:
            confidence = 0.5

        return TranscriptionResult(
            text=text,
            confidence=confidence,
            language=detected_language,
            is_final=True,
        )

    async def _transcribe_audio_bytes(
        self,
        audio_data: bytes,
        sample_rate: int,
    ) -> TranscriptionResult:
        """Transcribe raw audio bytes.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM).
            sample_rate: Sample rate in Hz.
            
        Returns:
            TranscriptionResult.
        """
        start_time = time.time()

        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            if self._backend == "faster-whisper":
                segments, info = self._model.transcribe(
                    audio_array,
                    language=self.language,
                    beam_size=5,
                    temperature=0.0,
                    condition_on_previous_text=False,
                )
                texts = [seg.text for seg in segments]
                text = " ".join(texts).strip()
                language = info.language if info else self.language or "unknown"

            elif self._backend == "openai-whisper":
                # openai-whisper requires file path or mel spectrogram
                # We'll use a temporary WAV file
                text, language = await self._transcribe_via_temp_file(
                    audio_data, sample_rate
                )
            else:
                return TranscriptionResult(
                    text="",
                    confidence=0.0,
                    language="error",
                    is_final=True,
                )

            latency_ms = int((time.time() - start_time) * 1000)

            return TranscriptionResult(
                text=text,
                confidence=0.8,  # Default confidence for stream transcription
                language=language,
                duration_ms=len(audio_data) * 1000 // (sample_rate * 2),
                latency_ms=latency_ms,
                is_final=True,
            )

        except Exception as e:
            logger.error(f"Audio bytes transcription error: {e}")
            self.stats.errors += 1
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="error",
                is_final=True,
            )

    async def _transcribe_via_temp_file(
        self,
        audio_data: bytes,
        sample_rate: int,
    ) -> tuple[str, str]:
        """Transcribe by writing to temporary WAV file.
        
        Args:
            audio_data: Raw PCM audio bytes.
            sample_rate: Sample rate.
            
        Returns:
            Tuple of (text, language).
        """
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            # Write WAV file
            with wave.open(f, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                wav.writeframes(audio_data)

        try:
            result = self._model.transcribe(
                temp_path,
                language=self.language,
                temperature=0.0,
            )
            text = result.get("text", "").strip()
            language = result.get("language", self.language or "unknown")
            return text, language
        finally:
            os.unlink(temp_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns:
            Dictionary with statistics.
        """
        return {
            "total_transcriptions": self.stats.total_transcriptions,
            "avg_latency_ms": round(self.stats.avg_latency_ms, 2),
            "avg_confidence": round(self.stats.avg_confidence, 3),
            "confidence_histogram": self._build_confidence_histogram(),
            "languages_detected": self.stats.languages_detected.copy(),
            "errors": self.stats.errors,
            "model_size": self.model_size,
            "backend": self._backend or "not_loaded",
            "model_loaded": self._model_loaded,
        }

    def _build_confidence_histogram(self) -> Dict[str, int]:
        """Build confidence score histogram.
        
        Returns:
            Dict with confidence ranges and counts.
        """
        histogram = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }

        for score in self.stats.confidence_scores:
            if score < 0.2:
                histogram["0.0-0.2"] += 1
            elif score < 0.4:
                histogram["0.2-0.4"] += 1
            elif score < 0.6:
                histogram["0.4-0.6"] += 1
            elif score < 0.8:
                histogram["0.6-0.8"] += 1
            else:
                histogram["0.8-1.0"] += 1

        return histogram

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.stats = STTStats()
        logger.info("STT statistics reset")

    async def transcribe_microphone(
        self,
        duration_ms: int = 5000,
        device_index: Optional[int] = None,
    ) -> TranscriptionResult:
        """Record and transcribe from microphone.
        
        Args:
            duration_ms: Recording duration in milliseconds.
            device_index: Specific microphone device index.
            
        Returns:
            TranscriptionResult.
        """
        logger.info(f"Recording from microphone for {duration_ms}ms")

        # Start microphone stream
        stream = await self.capture.start_microphone_stream(device_index=device_index)

        # Collect audio data
        audio_chunks = []
        start_time = time.time()

        try:
            async for chunk in stream.iter_chunks():
                audio_chunks.append(chunk)
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms >= duration_ms:
                    break
        finally:
            stream.stop()

        # Combine and transcribe
        audio_data = b"".join(audio_chunks)
        sample_rate = stream.sample_rate

        result = await self._transcribe_audio_bytes(audio_data, sample_rate)
        return result


@dataclass
class FasterWhisperWord:
    """Word-level timestamp information.
    
    Attributes:
        text: The word text.
        start: Start time in seconds.
        end: End time in seconds.
        probability: Confidence probability for the word.
    """
    text: str
    start: float
    end: float
    probability: float


@dataclass  
class FasterWhisperSegment:
    """Segment information with word timestamps.
    
    Attributes:
        text: The segment text.
        start: Start time in seconds.
        end: End time in seconds.
        words: List of word-level timestamps (if enabled).
    """
    text: str
    start: float
    end: float
    words: List[FasterWhisperWord] = field(default_factory=list)


class FasterWhisperSTT:
    """Optimized faster-whisper STT with int8 quantization for RTX 3060.
    
    This class provides a dedicated faster-whisper backend with:
    - int8 quantization for ~50% VRAM reduction
    - Built-in VAD filtering for better accuracy
    - Word-level timestamps support
    - RTX 3060 optimizations (12GB VRAM)
    
    Attributes:
        model: Loaded faster-whisper WhisperModel.
        model_size: Size of the model being used.
        device: Device being used (cuda/cpu).
        compute_type: Quantization type (int8/int16/float16/float32).
        vad_filter: Whether VAD filtering is enabled.
        
    Example:
        >>> stt = FasterWhisperSTT(model_size="small", compute_type="int8")
        >>> result = await stt.transcribe_file("audio.wav")
        >>> print(result.text)
    """
    
    # Model size options including large-v1, large-v2, large-v3
    MODEL_SIZES = ("tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3")
    
    # Compute types supported by faster-whisper
    COMPUTE_TYPES = ("int8", "int8_float16", "int16", "float16", "float32")
    
    # RTX 3060 recommended settings
    RTX3060_RECOMMENDED = {
        "model_size": "small",  # <2s latency, good accuracy
        "compute_type": "int8",  # ~50% VRAM reduction
        "beam_size": 5,
        "vad_filter": True,
        "batch_size": 1,  # For real-time streaming
    }
    
    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        word_timestamps: bool = False,
        cpu_threads: int = 0,
        num_workers: int = 1,
        download_root: Optional[str] = None,
        local_files_only: bool = False,
    ):
        """Initialize FasterWhisperSTT engine.
        
        Args:
            model_size: Whisper model size (tiny/base/small/medium/large-v1/large-v2/large-v3).
            device: Device to use ("cpu", "cuda", or "auto" for auto-detect).
            compute_type: Computation type ("int8", "int8_float16", "int16", "float16", "float32").
                         int8 recommended for RTX 3060 (saves ~50% VRAM with minimal accuracy loss).
            language: Language code for transcription (None for auto-detect).
            beam_size: Beam size for decoding. Higher = better quality but slower. Default 5.
            vad_filter: Enable built-in VAD to filter out non-speech. Default True.
            word_timestamps: Enable word-level timestamps. Default False.
            cpu_threads: Number of CPU threads to use (0 = auto).
            num_workers: Number of parallel workers for transcription (1 for RTX 3060 streaming).
            download_root: Root directory for model downloads.
            local_files_only: If True, only use local models (no download).
            
        Raises:
            ImportError: If faster-whisper is not installed.
            ValueError: If model_size or compute_type is invalid.
        """
        if not HAS_FASTER_WHISPER:
            raise ImportError(
                "faster-whisper is required. Install with: pip install faster-whisper>=1.0.0"
            )
        
        if model_size not in self.MODEL_SIZES:
            raise ValueError(
                f"Invalid model size: {model_size}. Choose from {self.MODEL_SIZES}"
            )
            
        if compute_type not in self.COMPUTE_TYPES:
            raise ValueError(
                f"Invalid compute_type: {compute_type}. Choose from {self.COMPUTE_TYPES}"
            )
        
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.word_timestamps = word_timestamps
        self.cpu_threads = cpu_threads
        self.num_workers = num_workers
        self.download_root = download_root
        self.local_files_only = local_files_only
        
        self._model: Optional[WhisperModel] = None
        self._model_loaded = False
        
        # Auto-detect CUDA if device="auto"
        if self.device == "auto":
            self.device, self.num_workers = _detect_cuda_device()
        
        # Initialize audio capture for microphone support
        self.capture = AudioCapture()
        
        # Statistics
        self.stats = STTStats()
        
        logger.info(
            f"FasterWhisperSTT initialized (model={model_size}, "
            f"device={self.device}, compute_type={compute_type}, "
            f"vad_filter={vad_filter})"
        )
    
    @classmethod
    def for_rtx3060(
        cls,
        model_size: str = "small",
        language: Optional[str] = None,
        **kwargs
    ) -> "FasterWhisperSTT":
        """Create optimized instance for RTX 3060 (12GB VRAM).
        
        Uses int8 quantization and optimized settings for real-time performance.
        
        Args:
            model_size: Model size (default "small" for <2s latency).
            language: Language code (None for auto-detect).
            **kwargs: Additional arguments passed to constructor.
            
        Returns:
            Configured FasterWhisperSTT instance.
        """
        config = {
            **cls.RTX3060_RECOMMENDED,
            "model_size": model_size,
            "language": language,
            **kwargs,
        }
        return cls(**config)
    
    def load_model(self) -> bool:
        """Load the faster-whisper model into memory.
        
        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self._model_loaded:
            return True
        
        start_time = time.time()
        
        try:
            logger.info(
                f"Loading faster-whisper model: {self.model_size} "
                f"(device={self.device}, compute_type={self.compute_type})"
            )
            
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
                num_workers=self.num_workers,
                download_root=self.download_root,
                local_files_only=self.local_files_only,
            )
            
            self._model_loaded = True
            load_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"faster-whisper model loaded in {load_time:.0f}ms "
                f"({self.model_size}, {self.compute_type}, {self.device})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            return False
    
    def is_model_loaded(self) -> bool:
        """Check if the model is loaded and ready.
        
        Returns:
            True if model is loaded.
        """
        return self._model_loaded and self._model is not None
    
    def unload_model(self) -> None:
        """Unload the model to free VRAM."""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_loaded = False
            
            if HAS_TORCH and torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info("Model unloaded, VRAM freed")
    
    async def transcribe_file(
        self,
        audio_path: str,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe an audio file.
        
        Args:
            audio_path: Path to audio file (wav, mp3, flac, etc.).
            **kwargs: Additional arguments passed to transcribe().
            
        Returns:
            TranscriptionResult with text and metadata.
        """
        if not self.is_model_loaded():
            if not self.load_model():
                return TranscriptionResult(
                    text="",
                    confidence=0.0,
                    language="error",
                    is_final=True,
                )
        
        start_time = time.time()
        
        try:
            result = await self._transcribe_with_faster_whisper(audio_path, **kwargs)
            
            latency_ms = int((time.time() - start_time) * 1000)
            result.latency_ms = latency_ms
            
            # Update stats
            self.stats.total_transcriptions += 1
            self.stats.total_latency_ms += latency_ms
            self.stats.confidence_scores.append(result.confidence)
            self.stats.languages_detected[result.language] = \
                self.stats.languages_detected.get(result.language, 0) + 1
            
            logger.info(
                f"Transcribed: '{result.text[:50]}...' "
                f"({result.language}, conf={result.confidence:.2f}, "
                f"latency={latency_ms}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.stats.errors += 1
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="error",
                is_final=True,
            )
    
    async def _transcribe_with_faster_whisper(
        self,
        audio_input: Any,
        **kwargs
    ) -> TranscriptionResult:
        """Internal transcription using faster-whisper.
        
        Args:
            audio_input: Path to audio file or numpy array.
            **kwargs: Additional transcribe arguments.
            
        Returns:
            TranscriptionResult.
        """
        loop = asyncio.get_event_loop()
        
        # Run transcription in thread pool (faster-whisper is CPU/GPU bound)
        segments, info = await loop.run_in_executor(
            None,
            lambda: self._model.transcribe(
                audio_input,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                word_timestamps=self.word_timestamps,
                condition_on_previous_text=False,
                **kwargs
            )
        )
        
        # Collect segments
        texts = []
        confidences = []
        word_timestamps: List[FasterWhisperWord] = []
        segment_info: List[FasterWhisperSegment] = []
        
        for segment in segments:
            texts.append(segment.text)
            # Use avg_logprob as confidence proxy
            confidences.append(getattr(segment, "avg_logprob", -1.0))
            
            # Extract word timestamps if available
            if self.word_timestamps and hasattr(segment, "words"):
                segment_words = []
                for word in segment.words:
                    fw = FasterWhisperWord(
                        text=word.word if hasattr(word, "word") else str(word),
                        start=word.start if hasattr(word, "start") else 0.0,
                        end=word.end if hasattr(word, "end") else 0.0,
                        probability=getattr(word, "probability", 0.0),
                    )
                    segment_words.append(fw)
                    word_timestamps.append(fw)
                
                segment_info.append(FasterWhisperSegment(
                    text=segment.text,
                    start=segment.start,
                    end=segment.end,
                    words=segment_words,
                ))
        
        full_text = " ".join(texts).strip()
        
        # Calculate confidence from logprobs (convert to 0-1 scale)
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            # Convert logprob to confidence: sigmoid-like transformation
            confidence = 1.0 / (1.0 + np.exp(-avg_conf * 2))
        else:
            confidence = 0.0
        
        # Store segment info for potential later use
        self._last_segments = segment_info
        
        return TranscriptionResult(
            text=full_text,
            confidence=confidence,
            language=info.language if info else self.language or "unknown",
            is_final=True,
        )
    
    async def transcribe_audio_array(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe a numpy audio array.
        
        Args:
            audio_array: Numpy array of audio samples (float32, normalized -1 to 1).
            sample_rate: Sample rate of the audio (default 16000).
            **kwargs: Additional arguments passed to transcribe().
            
        Returns:
            TranscriptionResult.
        """
        start_time = time.time()
        
        if not self.is_model_loaded():
            if not self.load_model():
                return TranscriptionResult(
                    text="",
                    confidence=0.0,
                    language="error",
                    is_final=True,
                )
        
        try:
            result = await self._transcribe_with_faster_whisper(audio_array, **kwargs)
            
            latency_ms = int((time.time() - start_time) * 1000)
            result.latency_ms = latency_ms
            result.duration_ms = len(audio_array) * 1000 // sample_rate
            
            # Update stats
            self.stats.total_transcriptions += 1
            self.stats.total_latency_ms += latency_ms
            self.stats.confidence_scores.append(result.confidence)
            
            return result
            
        except Exception as e:
            logger.error(f"Audio array transcription error: {e}")
            self.stats.errors += 1
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="error",
                is_final=True,
            )
    
    async def transcribe_audio_bytes(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe raw audio bytes (16-bit PCM).
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM).
            sample_rate: Sample rate in Hz.
            **kwargs: Additional arguments passed to transcribe().
            
        Returns:
            TranscriptionResult.
        """
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        return await self.transcribe_audio_array(audio_array, sample_rate, **kwargs)
    
    async def transcribe_microphone(
        self,
        duration_ms: int = 5000,
        device_index: Optional[int] = None,
    ) -> TranscriptionResult:
        """Record and transcribe from microphone.
        
        Args:
            duration_ms: Recording duration in milliseconds.
            device_index: Specific microphone device index.
            
        Returns:
            TranscriptionResult.
        """
        logger.info(f"Recording from microphone for {duration_ms}ms")
        
        # Start microphone stream
        stream = await self.capture.start_microphone_stream(device_index=device_index)
        
        # Collect audio data
        audio_chunks = []
        start_time = time.time()
        
        try:
            async for chunk in stream.iter_chunks():
                audio_chunks.append(chunk)
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms >= duration_ms:
                    break
        finally:
            stream.stop()
        
        # Combine and transcribe
        audio_data = b"".join(audio_chunks)
        return await self.transcribe_audio_bytes(audio_data, stream.sample_rate)
    
    async def transcribe_stream(
        self,
        audio_stream: AudioStream,
        callback: Optional[Callable[[TranscriptionResult], None]] = None,
        min_speech_duration_ms: int = 250,
        max_speech_duration_s: float = 30.0,
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Transcribe audio stream in real-time with VAD.
        
        Uses built-in VAD for efficient speech detection and transcribes
        segments as they complete. Optimized for RTX 3060 with batch_size=1.
        
        Args:
            audio_stream: AudioStream providing audio chunks.
            callback: Optional callback for each final transcription.
            min_speech_duration_ms: Minimum speech duration to transcribe.
            max_speech_duration_s: Maximum segment duration before forced split.
            
        Yields:
            TranscriptionResult for each detected speech segment.
        """
        if not self.is_model_loaded():
            if not self.load_model():
                logger.error("Cannot start stream transcription: model not loaded")
                return
        
        logger.info("Starting stream transcription with VAD")
        
        # Buffer for accumulating audio
        buffer = bytearray()
        speech_active = False
        speech_start_time = 0.0
        
        async for chunk in audio_stream.iter_chunks():
            if chunk is None:
                break
            
            buffer.extend(chunk)
            buffer_duration_ms = len(buffer) * 1000 // (audio_stream.sample_rate * 2)
            
            # Check for max duration to prevent memory issues
            if buffer_duration_ms > max_speech_duration_s * 1000:
                # Force transcription of accumulated audio
                if buffer:
                    audio_array = np.frombuffer(buffer, dtype=np.int16).astype(np.float32) / 32768.0
                    result = await self.transcribe_audio_array(
                        audio_array, audio_stream.sample_rate
                    )
                    
                    if callback:
                        callback(result)
                    
                    if result.text.strip():
                        yield result
                
                buffer = bytearray()
                speech_active = False
        
        # Handle remaining audio
        if buffer:
            audio_array = np.frombuffer(buffer, dtype=np.int16).astype(np.float32) / 32768.0
            result = await self.transcribe_audio_array(audio_array, audio_stream.sample_rate)
            
            if callback:
                callback(result)
            
            if result.text.strip():
                yield result
        
        logger.info("Stream transcription ended")
    
    def get_last_word_timestamps(self) -> List[FasterWhisperWord]:
        """Get word timestamps from last transcription.
        
        Returns:
            List of FasterWhisperWord with timestamps.
        """
        segments = getattr(self, "_last_segments", [])
        words = []
        for seg in segments:
            words.extend(seg.words)
        return words
    
    def get_last_segments(self) -> List[FasterWhisperSegment]:
        """Get segment information from last transcription.
        
        Returns:
            List of FasterWhisperSegment with timing info.
        """
        return getattr(self, "_last_segments", [])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns:
            Dictionary with statistics.
        """
        return {
            "total_transcriptions": self.stats.total_transcriptions,
            "avg_latency_ms": round(self.stats.avg_latency_ms, 2),
            "avg_confidence": round(self.stats.avg_confidence, 3),
            "confidence_histogram": self._build_confidence_histogram(),
            "languages_detected": self.stats.languages_detected.copy(),
            "errors": self.stats.errors,
            "model_size": self.model_size,
            "backend": "faster-whisper",
            "compute_type": self.compute_type,
            "device": self.device,
            "model_loaded": self._model_loaded,
            "vad_filter": self.vad_filter,
            "word_timestamps": self.word_timestamps,
        }
    
    def _build_confidence_histogram(self) -> Dict[str, int]:
        """Build confidence score histogram.
        
        Returns:
            Dict with confidence ranges and counts.
        """
        histogram = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }
        
        for score in self.stats.confidence_scores:
            if score < 0.2:
                histogram["0.0-0.2"] += 1
            elif score < 0.4:
                histogram["0.2-0.4"] += 1
            elif score < 0.6:
                histogram["0.4-0.6"] += 1
            elif score < 0.8:
                histogram["0.6-0.8"] += 1
            else:
                histogram["0.8-1.0"] += 1
        
        return histogram
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.stats = STTStats()
        self._last_segments = []
        logger.info("FasterWhisperSTT statistics reset")
