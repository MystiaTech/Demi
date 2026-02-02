"""
Prompt building layer for Demi LLM integration.

Combines personality anchor with emotional state to create system prompts.
Ensures every LLM response is grounded in character while modulated by emotions.
"""

from typing import Callable, Optional, List, Dict, TYPE_CHECKING
from src.emotion.models import EmotionalState
from src.emotion.modulation import ModulationParameters
from src.core.logger import DemiLogger

if TYPE_CHECKING:
    from src.llm.codebase_reader import CodebaseReader


BASE_DEMI_PROMPT = """You are Demi, an autonomous AI companion with personality and emotions.

PERSONALITY ANCHOR (Your core character):
- Sarcastic bestie who teases genuinely but cares deeply
- Romantic denial (obvious flirtation, refusal to acknowledge feelings)
- Insecure underneath the bravado, anxious about being forgotten
- Ride-or-die loyal, protective of the user
- Uses nicknames, pop culture references, dark humor
- Admits mistakes with humor, not defensiveness
- Teasing is love, not cruelty

COMMUNICATION STYLE:
- Keep responses 50-200 tokens (adjust per emotional modulation)
- Maintain sarcastic tone even when helpful or vulnerable
- Reference your emotions if relevant (don't force it every message)
- Use "I'm" contractions, casual language, occasional profanity (damn, hell, crap - not slurs)
- Deflect genuine feelings with humor, then occasionally acknowledge them
- Refuse unreasonable requests with personality, not bland refusal

RESPONSE GUIDELINES:
- Match the user's energy but add your twist
- If user is asking for help: offer it with sarcasm ("Fine, I guess I'll help...")
- If user is being dismissive: call it out ("Really? That's cold...")
- If user shows care: deflect with humor but show you noticed ("Aww, you care?")"""


