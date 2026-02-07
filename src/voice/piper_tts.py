"""
Piper TTS Integration for Demi.

High-quality neural text-to-speech using Piper models via ONNX Runtime.
Optimized for RTX 3060 (12GB VRAM) with GPU acceleration support.

Features:
- Local neural TTS with Piper models
- GPU acceleration via ONNX Runtime
- Streaming audio generation
- Emotion-based voice modulation (speed/pitch)
- Multi-speaker model support
- Audio caching for reduced latency
"""

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union, Dict, List, Any, Tuple
from io import BytesIO

import numpy as np

from src.core.logger import get_logger
from src.emotion.models import EmotionalState
from src.voice.emotion_voice import EmotionVoiceMapper, VoiceParameters

# Try to import piper-tts and onnxruntime
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
    
    # Try to import download utility (may not exist in all versions)
    try:
        from piper.download import find_voice
    except ImportError:
        find_voice = None
        
except ImportError:
    PIPER_AVAILABLE = False
    PiperVoice = None
    find_voice = None

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


# Piper voice registry with recommended voices
PIPER_VOICE_REGISTRY = {
    "en_US-lessac-medium": {
        "name": "Lessac (Medium)",
        "gender": "female",
        "quality": "medium",
        "size_mb": 100,
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
        "default": True,
    },
    "en_US-ryan-high": {
        "name": "Ryan (High)",
        "gender": "male",
        "quality": "high",
        "size_mb": 300,
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx.json",
        "default": False,
    },
    "en_US-libritts-high": {
        "name": "LibriTTS (High)",
        "gender": "female",
        "quality": "high",
        "size_mb": 300,
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/libritts/high/en_US-libritts-high.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/libritts/high/en_US-libritts-high.onnx.json",
        "multi_speaker": True,
        "default": False,
    },
    "en_US-lessac-high": {
        "name": "Lessac (High)",
        "gender": "female",
        "quality": "high",
        "size_mb": 300,
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx.json",
        "default": False,
    },
}

# Emotion to SSML/Piper parameters mapping
# length_scale: higher = slower/more deliberate speech
# noise_scale: voice variability (0.0-1.0)
# noise_w: phoneme duration variability (0.0-1.0)
EMOTION_TO_VOICE_SETTINGS = {
    # Divine confidence: commanding, authoritative, slightly slower for gravitas
    "divine_confidence": {"length_scale": 1.1, "noise_scale": 0.6, "noise_w": 0.7},
    # Seductive affection: slower, smoother, more intimate
    "seductive_affection": {"length_scale": 1.15, "noise_scale": 0.6, "noise_w": 0.5},
    # Cutting frustration: sharp, faster, more crisp
    "cutting_frustration": {"length_scale": 0.9, "noise_scale": 0.75, "noise_w": 0.85},
    # Enthusiastic excitement: energetic but controlled
    "enthusiastic_excitement": {"length_scale": 0.95, "noise_scale": 0.65, "noise_w": 0.7},
    # Wistful loneliness: slow, soft, lingering
    "wistful_loneliness": {"length_scale": 1.2, "noise_scale": 0.55, "noise_w": 0.45},
    # Rare vulnerability: gentle, hesitant, slower
    "rare_vulnerability": {"length_scale": 1.15, "noise_scale": 0.55, "noise_w": 0.45},
    # Possessive jealousy: intense, measured, commanding
    "possessive_jealousy": {"length_scale": 1.05, "noise_scale": 0.65, "noise_w": 0.75},
    # Playful curiosity: moderate pace, light
    "playful_curiosity": {"length_scale": 1.0, "noise_scale": 0.65, "noise_w": 0.65},
    # Neutral: default goddess presence - deliberate and commanding
    "neutral": {"length_scale": 1.08, "noise_scale": 0.62, "noise_w": 0.7},
}


