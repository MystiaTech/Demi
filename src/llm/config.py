"""
LLM configuration and settings for Ollama integration.

Provides LLMConfig dataclass for managing model parameters,
timeouts, and Ollama connection settings.
"""

from dataclasses import dataclass, field
from typing import Optional
from src.core.config import DemiConfig


@dataclass
class LLMConfig:
    """Configuration for LLM inference via Ollama or LMStudio."""

    model_name: str = "llama3.2:1b"
    """Name of the model to use with Ollama (e.g., llama3.2:1b, llama3.2:3b)."""

    temperature: float = 0.7
    """Temperature for response generation (0.0 = deterministic, 1.0 = creative)."""

    max_tokens: int = 2048
    """Maximum tokens to generate per response."""

    timeout_sec: int = 10
    """Timeout for Ollama requests in seconds."""

    ollama_base_url: str = "http://localhost:11434"
    """Base URL for Ollama API server."""

    lmstudio_base_url: str = "http://localhost:1234"
    """Base URL for LMStudio API server (fallback provider)."""

    enable_lmstudio_fallback: bool = True
    """Enable automatic fallback to LMStudio if Ollama is unavailable."""

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate all configuration parameters."""
        # Validate model_name
        if not self.model_name or not isinstance(self.model_name, str):
            raise ValueError("model_name must be non-empty string")

        # Validate temperature
        if not (0.0 <= self.temperature <= 1.0):
            raise ValueError("temperature must be in range [0.0, 1.0]")

        # Validate max_tokens
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0")

        # Validate timeout
        if self.timeout_sec <= 0:
            raise ValueError("timeout_sec must be greater than 0")

    @classmethod
    def from_global_config(cls, config: DemiConfig) -> "LLMConfig":
        """
        Load LLM configuration from global DemiConfig if available.

        Args:
            config: Global DemiConfig object

        Returns:
            LLMConfig instance with values from config or defaults
        """
        lm_settings = config.lm or {}
        ollama_settings = lm_settings.get("ollama", {})
        lmstudio_settings = lm_settings.get("lmstudio", {})

        return cls(
            model_name=ollama_settings.get("model", "llama3.2:1b"),
            temperature=ollama_settings.get("temperature", 0.7),
            max_tokens=ollama_settings.get("max_tokens", 2048),
            timeout_sec=ollama_settings.get("timeout", 30),
            ollama_base_url=ollama_settings.get(
                "base_url", "http://localhost:11434"
            ),
            lmstudio_base_url=lmstudio_settings.get(
                "base_url", "http://localhost:1234"
            ),
            enable_lmstudio_fallback=lm_settings.get(
                "enable_fallback", True
            ),
        )
