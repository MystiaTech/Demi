"""
MeloTTS Backend

High-quality multilingual TTS by MyShell.ai.
Best for: Good quality, emotion control, multiple languages
"""

import os
import time
import asyncio
from pathlib import Path
from typing import Optional, List

from src.core.logger import get_logger
from src.voice.tts_base import TTSBackend, TTSVoice, TTSBackendConfig

# Try to import MeloTTS
try:
    from melo.api import TTS as MeloTTSApi
    MELO_AVAILABLE = True
except ImportError:
    MELO_AVAILABLE = False
    MeloTTSApi = None


class MeloTTSBackend(TTSBackend):
    """MeloTTS backend implementation."""
    
    # Language codes mapping
    LANGUAGE_CODES = {
        "EN": "EN",      # English
        "ES": "ES",      # Spanish
        "FR": "FR",      # French
        "ZH": "ZH",      # Chinese
        "JP": "JP",      # Japanese
        "KR": "KR",      # Korean
    }
    
    DEFAULT_LANGUAGE = "EN"
    DEFAULT_SPEAKER_ID = "EN-US"  # For English
    
    def __init__(self, config: TTSBackendConfig):
        super().__init__(config)
        self.logger = get_logger()
        self._model = None
        self._speaker_id = config.extra_settings.get("speaker_id", self.DEFAULT_SPEAKER_ID)
        self._language = config.extra_settings.get("language", self.DEFAULT_LANGUAGE)
        self._device = self._get_device()
        
    @property
    def name(self) -> str:
        return "melotts"
    
    @property
    def is_available(self) -> bool:
        return MELO_AVAILABLE
    
    def _get_device(self) -> str:
        """Determine the best device to use."""
        import torch
        if self.config.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            return "cpu"
        return self.config.device
    
    async def initialize(self) -> bool:
        """Initialize MeloTTS model."""
        if not MELO_AVAILABLE:
            self.logger.error("MeloTTS not installed. Run: pip install melotts")
            return False
        
        try:
            # Run initialization in thread pool
            loop = asyncio.get_event_loop()
            
            def _init():
                # Load model for specified language
                model = MeloTTSApi(
                    language=self._language,
                    device=self._device
                )
                return model
            
            self._model = await loop.run_in_executor(None, _init)
            self._initialized = True
            self.logger.info(f"MeloTTS initialized (language: {self._language}, device: {self._device})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MeloTTS: {e}")
            return False
    
    async def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Synthesize text to audio."""
        if not self._initialized or self._model is None:
            self.logger.error("MeloTTS not initialized")
            return False
        
        start_time = time.time()
        
        try:
            speaker_id = kwargs.get("speaker_id", self._speaker_id)
            speed = kwargs.get("speed", self.config.rate)
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            
            def _synthesize():
                self._model.tts_to_file(
                    text,
                    speaker_id=speaker_id,
                    output_path=output_path,
                    sdp_ratio=0.2,  # Stochastic duration predictor
                    noise_scale=0.6,
                    noise_scale_w=0.8,
                    speed=speed
                )
                return True
            
            success = await loop.run_in_executor(None, _synthesize)
            
            if success:
                latency_ms = (time.time() - start_time) * 1000
                self._update_stats(latency_ms)
                self.logger.debug(f"MeloTTS synthesis: {latency_ms:.1f}ms")
            
            return success
            
        except Exception as e:
            self.logger.error(f"MeloTTS synthesis failed: {e}")
            return False
    
    def list_voices(self) -> List[TTSVoice]:
        """List available speakers."""
        # MeloTTS uses speaker IDs per language
        speakers = {
            "EN": ["EN-US", "EN-BR", "EN-AU", "EN-IN"],
            "ES": ["ES"],
            "FR": ["FR"],
            "ZH": ["ZH"],
            "JP": ["JP"],
            "KR": ["KR"],
        }
        
        voices = []
        for lang, spk_list in speakers.items():
            for spk in spk_list:
                voices.append(TTSVoice(
                    id=f"{lang}-{spk}",
                    name=f"Melo {lang} {spk}",
                    language=lang,
                    gender="unknown",
                    description=f"MeloTTS {lang} voice"
                ))
        return voices
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice (speaker)."""
        # Parse language-speaker format
        parts = voice_id.split("-")
        if len(parts) >= 2:
            lang = parts[0]
            speaker = "-".join(parts[1:])
            if lang in self.LANGUAGE_CODES:
                self._language = lang
                self._speaker_id = speaker
                self.config.voice_id = voice_id
                # Re-initialize with new language if needed
                if self._initialized:
                    self._initialized = False
                    asyncio.create_task(self.initialize())
                return True
        self.logger.warning(f"Unknown MeloTTS voice: {voice_id}")
        return False
    
    def set_language(self, language: str) -> bool:
        """Set the language."""
        if language.upper() in self.LANGUAGE_CODES:
            self._language = language.upper()
            if self._initialized:
                self._initialized = False
                asyncio.create_task(self.initialize())
            return True
        return False
