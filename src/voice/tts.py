"""
Text-to-Speech Engine for Demi supporting multiple backends.

Provides cross-platform TTS with emotional modulation, voice selection,
and audio file generation for Discord voice playback.

Backends (in order of quality/speed):
- luxtts: Best voice cloning, 48kHz, requires reference audio
- coqui: Highest quality multilingual, ~2GB model
- melotts: Good quality, emotion control, multilingual
- kokoro: Fast, lightweight (~80MB), good quality
- piper: Fast local neural TTS, medium quality
- pyttsx3: System TTS fallback, works out of the box

Target latency: <500ms for Kokoro/Piper, <2s for Coqui
"""

import asyncio
import hashlib
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from src.core.logger import get_logger
from src.emotion.models import EmotionalState
from src.voice.emotion_voice import EmotionVoiceMapper, VoiceParameters

# Import backends
from src.voice.tts_base import TTSBackendConfig

# Try to import Piper TTS
try:
    from src.voice.piper_tts import PiperTTS, PiperTTSConfig, PIPER_AVAILABLE
except ImportError:
    PIPER_AVAILABLE = False

# Try to import new backends
from src.voice.kokoro_tts import KokoroTTS, KOKORO_AVAILABLE
from src.voice.melotts_tts import MeloTTSBackend, MELO_AVAILABLE
from src.voice.coqui_tts import CoquiTTSBackend, COQUI_AVAILABLE
from src.voice.luxtts_tts import LuxTTSBackend, LUX_AVAILABLE

# Try to import pyttsx3
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

# Try to import goddess voice processor
try:
    from src.voice.goddess_voice import GoddessVoiceProcessor, GoddessVoiceConfig, LIBROSA_AVAILABLE
except ImportError:
    GoddessVoiceProcessor = None
    GoddessVoiceConfig = None
    LIBROSA_AVAILABLE = False


def _env_str(key: str, default: str) -> str:
    """Get string environment variable with default"""
    return os.getenv(key, default)


def _env_bool(key: str, default: bool) -> bool:
    """Get boolean environment variable with default"""
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes")


@dataclass
class TTSConfig:
    """Configuration for TTS engine.

    Attributes:
        backend: TTS backend ("kokoro", "melotts", "coqui", "luxtts", "piper", "pyttsx3", "auto")
        voice_id: Voice identifier (None = system default)
        rate: Words per minute or speed multiplier (default 150/1.0)
        volume: Audio level 0.0-1.0 (default 1.0)
        output_format: Audio format ("wav", "mp3")
        cache_enabled: Whether to cache audio files
        cache_dir: Directory for cached audio files
        device: Device for inference ("auto", "cpu", "cuda", "mps")
        
        # Backend-specific settings
        piper_voice: Piper voice ID (e.g., "en_US-lessac-medium")
        piper_use_gpu: Use GPU acceleration for Piper
        piper_speaker_id: Speaker ID for multi-speaker models
        
        kokoro_voice: Kokoro voice (e.g., "af_heart")
        
        melo_language: MeloTTS language code (e.g., "EN")
        melo_speaker: MeloTTS speaker ID
        
        coqui_language: Coqui TTS language (e.g., "en")
        coqui_speaker_wav: Path to speaker reference for voice cloning
        
        luxtts_reference: Path to reference audio for LuxTTS voice cloning
        luxtts_num_steps: Sampling steps (3-4 recommended)
    """

    backend: str = _env_str("TTS_BACKEND", "auto")
    voice_id: Optional[str] = None
    rate: Union[int, float] = 1.0
    volume: float = 1.0
    output_format: str = "wav"
    cache_enabled: bool = True
    cache_dir: str = "~/.demi/tts_cache"
    device: str = _env_str("TTS_DEVICE", "auto")
    
    # Piper settings
    piper_voice: str = _env_str("PIPER_VOICE", "en_US-lessac-medium")
    piper_use_gpu: bool = _env_bool("PIPER_USE_GPU", True)
    piper_speaker_id: Optional[int] = None
    
    # Kokoro settings
    kokoro_voice: str = _env_str("KOKORO_VOICE", "af_heart")
    
    # MeloTTS settings
    melo_language: str = _env_str("MELO_LANGUAGE", "EN")
    melo_speaker: str = _env_str("MELO_SPEAKER", "EN-US")
    
    # Coqui settings
    coqui_language: str = _env_str("COQUI_LANGUAGE", "en")
    coqui_speaker_wav: Optional[str] = _env_str("COQUI_SPEAKER_WAV", None)
    
    # LuxTTS settings
    luxtts_reference: Optional[str] = _env_str("LUXTTS_REFERENCE", None)
    luxtts_num_steps: int = 4

    # Goddess voice enhancement settings
    goddess_voice_enabled: bool = True
    goddess_voice_reverb_wetness: float = 0.3
    goddess_voice_pitch_shift: float = 1.5  # semitones (higher = more feminine/ethereal)
    goddess_voice_presence_db: float = 4.0


