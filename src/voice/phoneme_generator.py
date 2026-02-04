"""Phoneme generator for lip sync animation.

Converts text to phoneme timings for synchronizing avatar mouth animations
with speech. Uses malsami for text-to-phoneme conversion and maps to VRM
viseme targets (aa, ih, ou, E, oh).
"""

import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

from src.core.logger import get_logger

logger = get_logger()

# Try to import g2p_en for phoneme conversion
try:
    from g2p_en.g2p import G2p
    G2P_AVAILABLE = True
except ImportError:
    G2P_AVAILABLE = False


class Viseme(str, Enum):
    """VRM viseme targets for mouth shapes."""
    AA = "aa"      # Open mouth vowel (ah, a, aa)
    IH = "ih"      # Front closed vowel (ee, i, y)
    OU = "ou"      # Rounded back vowel (oh, o, oo, u)
    E = "E"        # Mid-front vowel (eh, e, ae)
    NEUTRAL = "neutral"  # Closed mouth / neutral position


# Phoneme to viseme mapping (ARPAbet phonemes to VRM visemes)
PHONEME_TO_VISEME = {
    # Vowels
    "AA": Viseme.AA,      # father, lot
    "AE": Viseme.E,       # trap, bat
    "AH": Viseme.AA,      # strut, cut
    "AO": Viseme.OU,      # thought, lot
    "AW": Viseme.OU,      # mouth, now
    "AY": Viseme.AA,      # price, my
    "EH": Viseme.E,       # dress, bed
    "ER": Viseme.E,       # nurse, bird
    "EY": Viseme.E,       # face, day
    "IH": Viseme.IH,      # kit, hit
    "IY": Viseme.IH,      # fleece, see
    "OW": Viseme.OU,      # goat, go
    "OY": Viseme.OU,      # choice, boy
    "UH": Viseme.OU,      # foot, pull
    "UW": Viseme.OU,      # goose, blue
    "Y": Viseme.IH,       # yes (approximant)

    # Consonants - generally neutral/silent (keep mouth position)
    # But some consonants may have slight mouth positions
    "B": Viseme.NEUTRAL,  # Bilabial closure
    "D": Viseme.NEUTRAL,
    "F": Viseme.NEUTRAL,  # Labiodental
    "G": Viseme.NEUTRAL,
    "HH": Viseme.NEUTRAL,
    "JH": Viseme.IH,      # Palatal (slightly forward)
    "K": Viseme.NEUTRAL,
    "L": Viseme.IH,       # Lateral (tongue forward)
    "M": Viseme.NEUTRAL,  # Bilabial
    "N": Viseme.NEUTRAL,
    "NG": Viseme.NEUTRAL,
    "P": Viseme.NEUTRAL,  # Bilabial
    "R": Viseme.OU,       # Rhotic (lips slightly rounded)
    "S": Viseme.IH,       # Dental sibilant
    "SH": Viseme.IH,      # Postalveolar
    "T": Viseme.NEUTRAL,
    "TH": Viseme.NEUTRAL,
    "V": Viseme.NEUTRAL,  # Labiodental
    "W": Viseme.OU,       # Rounded approximant
    "Z": Viseme.IH,       # Alveolar sibilant
    "ZH": Viseme.IH,      # Postalveolar fricative
}


@dataclass
class PhonemeFrame:
    """Single phoneme frame for lip sync animation.

    Attributes:
        time: Time in seconds when this phoneme should be active
        viseme: Viseme target (aa, ih, ou, E, neutral)
        weight: Blend shape weight 0.0-1.0 (1.0 = full intensity)
        duration: Optional duration of this phoneme in seconds
    """
    time: float
    viseme: str
    weight: float = 1.0
    duration: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class LipSyncData:
    """Complete lip sync data for a response.

    Attributes:
        audioUrl: URL to audio file
        phonemes: List of phoneme frames
        duration: Total duration in seconds
    """
    audioUrl: str
    phonemes: List[PhonemeFrame]
    duration: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "audioUrl": self.audioUrl,
            "phonemes": [p.to_dict() for p in self.phonemes],
            "duration": self.duration,
        }


