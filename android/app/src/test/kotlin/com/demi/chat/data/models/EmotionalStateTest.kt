package com.demi.chat.data.models

import org.junit.Test
import kotlin.test.assertEquals

class EmotionalStateTest {

    @Test
    fun `dominantEmotion returns highest value`() {
        val state = EmotionalState(
            happiness = 0.9f,
            sadness = 0.2f,
            anger = 0.1f,
            affection = 0.7f
        )

        val (emotion, intensity) = state.dominantEmotion()
        assertEquals("happiness", emotion)
        assertEquals(0.9f, intensity)
    }

    @Test
    fun `moodDescription formats correctly`() {
        val state = EmotionalState(
            excitement = 0.85f,
            happiness = 0.5f
        )

        val description = state.moodDescription()
        assertEquals("very excitement", description)
    }

    @Test
    fun `moodDescription intensity levels`() {
        val veryHappy = EmotionalState(happiness = 0.9f).moodDescription()
        val quiteHappy = EmotionalState(happiness = 0.7f).moodDescription()
        val somewhatHappy = EmotionalState(happiness = 0.5f).moodDescription()
        val slightlyHappy = EmotionalState(happiness = 0.3f).moodDescription()

        assertEquals("very happiness", veryHappy)
        assertEquals("quite happiness", quiteHappy)
        assertEquals("somewhat happiness", somewhatHappy)
        assertEquals("slightly happiness", slightlyHappy)
    }
}
