"""
LLM inference engine for Demi with Ollama backend.

Provides async interface to Ollama for response generation,
with context window management, token counting, and error handling.
"""

import asyncio
import time
from typing import Optional, List, Dict
from src.llm.config import LLMConfig
from src.core.logger import DemiLogger


class InferenceError(Exception):
    """Generic LLM inference error."""

    pass


class ContextOverflowError(InferenceError):
    """Context window exceeded maximum allowed tokens."""

    pass


class OllamaInference:
    """
    Async interface to Ollama for LLM inference.

    Handles chat completions with context trimming, token counting,
    health checks, and comprehensive error handling.
    """

    def __init__(self, config: LLMConfig, logger: DemiLogger, response_processor=None):
        """
        Initialize OllamaInference client.

        Args:
            config: LLMConfig with model and timeout settings
            logger: DemiLogger instance for logging
            response_processor: Optional ResponseProcessor for post-processing responses
        """
        self.config = config
        self.logger = logger
        self._tokenizer = None
        self._tokenizer_attempted = False
        self.response_processor = response_processor
        self.logger.debug(
            f"OllamaInference initialized with model: {config.model_name}"
        )

    async def health_check(self) -> bool:
        """
        Check if Ollama server is responding.

        Calls Ollama /api/tags endpoint to verify server availability.

        Returns:
            True if Ollama is online and responding, False otherwise
        """
        try:
            import ollama

            client = ollama.AsyncClient(host=self.config.ollama_base_url)
            try:
                # Call tags endpoint to check health
                response = await asyncio.wait_for(
                    client.list(), timeout=self.config.timeout_sec
                )
                self.logger.debug("Ollama health check: OK")
                return True
            except asyncio.TimeoutError:
                self.logger.warning("Ollama health check: timeout")
                return False
            except Exception as e:
                self.logger.warning(f"Ollama health check: {type(e).__name__}")
                return False
        except ImportError:
            self.logger.error("ollama package not installed")
            return False
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_context_tokens: int = 8000,
        emotional_state_before=None,
    ) -> str:
        """
        Generate a chat response using Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_context_tokens: Maximum tokens allowed in context window
            emotional_state_before: Optional emotional state for response processing

        Returns:
            Response text from the model (cleaned if processor available)

        Raises:
            InferenceError: On HTTP errors, timeouts, or Ollama unavailable
            ContextOverflowError: If context exceeds limit
            ValueError: If messages format is invalid
        """
        # Validate messages format
        self._validate_messages(messages)

        # Count initial context
        initial_token_count = sum(self._count_tokens(m["content"]) for m in messages)
        self.logger.debug(
            f"Chat request: {len(messages)} messages, ~{initial_token_count} tokens"
        )

        # Check if context already exceeds limit (before trimming)
        if initial_token_count > max_context_tokens:
            raise ContextOverflowError(
                f"Context exceeds limit: {initial_token_count} > {max_context_tokens}"
            )

        # Trim context if needed
        trimmed_messages = self._trim_context(messages, max_context_tokens)

        # Call Ollama with timing
        try:
            import ollama

            client = ollama.AsyncClient(host=self.config.ollama_base_url)

            # Record start time
            start_time = time.time()

            response = await asyncio.wait_for(
                client.chat(
                    model=self.config.model_name,
                    messages=trimmed_messages,
                    stream=False,
                    options={
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens,
                    },
                ),
                timeout=self.config.timeout_sec,
            )

            # Calculate inference time
            inference_time_sec = time.time() - start_time

            response_text = response.message.content
            self.logger.debug(
                f"Chat response: {len(response_text)} chars in {inference_time_sec:.2f}s"
            )

            # Post-process response if processor available
            if self.response_processor and emotional_state_before:
                processed = self.response_processor.process_response(
                    response_text=response_text,
                    inference_time_sec=inference_time_sec,
                    emotional_state_before=emotional_state_before,
                    interaction_type="successful_response",
                )
                return processed.text

            return response_text

        except asyncio.TimeoutError:
            raise InferenceError(
                f"Ollama request timeout (>{self.config.timeout_sec}s)"
            )
        except ImportError:
            raise InferenceError("ollama package not installed")
        except ConnectionError as e:
            raise InferenceError(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            self.logger.error(f"Ollama inference error: {type(e).__name__}: {e}")
            raise InferenceError(f"Inference failed: {e}")

    def _validate_messages(self, messages: List[Dict[str, str]]):
        """
        Validate message format.

        Args:
            messages: Message list to validate

        Raises:
            ValueError: If format is invalid
        """
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")

        if not messages:
            raise ValueError("messages list cannot be empty")

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message {i} must be a dict")

            if "role" not in msg or "content" not in msg:
                raise ValueError(f"Message {i} must have 'role' and 'content' fields")

            if msg["role"] not in ("system", "user", "assistant"):
                raise ValueError(f"Message {i} has invalid role: {msg['role']}")

            if not isinstance(msg["content"], str):
                raise ValueError(f"Message {i} content must be a string")

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Attempts to use transformers library for accurate tokenization,
        falls back to character-based estimation if unavailable.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Try transformers tokenizer
        if not self._tokenizer_attempted:
            try:
                from transformers import AutoTokenizer

                self._tokenizer = AutoTokenizer.from_pretrained(
                    "meta-llama/Llama-2-7b-hf"
                )
                self._tokenizer_attempted = True
                self.logger.debug("Loaded transformers tokenizer for token counting")
            except Exception as e:
                self._tokenizer_attempted = True
                self.logger.debug(
                    f"Tokenizer unavailable, using fallback estimation: {type(e).__name__}"
                )

        # Use tokenizer if available
        if self._tokenizer:
            try:
                tokens = self._tokenizer.encode(text, add_special_tokens=False)
                return len(tokens)
            except Exception as e:
                self.logger.warning(f"Tokenizer encoding failed: {e}, using fallback")

        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4

    def _trim_context(
        self, messages: List[Dict[str, str]], max_tokens: int
    ) -> List[Dict[str, str]]:
        """
        Trim message context to fit within token limit.

        Keeps system messages and user message, removes oldest assistant
        messages to make room.

        Args:
            messages: Full message list
            max_tokens: Maximum tokens allowed

        Returns:
            Trimmed message list (system always first if present)
        """
        if not messages:
            return messages

        # Calculate available tokens for history
        safety_margin = 256
        response_space = 256
        reserved = safety_margin + response_space

        # Separate system and conversation messages
        system_messages = [m for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        # Count tokens in system prompt
        system_tokens = sum(self._count_tokens(m["content"]) for m in system_messages)

        # Available tokens for conversation
        available_tokens = max_tokens - reserved - system_tokens

        if available_tokens <= 0:
            self.logger.warning(
                f"System prompt uses {system_tokens} tokens, limited room for conversation"
            )

        # Trim conversation history from oldest first
        trimmed_conversation = conversation
        while True:
            conv_tokens = sum(
                self._count_tokens(m["content"]) for m in trimmed_conversation
            )
            if conv_tokens <= available_tokens or len(trimmed_conversation) <= 1:
                break

            # Remove oldest message (first in list)
            if trimmed_conversation:
                trimmed_conversation = trimmed_conversation[1:]

        # If we trimmed, log it
        if len(trimmed_conversation) < len(conversation):
            self.logger.debug(
                f"Trimmed context from {len(conversation)} to {len(trimmed_conversation)} "
                f"messages to fit {max_tokens} token window"
            )

        # Reconstruct: system messages first, then conversation
        return system_messages + trimmed_conversation
