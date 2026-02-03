"""
Text-to-Speech Engine for Demi using pyttsx3.

Provides cross-platform TTS with emotional modulation, voice selection,
and audio file generation for Discord voice playback.

Target latency: <2 seconds for typical responses (<100 words).
"""

import asyncio
import hashlib
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import pyttsx3

from src.core.logger import get_logger
from src.emotion.models import EmotionalState
from src.voice.emotion_voice import EmotionVoiceMapper, VoiceParameters


@dataclass
class TTSConfig:
    """Configuration for TTS engine.

    Attributes:
        voice_id: Voice identifier (None = system default)
        rate: Words per minute (default 150)
        volume: Audio level 0.0-1.0 (default 1.0)
        output_format: Audio format ("wav", "mp3")
        cache_enabled: Whether to cache audio files
        cache_dir: Directory for cached audio files
    """

    voice_id: Optional[str] = None
    rate: int = 150
    volume: float = 1.0
    output_format: str = "wav"
    cache_enabled: bool = True
    cache_dir: str = "~/.demi/tts_cache"


class TextToSpeech:
    """Text-to-Speech engine using pyttsx3 backend.

    Converts text responses to spoken audio with emotional modulation
    based on Demi's current emotional state. Supports both immediate
    playback and file generation for Discord voice channels.

    Features:
    - Cross-platform TTS (Windows: SAPI5, macOS: NSSpeechSynthesizer, Linux: espeak)
    - Emotional voice modulation (rate, volume, pitch)
    - Voice selection with female voice preference
    - Audio caching for reduced latency
    - Async support for non-blocking operation
    - Text cleaning for optimal TTS output
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        """Initialize the TTS engine.

        Args:
            config: TTS configuration (uses defaults if None)
        """
        self.config = config or TTSConfig()
        self.logger = get_logger()
        self.emotion_mapper = EmotionVoiceMapper()

        # Initialize pyttsx3 engine
        try:
            self.engine = pyttsx3.init()
            self._initialize_voice_properties()
            self.logger.info("TTS engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS engine: {e}")
            self.engine = None

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
        }

    def _initialize_voice_properties(self):
        """Initialize voice properties from configuration."""
        if self.engine is None:
            return

        # Set rate
        self.engine.setProperty("rate", self.config.rate)

        # Set volume
        self.engine.setProperty("volume", self.config.volume)

        # Set voice if specified
        if self.config.voice_id:
            self.set_voice(self.config.voice_id)
        else:
            # Try to select a female voice by default
            self._select_female_voice()

    def _select_female_voice(self) -> bool:
        """Attempt to select a female voice matching the goddess persona.

        Returns:
            True if a female voice was selected, False otherwise
        """
        if self.engine is None:
            return False

        voices = self.engine.getProperty("voices")

        # Look for female voices (common patterns)
        female_patterns = ["female", "woman", "girl", "femme", "zira", "hazel", "samantha"]

        for voice in voices:
            voice_name = voice.name.lower()
            voice_id = voice.id.lower()

            # Check for female voice indicators
            for pattern in female_patterns:
                if pattern in voice_name or pattern in voice_id:
                    try:
                        self.engine.setProperty("voice", voice.id)
                        self._stats["preferred_voice"] = voice.id
                        self.logger.info(f"Selected female voice: {voice.name}")
                        return True
                    except Exception as e:
                        self.logger.warning(f"Failed to set voice {voice.name}: {e}")

        self.logger.info("No female voice found, using system default")
        return False

    def list_voices(self) -> list[dict]:
        """List available system voices.

        Returns:
            List of voice dictionaries with id, name, gender, and language
        """
        if self.engine is None:
            self.logger.error("TTS engine not initialized")
            return []

        voices = self.engine.getProperty("voices")
        voice_list = []

        for voice in voices:
            voice_info = {
                "id": voice.id,
                "name": voice.name,
                "languages": getattr(voice, "languages", ["unknown"]),
                "gender": getattr(voice, "gender", "unknown"),
            }
            voice_list.append(voice_info)

        return voice_list

    def set_voice(self, voice_id: str) -> bool:
        """Set TTS voice by ID.

        Args:
            voice_id: Voice identifier string

        Returns:
            True if successful, False otherwise
        """
        if self.engine is None:
            return False

        try:
            self.engine.setProperty("voice", voice_id)
            self.config.voice_id = voice_id
            self._stats["preferred_voice"] = voice_id
            self.logger.info(f"Voice set to: {voice_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set voice {voice_id}: {e}")
            return False

    def set_rate(self, rate: int) -> bool:
        """Set speaking rate (words per minute).

        Args:
            rate: Speaking rate in WPM (100-300)

        Returns:
            True if successful, False otherwise
        """
        if self.engine is None:
            return False

        try:
            clamped_rate = max(100, min(300, rate))
            self.engine.setProperty("rate", clamped_rate)
            self.config.rate = clamped_rate
            return True
        except Exception as e:
            self.logger.error(f"Failed to set rate: {e}")
            return False

    def set_volume(self, volume: float) -> bool:
        """Set volume level.

        Args:
            volume: Volume level 0.0-1.0

        Returns:
            True if successful, False otherwise
        """
        if self.engine is None:
            return False

        try:
            clamped_volume = max(0.0, min(1.0, volume))
            self.engine.setProperty("volume", clamped_volume)
            self.config.volume = clamped_volume
            return True
        except Exception as e:
            self.logger.error(f"Failed to set volume: {e}")
            return False

    async def speak(
        self,
        text: str,
        emotion_state: Optional[EmotionalState] = None,
        save_path: Optional[str] = None,
        play_immediately: bool = False,
    ) -> Optional[str]:
        """Convert text to speech with optional emotion modulation.

        Args:
            text: Text to speak
            emotion_state: Optional emotional state for voice modulation
            save_path: Optional path to save audio file (if None, temp file created)
            play_immediately: If True, play audio immediately (blocking)

        Returns:
            Path to audio file if saved, None if played immediately
        """
        if self.engine is None:
            self.logger.error("TTS engine not initialized")
            return None

        if not text or not text.strip():
            self.logger.warning("Empty text provided to TTS")
            return None

        start_time = time.time()

        # Clean text for TTS
        clean_text = self._clean_text_for_tts(text)

        # Apply emotion modulation if provided
        if emotion_state:
            voice_params = self.emotion_mapper.map_emotion_to_voice(emotion_state)
            await self._apply_voice_parameters(voice_params)
            # Add emotional emphasis to text
            clean_text = self.emotion_mapper.preprocess_for_emphasis(
                clean_text, voice_params.emphasis
            )
            clean_text = self.emotion_mapper.add_goddess_inflections(clean_text)

        # Determine output path
        if save_path:
            output_path = save_path
        elif not play_immediately:
            output_path = tempfile.mktemp(suffix=f".{self.config.output_format}")
        else:
            output_path = None

        # Check cache if enabled and no custom save path
        cache_hit = False
        if self.config.cache_enabled and not save_path and output_path:
            cached_path = self._get_cached_audio(clean_text, emotion_state)
            if cached_path:
                output_path = cached_path
                cache_hit = True
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1

        try:
            if output_path and not cache_hit:
                # Synthesize to file
                await self._synthesize_to_file(clean_text, output_path)

                # Cache the result if caching is enabled
                if self.config.cache_enabled and not save_path:
                    self._cache_audio(clean_text, emotion_state, output_path)

            elif play_immediately:
                # Play immediately (blocking)
                await self._synthesize_and_play(clean_text)

            # Update statistics
            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_utterances"] += 1
            self._stats["total_latency_ms"] += latency_ms

            self.logger.debug(f"TTS synthesis completed in {latency_ms:.1f}ms")

            return output_path if output_path else None

        except Exception as e:
            self.logger.error(f"TTS synthesis failed: {e}")
            return None

    async def speak_async(
        self,
        text: str,
        emotion_state: Optional[EmotionalState] = None,
        save_path: Optional[str] = None,
    ) -> Optional[str]:
        """Asynchronously convert text to speech (non-blocking).

        This is an alias for speak() with play_immediately=False.

        Args:
            text: Text to speak
            emotion_state: Optional emotional state for voice modulation
            save_path: Optional path to save audio file

        Returns:
            Path to audio file
        """
        return await self.speak(text, emotion_state, save_path, play_immediately=False)

    async def speak_to_file(
        self,
        text: str,
        filepath: str,
        emotion_state: Optional[EmotionalState] = None,
    ) -> Optional[str]:
        """Save text to audio file with optional emotion modulation.

        Args:
            text: Text to speak
            filepath: Path to save audio file
            emotion_state: Optional emotional state for voice modulation

        Returns:
            Path to audio file if successful
        """
        return await self.speak(text, emotion_state, save_path=filepath)

    async def speak_response(
        self, response_dict: dict, auto_play: bool = False
    ) -> Optional[str]:
        """Speak a processed LLM response with emotion modulation.

        Args:
            response_dict: Response dictionary with keys:
                - "content": Response text
                - "emotion_state": Dict of emotional values
                - "message_id": Optional tracking ID
            auto_play: If True, play audio immediately. If False, return path.

        Returns:
            Audio file path if auto_play=False, None otherwise
        """
        content = response_dict.get("content", "")
        emotion_state_dict = response_dict.get("emotion_state", {})

        # Convert dict to EmotionalState if needed
        if emotion_state_dict:
            emotion_state = EmotionalState.from_dict(emotion_state_dict)
        else:
            emotion_state = None

        # Clean text for TTS
        clean_text = self._clean_text_for_tts(content)

        if auto_play:
            await self.speak(clean_text, emotion_state=emotion_state, play_immediately=True)
            return None
        else:
            temp_path = tempfile.mktemp(suffix=f".{self.config.output_format}")
            return await self.speak(
                clean_text, emotion_state=emotion_state, save_path=temp_path
            )

    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS output.

        Removes markdown, code blocks, and other formatting that
        doesn't translate well to speech.

        Args:
            text: Raw text with potential markdown/formatting

        Returns:
            Cleaned text suitable for TTS
        """
        if not text:
            return ""

        # Remove markdown bold/italic
        text = re.sub(r"\*\*", "", text)  # Bold
        text = re.sub(r"\*(?!\*)", "", text)  # Italic
        text = re.sub(r"__", "", text)  # Bold
        text = re.sub(r"_(?!_)", "", text)  # Italic

        # Replace code blocks with verbal description
        text = re.sub(r"`([^`]+)`", r"\1", text)  # Inline code - just keep content
        text = re.sub(r"```[^`]*```", " code block ", text, flags=re.DOTALL)

        # Replace emoji with descriptions
        emoji_map = {
            "🔮": " crystal ball ",
            "✨": " sparkles ",
            "👑": " crown ",
            "💕": " heart ",
            "😊": " smile ",
            "🌟": " star ",
            "💫": " sparkle ",
            "🌙": " moon ",
        }
        for emoji, description in emoji_map.items():
            text = text.replace(emoji, description)

        # Remove URLs (replace with "link")
        text = re.sub(r"https?://\S+", " link ", text)

        # Remove Discord mentions
        text = re.sub(r"<@!?\d+>", " mention ", text)
        text = re.sub(r"<#\d+>", " channel ", text)
        text = re.sub(r"<@&\d+>", " role mention ", text)

        # Clean up whitespace
        text = " ".join(text.split())

        return text.strip()

    async def _apply_voice_parameters(self, params: VoiceParameters):
        """Apply voice parameters to pyttsx3 engine.

        Args:
            params: VoiceParameters to apply
        """
        if self.engine is None:
            return

        # Apply rate
        self.engine.setProperty("rate", params.rate)

        # Apply volume
        self.engine.setProperty("volume", params.volume)

        # Note: pyttsx3 doesn't support direct pitch control
        # Pitch modulation would need SSML or audio post-processing
        # For now, we log the intended pitch
        if params.pitch != 1.0:
            self.logger.debug(f"Pitch modulation requested: {params.pitch} (not directly supported)")

    async def _synthesize_to_file(self, text: str, output_path: str):
        """Synthesize text to audio file.

        Runs in thread pool since pyttsx3 is blocking.

        Args:
            text: Text to synthesize
            output_path: Path for output audio file
        """
        if self.engine is None:
            raise RuntimeError("TTS engine not initialized")

        def _synthesize():
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _synthesize)

    async def _synthesize_and_play(self, text: str):
        """Synthesize and immediately play text.

        Runs in thread pool since pyttsx3 is blocking.

        Args:
            text: Text to synthesize and play
        """
        if self.engine is None:
            raise RuntimeError("TTS engine not initialized")

        def _speak():
            self.engine.say(text)
            self.engine.runAndWait()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _speak)

    def _get_cache_key(self, text: str, emotion_state: Optional[EmotionalState]) -> str:
        """Generate cache key for text and emotion state.

        Args:
            text: Text content
            emotion_state: Optional emotional state

        Returns:
            Cache key string
        """
        # Create deterministic key from text and emotion
        content = text
        if emotion_state:
            emotions = emotion_state.get_all_emotions()
            emotion_str = ",".join(f"{k}={v:.2f}" for k, v in sorted(emotions.items()))
            content = f"{text}|{emotion_str}"

        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_audio(
        self, text: str, emotion_state: Optional[EmotionalState]
    ) -> Optional[str]:
        """Check if audio is cached and return path if found.

        Args:
            text: Text content
            emotion_state: Optional emotional state

        Returns:
            Path to cached audio file, or None if not cached
        """
        if not self.config.cache_enabled:
            return None

        cache_key = self._get_cache_key(text, emotion_state)
        cached_file = self.cache_dir / f"{cache_key}.{self.config.output_format}"

        if cached_file.exists():
            return str(cached_file)

        return None

    def _cache_audio(
        self, text: str, emotion_state: Optional[EmotionalState], audio_path: str
    ):
        """Cache audio file for future use.

        Args:
            text: Text content
            emotion_state: Optional emotional state
            audio_path: Path to audio file to cache
        """
        if not self.config.cache_enabled:
            return

        cache_key = self._get_cache_key(text, emotion_state)
        cached_file = self.cache_dir / f"{cache_key}.{self.config.output_format}"

        try:
            # Copy file to cache
            import shutil

            shutil.copy2(audio_path, cached_file)

            # Limit cache size (keep most recent 100 files)
            self._enforce_cache_limit(100)
        except Exception as e:
            self.logger.warning(f"Failed to cache audio: {e}")

    def _enforce_cache_limit(self, max_files: int):
        """Enforce cache size limit by removing oldest files.

        Args:
            max_files: Maximum number of files to keep in cache
        """
        try:
            cache_files = sorted(
                self.cache_dir.glob(f"*.{self.config.output_format}"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )

            if len(cache_files) > max_files:
                for old_file in cache_files[max_files:]:
                    old_file.unlink()
                    self.logger.debug(f"Removed old cached audio: {old_file}")
        except Exception as e:
            self.logger.warning(f"Cache cleanup failed: {e}")

    def get_available_voices(self) -> list[dict]:
        """Get list of available voices (alias for list_voices).

        Returns:
            List of voice dictionaries
        """
        return self.list_voices()

    def get_stats(self) -> dict:
        """Get TTS statistics.

        Returns:
            Dictionary with TTS metrics:
            - total_utterances: Total number of synthesis operations
            - avg_latency_ms: Average synthesis latency in milliseconds
            - cache_hit_rate: Cache hit rate (0.0-1.0)
            - preferred_voice: Currently selected voice ID
        """
        stats = self._stats.copy()

        # Calculate average latency
        if stats["total_utterances"] > 0:
            stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["total_utterances"]
        else:
            stats["avg_latency_ms"] = 0

        # Calculate cache hit rate
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
            for cache_file in self.cache_dir.glob(f"*.{self.config.output_format}"):
                cache_file.unlink()
                count += 1
            self.logger.info(f"Cleared {count} cached audio files")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")

        return count
