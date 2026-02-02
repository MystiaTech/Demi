package com.demi.chat.utils

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
class TokenManagerTest {

    private lateinit var tokenManager: TokenManager
    private lateinit var context: Context

    @Before
    fun setup() {
        context = ApplicationProvider.getApplicationContext()
        tokenManager = TokenManager(context)
        tokenManager.clearAll()
    }

    @Test
    fun `isLoggedIn returns false when no tokens`() {
        assertFalse(tokenManager.isLoggedIn())
    }

    @Test
    fun `isLoggedIn returns true when tokens exist`() {
        tokenManager.accessToken = "access_token"
        tokenManager.refreshToken = "refresh_token"

        assertTrue(tokenManager.isLoggedIn())
    }

    @Test
    fun `session timeout detected after 30 minutes`() {
        tokenManager.lastActivity = System.currentTimeMillis() - (31 * 60 * 1000L)
        assertTrue(tokenManager.isSessionTimedOut())
    }

    @Test
    fun `session not timed out within 30 minutes`() {
        tokenManager.updateActivity()
        assertFalse(tokenManager.isSessionTimedOut())
    }

    @Test
    fun `clearAll removes all data`() {
        tokenManager.accessToken = "token"
        tokenManager.refreshToken = "refresh"
        tokenManager.userId = "user123"

        tokenManager.clearAll()

        assertEquals(null, tokenManager.accessToken)
        assertEquals(null, tokenManager.refreshToken)
        assertEquals(null, tokenManager.userId)
    }
}