class PhonemeGenerator:
    """Generate phoneme timings for lip sync animation.

    Converts text to phonemes, estimates timing based on audio duration,
    and maps phonemes to VRM viseme targets.
    """

    def __init__(self):
        """Initialize phoneme generator."""
        self.logger = logger

        if not G2P_AVAILABLE:
            self.logger.warning(
                "g2p_en not installed. Phoneme generation will use fallback. "
                "Install with: pip install g2p_en"
            )

    def generate_phonemes(
        self,
        text: str,
        audio_duration: float,
        speech_rate: float = 1.0,
    ) -> List[PhonemeFrame]:
        """Generate phoneme frames from text and audio duration.

        Args:
            text: Text to generate phonemes for
            audio_duration: Duration of audio in seconds
            speech_rate: Speech rate modifier (1.0 = normal)

        Returns:
            List of phoneme frames with timing
        """
        if not text or not text.strip():
            return []

        try:
            # Get phonemes from text
            if G2P_AVAILABLE:
                phoneme_list = self._get_phonemes_g2p(text)
            else:
                phoneme_list = self._get_phonemes_fallback(text)

            if not phoneme_list:
                self.logger.warning(f"No phonemes generated for: {text}")
                return []

            # Estimate timing for each phoneme
            frames = self._estimate_timing(
                phoneme_list,
                audio_duration,
                speech_rate,
            )

            return frames

        except Exception as e:
            self.logger.error(f"Phoneme generation failed: {e}")
            return []

    def _get_phonemes_g2p(self, text: str) -> List[str]:
        """Get phonemes using g2p_en library.

        Args:
            text: Text to convert

        Returns:
            List of phonemes in ARPAbet format
        """
        try:
            g2p = G2p()
            phonemes = g2p(text)

            # g2p_en returns list of phoneme strings and spaces
            # Filter out spaces and convert to uppercase
            return [p.upper() for p in phonemes if p.strip() and p != ' ']

        except Exception as e:
            self.logger.warning(f"g2p_en phoneme generation failed: {e}")
            return []

    def _get_phonemes_fallback(self, text: str) -> List[str]:
        """Fallback phoneme generation using simple heuristics.

        This is a basic fallback that splits text into syllables and
        estimates phoneme sequences. For production, use malsami or
        another proper phoneme converter.

        Args:
            text: Text to convert

        Returns:
            List of estimated phonemes
        """
        # Clean text
        text = text.lower().strip()
        text = re.sub(r'[^a-z\s]', '', text)

        if not text:
            return []

        # Very basic vowel detection
        # This is a last-resort fallback - real implementation needs malsami
        phonemes = []
        vowels = "aeiou"

        for char in text:
            if char in vowels:
                # Map to ARPAbet vowel
                phonemes.append(char.upper())
            elif char.isalpha():
                # Map consonants to basic ARPAbet
                phonemes.append(char.upper())

        return phonemes if phonemes else []

    def _estimate_timing(
        self,
        phonemes: List[str],
        total_duration: float,
        speech_rate: float = 1.0,
    ) -> List[PhonemeFrame]:
        """Estimate timing for phonemes based on total audio duration.

        Distributes phonemes evenly across audio duration, accounting for
        natural speech patterns (vowels longer, consonants shorter).

        Args:
            phonemes: List of phoneme strings
            total_duration: Total audio duration in seconds
            speech_rate: Speech rate modifier (1.0 = normal, 0.5 = slower)

        Returns:
            List of phoneme frames with timing
        """
        if not phonemes:
            return []

        # Adjust duration by speech rate
        adjusted_duration = total_duration / speech_rate

        frames = []

        # Estimate phoneme duration based on type
        # Vowels typically 80-140ms, consonants 20-100ms
        phoneme_durations = []
        for phoneme in phonemes:
            if phoneme in ["AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
                          "IH", "IY", "OW", "OY", "UH", "UW"]:
                # Vowel - longer duration
                duration = 0.1  # 100ms base
            else:
                # Consonant - shorter duration
                duration = 0.04  # 40ms base

            phoneme_durations.append(duration)

        # Normalize to fit total duration
        total_est_duration = sum(phoneme_durations)
        scale_factor = adjusted_duration / total_est_duration if total_est_duration > 0 else 1.0

        # Cap scale factor to reasonable range (0.5x to 2x of estimated)
        scale_factor = min(2.0, max(0.5, scale_factor))

        # Generate frames
        current_time = 0.0
        for phoneme, base_duration in zip(phonemes, phoneme_durations):
            scaled_duration = base_duration * scale_factor

            # Skip very short durations
            if scaled_duration < 0.01:
                continue

            # Map phoneme to viseme
            viseme = PHONEME_TO_VISEME.get(phoneme, Viseme.NEUTRAL)

            # Create frame
            frame = PhonemeFrame(
                time=current_time,
                viseme=viseme.value,
                weight=1.0,
                duration=scaled_duration,
            )
            frames.append(frame)

            current_time += scaled_duration

        # Add a final neutral frame to reset mouth
        if frames and current_time < adjusted_duration:
            frames.append(
                PhonemeFrame(
                    time=min(current_time, adjusted_duration),
                    viseme=Viseme.NEUTRAL.value,
                    weight=0.0,
                    duration=0.0,
                )
            )

        return frames

    def create_lip_sync_data(
        self,
        text: str,
        audio_url: str,
        audio_duration: float,
        speech_rate: float = 1.0,
    ) -> LipSyncData:
        """Create complete lip sync data for a response.

        Args:
            text: Text that was spoken
            audio_url: URL to audio file
            audio_duration: Duration of audio in seconds
            speech_rate: Speech rate modifier (1.0 = normal)

        Returns:
            LipSyncData object ready for serialization
        """
        phonemes = self.generate_phonemes(text, audio_duration, speech_rate)

        return LipSyncData(
            audioUrl=audio_url,
            phonemes=phonemes,
            duration=audio_duration,
        )


# Export
__all__ = [
    "PhonemeGenerator",
    "PhonemeFrame",
    "LipSyncData",
    "Viseme",
    "PHONEME_TO_VISEME",
]
