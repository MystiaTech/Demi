"""
LLM integration module for Demi.

Provides Ollama-based inference engine with context management, prompt building,
and conversation history management.
"""

from src.llm.config import LLMConfig
from src.llm.inference import OllamaInference, InferenceError, ContextOverflowError
from src.llm.prompt_builder import PromptBuilder, BASE_DEMI_PROMPT
from src.llm.history_manager import ConversationHistory, Message
from src.llm.response_processor import ResponseProcessor, ProcessedResponse
from src.llm.codebase_reader import CodebaseReader, CodeSnippet

__all__ = [
    "LLMConfig",
    "OllamaInference",
    "InferenceError",
    "ContextOverflowError",
    "PromptBuilder",
    "BASE_DEMI_PROMPT",
    "ConversationHistory",
    "Message",
    "ResponseProcessor",
    "ProcessedResponse",
    "CodebaseReader",
    "CodeSnippet",
]
