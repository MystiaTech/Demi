package com.demi.chat.data.models

import com.google.gson.annotations.SerializedName

/**
 * Demi's 9-dimension emotional state.
 * Matches src/models/emotional_state.py
 */
data class EmotionalState(
    @SerializedName("happiness") val happiness: Float = 0.5f,
    @SerializedName("sadness") val sadness: Float = 0.2f,
    @SerializedName("anger") val anger: Float = 0.1f,
    @SerializedName("fear") val fear: Float = 0.1f,
    @SerializedName("surprise") val surprise: Float = 0.3f,
    @SerializedName("disgust") val disgust: Float = 0.05f,
    @SerializedName("trust") val trust: Float = 0.5f,
    @SerializedName("anticipation") val anticipation: Float = 0.4f,
    @SerializedName("loneliness") val loneliness: Float = 0.3f,
    @SerializedName("excitement") val excitement: Float = 0.4f,
    @SerializedName("frustration") val frustration: Float = 0.2f,
    @SerializedName("affection") val affection: Float = 0.5f
) {
    /**
     * Get dominant emotion (highest value)
     */
    fun dominantEmotion(): Pair<String, Float> {
        val emotions = mapOf(
            "happiness" to happiness,
            "sadness" to sadness,
            "anger" to anger,
            "fear" to fear,
            "surprise" to surprise,
            "trust" to trust,
            "loneliness" to loneliness,
            "excitement" to excitement,
            "affection" to affection
        )
        return emotions.maxByOrNull { it.value }?.toPair() ?: ("neutral" to 0.5f)
    }

    /**
     * Get mood description for UI
     */
    fun moodDescription(): String {
        val (emotion, intensity) = dominantEmotion()
        val intensityWord = when {
            intensity > 0.8f -> "very"
            intensity > 0.6f -> "quite"
            intensity > 0.4f -> "somewhat"
            else -> "slightly"
        }
        return "$intensityWord $emotion"
    }
}
