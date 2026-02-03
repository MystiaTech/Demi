"""
Response processing for LLM outputs.

Handles text cleaning, interaction logging, emotional state updates,
and conversation persistence after Ollama inference.
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from src.core.logger import DemiLogger
from src.emotion.models import EmotionalState
from src.emotion.interactions import InteractionHandler, InteractionType
from src.emotion.persistence import EmotionPersistence
from src.autonomy.refusals import RefusalSystem, RefusalAnalysis, RefusalCategory


@dataclass
class ProcessedResponse:
    """Response after cleaning and logging."""

    text: str  # Cleaned response text
    tokens_generated: int  # Token count of response
    inference_time_sec: float  # Time from request to response
    interaction_log: Dict[str, Any]  # Logged interaction data
    emotional_state_before: EmotionalState
    emotional_state_after: Optional[EmotionalState] = None
    refusal_detected: bool = False
    refusal_category: Optional[str] = None
    refusal_reason: Optional[str] = None


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
        refusal_system: Optional[RefusalSystem] = None,
    ):
        """
        Initialize response processor.

        Args:
            logger: DemiLogger instance
            db_session: SQLAlchemy session for database operations
            interaction_handler: InteractionHandler for emotional updates
            refusal_system: Optional RefusalSystem for boundary enforcement
        """
        self.logger = logger
        self.db_session = db_session
        self.interaction_handler = interaction_handler
        self.emotion_persistence = EmotionPersistence()
        self.refusal_system = refusal_system or RefusalSystem(logger)

        # Refusal tracking
        self.refusal_attempts = {}  # Track refusal attempts by user/session

        self.logger.debug("ResponseProcessor initialized")

    def process_response(
        self,
        response_text: str,
        inference_time_sec: float,
        emotional_state_before: EmotionalState,
        interaction_type: str = "successful_response",
        should_check_refusal: bool = True,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessedResponse:
        """
        Process raw response from Ollama.

        Args:
            response_text: Raw text from Ollama or user request
            inference_time_sec: Time taken for inference
            emotional_state_before: Emotional state before interaction
            interaction_type: Type of interaction (for logging)
            should_check_refusal: Whether to check for refusal before processing
            request_context: Context about the request (for refusal detection)

        Returns:
            ProcessedResponse with cleaned text and logs
        """
        # Step 1: Check for refusal if enabled and this is a user request
        if should_check_refusal and interaction_type == "user_request":
            refusal_analysis = self.refusal_system.should_refuse(
                response_text, request_context
            )
            if refusal_analysis.should_refuse:
                # Category should never be None when should_refuse is True
                return self._handle_refusal(
                    refusal_analysis,
                    emotional_state_before,
                    inference_time_sec,
                    request_context,
                )

        # Step 2: Clean response text
        cleaned_text = self._clean_text(response_text)

        # Step 2: Count tokens in cleaned response
        tokens_generated = self._count_tokens(cleaned_text)

        # Step 3: Log interaction
        interaction_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

    def _handle_refusal(
        self,
        refusal_analysis: RefusalAnalysis,
        emotional_state_before: EmotionalState,
        inference_time_sec: float,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessedResponse:
        """
        Handle a refused request by generating a personality-appropriate refusal.

        Args:
            refusal_analysis: Result of refusal analysis
            emotional_state_before: Emotional state before interaction
            inference_time_sec: Time taken for processing
            request_context: Request context for attempt tracking

        Returns:
            ProcessedResponse with refusal text and metadata
        """
        # Track refusal attempts
        attempt_count = self._track_refusal_attempt(request_context)

        # Generate personality-appropriate refusal
        # Ensure category is not None (it should never be None when should_refuse is True)
        category = refusal_analysis.category or RefusalCategory.HARMFUL_REQUESTS
        refusal_text, refusal_metadata = self.refusal_system.generate_refusal(
            category, emotional_state_before, attempt_count
        )

        # Create interaction log for refusal
        interaction_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "interaction_type": "refusal",
            "response_text": refusal_text,
            "inference_time_sec": inference_time_sec,
            "token_count": self._count_tokens(refusal_text),
            "response_length": len(refusal_text),
            "refusal_category": category.value,
            "refusal_confidence": refusal_analysis.confidence,
            "refusal_reason": refusal_analysis.reason,
            "attempt_count": attempt_count,
        }

        # Update emotional state for refusal interaction
        # Use USER_REFUSAL interaction type instead of SUCCESSFUL_HELP
        from src.emotion.interactions import InteractionType

        emotional_state_after = self._update_emotional_state_refusal(
            emotional_state_before, refusal_analysis, interaction_type="refusal"
        )

        # Persist refusal to database
        self._persist_refusal_interaction(
            interaction_log,
            emotional_state_before,
            emotional_state_after,
            refusal_analysis,
            category,
        )

        # Create ProcessedResponse with refusal data
        processed = ProcessedResponse(
            text=refusal_text,
            tokens_generated=self._count_tokens(refusal_text),
            inference_time_sec=inference_time_sec,
            interaction_log=interaction_log,
            emotional_state_before=emotional_state_before,
            emotional_state_after=emotional_state_after,
            refusal_detected=True,
            refusal_category=category.value,
            refusal_reason=refusal_analysis.reason,
        )

        # Log refusal at INFO level
        self.logger.info(
            f"Refusal generated ({category.value}) with confidence {refusal_analysis.confidence:.2f}. "
            f"Attempt {attempt_count}. "
            f"Emotion delta: defensiveness {emotional_state_before.defensiveness:.1f} → "
            f"{emotional_state_after.defensiveness:.1f}"
        )

        return processed

    def _track_refusal_attempt(self, request_context: Optional[Dict[str, Any]]) -> int:
        """
        Track refusal attempts for escalation.

        Args:
            request_context: Request context containing user/session info

        Returns:
            Current attempt count for this user/session
        """
        if not request_context:
            return 1

        # Use user_id or session_id as key
        user_id = (
            request_context.get("user_id")
            or request_context.get("session_id")
            or "default"
        )

        # Increment attempt count
        self.refusal_attempts[user_id] = self.refusal_attempts.get(user_id, 0) + 1

        return self.refusal_attempts[user_id]

    def _update_emotional_state_refusal(
        self,
        state_before: EmotionalState,
        refusal_analysis: RefusalAnalysis,
        interaction_type: str = "refusal",
    ) -> EmotionalState:
        """
        Update emotional state based on refusal interaction.

        Args:
            state_before: Emotional state before interaction
            refusal_analysis: Refusal analysis result
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

        # Apply user refusal interaction (different from successful response)
        # This increases defensiveness and frustration slightly
        from src.emotion.interactions import InteractionType

        try:
            updated_state, effect_log = self.interaction_handler.apply_interaction(
                state, InteractionType.USER_REFUSAL, momentum_override=False
            )
            self.logger.debug(f"Refusal interaction effect: {effect_log}")
            return updated_state
        except:
            # Fallback if USER_REFUSAL not available
            # Manual emotional adjustments for refusal
            state.delta_emotion("defensiveness", +0.15)
            state.delta_emotion("frustration", +0.10)
            state.delta_emotion("vulnerability", -0.05)

            self.logger.debug(f"Manual refusal emotion adjustments applied")
            return state

    def _persist_refusal_interaction(
        self,
        interaction_log: Dict[str, Any],
        emotional_state_before: EmotionalState,
        emotional_state_after: EmotionalState,
        refusal_analysis: RefusalAnalysis,
        category: RefusalCategory,
    ) -> bool:
        """
        Persist refusal interaction to database.

        Args:
            interaction_log: Interaction details
            emotional_state_before: State before
            emotional_state_after: State after
            refusal_analysis: Refusal analysis result

        Returns:
            True if persisted successfully
        """
        try:
            # Save to emotion persistence with refusal-specific data
            self.emotion_persistence.log_interaction(
                interaction_type=InteractionType.USER_REFUSAL,
                state_before=emotional_state_before,
                state_after=emotional_state_after,
                effects={
                    "refusal_category": category.value,
                    "refusal_confidence": refusal_analysis.confidence,
                    "refusal_reason": refusal_analysis.reason,
                    "token_count": interaction_log["token_count"],
                    "inference_time_sec": interaction_log["inference_time_sec"],
                    "response_length": interaction_log["response_length"],
                    "attempt_count": interaction_log["attempt_count"],
                },
                user_message=interaction_log.get("response_text", ""),
                confidence_level=refusal_analysis.confidence,
                notes=f"Refused {category.value}: {refusal_analysis.reason}",
            )

            self.logger.debug("Refusal interaction persisted to database")
            return True
        except Exception as e:
            self.logger.error(f"Failed to persist refusal interaction: {e}")
            return False

    def get_refusal_statistics(self) -> Dict[str, Any]:
        """
        Get refusal tracking statistics.

        Returns:
            Dictionary with refusal statistics
        """
        return {
            "total_refusal_attempts": sum(self.refusal_attempts.values()),
            "unique_users": len(self.refusal_attempts),
            "refusal_attempts_by_user": self.refusal_attempts.copy(),
            "refusal_system_stats": self.refusal_system.get_statistics(),
        }

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