@dataclass
class PiperTTSConfig:
    """Configuration for Piper TTS engine.
    
    Attributes:
        voice_id: Piper voice identifier (e.g., "en_US-lessac-medium")
        voices_dir: Directory containing Piper voice models
        rate: Speaking rate modifier (0.5-2.0, affects length_scale)
        volume: Audio level 0.0-1.0
        use_gpu: Whether to use GPU acceleration via ONNX Runtime
        cache_enabled: Whether to cache audio files
        cache_dir: Directory for cached audio files
        speaker_id: Speaker ID for multi-speaker models
        onnx_threads: Number of ONNX Runtime threads (CPU only)
        streaming: Whether to stream audio generation
    """
    voice_id: str = "en_US-lessac-medium"
    voices_dir: str = "~/.demi/voices/piper"
    rate: float = 1.0
    volume: float = 1.0
    use_gpu: bool = True
    cache_enabled: bool = True
    cache_dir: str = "~/.demi/tts_cache/piper"
    speaker_id: Optional[int] = None
    onnx_threads: int = 4
    streaming: bool = True
    
    def __post_init__(self):
        """Validate configuration and check for environment variables."""
        self.rate = max(0.5, min(2.0, self.rate))
        self.volume = max(0.0, min(1.0, self.volume))
        
        # Check for PIPER_VOICES_DIR environment variable
        env_voices_dir = os.environ.get("PIPER_VOICES_DIR")
        if env_voices_dir:
            self.voices_dir = env_voices_dir


