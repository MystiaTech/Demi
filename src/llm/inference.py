"""
LLM inference engine for Demi with Ollama and LMStudio support.

Provides async interface to Ollama (primary) and LMStudio (fallback) for response generation,
with context window management, token counting, and error handling.
Automatically falls back to LMStudio if Ollama is unavailable.
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

    def __init__(
        self,
        config: LLMConfig,
        logger: DemiLogger,
        response_processor=None,
        codebase_reader=None,
    ):
        """
        Initialize OllamaInference client.

        Args:
            config: LLMConfig with model and timeout settings
            logger: DemiLogger instance for logging
            response_processor: Optional ResponseProcessor for post-processing responses
            codebase_reader: Optional CodebaseReader for code context injection
        """
        self.config = config
        self.logger = logger
        self._tokenizer = None
        self._tokenizer_attempted = False
        self.response_processor = response_processor
        self.codebase_reader = codebase_reader
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


class LMStudioInference:
    """
    Async interface to LMStudio for LLM inference.

    Handles chat completions compatible with OpenAI API format,
    used as fallback when Ollama is unavailable.
    """

    def __init__(
        self,
        config: LLMConfig,
        logger: DemiLogger,
        response_processor=None,
        codebase_reader=None,
    ):
        """
        Initialize LMStudioInference client.

        Args:
            config: LLMConfig with model and timeout settings
            logger: DemiLogger instance for logging
            response_processor: Optional ResponseProcessor for post-processing responses
            codebase_reader: Optional CodebaseReader for code context injection
        """
        self.config = config
        self.logger = logger
        self._tokenizer = None
        self._tokenizer_attempted = False
        self.response_processor = response_processor
        self.codebase_reader = codebase_reader
        self.logger.debug(
            f"LMStudioInference initialized with endpoint: {config.lmstudio_base_url}"
        )

    async def health_check(self) -> bool:
        """
        Check if LMStudio server is responding.

        Returns:
            True if LMStudio is online, False otherwise
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                try:
                    # Try the /api/tags endpoint (compatible with Ollama format)
                    url = f"{self.config.lmstudio_base_url}/api/tags"
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=self.config.timeout_sec)
                    ) as resp:
                        if resp.status == 200:
                            self.logger.debug("LMStudio health check: OK")
                            return True
                        else:
                            self.logger.warning(
                                f"LMStudio health check: HTTP {resp.status}"
                            )
                            return False
                except asyncio.TimeoutError:
                    self.logger.warning("LMStudio health check: timeout")
                    return False
                except Exception as e:
                    self.logger.warning(f"LMStudio health check: {type(e).__name__}")
                    return False
        except ImportError:
            self.logger.error("aiohttp package not installed")
            return False
        except Exception as e:
            self.logger.error(f"LMStudio health check failed: {e}")
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_context_tokens: int = 8000,
        emotional_state_before=None,
    ) -> str:
        """
        Generate a chat response using LMStudio.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_context_tokens: Maximum tokens allowed in context window
            emotional_state_before: Optional emotional state for response processing

        Returns:
            Response text from the model (cleaned if processor available)

        Raises:
            InferenceError: On HTTP errors, timeouts, or LMStudio unavailable
        """
        try:
            import aiohttp

            # Validate messages
            self._validate_messages(messages)

            # Trim context if needed
            trimmed_messages = self._trim_context(messages, max_context_tokens)

            # Call LMStudio API with timing
            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                url = f"{self.config.lmstudio_base_url}/v1/chat/completions"
                payload = {
                    "model": self.config.model_name,
                    "messages": trimmed_messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                }

                try:
                    async with session.post(
                        url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout_sec),
                    ) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            raise InferenceError(
                                f"LMStudio returned HTTP {resp.status}: {error_text}"
                            )

                        data = await resp.json()
                        response_text = data["choices"][0]["message"]["content"]
                        inference_time_sec = time.time() - start_time

                        self.logger.debug(
                            f"LMStudio response: {len(response_text)} chars in {inference_time_sec:.2f}s"
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
                        f"LMStudio request timeout (>{self.config.timeout_sec}s)"
                    )
                except ConnectionError as e:
                    raise InferenceError(f"Failed to connect to LMStudio: {e}")

        except InferenceError:
            raise
        except ImportError:
            raise InferenceError("aiohttp package not installed")
        except Exception as e:
            self.logger.error(f"LMStudio inference error: {type(e).__name__}: {e}")
            raise InferenceError(f"Inference failed: {e}")

    def _validate_messages(self, messages: List[Dict[str, str]]):
        """Validate message format."""
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
        Count tokens in text (same logic as OllamaInference).

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
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
        Trim message context to fit within token limit (same logic as OllamaInference).

        Args:
            messages: Full message list
            max_tokens: Maximum tokens allowed

        Returns:
            Trimmed message list
        """
        if not messages:
            return messages

        safety_margin = 256
        response_space = 256
        reserved = safety_margin + response_space

        system_messages = [m for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        system_tokens = sum(self._count_tokens(m["content"]) for m in system_messages)
        available_tokens = max_tokens - reserved - system_tokens

        if available_tokens <= 0:
            self.logger.warning(
                f"System prompt uses {system_tokens} tokens, limited room for conversation"
            )

        trimmed_conversation = conversation
        while True:
            conv_tokens = sum(
                self._count_tokens(m["content"]) for m in trimmed_conversation
            )
            if conv_tokens <= available_tokens or len(trimmed_conversation) <= 1:
                break

            if trimmed_conversation:
                trimmed_conversation = trimmed_conversation[1:]

        if len(trimmed_conversation) < len(conversation):
            self.logger.debug(
                f"Trimmed context from {len(conversation)} to {len(trimmed_conversation)} "
                f"messages to fit {max_tokens} token window"
            )

        return system_messages + trimmed_conversation


class UnifiedLLMInference:
    """
    Unified LLM inference with automatic fallback from Ollama to LMStudio.

    Tries Ollama first, and if unavailable, automatically falls back to LMStudio.
    Maintains consistent interface regardless of underlying provider.
    """

    def __init__(
        self,
        config: LLMConfig,
        logger: DemiLogger,
        response_processor=None,
        codebase_reader=None,
    ):
        """
        Initialize unified inference with both providers.

        Args:
            config: LLMConfig with settings for both providers
            logger: DemiLogger instance for logging
            response_processor: Optional ResponseProcessor
            codebase_reader: Optional CodebaseReader
        """
        self.config = config
        self.logger = logger
        self.response_processor = response_processor
        self.codebase_reader = codebase_reader

        # Initialize both providers
        self.ollama = OllamaInference(config, logger, response_processor, codebase_reader)
        self.lmstudio = LMStudioInference(
            config, logger, response_processor, codebase_reader
        )

        self._active_provider = None
        self._last_health_check = 0
        self._health_check_interval = 60  # seconds
        self._tokenizer = None
        self._tokenizer_attempted = False

        self.logger.info(
            f"Unified LLM inference initialized. "
            f"Ollama: {config.ollama_base_url}, "
            f"LMStudio: {config.lmstudio_base_url} (fallback enabled: {config.enable_lmstudio_fallback})"
        )

    async def health_check(self) -> bool:
        """Check if any provider is available."""
        now = time.time()
        if now - self._last_health_check < self._health_check_interval:
            # Use cached result
            return self._active_provider is not None

        self._last_health_check = now

        # Try Ollama first
        if await self.ollama.health_check():
            self._active_provider = "ollama"
            self.logger.debug("Using Ollama as active provider")
            return True

        # Fall back to LMStudio if enabled
        if self.config.enable_lmstudio_fallback:
            if await self.lmstudio.health_check():
                self._active_provider = "lmstudio"
                self.logger.info("Ollama unavailable, switched to LMStudio provider")
                return True

        self._active_provider = None
        self.logger.warning("No LLM providers available")
        return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_context_tokens: int = 8000,
        emotional_state_before=None,
    ) -> str:
        """
        Generate response using available provider.

        Tries Ollama first, falls back to LMStudio if configured and Ollama fails.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_context_tokens: Maximum tokens allowed
            emotional_state_before: Optional emotional state for response processing

        Returns:
            Response text from the model

        Raises:
            InferenceError: If both providers are unavailable
        """
        # Try Ollama first
        try:
            if await self.ollama.health_check():
                self._active_provider = "ollama"
                self.logger.debug("Using Ollama provider")
                return await self.ollama.chat(
                    messages, max_context_tokens, emotional_state_before
                )
        except InferenceError as e:
            self.logger.warning(f"Ollama inference failed: {e}")
            if not self.config.enable_lmstudio_fallback:
                raise

        # Fall back to LMStudio if enabled
        if self.config.enable_lmstudio_fallback:
            try:
                if await self.lmstudio.health_check():
                    self._active_provider = "lmstudio"
                    self.logger.info("Switched to LMStudio provider")
                    return await self.lmstudio.chat(
                        messages, max_context_tokens, emotional_state_before
                    )
            except InferenceError as e:
                self.logger.error(f"LMStudio inference also failed: {e}")
                raise InferenceError(
                    "Both Ollama and LMStudio providers failed. "
                    "Please ensure at least one is running."
                )

        raise InferenceError(
            "Ollama provider failed and fallback is disabled. "
            "Please ensure Ollama is running or enable LMStudio fallback."
        )

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text (delegates to active provider or uses fallback estimation).

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Try to use transformers tokenizer
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