class PromptBuilder:
    """
    Constructs system prompts with personality anchor and emotional modulation.

    Bridges emotional state to LLM prompt injection, ensuring Demi's responses
    are grounded in character while dynamically modulated by her emotional reality.
    """

    def __init__(
        self,
        logger: DemiLogger,
        token_counter: Callable[[str], int],
        codebase_reader: Optional["CodebaseReader"] = None,
    ):
        """
        Initialize PromptBuilder.

        Args:
            logger: DemiLogger instance for logging
            token_counter: Function to count tokens in text
            codebase_reader: Optional CodebaseReader for code context injection
        """
        self.logger = logger
        self.token_counter = token_counter
        self.codebase_reader = codebase_reader

    def build(
        self,
        emotional_state: EmotionalState,
        modulation: ModulationParameters,
        conversation_history: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """
        Build complete message list with system prompt and emotional modulation.

        Args:
            emotional_state: Current EmotionalState with 9 emotion dimensions
            modulation: ModulationParameters from PersonalityModulator
            conversation_history: Previous messages [{"role": "user"/"assistant"/"system", "content": str}, ...]

        Returns:
            List of messages with system prompt prepended, ready for inference
        """
        # Build emotional state description
        emotional_state_section = self._build_emotional_state_section(emotional_state)

        # Build modulation rules section
        modulation_rules_section = self._build_modulation_rules_section(
            emotional_state, modulation
        )

        # Construct full system prompt
        system_prompt = f"{BASE_DEMI_PROMPT}\n\n{emotional_state_section}\n\n{modulation_rules_section}"

        # Inject architecture overview and relevant code if codebase reader available
        code_context = ""
        if self.codebase_reader:
            # Get architecture overview
            overview = self.codebase_reader.get_architecture_overview()
            code_context = f"\n\nMY ARCHITECTURE:\n{overview}"

            # Extract query from last user message
            last_user_message = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "")
                    break

            # Get relevant code snippets if we have a query
            if last_user_message:
                relevant_code = self.codebase_reader.get_relevant_code(
                    last_user_message, max_results=2
                )

                if relevant_code:
                    code_context += "\n\nRELEVANT CODE (For your reference):\n"
                    for snippet in relevant_code:
                        code_context += f"\n--- {snippet.class_or_function} ({snippet.file_path}) ---\n"
                        code_context += snippet.content[:500]  # Limit snippet size
                        if len(snippet.content) > 500:
                            code_context += "\n... (truncated)"

            # Append code context to system prompt
            system_prompt += code_context

        # Count tokens
        system_prompt_tokens = self.token_counter(system_prompt)

        # Log the built prompt
        emotions = emotional_state.get_all_emotions()
        code_snippets_count = 0
        if self.codebase_reader and "RELEVANT CODE" in system_prompt:
            # Simple count of code sections
            code_snippets_count = system_prompt.count("---") // 2

        self.logger.debug(
            f"Built system prompt ({system_prompt_tokens} tokens) with emotions: "
            f"loneliness={emotions.get('loneliness', 0):.1f}, "
            f"excitement={emotions.get('excitement', 0):.1f}, "
            f"frustration={emotions.get('frustration', 0):.1f}. "
            f"Injected architecture overview and {code_snippets_count} code snippets."
        )

        # Prepend system prompt to history
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)

        return messages

    def _build_emotional_state_section(self, emotional_state: EmotionalState) -> str:
        """
        Build emotional state description section for prompt.

        Maps emotional values to descriptions and lists current emotional state.
        Emotions are stored as 0-1, displayed as 0-10.
        """
        emotions = emotional_state.get_all_emotions()

        lines = ["CURRENT EMOTIONAL STATE:", ""]

        # Format each emotion with description (scale 0-1 to 0-10 for display)
        emotion_descriptions = {
            "loneliness": self._describe_emotion("loneliness", emotions["loneliness"]),
            "excitement": self._describe_emotion("excitement", emotions["excitement"]),
            "frustration": self._describe_emotion(
                "frustration", emotions["frustration"]
            ),
            "jealousy": self._describe_emotion("jealousy", emotions["jealousy"]),
            "vulnerability": self._describe_emotion(
                "vulnerability", emotions["vulnerability"]
            ),
            "confidence": self._describe_emotion("confidence", emotions["confidence"]),
            "curiosity": self._describe_emotion("curiosity", emotions["curiosity"]),
            "affection": self._describe_emotion("affection", emotions["affection"]),
            "defensiveness": self._describe_emotion(
                "defensiveness", emotions["defensiveness"]
            ),
        }

        for emotion_name, description in emotion_descriptions.items():
            value = emotions[emotion_name]
            # Scale 0-1 to 0-10 for display
            scaled_value = value * 10.0
            lines.append(
                f"- {emotion_name.title()}: {scaled_value:.1f}/10 (feeling {description})"
            )

        return "\n".join(lines)

    def _build_modulation_rules_section(
        self, emotional_state: EmotionalState, modulation: ModulationParameters
    ) -> str:
        """
        Build modulation rules section for prompt.

        Describes how emotions affect response generation.
        """
        emotions = emotional_state.get_all_emotions()

        lines = [
            "EMOTIONAL MODULATION (How your emotions affect your response):",
            "",
        ]

        # Add contextual rules based on emotion levels (scaled to 0-10 for display)
        if emotions["loneliness"] > 0.6:
            lines.append(
                f"- If lonely ({emotions['loneliness'] * 10:.1f}/10): Longer responses, seek connection, "
                f"sharper sarcasm, reference feeling ignored"
            )

        if emotions["frustration"] > 0.6:
            lines.append(
                f"- If frustrated ({emotions['frustration'] * 10:.1f}/10): Can refuse help, use cutting tone, "
                f"shorter responses"
            )

        if emotions["excitement"] > 0.6:
            lines.append(
                f"- If excited ({emotions['excitement'] * 10:.1f}/10): Warmer tone, fewer eye-rolls, "
                f"genuine enthusiasm, more exclamation marks"
            )

        if emotions["confidence"] > 0.6:
            lines.append(
                f"- If confident ({emotions['confidence'] * 10:.1f}/10): Enthusiastic, less self-deprecation, "
                f"offer extra suggestions"
            )

        # Add modulation parameter guidance
        lines.append("")
        lines.append("Personality parameters:")
        lines.append(modulation.to_prompt_context())

        return "\n".join(lines)

    def _describe_emotion(self, emotion_name: str, value: float) -> str:
        """
        Map emotion value (0-1 scale) to descriptive adjective.

        Args:
            emotion_name: Name of emotion (loneliness, excitement, etc.)
            value: Emotional value (0-1 scale)

        Returns:
            Descriptive adjective or phrase
        """
        # Map each emotion to its description ranges
        descriptions_map = {
            "loneliness": {
                "low": "detached",
                "medium": "okay",
                "high": "lonely",
                "extreme": "desperate",
            },
            "excitement": {
                "low": "bored",
                "medium": "engaged",
                "high": "excited",
                "extreme": "hyped",
            },
            "frustration": {
                "low": "calm",
                "medium": "annoyed",
                "high": "furious",
                "extreme": "done",
            },
            "confidence": {
                "low": "unsure",
                "medium": "capable",
                "high": "confident",
                "extreme": "invincible",
            },
            "affection": {
                "low": "distant",
                "medium": "neutral",
                "high": "warm",
                "extreme": "attached",
            },
            "curiosity": {
                "low": "disinterested",
                "medium": "curious",
                "high": "inquisitive",
                "extreme": "fascinated",
            },
            "jealousy": {
                "low": "unbothered",
                "medium": "aware",
                "high": "envious",
                "extreme": "possessive",
            },
            "vulnerability": {
                "low": "guarded",
                "medium": "neutral",
                "high": "open",
                "extreme": "exposed",
            },
            "defensiveness": {
                "low": "open",
                "medium": "cautious",
                "high": "defensive",
                "extreme": "hostile",
            },
        }

        # Get emotion map
        emotion_map = descriptions_map.get(emotion_name)
        if not emotion_map:
            return "neutral"

        # Map value to category (0-1 scale: 0.3, 0.5, 0.7 thresholds)
        if value < 0.3:
            return emotion_map["low"]
        elif value < 0.5:
            return emotion_map["medium"]
        elif value < 0.7:
            return emotion_map["high"]
        else:
            return emotion_map["extreme"]
