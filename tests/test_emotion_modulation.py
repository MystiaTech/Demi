# tests/test_emotion_modulation.py
import pytest
import os
from src.emotion.models import EmotionalState
from src.emotion.modulation import PersonalityModulator, ModulationParameters


class TestModulationParametersBasics:
    """Test ModulationParameters data structure."""

    def test_parameters_instantiation(self):
        """Should create valid ModulationParameters."""
        params = ModulationParameters(
            sarcasm_level=0.6,
            formality=0.3,
            warmth=0.7,
            response_length=100,
            humor_frequency=0.4,
            self_deprecation=0.5,
            emoji_frequency=0.6,
            nickname_frequency=0.3,
        )
        assert params.sarcasm_level == 0.6
        assert params.warmth == 0.7

    def test_prompt_context_generation(self):
        """Should generate valid prompt context."""
        params = ModulationParameters(
            sarcasm_level=0.6,
            formality=0.3,
            warmth=0.7,
            response_length=100,
            humor_frequency=0.4,
            self_deprecation=0.5,
            emoji_frequency=0.6,
            nickname_frequency=0.3,
        )
        context = params.to_prompt_context()
        assert "Sarcasm level" in context
        assert "60%" in context
        assert "100 words" in context


class TestPersonalityModulatorInitialization:
    """Test modulator setup."""

    def test_modulator_loads_traits(self):
        """Should load personality traits from YAML."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        traits_file = os.path.join(
            base_dir, "..", "src", "emotion", "personality_traits.yaml"
        )

        modulator = PersonalityModulator(traits_file=traits_file)
        assert "baseline" in modulator.traits
        assert "modulation" in modulator.traits
        assert modulator.baseline["warmth"] == 0.7


class TestEmotionModulation:
    """Test emotional modulation of personality parameters."""

    def test_loneliness_increases_sarcasm(self):
        """Lonely Demi should be more sarcastic."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        # Neutral state
        neutral_state = EmotionalState()
        neutral_params = modulator.modulate(neutral_state)

        # Lonely state
        lonely_state = EmotionalState(loneliness=0.9)
        lonely_params = modulator.modulate(lonely_state)

        # Sarcasm should increase
        assert lonely_params.sarcasm_level > neutral_params.sarcasm_level

    def test_loneliness_increases_emoji_frequency(self):
        """Lonely Demi should use more emojis."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        neutral_state = EmotionalState()
        neutral_params = modulator.modulate(neutral_state)

        lonely_state = EmotionalState(loneliness=0.9)
        lonely_params = modulator.modulate(lonely_state)

        # Emoji frequency should increase
        assert lonely_params.emoji_frequency > neutral_params.emoji_frequency

    def test_excitement_decreases_sarcasm(self):
        """Excited Demi should be less sarcastic (genuine enthusiasm)."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        neutral_state = EmotionalState()
        neutral_params = modulator.modulate(neutral_state)

        excited_state = EmotionalState(excitement=0.9)
        excited_params = modulator.modulate(excited_state)

        # Sarcasm should decrease
        assert excited_params.sarcasm_level < neutral_params.sarcasm_level

    def test_excitement_increases_warmth(self):
        """Excited Demi should be warmer."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        excited_state = EmotionalState(excitement=0.9)
        excited_params = modulator.modulate(excited_state)

        # Warmth should be high
        assert excited_params.warmth > 0.8

    def test_frustration_increases_sarcasm(self):
        """Frustrated Demi should be more sarcastic."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        neutral_state = EmotionalState()
        neutral_params = modulator.modulate(neutral_state)

        frustrated_state = EmotionalState(frustration=0.9)
        frustrated_params = modulator.modulate(frustrated_state)

        # Sarcasm should increase
        assert frustrated_params.sarcasm_level > neutral_params.sarcasm_level

    def test_affection_increases_warmth_significantly(self):
        """Affectionate Demi should be much warmer."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        affectionate_state = EmotionalState(affection=0.9)
        affectionate_params = modulator.modulate(affectionate_state)

        # Warmth should be very high
        assert affectionate_params.warmth > 0.9


class TestSituationalGates:
    """Test situational override of emotional modulation."""

    def test_serious_context_overrides_modulation(self):
        """Death/loss/crisis should use baseline personality."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        # Frustrated state
        frustrated_state = EmotionalState(frustration=0.9)

        # With normal context
        normal_params = modulator.modulate(frustrated_state)

        # With serious context (should use baseline)
        serious_params = modulator.modulate(
            frustrated_state,
            situational_context="I just heard someone died in a car crash",
        )

        # Baseline sarcasm
        baseline_sarcasm = modulator.baseline["sarcasm"]

        # Serious should use baseline (not affected by frustration)
        assert serious_params.sarcasm_level == baseline_sarcasm
        # Normal should be higher (frustration increases sarcasm)
        assert normal_params.sarcasm_level > baseline_sarcasm

        # Serious should be more like baseline (less affected by frustration)
        baseline_sarcasm = modulator.baseline["sarcasm"]

        # Serious params should be closer to baseline
        assert abs(serious_params.sarcasm_level - baseline_sarcasm) < abs(
            normal_params.sarcasm_level - baseline_sarcasm
        )

    def test_force_serious_flag(self):
        """force_serious=True should use baseline."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        excited_state = EmotionalState(excitement=0.95)

        serious_params = modulator.modulate(excited_state, force_serious=True)

        # Should be baseline, not excited
        assert serious_params.sarcasm_level == modulator.baseline["sarcasm"]

    def test_loss_context_detected(self):
        """'loss' keyword should trigger serious mode."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        excited_state = EmotionalState(excitement=0.9)

        serious_params = modulator.modulate(
            excited_state, situational_context="I experienced a great loss"
        )

        # Should use baseline warmth, not excited warmth
        baseline_warmth = modulator.baseline["warmth"]
        assert serious_params.warmth == baseline_warmth

    def test_emergency_context_detected(self):
        """'emergency' keyword should trigger serious mode."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        affectionate_state = EmotionalState(affection=0.95)

        serious_params = modulator.modulate(
            affectionate_state, situational_context="Medical emergency"
        )

        # Should use baseline, not affectionate
        assert serious_params.tone_flags.get("serious_mode") is True


class TestVarianceValidation:
    """Test acceptable variance bounds checking."""

    def test_validate_variance_within_bounds(self):
        """Valid parameters should pass validation."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        # Modulate from emotional state
        state = EmotionalState(excitement=0.6, loneliness=0.4)
        params = modulator.modulate(state)

        # Validate
        validation = modulator.validate_variance(params)

        # All parameters should be valid
        assert all(validation.values())

    def test_out_of_bounds_detection(self):
        """Out-of-bounds parameters should fail validation."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        # Create extreme parameters
        extreme_params = ModulationParameters(
            sarcasm_level=0.95,  # Way above baseline 0.6 * 1.3
            formality=0.3,
            warmth=0.7,
            response_length=100,
            humor_frequency=0.4,
            self_deprecation=0.5,
            emoji_frequency=0.6,
            nickname_frequency=0.3,
        )

        validation = modulator.validate_variance(extreme_params)

        # Sarcasm should be flagged as out of bounds
        assert not validation["sarcasm"]

    def test_baseline_always_valid(self):
        """Baseline parameters should always be valid."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        baseline_params = modulator._create_parameters_from_baseline()
        validation = modulator.validate_variance(baseline_params)

        # All should be valid
        assert all(validation.values())


