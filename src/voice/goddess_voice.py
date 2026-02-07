"""
Goddess Voice Processor - Audio Enhancement for Divine Voice

Adds ethereal, angelic qualities to TTS output:
- Reverb (cathedral-like space)
- Pitch shifting (slightly higher)
- Compression (controlled dynamics)
- EQ enhancement (presence peak, warmth)
- Optional: Auto-tune for perfect pitch
"""

import os
import numpy as np
import asyncio
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.core.logger import get_logger

# Try to import audio libraries
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import pyloudnorm
    PYLOUDNORM_AVAILABLE = True
except ImportError:
    PYLOUDNORM_AVAILABLE = False


@dataclass
class GoddessVoiceConfig:
    """Configuration for goddess voice enhancement."""

    # Reverb settings (cathedral-like)
    reverb_enabled: bool = True
    reverb_room_scale: float = 0.8  # 0.0-1.0 (larger = more reverb)
    reverb_wetness: float = 0.3  # 0.0-1.0 (0.3 = subtle, 0.5+ = obvious)

    # Pitch shifting (make voice slightly higher, more ethereal)
    pitch_shift_semitones: float = 1.5  # Slight raise for "divine" quality

    # Compression (control dynamics, add presence)
    compression_enabled: bool = True
    compression_threshold_db: float = -20.0
    compression_ratio: float = 4.0  # 4:1 compression

    # EQ enhancement
    eq_enabled: bool = True
    presence_peak_hz: float = 3000.0  # Adds clarity/presence
    presence_peak_db: float = 4.0
    warmth_hz: float = 200.0  # Adds warmth
    warmth_db: float = 2.0

    # Normalization
    normalize_loudness: bool = True
    target_loudness_lufs: float = -14.0  # Broadcast standard

    # Overall characteristics
    breathiness: float = 0.1  # 0.0-1.0, adds subtle air/shimmer
    etherealness: float = 0.5  # 0.0-1.0, blend of effects


