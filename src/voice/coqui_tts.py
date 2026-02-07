"""
Coqui TTS Backend (XTTS-v2)

State-of-the-art voice cloning and multilingual TTS.
Best for: Voice cloning, highest quality, 16 languages supported
Note: ~2GB model, slower inference (1-3s), GPU recommended
"""

import os
import time
import asyncio
from pathlib import Path
from typing import Optional, List

from src.core.logger import get_logger
from src.voice.tts_base import TTSBackend, TTSVoice, TTSBackendConfig

# Try to import Coqui TTS
try:
    from TTS.api import TTS as CoquiTTSApi
    import torch
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False
    CoquiTTSApi = None


class CoquiTTSBackend(TTSBackend):
    """Coqui TTS backend with XTTS-v2 support."""
    
    MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
    
    # Supported languages for XTTS-v2
    SUPPORTED_LANGUAGES = [
        "en", "es", "fr", "de", "it", "pt", "pl", "tr", 
        "ru", "nl", "cs", "ar", "zh", "ja", "hu", "ko"
    ]
    
    DEFAULT_LANGUAGE = "en"
    
    def __init__(self, config: TTSBackendConfig):
        super().__init__(config)
        self.logger = get_logger()
        self._model = None
        self._language = config.extra_settings.get("language", self.DEFAULT_LANGUAGE)
        self._speaker_wav = config.extra_settings.get("speaker_wav", None)
        self._device = self._get_device()
        
    @property
    def name(self) -> str:
        return "coqui"
    
    @property
    def is_available(self) -> bool:
        return COQUI_AVAILABLE
    
    def _get_device(self) -> str:
        """Determine the best device to use."""
        if self.config.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            return "cpu"
        return self.config.device
    
    async def initialize(self) -> bool:
        """Initialize Coqui TTS model."""
        if not COQUI_AVAILABLE:
            self.logger.error("Coqui TTS not installed. Run: pip install TTS")
            return False
        
        try:
            # Run initialization in thread pool (may download model)
            loop = asyncio.get_event_loop()
            
            def _init():
                self.logger.info("Loading Coqui XTTS-v2 model (this may take a while)...")
                model = CoquiTTSApi(self.MODEL_NAME).to(self._device)
                return model
            
            self._model = await loop.run_in_executor(None, _init)
            self._initialized = True
            self.logger.info(f"Coqui TTS initialized (device: {self._device})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Coqui TTS: {e}")
            return False
    
    async def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Synthesize text to audio."""
        if not self._initialized or self._model is None:
            self.logger.error("Coqui TTS not initialized")
            return False
        
        start_time = time.time()
        
        try:
            language = kwargs.get("language", self._language)
            speaker_wav = kwargs.get("speaker_wav", self._speaker_wav)
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            
            def _synthesize():
                if speaker_wav and os.path.exists(speaker_wav):
                    # Voice cloning mode
                    self._model.tts_to_file(
                        text=text,
                        speaker_wav=speaker_wav,
                        language=language,
                        file_path=output_path
                    )
                else:
                    # Default voice (won't work well with XTTS without speaker_wav)
                    # Use a default speaker reference if available
                    self.logger.warning("No speaker_wav provided for XTTS, using default")
                    self._model.tts_to_file(
                        text=text,
                        language=language,
                        file_path=output_path
                    )
                return True
            
            success = await loop.run_in_executor(None, _synthesize)
            
            if success:
                latency_ms = (time.time() - start_time) * 1000
                self._update_stats(latency_ms)
                self.logger.debug(f"Coqui synthesis: {latency_ms:.1f}ms")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Coqui TTS synthesis failed: {e}")
            return False
    
    def list_voices(self) -> List[TTSVoice]:
        """List available voices (languages for XTTS)."""
        voices = []
        lang_names = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "pl": "Polish", "tr": "Turkish",
            "ru": "Russian", "nl": "Dutch", "cs": "Czech", "ar": "Arabic",
            "zh": "Chinese", "ja": "Japanese", "hu": "Hungarian", "ko": "Korean"
        }
        
        for lang in self.SUPPORTED_LANGUAGES:
            voices.append(TTSVoice(
                id=lang,
                name=f"XTTS {lang_names.get(lang, lang)}",
                language=lang,
                gender="unknown",
                description=f"XTTS-v2 {lang_names.get(lang, lang)}"
            ))
        return voices
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice (language for XTTS)."""
        if voice_id in self.SUPPORTED_LANGUAGES:
            self._language = voice_id
            self.config.voice_id = voice_id
            return True
        # Check if it's a speaker wav file path
        if voice_id.endswith(".wav") and os.path.exists(voice_id):
            self._speaker_wav = voice_id
            self.config.voice_id = voice_id
            return True
        self.logger.warning(f"Unknown Coqui voice/language: {voice_id}")
        return False
    
    def set_speaker_wav(self, speaker_wav_path: str) -> bool:
        """Set the speaker reference for voice cloning."""
        if os.path.exists(speaker_wav_path):
            self._speaker_wav = speaker_wav_path
            return True
        self.logger.error(f"Speaker wav not found: {speaker_wav_path}")
        return False
