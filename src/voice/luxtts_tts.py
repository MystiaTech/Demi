"""
LuxTTS Backend

High-quality rapid voice cloning with 48kHz output.
Best for: Voice cloning, 48kHz clarity, fast inference (150x realtime on GPU)
Note: Requires reference audio for voice cloning, fits in 1GB VRAM
"""

import os
import time
import asyncio
from pathlib import Path
from typing import Optional, List

from src.core.logger import get_logger
from src.voice.tts_base import TTSBackend, TTSVoice, TTSBackendConfig

# Try to import LuxTTS
try:
    # LuxTTS uses zipvoice module
    from zipvoice.luxvoice import LuxTTS as LuxTTSModel
    LUX_AVAILABLE = True
except ImportError:
    LUX_AVAILABLE = False
    LuxTTSModel = None


class LuxTTSBackend(TTSBackend):
    """LuxTTS backend implementation."""
    
    MODEL_ID = "YatharthS/LuxTTS"
    DEFAULT_NUM_STEPS = 4  # 3-4 recommended for efficiency
    DEFAULT_T_SHIFT = 0.9
    DEFAULT_SPEED = 1.0
    
    def __init__(self, config: TTSBackendConfig):
        super().__init__(config)
        self.logger = get_logger()
        self._model = None
        self._device = self._get_device()
        self._reference_audio = config.extra_settings.get("reference_audio", None)
        self._encoded_prompt = None
        self._num_steps = config.extra_settings.get("num_steps", self.DEFAULT_NUM_STEPS)
        self._t_shift = config.extra_settings.get("t_shift", self.DEFAULT_T_SHIFT)
        self._speed = config.extra_settings.get("speed", self.DEFAULT_SPEED)
        self._rms = config.extra_settings.get("rms", 0.01)
        
    @property
    def name(self) -> str:
        return "luxtts"
    
    @property
    def is_available(self) -> bool:
        return LUX_AVAILABLE
    
    def _get_device(self) -> str:
        """Determine the best device to use."""
        if self.config.device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return "mps"
            except ImportError:
                pass
            return "cpu"
        return self.config.device
    
    async def initialize(self) -> bool:
        """Initialize LuxTTS model."""
        if not LUX_AVAILABLE:
            self.logger.error("LuxTTS not installed. See: https://github.com/ysharma3501/LuxTTS")
            return False
        
        try:
            # Run initialization in thread pool
            loop = asyncio.get_event_loop()
            
            def _init():
                self.logger.info("Loading LuxTTS model...")
                # Determine threads for CPU
                kwargs = {"device": self._device}
                if self._device == "cpu":
                    kwargs["threads"] = 2
                
                model = LuxTTSModel(self.MODEL_ID, **kwargs)
                return model
            
            self._model = await loop.run_in_executor(None, _init)
            
            # Encode reference audio if provided
            if self._reference_audio and os.path.exists(self._reference_audio):
                await self._encode_reference()
            
            self._initialized = True
            self.logger.info(f"LuxTTS initialized (device: {self._device})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LuxTTS: {e}")
            return False
    
    async def _encode_reference(self):
        """Encode the reference audio for voice cloning."""
        if not self._model or not self._reference_audio:
            return
        
        try:
            loop = asyncio.get_event_loop()
            
            def _encode():
                self.logger.info(f"Encoding reference audio: {self._reference_audio}")
                self._encoded_prompt = self._model.encode_prompt(
                    self._reference_audio,
                    rms=self._rms
                )
            
            await loop.run_in_executor(None, _encode)
            
        except Exception as e:
            self.logger.error(f"Failed to encode reference audio: {e}")
    
    async def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Synthesize text to audio."""
        if not self._initialized or self._model is None:
            self.logger.error("LuxTTS not initialized")
            return False
        
        if self._encoded_prompt is None:
            self.logger.error("LuxTTS requires a reference audio for voice cloning")
            return False
        
        start_time = time.time()
        
        try:
            # Get synthesis parameters
            num_steps = kwargs.get("num_steps", self._num_steps)
            t_shift = kwargs.get("t_shift", self._t_shift)
            speed = kwargs.get("speed", self._speed / self.config.rate)  # Adjust for rate
            return_smooth = kwargs.get("return_smooth", False)
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            
            def _synthesize():
                import soundfile as sf
                
                # Generate speech
                final_wav = self._model.generate_speech(
                    text,
                    self._encoded_prompt,
                    num_steps=num_steps,
                    t_shift=t_shift,
                    speed=speed,
                    return_smooth=return_smooth
                )
                
                # Convert to numpy and save
                final_wav = final_wav.numpy().squeeze()
                sf.write(output_path, final_wav, 48000)  # 48kHz output
                return True
            
            success = await loop.run_in_executor(None, _synthesize)
            
            if success:
                latency_ms = (time.time() - start_time) * 1000
                self._update_stats(latency_ms)
                self.logger.debug(f"LuxTTS synthesis: {latency_ms:.1f}ms")
            
            return success
            
        except Exception as e:
            self.logger.error(f"LuxTTS synthesis failed: {e}")
            return False
    
    def list_voices(self) -> List[TTSVoice]:
        """List available voices (references)."""
        # LuxTTS is voice cloning only - voices depend on reference audio
        voices = [
            TTSVoice(
                id="cloned",
                name="Cloned Voice",
                language="en",
                gender="unknown",
                description="Voice cloned from reference audio"
            )
        ]
        return voices
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice (reference audio path)."""
        if voice_id.endswith(".wav") or voice_id.endswith(".mp3"):
            if os.path.exists(voice_id):
                self._reference_audio = voice_id
                self.config.voice_id = voice_id
                # Re-encode reference
                if self._initialized:
                    asyncio.create_task(self._encode_reference())
                return True
            else:
                self.logger.error(f"Reference audio not found: {voice_id}")
                return False
        self.logger.warning(f"LuxTTS requires a reference audio file path")
        return False
    
    def set_reference_audio(self, audio_path: str) -> bool:
        """Set the reference audio for voice cloning."""
        return self.set_voice(audio_path)
    
    def set_sampling_params(
        self,
        num_steps: Optional[int] = None,
        t_shift: Optional[float] = None,
        speed: Optional[float] = None,
        rms: Optional[float] = None
    ):
        """Set sampling parameters for generation.
        
        Args:
            num_steps: Higher = better quality but slower (3-4 recommended)
            t_shift: Higher = better quality but worse WER (0.9 default)
            speed: Speed multiplier (1.0 = normal, lower = slower)
            rms: Higher = louder audio (0.01 recommended)
        """
        if num_steps is not None:
            self._num_steps = num_steps
        if t_shift is not None:
            self._t_shift = t_shift
        if speed is not None:
            self._speed = speed
        if rms is not None:
            self._rms = rms
