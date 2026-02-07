"""
Base interface for TTS backends.

All TTS backends must implement the TTSBackend interface for consistent
integration with the main TTS engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import asyncio


@dataclass
class TTSVoice:
    """Represents a TTS voice."""
    id: str
    name: str
    language: str
    gender: str = "unknown"
    description: str = ""


@dataclass
class TTSBackendConfig:
    """Configuration for a TTS backend."""
    voice_id: Optional[str] = None
    rate: float = 1.0
    volume: float = 1.0
    cache_enabled: bool = True
    cache_dir: str = "~/.demi/tts_cache"
    device: str = "auto"  # "auto", "cpu", "cuda", "mps"
    
    # Backend-specific settings
    extra_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_settings is None:
            self.extra_settings = {}


class TTSBackend(ABC):
    """Abstract base class for TTS backends."""
    
    def __init__(self, config: TTSBackendConfig):
        self.config = config
        self._initialized = False
        self._stats = {
            "total_utterances": 0,
            "total_latency_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available (dependencies installed)."""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the backend. Returns True if successful."""
        pass
    
    @abstractmethod
    async def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Synthesize text to audio file.
        
        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            **kwargs: Additional synthesis options
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def list_voices(self) -> List[TTSVoice]:
        """List available voices."""
        pass
    
    @abstractmethod
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice."""
        pass
    
    def set_rate(self, rate: float) -> bool:
        """Set speaking rate (1.0 = normal)."""
        self.config.rate = rate
        return True
    
    def set_volume(self, volume: float) -> bool:
        """Set volume (0.0-1.0)."""
        self.config.volume = volume
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get backend statistics."""
        stats = self._stats.copy()
        if stats["total_utterances"] > 0:
            stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["total_utterances"]
        else:
            stats["avg_latency_ms"] = 0
        return stats
    
    def _update_stats(self, latency_ms: float):
        """Update synthesis statistics."""
        self._stats["total_utterances"] += 1
        self._stats["total_latency_ms"] += latency_ms