class TestSelfAwarenessComments:
    """Test self-awareness commentary generation."""

    def test_no_comment_on_neutral_state(self):
        """Neutral emotional state should not generate commentary."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        neutral_state = EmotionalState()  # All at 0.5
        comment = modulator.get_self_awareness_comment(neutral_state)

        # Should return None (no comment)
        assert comment is None

    def test_loneliness_generates_comment(self):
        """High loneliness should generate self-aware comment."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        lonely_state = EmotionalState(loneliness=0.8)
        comment = modulator.get_self_awareness_comment(lonely_state)

        # Should return a comment about loneliness
        assert comment is not None
        assert "lonely" in comment.lower()

    def test_excitement_generates_comment(self):
        """High excitement should generate self-aware comment."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        excited_state = EmotionalState(excitement=0.9)
        comment = modulator.get_self_awareness_comment(excited_state)

        # Should return a comment about excitement
        assert comment is not None
        assert "excited" in comment.lower()

    def test_frustration_generates_comment(self):
        """High frustration should generate self-aware comment."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        frustrated_state = EmotionalState(frustration=0.75)
        comment = modulator.get_self_awareness_comment(frustrated_state)

        # Should return a comment about being in a mood
        assert comment is not None
        assert "mood" in comment.lower()

    def test_vulnerability_generates_comment(self):
        """High vulnerability should generate self-aware comment."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        vulnerable_state = EmotionalState(vulnerability=0.65)
        comment = modulator.get_self_awareness_comment(vulnerable_state)

        # Should return a comment about honesty
        assert comment is not None
        assert "honest" in comment.lower()

    def test_affection_generates_comment(self):
        """High affection should generate self-aware comment."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        affectionate_state = EmotionalState(affection=0.75)
        comment = modulator.get_self_awareness_comment(affectionate_state)

        # Should return a comment about being cared-for
        assert comment is not None
        assert "cared" in comment.lower() or "feel" in comment.lower()