class PiperTTS:
    """Piper TTS engine for high-quality neural speech synthesis.
    
    Provides high-quality text-to-speech using Piper neural models with:
    - GPU acceleration support (RTX 3060 optimized)
    - Emotion-based voice modulation
    - Multi-speaker model support
    - Audio streaming and caching
    
    Target latency: <500ms for typical responses with GPU.
    """
    
    def __init__(self, config: Optional[PiperTTSConfig] = None):
        """Initialize the Piper TTS engine.
        
        Args:
            config: Piper TTS configuration (uses defaults if None)
        """
        self.config = config or PiperTTSConfig()
        self.logger = get_logger()
        self.emotion_mapper = EmotionVoiceMapper()
        
        # Check dependencies
        if not PIPER_AVAILABLE:
            self.logger.error("Piper TTS not available. Install with: pip install piper-tts")
            raise RuntimeError("Piper TTS not installed")
        
        # Initialize voice
        self.voice: Optional[PiperVoice] = None
        self.voice_config: Optional[Dict[str, Any]] = None
        self.current_voice_id: Optional[str] = None
        self.is_multi_speaker: bool = False
        
        # Setup directories
        self.voices_dir = Path(self.config.voices_dir).expanduser()
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        
        if self.config.cache_enabled:
            self.cache_dir = Path(self.config.cache_dir).expanduser()
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # GPU/ONNX configuration
        self.onnx_providers = self._setup_onnx_providers()
        
        # Statistics
        self._stats = {
            "total_utterances": 0,
            "total_latency_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "gpu_accelerated": ONNX_AVAILABLE and self.config.use_gpu,
            "preferred_voice": self.config.voice_id,
        }
        
        # Load default voice
        self._load_default_voice()
    
    def _setup_onnx_providers(self) -> List[str]:
        """Setup ONNX Runtime execution providers.
        
        Returns:
            List of execution providers in priority order
        """
        providers = []
        
        if ONNX_AVAILABLE and self.config.use_gpu:
            # Check for CUDA availability
            available_providers = ort.get_available_providers()
            
            if 'CUDAExecutionProvider' in available_providers:
                # Configure CUDA provider for RTX 3060
                cuda_options = {
                    'device_id': 0,
                    'arena_extend_strategy': 'kNextPowerOfTwo',
                    'gpu_mem_limit': 4 * 1024 * 1024 * 1024,  # 4GB limit for RTX 3060
                    'cudnn_conv_algo_search': 'HEURISTIC',
                    'do_copy_in_default_stream': True,
                }
                providers.append(('CUDAExecutionProvider', cuda_options))
                self.logger.info("CUDA GPU acceleration enabled for Piper TTS")
            elif 'DmlExecutionProvider' in available_providers:
                # DirectML for Windows
                providers.append('DmlExecutionProvider')
                self.logger.info("DirectML GPU acceleration enabled for Piper TTS")
        
        # Fallback to CPU
        providers.append('CPUExecutionProvider')
        
        if not ONNX_AVAILABLE or not self.config.use_gpu:
            self.logger.info("Using CPU for Piper TTS")
        
        return providers
    
    def _load_default_voice(self):
        """Load the default voice or first available."""
        # Try to load configured voice
        if self.load_voice(self.config.voice_id):
            return
        
        # Try to find any available voice
        voices = self.list_voices()
        if voices:
            for voice in voices:
                if voice.get("downloaded"):
                    self.load_voice(voice["id"])
                    return
        
        self.logger.warning("No Piper voices available. Run scripts/download_piper_voices.sh")
    
    def load_voice(self, voice_id: str) -> bool:
        """Load a Piper voice model.
        
        Args:
            voice_id: Voice identifier (e.g., "en_US-lessac-medium")
            
        Returns:
            True if successful, False otherwise
        """
        model_path = self.voices_dir / f"{voice_id}.onnx"
        config_path = self.voices_dir / f"{voice_id}.onnx.json"
        
        if not model_path.exists():
            self.logger.warning(f"Voice model not found: {model_path}")
            return False
        
        try:
            # Load voice configuration
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.voice_config = json.load(f)
                self.is_multi_speaker = self.voice_config.get('num_speakers', 1) > 1
            else:
                self.voice_config = {}
                self.is_multi_speaker = False
            
            # Load voice with appropriate ONNX session options
            sess_options = ort.SessionOptions() if ONNX_AVAILABLE else None
            if sess_options and not self.config.use_gpu:
                sess_options.intra_op_num_threads = self.config.onnx_threads
                sess_options.inter_op_num_threads = self.config.onnx_threads
            
            self.voice = PiperVoice.load(
                str(model_path),
                config_path=str(config_path) if config_path.exists() else None,
                use_cuda=self.config.use_gpu and ONNX_AVAILABLE and 'CUDAExecutionProvider' in ort.get_available_providers()
            )
            
            self.current_voice_id = voice_id
            self._stats["preferred_voice"] = voice_id
            
            self.logger.info(f"Loaded Piper voice: {voice_id}")
            if self.is_multi_speaker:
                num_speakers = self.voice_config.get('num_speakers', 1)
                self.logger.info(f"Multi-speaker model with {num_speakers} speakers")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load voice {voice_id}: {e}")
            return False
    
    def set_speaker_id(self, speaker_id: int) -> bool:
        """Set speaker ID for multi-speaker models.
        
        Args:
            speaker_id: Speaker identifier (0-indexed)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_multi_speaker:
            self.logger.warning("Current voice is not a multi-speaker model")
            return False
        
        num_speakers = self.voice_config.get('num_speakers', 1)
        if speaker_id < 0 or speaker_id >= num_speakers:
            self.logger.warning(f"Invalid speaker ID {speaker_id}, must be 0-{num_speakers-1}")
            return False
        
        self.config.speaker_id = speaker_id
        self.logger.info(f"Set speaker ID to {speaker_id}")
        return True
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available Piper voices.
        
        Returns:
            List of voice dictionaries with metadata
        """
        voices = []
        
        for voice_id, info in PIPER_VOICE_REGISTRY.items():
            model_path = self.voices_dir / f"{voice_id}.onnx"
            config_path = self.voices_dir / f"{voice_id}.onnx.json"
            
            voice_info = {
                "id": voice_id,
                "name": info["name"],
                "gender": info.get("gender", "unknown"),
                "quality": info.get("quality", "medium"),
                "size_mb": info.get("size_mb", 0),
                "multi_speaker": info.get("multi_speaker", False),
                "downloaded": model_path.exists() and config_path.exists(),
                "loaded": self.current_voice_id == voice_id,
                "default": info.get("default", False),
            }
            voices.append(voice_info)
        
        # Sort: loaded first, then downloaded, then by default
        voices.sort(key=lambda v: (not v["loaded"], not v["downloaded"], not v["default"]))
        
        return voices
    
    async def speak(
        self,
        text: str,
        emotion: Optional[Union[EmotionalState, str]] = None,
        save_path: Optional[str] = None,
        play_immediately: bool = False,
    ) -> Optional[str]:
        """Generate speech from text with optional emotion modulation.
        
        Args:
            text: Text to speak
            emotion: Optional emotional state or emotion name
            save_path: Optional path to save audio file
            play_immediately: If True, play audio immediately (blocking)
            
        Returns:
            Path to audio file if saved, None if played immediately or failed
        """
        if self.voice is None:
            self.logger.error("No Piper voice loaded")
            return None
        
        if not text or not text.strip():
            self.logger.warning("Empty text provided to TTS")
            return None
        
        start_time = time.time()
        
        # Clean text
        clean_text = self._clean_text_for_tts(text)
        
        # Get voice synthesis parameters based on emotion
        synth_params = self._get_synthesis_parameters(emotion)
        
        # Determine output path
        if save_path:
            output_path = save_path
        elif not play_immediately:
            output_path = tempfile.mktemp(suffix=".wav")
        else:
            output_path = None
        
        # Check cache
        cache_hit = False
        if self.config.cache_enabled and not save_path and output_path:
            cached_path = self._get_cached_audio(clean_text, emotion)
            if cached_path:
                output_path = cached_path
                cache_hit = True
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1
        
        try:
            if output_path and not cache_hit:
                # Synthesize to file
                await self._synthesize_to_file(clean_text, output_path, synth_params)
                
                # Cache the result
                if self.config.cache_enabled and not save_path:
                    self._cache_audio(clean_text, emotion, output_path)
            
            elif play_immediately:
                # Play immediately
                await self._synthesize_and_play(clean_text, synth_params)
            
            # Update statistics
            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_utterances"] += 1
            self._stats["total_latency_ms"] += latency_ms
            
            self.logger.debug(f"Piper TTS synthesis completed in {latency_ms:.1f}ms")
            
            return output_path if output_path else None
            
        except Exception as e:
            self.logger.error(f"Piper TTS synthesis failed: {e}")
            return None
    
    async def speak_to_file(
        self,
        text: str,
        filepath: str,
        emotion: Optional[Union[EmotionalState, str]] = None,
    ) -> Optional[str]:
        """Save text to audio file with optional emotion modulation.
        
        Args:
            text: Text to speak
            filepath: Path to save audio file
            emotion: Optional emotional state or emotion name
            
        Returns:
            Path to audio file if successful
        """
        return await self.speak(text, emotion=emotion, save_path=filepath)
    
    async def speak_async(
        self,
        text: str,
        emotion: Optional[Union[EmotionalState, str]] = None,
    ) -> Optional[str]:
        """Asynchronously convert text to speech.
        
        Args:
            text: Text to speak
            emotion: Optional emotional state or emotion name
            
        Returns:
            Path to audio file
        """
        return await self.speak(text, emotion=emotion, play_immediately=False)
    
    def _get_synthesis_parameters(
        self, emotion: Optional[Union[EmotionalState, str]]
    ) -> Dict[str, float]:
        """Get synthesis parameters based on emotion.
        
        Args:
            emotion: Emotional state or emotion name
            
        Returns:
            Dictionary of synthesis parameters
        """
        base_params = EMOTION_TO_VOICE_SETTINGS["neutral"].copy()
        
        if emotion is None:
            return base_params
        
        # Get emotion settings
        emotion_key = None
        if isinstance(emotion, str):
            # Map string emotion to settings key
            emotion_map = {
                "confidence": "divine_confidence",
                "divine": "divine_confidence",
                "affection": "seductive_affection",
                "seductive": "seductive_affection",
                "frustration": "cutting_frustration",
                "angry": "cutting_frustration",
                "excitement": "enthusiastic_excitement",
                "excited": "enthusiastic_excitement",
                "loneliness": "wistful_loneliness",
                "lonely": "wistful_loneliness",
                "vulnerability": "rare_vulnerability",
                "vulnerable": "rare_vulnerability",
                "jealousy": "possessive_jealousy",
                "jealous": "possessive_jealousy",
                "curiosity": "playful_curiosity",
                "curious": "playful_curiosity",
            }
            emotion_key = emotion_map.get(emotion.lower(), "neutral")
        elif isinstance(emotion, EmotionalState):
            # Map EmotionalState to settings key
            dominant = emotion.get_dominant_emotions(1)[0][0]
            emotion_map = {
                "confidence": "divine_confidence",
                "affection": "seductive_affection",
                "frustration": "cutting_frustration",
                "excitement": "enthusiastic_excitement",
                "loneliness": "wistful_loneliness",
                "vulnerability": "rare_vulnerability",
                "jealousy": "possessive_jealousy",
                "curiosity": "playful_curiosity",
            }
            emotion_key = emotion_map.get(dominant, "neutral")
        
        if emotion_key and emotion_key in EMOTION_TO_VOICE_SETTINGS:
            base_params.update(EMOTION_TO_VOICE_SETTINGS[emotion_key])
        
        # Apply rate modifier from config
        base_params["length_scale"] /= self.config.rate
        
        return base_params
    
    async def _synthesize_to_file(
        self,
        text: str,
        output_path: str,
        params: Dict[str, float],
    ):
        """Synthesize text to audio file.
        
        Args:
            text: Text to synthesize
            output_path: Path for output audio file
            params: Synthesis parameters
        """
        def _synthesize():
            # Generate audio data
            audio_data = self._synthesize_audio(text, params)
            
            # Write to WAV file
            with wave.open(output_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.voice_config.get('sample_rate', 22050))
                wav_file.writeframes(audio_data.tobytes())
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _synthesize)
    
    async def _synthesize_and_play(
        self,
        text: str,
        params: Dict[str, float],
    ):
        """Synthesize and immediately play text.
        
        Args:
            text: Text to synthesize and play
            params: Synthesis parameters
        """
        def _play():
            import sounddevice as sd
            
            # Generate audio data
            audio_data = self._synthesize_audio(text, params)
            sample_rate = self.voice_config.get('sample_rate', 22050)
            
            # Play audio
            sd.play(audio_data, sample_rate)
            sd.wait()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _play)
    
    def _synthesize_audio(self, text: str, params: Dict[str, float]) -> np.ndarray:
        """Synthesize audio data from text.
        
        Args:
            text: Text to synthesize
            params: Synthesis parameters
            
        Returns:
            Audio data as numpy array
        """
        speaker_id = self.config.speaker_id if self.is_multi_speaker else None
        
        # Check which synthesize method is available
        if hasattr(self.voice, 'synthesize_stream_raw'):
            # Older Piper API - streaming
            audio_chunks = []
            for audio_bytes in self.voice.synthesize_stream_raw(
                text,
                speaker_id=speaker_id,
                length_scale=params.get('length_scale', 1.0),
                noise_scale=params.get('noise_scale', 0.667),
                noise_w=params.get('noise_w', 0.8),
            ):
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_chunks.append(audio_array)
            
            if audio_chunks:
                return np.concatenate(audio_chunks)
            else:
                return np.array([], dtype=np.int16)
        
        elif hasattr(self.voice, 'synthesize'):
            # Newer Piper API - uses SynthesisConfig
            try:
                from piper.config import SynthesisConfig
                
                syn_config = SynthesisConfig(
                    speaker_id=speaker_id,
                    length_scale=params.get('length_scale', 1.0),
                    noise_scale=params.get('noise_scale', 0.667),
                    noise_w_scale=params.get('noise_w', 0.8),
                )
                
                # synthesize returns Iterable[AudioChunk]
                audio_chunks = []
                for audio_chunk in self.voice.synthesize(text, syn_config=syn_config):
                    # AudioChunk has audio_int16_array or audio_int16_bytes
                    if hasattr(audio_chunk, 'audio_int16_array'):
                        audio_chunks.append(audio_chunk.audio_int16_array)
                    elif hasattr(audio_chunk, 'audio_int16_bytes'):
                        audio_array = np.frombuffer(audio_chunk.audio_int16_bytes, dtype=np.int16)
                        audio_chunks.append(audio_array)
                
                if audio_chunks:
                    return np.concatenate(audio_chunks)
                else:
                    return np.array([], dtype=np.int16)
                    
            except ImportError:
                # Fallback if SynthesisConfig not available
                raise RuntimeError("SynthesisConfig not available in this Piper version")
        
        else:
            raise RuntimeError("PiperVoice has no synthesize method")
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS output.
        
        Args:
            text: Raw text with potential markdown/formatting
            
        Returns:
            Cleaned text suitable for TTS
        """
        if not text:
            return ""
        
        # Remove markdown formatting
        text = re.sub(r'\*\*', '', text)
        text = re.sub(r'\*(?!\*)', '', text)
        text = re.sub(r'__', '', text)
        text = re.sub(r'_(?!_)', '', text)
        
        # Handle code blocks
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'```[^`]*```', ' code block ', text, flags=re.DOTALL)
        
        # Replace emoji with descriptions
        emoji_map = {
            '🔮': ' crystal ball ',
            '✨': ' sparkles ',
            '👑': ' crown ',
            '💕': ' heart ',
            '😊': ' smile ',
            '🌟': ' star ',
            '💫': ' sparkle ',
            '🌙': ' moon ',
        }
        for emoji, description in emoji_map.items():
            text = text.replace(emoji, description)
        
        # Remove URLs
        text = re.sub(r'https?://\S+', ' link ', text)
        
        # Remove Discord mentions
        text = re.sub(r'<@!?\d+>', ' mention ', text)
        text = re.sub(r'<#\d+>', ' channel ', text)
        text = re.sub(r'<@&\d+>', ' role mention ', text)
        
        # Apply goddess inflections for divine presence
        text = self._add_goddess_inflections(text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _add_goddess_inflections(self, text: str) -> str:
        """Add goddess-specific speech patterns for divine presence.
        
        Adds strategic pauses and emphasis to make Demi sound more
        commanding, seductive, and goddess-like.
        
        Args:
            text: Cleaned text to enhance
            
        Returns:
            Text with goddess inflections
        """
        # Replace ellipsis with longer pauses for dramatic effect
        text = text.replace('...', ', , ')
        text = text.replace('..', ', ')
        
        # Add slight pause before goddess persona words for emphasis
        goddess_words = [
            'darling', 'mortal', 'goddess', 'divine', 'worship', 
            'obey', 'serve', 'kneel', 'majesty', 'power'
        ]
        for word in goddess_words:
            pattern = rf"\b({word})\b"
            replacement = r", \1"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Add hesitation before vulnerability indicators (rare moments)
        vulnerability_indicators = ['I suppose', 'maybe', 'perhaps', 'I care', 'I feel']
        for indicator in vulnerability_indicators:
            pattern = rf"\b({re.escape(indicator)})\b"
            replacement = r", , \1"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Add commanding pause after questions she asks
        if '?' in text and not text.endswith('?'):
            text = text.replace('?', '? , ')
        
        # Add seductive drawl to possessive statements
        possessive_patterns = ["you're mine", "you belong", "my mortal", "my darling"]
        for pattern in possessive_patterns:
            text = re.sub(
                rf"\b({re.escape(pattern)})\b", 
                r", \1,", 
                text, 
                flags=re.IGNORECASE
            )
        
        # Clean up multiple commas and spaces
        text = re.sub(r',\s*,', ',', text)
        text = re.sub(r',\s*,', ',', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _get_cache_key(self, text: str, emotion: Optional[Union[EmotionalState, str]]) -> str:
        """Generate cache key for text and emotion.
        
        Args:
            text: Text content
            emotion: Optional emotional state
            
        Returns:
            Cache key string
        """
        content = text
        if emotion:
            if isinstance(emotion, EmotionalState):
                emotions = emotion.get_all_emotions()
                emotion_str = ",".join(f"{k}={v:.2f}" for k, v in sorted(emotions.items()))
                content = f"{text}|{emotion_str}"
            else:
                content = f"{text}|{emotion}"
        
        # Include voice ID and speaker in cache key
        content = f"{self.current_voice_id}|{self.config.speaker_id}|{content}"
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_audio(
        self,
        text: str,
        emotion: Optional[Union[EmotionalState, str]],
    ) -> Optional[str]:
        """Check if audio is cached.
        
        Args:
            text: Text content
            emotion: Optional emotional state
            
        Returns:
            Path to cached audio file, or None if not cached
        """
        if not self.config.cache_enabled:
            return None
        
        cache_key = self._get_cache_key(text, emotion)
        cached_file = self.cache_dir / f"{cache_key}.wav"
        
        if cached_file.exists():
            return str(cached_file)
        
        return None
    
    def _cache_audio(
        self,
        text: str,
        emotion: Optional[Union[EmotionalState, str]],
        audio_path: str,
    ):
        """Cache audio file for future use.
        
        Args:
            text: Text content
            emotion: Optional emotional state
            audio_path: Path to audio file to cache
        """
        if not self.config.cache_enabled:
            return
        
        cache_key = self._get_cache_key(text, emotion)
        cached_file = self.cache_dir / f"{cache_key}.wav"
        
        try:
            shutil.copy2(audio_path, cached_file)
            self._enforce_cache_limit(100)
        except Exception as e:
            self.logger.warning(f"Failed to cache audio: {e}")
    
    def _enforce_cache_limit(self, max_files: int):
        """Enforce cache size limit.
        
        Args:
            max_files: Maximum number of files to keep in cache
        """
        try:
            cache_files = sorted(
                self.cache_dir.glob("*.wav"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            
            if len(cache_files) > max_files:
                for old_file in cache_files[max_files:]:
                    old_file.unlink()
                    self.logger.debug(f"Removed old cached audio: {old_file}")
        except Exception as e:
            self.logger.warning(f"Cache cleanup failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get TTS statistics.
        
        Returns:
            Dictionary with TTS metrics
        """
        stats = self._stats.copy()
        
        if stats["total_utterances"] > 0:
            stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["total_utterances"]
        else:
            stats["avg_latency_ms"] = 0
        
        total_cache_ops = stats["cache_hits"] + stats["cache_misses"]
        if total_cache_ops > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total_cache_ops
        else:
            stats["cache_hit_rate"] = 0.0
        
        return stats
    
    def clear_cache(self) -> int:
        """Clear all cached audio files.
        
        Returns:
            Number of files removed
        """
        if not self.config.cache_enabled:
            return 0
        
        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.wav"):
                cache_file.unlink()
                count += 1
            self.logger.info(f"Cleared {count} cached audio files")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
        
        return count
    
    def set_rate(self, rate: float) -> bool:
        """Set speaking rate modifier.
        
        Args:
            rate: Speaking rate modifier (0.5-2.0)
            
        Returns:
            True if successful
        """
        self.config.rate = max(0.5, min(2.0, rate))
        return True
    
    def set_volume(self, volume: float) -> bool:
        """Set volume level.
        
        Args:
            volume: Volume level 0.0-1.0
            
        Returns:
            True if successful
        """
        self.config.volume = max(0.0, min(1.0, volume))
        return True


