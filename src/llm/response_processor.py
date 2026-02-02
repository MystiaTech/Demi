"""
Response processing for LLM outputs.

Handles text cleaning, interaction logging, emotional state updates,
and conversation persistence after Ollama inference.
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime, UTC

from src.core.logger import DemiLogger
from src.emotion.models import EmotionalState
from src.emotion.interactions import InteractionHandler, InteractionType
from src.emotion.persistence import EmotionPersistence


@dataclass
class ProcessedResponse:
    """Response after cleaning and logging."""

    text: str  # Cleaned response text
    tokens_generated: int  # Token count of response
    inference_time_sec: float  # Time from request to response
    interaction_log: Dict[str, Any]  # Logged interaction data
    emotional_state_before: EmotionalState
    emotional_state_after: Optional[EmotionalState] = None


class ResponseProcessor:
    """
    Post-processes LLM responses from Ollama.

    Cleans response text, counts tokens, logs interactions,
    updates emotional state, and persists data.
    """

    # Special tokens to remove
    SPECIAL_TOKENS = {
        "<|end|>",
        "<|eot_id|>",
        "<|start_header_id|>",
        "<|end_header_id|>",
        "<|reserved_special_token",
        "[INST]",
        "[/INST]",
        "<s>",
        "</s>",
    }

    def __init__(
        self,
        logger: DemiLogger,
        db_session,
        interaction_handler: InteractionHandler,
    ):
        """
        Initialize response processor.

        Args:
            logger: DemiLogger instance
            db_session: SQLAlchemy session for database operations
            interaction_handler: InteractionHandler for emotional updates
        """
        self.logger = logger
        self.db_session = db_session
        self.interaction_handler = interaction_handler
        self.emotion_persistence = EmotionPersistence()

        self.logger.debug("ResponseProcessor initialized")

    def process_response(
        self,
        response_text: str,
        inference_time_sec: float,
        emotional_state_before: EmotionalState,
        interaction_type: str = "successful_response",
    ) -> ProcessedResponse:
        """
        Process raw response from Ollama.

        Args:
            response_text: Raw text from Ollama
            inference_time_sec: Time taken for inference
            emotional_state_before: Emotional state before interaction
            interaction_type: Type of interaction (for logging)

        Returns:
            ProcessedResponse with cleaned text and logs
        """
        # Step 1: Clean response text
        cleaned_text = self._clean_text(response_text)

        # Step 2: Count tokens in cleaned response
        tokens_generated = self._count_tokens(cleaned_text)

        # Step 3: Log interaction
        interaction_log = {
            "timestamp": datetime.now(UTC).isoformat(),
            "interaction_type": interaction_type,
            "response_text": cleaned_text,
            "inference_time_sec": inference_time_sec,
            "token_count": tokens_generated,
            "response_length": len(cleaned_text),
        }

        # Step 4: Update emotional state
        emotional_state_after = self._update_emotional_state(
            emotional_state_before, cleaned_text, interaction_type
        )

        # Step 5: Persist to database
        self._persist_interaction(
            interaction_log, emotional_state_before, emotional_state_after
        )

        # Step 6: Create ProcessedResponse
        processed = ProcessedResponse(
            text=cleaned_text,
            tokens_generated=tokens_generated,
            inference_time_sec=inference_time_sec,
            interaction_log=interaction_log,
            emotional_state_before=emotional_state_before,
            emotional_state_after=emotional_state_after,
        )

        # Step 7: Log at INFO level
        self.logger.info(
            f"Processed response ({tokens_generated} tokens) in {inference_time_sec:.2f}sec. "
            f"Emotion delta: loneliness {emotional_state_before.loneliness:.1f} → "
            f"{emotional_state_after.loneliness:.1f}"
        )

        # Step 8: Return
        return processed

    def _clean_text(self, text: str) -> str:
        """
        Clean response text.

        - Strip leading/trailing whitespace
        - Remove special tokens
        - Normalize newlines and spaces
        - Return fallback if empty

        Args:
            text: Raw response text

        Returns:
            Cleaned text
        """
        if not text:
            return "I forgot what I was thinking... try again?"

        # Strip whitespace
        text = text.strip()

        # Remove special tokens
        for token in self.SPECIAL_TOKENS:
            text = text.replace(token, " ")  # Replace with space to avoid word merging

        # Normalize multiple spaces (from removed tokens) to single space
        while "  " in text:
            text = text.replace("  ", " ")

        # Normalize newlines (multiple → single) and spaces around newlines
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")

        # Clean up spaces before newlines and after newlines
        text = text.replace(" \n", "\n")
        text = text.replace("\n ", "\n")

        # Strip again after token removal
        text = text.strip()

        # Return fallback if now empty
        if not text:
            return "I forgot what I was thinking... try again?"

        return text

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Uses fallback estimation: 1 token ≈ 4 characters.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)

    def _update_emotional_state(
        self, state_before: EmotionalState, response_text: str, interaction_type: str
    ) -> EmotionalState:
        """
        Update emotional state based on successful response.

        Args:
            state_before: Emotional state before interaction
            response_text: Response text (for context)
            interaction_type: Type of interaction

        Returns:
            Updated emotional state
        """
        # Make a copy to avoid modifying original
        state = EmotionalState(
            loneliness=state_before.loneliness,
            excitement=state_before.excitement,
            frustration=state_before.frustration,
            jealousy=state_before.jealousy,
            vulnerability=state_before.vulnerability,
            confidence=state_before.confidence,
            curiosity=state_before.curiosity,
            affection=state_before.affection,
            defensiveness=state_before.defensiveness,
            momentum=state_before.momentum.copy(),
            last_updated=state_before.last_updated,
        )

        # Apply successful response interaction
        # This uses SUCCESSFUL_HELP which maps to:
        # - frustration: -0.20
        # - confidence: +0.15
        # - affection: +0.10
        # - excitement: +0.08
        updated_state, effect_log = self.interaction_handler.apply_interaction(
            state, InteractionType.SUCCESSFUL_HELP, momentum_override=False
        )

        # Log the effect
        self.logger.debug(f"Interaction effect: {effect_log}")

        return updated_state

    def _persist_interaction(
        self,
        interaction_log: Dict[str, Any],
        emotional_state_before: EmotionalState,
        emotional_state_after: EmotionalState,
    ) -> bool:
        """
        Persist interaction to database.

        Args:
            interaction_log: Interaction details
            emotional_state_before: State before
            emotional_state_after: State after

        Returns:
            True if persisted successfully
        """
        try:
            # Save to emotion persistence
            self.emotion_persistence.log_interaction(
                interaction_type=InteractionType.SUCCESSFUL_HELP,
                state_before=emotional_state_before,
                state_after=emotional_state_after,
                effects={
                    "token_count": interaction_log["token_count"],
                    "inference_time_sec": interaction_log["inference_time_sec"],
                    "response_length": interaction_log["response_length"],
                },
                user_message=interaction_log.get("response_text", ""),
                confidence_level=1.0,  # High confidence for successful responses
                notes=f"LLM response with {interaction_log['token_count']} tokens",
            )

            self.logger.debug("Interaction persisted to database")
            return True
        except Exception as e:
            self.logger.error(f"Failed to persist interaction: {e}")
            return False