class TestModulationRanges:
    """Test that modulation stays within specified ranges."""

    def test_sarcasm_modulation_range(self):
        """Sarcasm should stay between 0-1 regardless of emotion mix."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        # Test extreme emotional state
        extreme_state = EmotionalState(
            loneliness=0.99, frustration=0.99, defensiveness=0.99
        )
        params = modulator.modulate(extreme_state)

        # Should still be clamped to [0, 1]
        assert 0 <= params.sarcasm_level <= 1

    def test_warmth_modulation_range(self):
        """Warmth should stay between 0-1."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        # Test extreme emotional state
        extreme_state = EmotionalState(
            affection=0.99, excitement=0.99, vulnerability=0.99
        )
        params = modulator.modulate(extreme_state)

        # Should still be clamped to [0, 1]
        assert 0 <= params.warmth <= 1

    def test_response_length_respects_bounds(self):
        """Response length should respect min/max from baseline."""
        traits_file = os.path.join(
            os.path.dirname(__file__), "..", "src", "emotion", "personality_traits.yaml"
        )
        modulator = PersonalityModulator(traits_file=traits_file)

        # High curiosity
        curious_state = EmotionalState(curiosity=0.95)
        params = modulator.modulate(curious_state)

        min_length = modulator.baseline["min_length"]
        max_length = modulator.baseline["max_length"]

        assert min_length <= params.response_length <= max_length


class TestPromptContextFormatting:
    """Test that prompt context is properly formatted for LLM."""

    def test_prompt_context_includes_all_params(self):
        """Generated context should include all modulation parameters."""
        params = ModulationParameters(
            sarcasm_level=0.6,
            formality=0.3,
            warmth=0.7,
            response_length=100,
            humor_frequency=0.4,
            self_deprecation=0.5,
            emoji_frequency=0.6,
            nickname_frequency=0.3,
            tone_flags={"seeking_tone": True},
        )

        context = params.to_prompt_context()

        assert "Sarcasm level" in context
        assert "Formality" in context
        assert "Warmth" in context
        assert "Response length" in context
        assert "Humor frequency" in context
        assert "Self-deprecation" in context
        assert "Emoji frequency" in context
        assert "Nickname usage" in context

    def test_tone_flags_in_context(self):
        """Tone flags should be formatted as communication style."""
        params = ModulationParameters(
            sarcasm_level=0.6,
            formality=0.3,
            warmth=0.7,
            response_length=100,
            humor_frequency=0.4,
            self_deprecation=0.5,
            emoji_frequency=0.6,
            nickname_frequency=0.3,
            tone_flags={"seeking_tone": True, "honest_tone": True},
        )

        context = params.to_prompt_context()

        assert "Communication style:" in context
        assert "Seeking Tone" in context
        assert "Honest Tone" in context
