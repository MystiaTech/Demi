"""
LLM integration module for Demi.

Provides Ollama-based inference engine with context management and error handling.
"""

from src.llm.config import LLMConfig
from src.llm.inference import OllamaInference, InferenceError, ContextOverflowError

__all__ = [
    "LLMConfig",
    "OllamaInference",
    "InferenceError",
    "ContextOverflowError",
]
