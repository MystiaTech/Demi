"""
Kokoro TTS Backend

Lightweight TTS with 82M parameters, Apache-licensed.
Best for: Fast inference, good quality, small model size (~80MB)
"""

import os
import time
import asyncio
from pathlib import Path
from typing import Optional, List
import tempfile

from src.core.logger import get_logger
from src.voice.tts_base import TTSBackend, TTSVoice, TTSBackendConfig

# Try to import kokoro
try:
    from kokoro import KPipeline
    import torch
    import soundfile as sf
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    KPipeline = None


class KokoroTTS(TTSBackend):
    """Kokoro TTS backend implementation."""
    
    # Available voices (af = American Female, am = American Male, etc.)
    DEFAULT_VOICE = "af_heart"  # American Female, Heart voice
    
    VOICE_MAP = {
        "af_heart": ("American Female", "en-US"),
        "af_bella": ("American Female", "en-US"),
        "af_nicole": ("American Female", "en-US"),
        "af_sky": ("American Female", "en-US"),
        "am_adam": ("American Male", "en-US"),
        "am_michael": ("American Male", "en-US"),
        "bf_emma": ("British Female", "en-GB"),
        "bf_isabella": ("British Female", "en-GB"),
        "bm_george": ("British Male", "en-GB"),
        "bm_lewis": ("British Male", "en-GB"),
    }
    
    def __init__(self, config: TTSBackendConfig):
        super().__init__(config)
        self.logger = get_logger()
        self._pipeline = None
        self._current_voice = config.voice_id or self.DEFAULT_VOICE
        self._device = self._get_device()
        
    @property
    def name(self) -> str:
        return "kokoro"
    
    @property
    def is_available(self) -> bool:
        return KOKORO_AVAILABLE
    
    def _get_device(self) -> str:
        """Determine the best device to use."""
        if self.config.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        return self.config.device
    
    async def initialize(self) -> bool:
        """Initialize Kokoro pipeline."""
        if not KOKORO_AVAILABLE:
            self.logger.error("Kokoro not installed. Run: pip install kokoro soundfile")
            return False
        
        try:
            # Run initialization in thread pool
            loop = asyncio.get_event_loop()
            self._pipeline = await loop.run_in_executor(
                None, 
                lambda: KPipeline(lang_code='a')  # American English
            )
            self._initialized = True
            self.logger.info(f"Kokoro TTS initialized (device: {self._device})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Kokoro: {e}")
            return False
    
    async def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Synthesize text to audio."""
        if not self._initialized or self._pipeline is None:
            self.logger.error("Kokoro not initialized")
            return False
        
        start_time = time.time()
        
        try:
            voice = kwargs.get("voice", self._current_voice)
            speed = kwargs.get("speed", 1.0 / self.config.rate)  # Invert rate for speed
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            
            def _synthesize():
                generator = self._pipeline(text, voice=voice, speed=speed)
                # Get the first (and usually only) audio segment
                for i, (gs, ps, audio) in enumerate(generator):
                    sf.write(output_path, audio, 24000)
                    return True
                return False
            
            success = await loop.run_in_executor(None, _synthesize)
            
            if success:
                latency_ms = (time.time() - start_time) * 1000
                self._update_stats(latency_ms)
                self.logger.debug(f"Kokoro synthesis: {latency_ms:.1f}ms")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Kokoro synthesis failed: {e}")
            return False
    
    def list_voices(self) -> List[TTSVoice]:
        """List available voices."""
        voices = []
        for voice_id, (name, lang) in self.VOICE_MAP.items():
            gender = "female" if voice_id.startswith("af") or voice_id.startswith("bf") else "male"
            voices.append(TTSVoice(
                id=voice_id,
                name=name,
                language=lang,
                gender=gender,
                description=f"{name} voice"
            ))
        return voices
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice."""
        if voice_id in self.VOICE_MAP:
            self._current_voice = voice_id
            self.config.voice_id = voice_id
            return True
        self.logger.warning(f"Unknown Kokoro voice: {voice_id}")
        return False