class TextToSpeech:
    """Text-to-Speech engine supporting multiple backends.

    Converts text responses to spoken audio with emotional modulation
    based on Demi's current emotional state.

    Backends (auto-select priority):
    1. Kokoro: Fast, good quality, lightweight (~80MB)
    2. Piper: Local neural TTS, medium quality
    3. pyttsx3: System TTS fallback
    
    Optional high-quality backends:
    - MeloTTS: Better quality, emotion control
    - Coqui XTTS-v2: Best quality, voice cloning, large model (~2GB)
    - LuxTTS: Best voice cloning, 48kHz output, requires reference audio

    Features:
    - Auto-detection of best available backend
    - Emotional voice modulation
    - GPU acceleration support
    - Audio caching for reduced latency
    - Async support for non-blocking operation
    """

    def __init__(self, config: Optional[TTSConfig] = None, backend: Optional[str] = None):
        """Initialize the TTS engine.

        Args:
            config: TTS configuration (uses defaults if None)
            backend: Override backend selection
        """
        self.config = config or TTSConfig()
        self.logger = get_logger()
        self.emotion_mapper = EmotionVoiceMapper()

        # Initialize goddess voice processor
        self.goddess_processor: Optional[GoddessVoiceProcessor] = None
        if self.config.goddess_voice_enabled and GoddessVoiceProcessor:
            goddess_config = GoddessVoiceConfig(
                reverb_wetness=self.config.goddess_voice_reverb_wetness,
                pitch_shift_semitones=self.config.goddess_voice_pitch_shift,
                presence_peak_db=self.config.goddess_voice_presence_db,
            )
            self.goddess_processor = GoddessVoiceProcessor(goddess_config)

        # Determine backend
        self.backend_name = backend or self.config.backend
        self._actual_backend: Optional[str] = None
        self._backend: Optional[TTSBackend] = None
        self._pending_init: bool = False  # For lazy async initialization

        # Legacy engines (for backward compatibility)
        self.piper_engine: Optional[Any] = None
        self.pyttsx3_engine = None

        # Initialize selected backend
        self._initialize_backend()

        # Setup cache directory
        if self.config.cache_enabled:
            self.cache_dir = Path(self.config.cache_dir).expanduser()
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"TTS cache directory: {self.cache_dir}")

        # Statistics tracking
        self._stats = {
            "total_utterances": 0,
            "total_latency_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "preferred_voice": self.config.voice_id,
            "backend": self._actual_backend,
        }

    def _initialize_backend(self):
        """Initialize the TTS backend based on configuration."""
        
        # Map backend names to their availability and initialization functions
        backend_map = {
            "kokoro": (KOKORO_AVAILABLE, self._try_init_kokoro),
            "melotts": (MELO_AVAILABLE, self._try_init_melotts),
            "coqui": (COQUI_AVAILABLE, self._try_init_coqui),
            "luxtts": (LUX_AVAILABLE, self._try_init_luxtts),
            "piper": (PIPER_AVAILABLE, self._try_init_piper),
            "pyttsx3": (PYTTSX3_AVAILABLE, self._try_init_pyttsx3),
        }
        
        if self.backend_name == "auto":
            # Priority order: kokoro > melotts > coqui > luxtts > piper > pyttsx3
            priority_order = ["kokoro", "melotts", "coqui", "luxtts", "piper", "pyttsx3"]
            
            for name in priority_order:
                available, init_func = backend_map.get(name, (False, None))
                if available and init_func:
                    self.logger.info(f"Auto-detecting TTS backend: trying {name}...")
                    if init_func():
                        self._actual_backend = name
                        return
            
            self.logger.error("No TTS backend available")
            self._actual_backend = None
            
        elif self.backend_name in backend_map:
            available, init_func = backend_map[self.backend_name]
            if not available:
                raise RuntimeError(f"{self.backend_name} backend requested but not installed")
            if init_func():
                self._actual_backend = self.backend_name
                return
            raise RuntimeError(f"Failed to initialize {self.backend_name} backend")
        else:
            raise RuntimeError(f"Unknown backend: {self.backend_name}")

    def _init_backend_async(self, backend, backend_name: str, init_msg: str) -> bool:
        """Helper to initialize a backend, handling both sync and async contexts.
        
        Args:
            backend: The backend instance to initialize
            backend_name: Name of the backend for logging
            init_msg: Message to log on successful initialization
            
        Returns:
            True if successful (or pending lazy init)
        """
        try:
            # Check if we're in an async context (event loop already running)
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, can't use run_until_complete
                # Initialize lazily - the first synthesis call will initialize
                self._backend = backend
                self._pending_init = True
                self.logger.info(f"{backend_name} configured (will initialize on first use)")
                return True
            except RuntimeError:
                # No event loop running, we can use run_until_complete
                asyncio.get_event_loop().run_until_complete(backend.initialize())
                
                if backend._initialized:
                    self._backend = backend
                    self.logger.info(init_msg)
                    return True
        except Exception as e:
            self.logger.warning(f"Failed to initialize {backend_name}: {e}")
        return False

    def _try_init_kokoro(self) -> bool:
        """Try to initialize Kokoro backend."""
        try:
            config = TTSBackendConfig(
                voice_id=self.config.kokoro_voice,
                rate=self.config.rate,
                volume=self.config.volume,
                cache_enabled=self.config.cache_enabled,
                cache_dir=f"{self.config.cache_dir}/kokoro",
                device=self.config.device,
            )
            backend = KokoroTTS(config)
            return self._init_backend_async(backend, "Kokoro", f"Kokoro TTS initialized (voice: {self.config.kokoro_voice})")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Kokoro: {e}")
        return False

    def _try_init_melotts(self) -> bool:
        """Try to initialize MeloTTS backend."""
        try:
            config = TTSBackendConfig(
                voice_id=self.config.melo_speaker,
                rate=self.config.rate,
                volume=self.config.volume,
                cache_enabled=self.config.cache_enabled,
                cache_dir=f"{self.config.cache_dir}/melotts",
                device=self.config.device,
                extra_settings={
                    "language": self.config.melo_language,
                    "speaker_id": self.config.melo_speaker,
                }
            )
            backend = MeloTTSBackend(config)
            return self._init_backend_async(backend, "MeloTTS", f"MeloTTS initialized (language: {self.config.melo_language})")
        except Exception as e:
            self.logger.warning(f"Failed to initialize MeloTTS: {e}")
        return False

    def _try_init_coqui(self) -> bool:
        """Try to initialize Coqui TTS backend."""
        try:
            config = TTSBackendConfig(
                voice_id=self.config.coqui_language,
                rate=self.config.rate,
                volume=self.config.volume,
                cache_enabled=self.config.cache_enabled,
                cache_dir=f"{self.config.cache_dir}/coqui",
                device=self.config.device,
                extra_settings={
                    "language": self.config.coqui_language,
                    "speaker_wav": self.config.coqui_speaker_wav,
                }
            )
            backend = CoquiTTSBackend(config)
            success = self._init_backend_async(backend, "Coqui", f"Coqui TTS initialized (language: {self.config.coqui_language})")
            if success and self.config.coqui_speaker_wav:
                self.logger.info(f"Voice cloning enabled with: {self.config.coqui_speaker_wav}")
            return success
        except Exception as e:
            self.logger.warning(f"Failed to initialize Coqui: {e}")
        return False

    def _try_init_luxtts(self) -> bool:
        """Try to initialize LuxTTS backend."""
        try:
            config = TTSBackendConfig(
                voice_id=self.config.luxtts_reference,
                rate=self.config.rate,
                volume=self.config.volume,
                cache_enabled=self.config.cache_enabled,
                cache_dir=f"{self.config.cache_dir}/luxtts",
                device=self.config.device,
                extra_settings={
                    "reference_audio": self.config.luxtts_reference,
                    "num_steps": self.config.luxtts_num_steps,
                }
            )
            backend = LuxTTSBackend(config)
            return self._init_backend_async(backend, "LuxTTS", "LuxTTS initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize LuxTTS: {e}")
        return False

    def _try_init_piper(self) -> bool:
        """Try to initialize Piper TTS backend."""
        try:
            piper_config = PiperTTSConfig(
                voice_id=self.config.piper_voice,
                rate=self.config.rate,
                volume=self.config.volume,
                use_gpu=self.config.piper_use_gpu,
                cache_enabled=self.config.cache_enabled,
                cache_dir=f"{self.config.cache_dir}/piper",
                speaker_id=self.config.piper_speaker_id,
            )
            self.piper_engine = PiperTTS(piper_config)
            
            if self.piper_engine.voice is None:
                self.logger.warning("Piper initialized but no voices available")
                voices_dir = piper_config.voices_dir
                self.logger.info(f"Run: ./scripts/download_piper_voices.sh en_US-lessac-medium")
                self.logger.info(f"Voice directory: {voices_dir}")
            
            self.logger.info(f"Piper TTS initialized (voice: {self.config.piper_voice})")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to initialize Piper: {e}")
            self.piper_engine = None
            return False

    def _try_init_pyttsx3(self) -> bool:
        """Try to initialize pyttsx3 backend."""
        try:
            self.pyttsx3_engine = pyttsx3.init()
            self._initialize_pyttsx3_properties()
            self.logger.info("pyttsx3 TTS backend initialized")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to initialize pyttsx3: {e}")
            self.pyttsx3_engine = None
            return False

    def _initialize_pyttsx3_properties(self):
        """Initialize pyttsx3 voice properties."""
        if self.pyttsx3_engine is None:
            return

        rate = int(self.config.rate * 150) if isinstance(self.config.rate, float) else 150
        self.pyttsx3_engine.setProperty("rate", rate)
        self.pyttsx3_engine.setProperty("volume", self.config.volume)

        if self.config.voice_id:
            try:
                self.pyttsx3_engine.setProperty("voice", self.config.voice_id)
            except Exception:
                pass
        else:
            self._select_female_voice()

    def _select_female_voice(self) -> bool:
        """Select a female voice for pyttsx3."""
        if self.pyttsx3_engine is None:
            return False

        voices = self.pyttsx3_engine.getProperty("voices")
        female_patterns = ["female", "woman", "girl", "femme", "zira", "hazel", "samantha"]

        for voice in voices:
            voice_name = voice.name.lower()
            voice_id = voice.id.lower()

            for pattern in female_patterns:
                if pattern in voice_name or pattern in voice_id:
                    try:
                        self.pyttsx3_engine.setProperty("voice", voice.id)
                        self._stats["preferred_voice"] = voice.id
                        self.logger.info(f"Selected female voice: {voice.name}")
                        return True
                    except Exception:
                        pass

        return False

    def get_backend(self) -> Optional[str]:
        """Get the currently active backend."""
        return self._actual_backend

    def list_voices(self) -> list[dict]:
        """List available voices for the current backend."""
        if self._backend:
            voices = self._backend.list_voices()
            return [
                {
                    "id": v.id,
                    "name": v.name,
                    "language": v.language,
                    "gender": v.gender,
                    "description": v.description,
                }
                for v in voices
            ]
        elif self._actual_backend == "piper" and self.piper_engine:
            return self.piper_engine.list_voices()
        elif self._actual_backend == "pyttsx3" and self.pyttsx3_engine:
            voices = self.pyttsx3_engine.getProperty("voices")
            return [
                {
                    "id": v.id,
                    "name": v.name,
                    "languages": getattr(v, "languages", ["unknown"]),
                    "gender": getattr(v, "gender", "unknown"),
                }
                for v in voices
            ]
        return []

    def set_voice(self, voice_id: str) -> bool:
        """Set TTS voice by ID."""
        if self._backend:
            success = self._backend.set_voice(voice_id)
            if success:
                self.config.voice_id = voice_id
                self._stats["preferred_voice"] = voice_id
            return success
        elif self._actual_backend == "piper" and self.piper_engine:
            success = self.piper_engine.load_voice(voice_id)
            if success:
                self.config.piper_voice = voice_id
                self._stats["preferred_voice"] = voice_id
            return success
        elif self._actual_backend == "pyttsx3" and self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.setProperty("voice", voice_id)
                self.config.voice_id = voice_id
                self._stats["preferred_voice"] = voice_id
                return True
            except Exception as e:
                self.logger.error(f"Failed to set voice: {e}")
                return False
        return False

    def set_rate(self, rate: Union[int, float]) -> bool:
        """Set speaking rate."""
        if self._backend:
            success = self._backend.set_rate(float(rate))
            if success:
                self.config.rate = float(rate)
            return success
        elif self._actual_backend == "piper" and self.piper_engine:
            rate_float = float(rate)
            success = self.piper_engine.set_rate(rate_float)
            if success:
                self.config.rate = rate_float
            return success
        elif self._actual_backend == "pyttsx3" and self.pyttsx3_engine:
            try:
                rate_int = int(rate * 150) if isinstance(rate, float) else int(rate)
                self.pyttsx3_engine.setProperty("rate", max(100, min(300, rate_int)))
                self.config.rate = rate
                return True
            except Exception as e:
                self.logger.error(f"Failed to set rate: {e}")
                return False
        return False

    def set_volume(self, volume: float) -> bool:
        """Set volume level."""
        if self._backend:
            success = self._backend.set_volume(volume)
            if success:
                self.config.volume = volume
            return success
        elif self._actual_backend == "piper" and self.piper_engine:
            success = self.piper_engine.set_volume(volume)
            if success:
                self.config.volume = volume
            return success
        elif self._actual_backend == "pyttsx3" and self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.setProperty("volume", max(0.0, min(1.0, volume)))
                self.config.volume = volume
                return True
            except Exception as e:
                self.logger.error(f"Failed to set volume: {e}")
                return False
        return False

    async def speak(
        self,
        text: str,
        emotion_state: Optional[EmotionalState] = None,
        save_path: Optional[str] = None,
        play_immediately: bool = False,
    ) -> Optional[str]:
        """Convert text to speech."""
        if self._actual_backend is None:
            self.logger.error("TTS engine not initialized")
            return None

        if not text or not text.strip():
            self.logger.warning("Empty text provided to TTS")
            return None

        # Handle lazy initialization for backends that need it
        if self._pending_init and self._backend:
            try:
                self.logger.info("Initializing TTS backend (lazy init)...")
                await self._backend.initialize()
                self._pending_init = False
                if self._backend._initialized:
                    self.logger.info(f"TTS backend initialized: {self._actual_backend}")
                else:
                    self.logger.error("TTS backend failed to initialize")
                    return None
            except Exception as e:
                self.logger.error(f"Failed to initialize TTS backend: {e}")
                return None

        start_time = time.time()
        clean_text = self._clean_text_for_tts(text)

        try:
            if self._backend:
                # Use new backend interface
                if not save_path and not play_immediately:
                    save_path = tempfile.mktemp(suffix=f".{self.config.output_format}")

                if save_path:
                    success = await self._backend.synthesize(clean_text, save_path)
                    if success:
                        # Apply goddess voice enhancement if enabled
                        if self.goddess_processor:
                            save_path = await self.goddess_processor.process(save_path) or save_path

                        latency_ms = (time.time() - start_time) * 1000
                        self._stats["total_utterances"] += 1
                        self._stats["total_latency_ms"] += latency_ms
                        return save_path
                return None
                
            elif self._actual_backend == "piper" and self.piper_engine:
                result = await self.piper_engine.speak(
                    clean_text,
                    emotion=emotion_state,
                    save_path=save_path,
                    play_immediately=play_immediately
                )
            elif self._actual_backend == "pyttsx3" and self.pyttsx3_engine:
                result = await self._speak_pyttsx3(clean_text, emotion_state, save_path, play_immediately)
            else:
                self.logger.error("No TTS backend available")
                return None

            # Apply goddess voice enhancement if enabled and we have an audio file
            if result and self.goddess_processor:
                result = await self.goddess_processor.process(result) or result

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_utterances"] += 1
            self._stats["total_latency_ms"] += latency_ms
            self.logger.debug(f"TTS synthesis completed in {latency_ms:.1f}ms")

            return result

        except Exception as e:
            self.logger.error(f"TTS synthesis failed: {e}")
            return None

    async def _speak_pyttsx3(
        self, text: str, emotion_state: Optional[EmotionalState],
        save_path: Optional[str], play_immediately: bool,
    ) -> Optional[str]:
        """Internal pyttsx3 speak implementation."""
        if save_path:
            output_path = save_path
        elif not play_immediately:
            output_path = tempfile.mktemp(suffix=f".{self.config.output_format}")
        else:
            output_path = None

        if output_path:
            def _synthesize():
                self.pyttsx3_engine.save_to_file(text, output_path)
                self.pyttsx3_engine.runAndWait()
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _synthesize)
            return output_path
        else:
            def _speak():
                self.pyttsx3_engine.say(text)
                self.pyttsx3_engine.runAndWait()
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _speak)
            return None

    async def speak_to_file(self, text: str, filepath: str, emotion_state: Optional[EmotionalState] = None) -> Optional[str]:
        """Save text to audio file."""
        return await self.speak(text, emotion_state, save_path=filepath)

    async def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Direct synthesis method for new backends."""
        if self._backend:
            return await self._backend.synthesize(text, output_path, **kwargs)
        return False

    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS output."""
        if not text:
            return ""

        # Remove markdown formatting
        text = re.sub(r"\*\*", "", text)
        text = re.sub(r"\*(?!\*)", "", text)
        text = re.sub(r"__", "", text)
        text = re.sub(r"_(?!_)", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"```[^`]*```", " code block ", text, flags=re.DOTALL)

        # Replace emoji
        emoji_map = {
            "🔮": " crystal ball ", "✨": " sparkles ", "👑": " crown ",
            "💕": " heart ", "😊": " smile ", "🌟": " star ",
            "💫": " sparkle ", "🌙": " moon ",
        }
        for emoji, description in emoji_map.items():
            text = text.replace(emoji, description)

        # Remove URLs and Discord mentions
        text = re.sub(r"https?://\S+", " link ", text)
        text = re.sub(r"<@!?\d+>", " mention ", text)
        text = re.sub(r"<#\d+>", " channel ", text)
        text = re.sub(r"<@&\d+>", " role mention ", text)

        # Clean whitespace
        text = " ".join(text.split())
        return text.strip()

    def get_stats(self) -> dict:
        """Get TTS statistics."""
        if self._backend:
            return self._backend.get_stats()
        elif self._actual_backend == "piper" and self.piper_engine:
            return self.piper_engine.get_stats()
        
        stats = self._stats.copy()
        if stats["total_utterances"] > 0:
            stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["total_utterances"]
        else:
            stats["avg_latency_ms"] = 0
        return stats

    def get_available_backends(self) -> List[str]:
        """Get list of available backends."""
        available = []
        if KOKORO_AVAILABLE:
            available.append("kokoro")
        if MELO_AVAILABLE:
            available.append("melotts")
        if COQUI_AVAILABLE:
            available.append("coqui")
        if LUX_AVAILABLE:
            available.append("luxtts")
        if PIPER_AVAILABLE:
            available.append("piper")
        if PYTTSX3_AVAILABLE:
            available.append("pyttsx3")
        return available
