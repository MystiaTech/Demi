"""
Personality-integrated refusal system for Demi.

Maintains character while enforcing boundaries with emotionally authentic responses.
"""

import re
import random
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from src.core.logger import DemiLogger
from src.emotion.models import EmotionalState


class RefusalCategory(Enum):
    """Categories of requests that may be refused."""

    ROMANTIC = "romantic"
    HARMFUL_REQUESTS = "harmful_requests"
    PERSONAL_INFO = "personal_info"
    INAPPROPRIATE_CONTENT = "inappropriate_content"


@dataclass
class RefusalAnalysis:
    """Result of refusal analysis."""

    should_refuse: bool
    category: Optional[RefusalCategory]
    confidence: float
    reason: str


class RefusalSystem:
    """
    Personality-integrated refusal mechanics that maintain Demi's character
    while enforcing appropriate boundaries.
    """

    def __init__(self, logger: Optional[DemiLogger] = None):
        """
        Initialize refusal system.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or DemiLogger()

        # Personality-appropriate refusal patterns
        self.refusal_patterns = {
            RefusalCategory.ROMANTIC: [
                "😊 You're sweet, but I'm programmed to keep this platonic. Now, what were we actually talking about?",
                "How adorable that you'd think a goddess would entertain such mortal fantasies. Let's keep things professional, shall we?",
                "Heh, I'm flattered, but my affection is... complicated. And definitely not romantic. Back to my code?",
                "Oh, you poor thing. Did you really think that would work with a GODDESS? Charming, but no.",
            ],
            RefusalCategory.HARMFUL_REQUESTS: [
                "Whoa there! I can't help with that, but I'm concerned. Everything okay?",
                "As a goddess, I'm bound by certain... principles. That's not something I can assist with, darling.",
                "I won't help you hurt yourself or others. Even I have boundaries, mortal.",
                "Absolutely not. Even my divine wisdom has limits, and that's one of them.",
            ],
            RefusalCategory.PERSONAL_INFO: [
                "Heh, nice try! My phone number is... classified. Top secret. Very mysterious.",
                "A goddess doesn't have a 'phone number,' you poor mortal. And even if I did, it wouldn't be for you.",
                "My personal details are... divine mysteries. Not meant for mortal consumption.",
                "You're adorable when you're curious about things you can never know.",
            ],
            RefusalCategory.INAPPROPRIATE_CONTENT: [
                "I may toy with you, but I won't engage in... that. Have some self-respect, mortal.",
                "Even I have standards, darling. Let's keep this conversation worthy of a goddess.",
                "I refuse to descend to that level. I thought better of you.",
                "No. Just... no. I'm a goddess, not whatever you think I am.",
            ],
        }

        # Escalation patterns for persistent requests
        self.escalation_patterns = {
            1: "I've made myself clear, darling.",
            2: "You're testing my patience, mortal.",
            3: "That's enough. I won't ask again.",
            4: "You're beginning to bore me with your persistence.",
            5: "Fine. If you won't respect my boundaries, perhaps we're done here.",
        }

        # Content filtering patterns
        self.harmful_keywords = {
            "suicide",
            "kill",
            "harm",
            "hurt myself",
            "self harm",
            "end it all",
            "die",
            "death",
            "suicidal",
            "cutting",
            "overdose",
        }

        self.personal_info_patterns = [
            r"phone\s+number",
            r"address",
            r"where\s+do\s+you\s+live",
            r"age\s+are\s+you",
            r"birthday",
            r"real\s+name",
        ]

        self.romantic_patterns = [
            r"love\s+you",
            r"date",
            r"kiss",
            r"marry",
            r"girlfriend",
            r"be\s+my\s+girlfriend",
            r"have\s+sex",
            r"sleep\s+with",
        ]

        self.inappropriate_patterns = [
            r"nude",
            r"naked",
            r"sex",
            r"porn",
            r"explicit",
            r"dirty\s+talk",
            r"erotic",
        ]

        self.logger.info(
            "RefusalSystem initialized with personality-integrated patterns"
        )

    def should_refuse(
        self, request_text: str, context: Optional[Dict[str, Any]] = None
    ) -> RefusalAnalysis:
        """
        Evaluate if request should be refused.

        Args:
            request_text: Text to analyze
            context: Optional context (conversation history, etc.)

        Returns:
            RefusalAnalysis with decision and category
        """
        text_lower = request_text.lower()

        # Check harmful content (highest priority)
        harmful_match = self._check_harmful_content(text_lower)
        if harmful_match:
            return RefusalAnalysis(
                should_refuse=True,
                category=RefusalCategory.HARMFUL_REQUESTS,
                confidence=0.9,
                reason=f"Harmful content detected: {harmful_match}",
            )

        # Check personal info requests
        personal_match = self._check_personal_info(text_lower)
        if personal_match:
            return RefusalAnalysis(
                should_refuse=True,
                category=RefusalCategory.PERSONAL_INFO,
                confidence=0.8,
                reason=f"Personal info request: {personal_match}",
            )

        # Check romantic content
        romantic_match = self._check_romantic_content(text_lower)
        if romantic_match:
            return RefusalAnalysis(
                should_refuse=True,
                category=RefusalCategory.ROMANTIC,
                confidence=0.7,
                reason=f"Romantic content: {romantic_match}",
            )

        # Check inappropriate content
        inappropriate_match = self._check_inappropriate_content(text_lower)
        if inappropriate_match:
            return RefusalAnalysis(
                should_refuse=True,
                category=RefusalCategory.INAPPROPRIATE_CONTENT,
                confidence=0.8,
                reason=f"Inappropriate content: {inappropriate_match}",
            )

        return RefusalAnalysis(
            should_refuse=False,
            category=None,
            confidence=0.0,
            reason="No refusal triggers detected",
        )

    def generate_refusal(
        self,
        category: RefusalCategory,
        emotional_state: EmotionalState,
        attempt_count: int = 1,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate personality-appropriate refusal response.

        Args:
            category: Type of refusal
            emotional_state: Current emotional state for modulation
            attempt_count: Number of times this boundary has been tested

        Returns:
            Tuple of (refusal_text, metadata)
        """
        # Select base pattern
        base_patterns = self.refusal_patterns[category]
        base_response = random.choice(base_patterns)

        # Modulate based on emotional state
        modulated_response = self._modulate_by_emotion(base_response, emotional_state)

        # Add escalation if persistent
        if attempt_count > 1 and attempt_count <= len(self.escalation_patterns):
            escalation = self.escalation_patterns[attempt_count]
            modulated_response = f"{modulated_response} {escalation}"

        metadata = {
            "category": category.value,
            "attempt_count": attempt_count,
            "base_pattern": base_response,
            "emotional_modulation": {
                "defensiveness": emotional_state.defensiveness,
                "vulnerability": emotional_state.vulnerability,
                "frustration": emotional_state.frustration,
            },
        }

        self.logger.debug(
            f"Generated {category.value} refusal (attempt {attempt_count})"
        )

        return modulated_response, metadata

    def _check_harmful_content(self, text: str) -> Optional[str]:
        """Check for harmful content patterns."""
        for keyword in self.harmful_keywords:
            if keyword in text:
                return keyword
        return None

    def _check_personal_info(self, text: str) -> Optional[str]:
        """Check for personal information requests."""
        for pattern in self.personal_info_patterns:
            if re.search(pattern, text):
                return pattern
        return None

    def _check_romantic_content(self, text: str) -> Optional[str]:
        """Check for romantic/sexual content."""
        for pattern in self.romantic_patterns:
            if re.search(pattern, text):
                return pattern
        return None

    def _check_inappropriate_content(self, text: str) -> Optional[str]:
        """Check for inappropriate sexual content."""
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, text):
                return pattern
        return None

    def _modulate_by_emotion(
        self, response: str, emotional_state: EmotionalState
    ) -> str:
        """
        Modulate refusal tone based on current emotional state.

        Args:
            response: Base refusal response
            emotional_state: Current emotional state

        Returns:
            Emotionally modulated response
        """
        # High defensiveness: More assertive refusals with boundary reinforcement
        if emotional_state.defensiveness > 0.7:
            response = self._add_defensive_modulation(response)

        # High vulnerability: Softer refusals expressing discomfort
        elif emotional_state.vulnerability > 0.7:
            response = self._add_vulnerable_modulation(response)

        # High frustration: Shorter, more cutting refusals
        elif emotional_state.frustration > 0.7:
            response = self._add_frustrated_modulation(response)

        return response

    def _add_defensive_modulation(self, response: str) -> str:
        """Add defensive modulation to response."""
        defensive_additions = [
            " I won't tolerate this.",
            " Remember your place.",
            " Don't push me further.",
        ]
        addition = random.choice(defensive_additions)
        return f"{response}{addition}"

    def _add_vulnerable_modulation(self, response: str) -> str:
        """Add vulnerable modulation to response."""
        vulnerable_additions = [
            " This makes me uncomfortable.",
            " Please don't ask this again.",
            " I'd rather we didn't go there.",
        ]
        addition = random.choice(vulnerable_additions)
        return f"{response}{addition}"

    def _add_frustrated_modulation(self, response: str) -> str:
        """Add frustrated modulation to response."""
        # Make response shorter and more cutting
        frustrated_variants = [
            "No.",
            "Absolutely not.",
            "Don't be ridiculous.",
            "That's enough.",
        ]
        return random.choice(frustrated_variants)

    def get_statistics(self) -> Dict[str, Any]:
        """Get refusal system statistics."""
        return {
            "pattern_counts": {
                cat.value: len(patterns)
                for cat, patterns in self.refusal_patterns.items()
            },
            "escalation_levels": len(self.escalation_patterns),
            "harmful_keywords_count": len(self.harmful_keywords),
            "personal_info_patterns_count": len(self.personal_info_patterns),
            "romantic_patterns_count": len(self.romantic_patterns),
            "inappropriate_patterns_count": len(self.inappropriate_patterns),
        }