class GoddessVoiceProcessor:
    """Process TTS audio to sound divine/ethereal."""

    def __init__(self, config: Optional[GoddessVoiceConfig] = None):
        self.config = config or GoddessVoiceConfig()
        self.logger = get_logger()

        if not LIBROSA_AVAILABLE or not SCIPY_AVAILABLE:
            self.logger.warning(
                "Goddess voice processor requires librosa and scipy. "
                "Install: pip install librosa scipy soundfile pyloudnorm"
            )

    async def process(self, audio_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Process audio to enhance goddess qualities.

        Args:
            audio_path: Path to input audio file
            output_path: Path to save processed audio (uses input path if None)

        Returns:
            Path to processed audio file, or None if processing failed
        """
        if not LIBROSA_AVAILABLE or not SCIPY_AVAILABLE:
            self.logger.warning("Cannot process: librosa/scipy not installed")
            return audio_path  # Return original

        try:
            output_path = output_path or audio_path

            # Run processing in thread pool (can be slow)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._process_sync,
                audio_path,
                output_path
            )
            return result

        except Exception as e:
            self.logger.error(f"Goddess voice processing failed: {e}")
            return audio_path  # Return original on error

    def _process_sync(self, audio_path: str, output_path: str) -> str:
        """Synchronous audio processing."""

        # Load audio
        self.logger.debug(f"Loading audio: {audio_path}")
        y, sr = librosa.load(audio_path, sr=None)

        # Apply enhancements
        y = self._apply_pitch_shift(y, sr)
        y = self._apply_reverb(y, sr)
        y = self._apply_compression(y)
        y = self._apply_eq(y, sr)
        y = self._add_breathiness(y)
        y = self._normalize_loudness(y, sr)

        # Save processed audio
        sf.write(output_path, y, sr)
        self.logger.debug(f"Saved processed audio: {output_path}")

        return output_path

    def _apply_pitch_shift(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Apply subtle pitch shift for ethereal quality."""
        if self.config.pitch_shift_semitones == 0:
            return y

        self.logger.debug(f"Pitch shifting: {self.config.pitch_shift_semitones} semitones")
        y_shifted = librosa.effects.pitch_shift(
            y,
            sr=sr,
            n_steps=self.config.pitch_shift_semitones
        )
        return y_shifted

    def _apply_reverb(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Apply cathedral-like reverb."""
        if not self.config.reverb_enabled or self.config.reverb_wetness == 0:
            return y

        self.logger.debug(f"Applying reverb (wetness: {self.config.reverb_wetness})")

        # Simple reverb using delay + feedback
        room_size = int(self.config.reverb_room_scale * sr * 0.05)  # Up to 50ms delay
        y_reverb = self._simple_reverb(y, room_size, self.config.reverb_wetness)

        return y_reverb

    @staticmethod
    def _simple_reverb(y: np.ndarray, delay_samples: int, wetness: float) -> np.ndarray:
        """Simple reverb using delaying and feedback."""
        if delay_samples <= 0:
            return y

        # Pad audio with zeros for delay
        y_delayed = np.zeros(len(y) + delay_samples)
        y_delayed[:len(y)] = y

        # Create delayed copies with feedback
        reverb = np.zeros_like(y_delayed)
        reverb[:len(y)] = y

        # Add delayed version (creates echo/reverb effect)
        decay = 0.5
        for i in range(3):  # 3 reflections
            delay = delay_samples * (i + 1)
            if delay < len(y_delayed):
                y_delayed[delay:delay+len(y)] += y * (decay ** (i + 1))

        # Blend wet and dry
        return y * (1 - wetness) + y_delayed[:len(y)] * wetness

    def _apply_compression(self, y: np.ndarray) -> np.ndarray:
        """Apply dynamic range compression for presence."""
        if not self.config.compression_enabled:
            return y

        self.logger.debug("Applying compression")

        threshold = 10 ** (self.config.compression_threshold_db / 20)
        ratio = self.config.compression_ratio

        # Simple compressor
        abs_y = np.abs(y)
        mask = abs_y > threshold

        y_compressed = y.copy()
        y_compressed[mask] = np.sign(y[mask]) * (
            threshold + (abs_y[mask] - threshold) / ratio
        )

        return y_compressed

    def _apply_eq(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Apply EQ to enhance presence and warmth."""
        if not self.config.eq_enabled:
            return y

        self.logger.debug("Applying EQ enhancement")
        y_eq = y.copy()

        # Presence peak (clarity)
        if self.config.presence_peak_db != 0:
            y_eq = self._apply_peak_filter(
                y_eq, sr,
                self.config.presence_peak_hz,
                self.config.presence_peak_db,
                q=2.0
            )

        # Warmth boost
        if self.config.warmth_db != 0:
            y_eq = self._apply_peak_filter(
                y_eq, sr,
                self.config.warmth_hz,
                self.config.warmth_db,
                q=0.7
            )

        return y_eq

    @staticmethod
    def _apply_peak_filter(y: np.ndarray, sr: int, freq: float, gain_db: float, q: float) -> np.ndarray:
        """Apply peaking EQ filter."""
        if not SCIPY_AVAILABLE:
            return y

        # Convert gain to linear
        gain_linear = 10 ** (gain_db / 20)

        # Design peaking filter
        w0 = 2 * np.pi * freq / sr
        alpha = np.sin(w0) / (2 * q)

        b = np.array([
            1 + alpha * gain_linear,
            -2 * np.cos(w0),
            1 - alpha * gain_linear
        ])
        a = np.array([
            1 + alpha / gain_linear,
            -2 * np.cos(w0),
            1 - alpha / gain_linear
        ])

        # Apply filter
        return signal.lfilter(b, a, y)

    def _add_breathiness(self, y: np.ndarray) -> np.ndarray:
        """Add subtle air/shimmer for ethereal quality."""
        if self.config.breathiness == 0:
            return y

        self.logger.debug(f"Adding breathiness: {self.config.breathiness}")

        # Add high-frequency shimmer (white noise filtered)
        noise = np.random.randn(len(y)) * 0.01
        shimmer = noise * self.config.breathiness

        return y + shimmer

    def _normalize_loudness(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Normalize loudness to broadcast standard."""
        if not self.config.normalize_loudness:
            return y

        self.logger.debug(f"Normalizing to {self.config.target_loudness_lufs} LUFS")

        if PYLOUDNORM_AVAILABLE:
            try:
                meter = pyloudnorm.Meter(sr)
                loudness = meter.integrated_loudness(y)

                if loudness > -40:  # Valid measurement
                    normalized = pyloudnorm.normalize(meter, y, self.config.target_loudness_lufs)
                    return normalized
            except Exception:
                pass

        # Fallback: simple peak normalization
        peak = np.max(np.abs(y))
        if peak > 0:
            y = y * (0.95 / peak)  # Normalize to 0.95 to prevent clipping

        return y