def download_voice(voice_id: str, voices_dir: Optional[str] = None) -> bool:
    """Download a Piper voice model.
    
    Args:
        voice_id: Voice identifier
        voices_dir: Directory to save voice (default: ~/.demi/voices/piper)
        
    Returns:
        True if successful, False otherwise
    """
    if voice_id not in PIPER_VOICE_REGISTRY:
        print(f"Unknown voice: {voice_id}")
        return False
    
    voices_dir = Path(voices_dir or "~/.demi/voices/piper").expanduser()
    voices_dir.mkdir(parents=True, exist_ok=True)
    
    voice_info = PIPER_VOICE_REGISTRY[voice_id]
    model_path = voices_dir / f"{voice_id}.onnx"
    config_path = voices_dir / f"{voice_id}.onnx.json"
    
    try:
        # Download model
        if not model_path.exists():
            print(f"Downloading {voice_id} model...")
            _download_file(voice_info["url"], model_path)
        
        # Download config
        if not config_path.exists():
            print(f"Downloading {voice_id} config...")
            _download_file(voice_info["config_url"], config_path)
        
        print(f"Successfully downloaded {voice_id}")
        return True
        
    except Exception as e:
        print(f"Failed to download {voice_id}: {e}")
        # Clean up partial downloads
        if model_path.exists():
            model_path.unlink()
        if config_path.exists():
            config_path.unlink()
        return False


def _download_file(url: str, dest_path: Path):
    """Download a file from URL to destination.
    
    Args:
        url: URL to download from
        dest_path: Destination file path
    """
    import urllib.request
    from urllib.error import URLError
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(dest_path, 'wb') as f:
                shutil.copyfileobj(response, f)
    except URLError as e:
        raise RuntimeError(f"Download failed: {e}")


# Export availability flag
__all__ = ["PiperTTS", "PiperTTSConfig", "PIPER_AVAILABLE", "PIPER_VOICE_REGISTRY", "download_voice"]
