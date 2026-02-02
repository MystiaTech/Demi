import pytest
import discord
from src.integrations.discord_bot import (
    format_response_as_embed,
    get_dominant_emotion,
    EMOTION_COLORS
)


class TestEmotionColorMapping:
    def test_get_dominant_emotion_with_excited(self):
        emotion_state = {"excitement": 0.9, "loneliness": 0.1}
        emotion, color = get_dominant_emotion(emotion_state)
        assert emotion == "excitement"
        assert color == EMOTION_COLORS["excitement"]

    def test_get_dominant_emotion_with_lonely(self):
        emotion_state = {"loneliness": 0.8, "excitement": 0.2}
        emotion, color = get_dominant_emotion(emotion_state)
        assert emotion == "loneliness"
        assert color == EMOTION_COLORS["loneliness"]

    def test_get_dominant_emotion_empty_dict(self):
        emotion, color = get_dominant_emotion({})
        assert emotion == "neutral"
        assert color == discord.Color.blurple()

    def test_get_dominant_emotion_none(self):
        emotion, color = get_dominant_emotion(None)
        assert emotion == "neutral"
        assert color == discord.Color.blurple()


class TestEmbedFormatting:
    def test_format_response_basic(self):
        response = {
            "content": "Hey, how's it going?",
            "emotion_state": {"excitement": 0.7}
        }
        embed = format_response_as_embed(response, "TestUser")

        assert embed.title == "Demi's Response"
        assert "Hey, how's it going?" in embed.description
        assert embed.color == discord.Color.green()  # excitement color

    def test_format_response_long_content_truncated(self):
        long_content = "x" * 2500
        response = {
            "content": long_content,
            "emotion_state": {}
        }
        embed = format_response_as_embed(response)

        # Description should be truncated to 2000 chars
        assert len(embed.description) <= 2000
        assert embed.description.endswith("x")

    def test_format_response_with_emotion_breakdown(self):
        response = {
            "content": "Response text",
            "emotion_state": {
                "excitement": 0.8,
                "affection": 0.6,
                "loneliness": 0.1  # Below threshold, shouldn't appear
            }
        }
        embed = format_response_as_embed(response)

        # Should have emotion breakdown field
        fields = [f.name for f in embed.fields]
        assert "Emotional Context" in fields

    def test_format_response_missing_emotion_state(self):
        response = {"content": "Just text"}
        embed = format_response_as_embed(response)

        assert embed.description == "Just text"
        assert embed.color == discord.Color.blurple()  # fallback color


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
