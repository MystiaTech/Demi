package com.demi.chat.viewmodel

import com.demi.chat.data.models.TokenResponse
import com.demi.chat.data.repository.AuthRepository
import com.demi.chat.data.repository.AuthResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.MockitoAnnotations
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {

    @Mock
    private lateinit var authRepository: AuthRepository

    private lateinit var viewModel: AuthViewModel
    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        MockitoAnnotations.openMocks(this)
        Dispatchers.setMain(testDispatcher)
        `when`(authRepository.isLoggedIn()).thenReturn(false)
        `when`(authRepository.isSessionTimedOut()).thenReturn(false)
        viewModel = AuthViewModel(authRepository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `login success updates state correctly`() = runTest {
        val email = "test@example.com"
        val password = "password123"
        val tokenResponse = TokenResponse(
            accessToken = "token",
            refreshToken = "refresh",
            tokenType = "Bearer",
            expiresIn = 3600,
            refreshExpiresIn = 86400,
            userId = "user123",
            email = email,
            sessionId = "session123"
        )

        `when`(authRepository.login(email, password))
            .thenReturn(AuthResult.Success(tokenResponse))

        viewModel.login(email, password)
        advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertFalse(state.isLoading)
        assertTrue(state.isLoggedIn)
        assertEquals(email, state.email)
        assertEquals(null, state.error)
    }

    @Test
    fun `login failure shows error`() = runTest {
        val email = "test@example.com"
        val password = "wrongpassword"
        val errorMessage = "Invalid credentials"

        `when`(authRepository.login(email, password))
            .thenReturn(AuthResult.Error(errorMessage))

        viewModel.login(email, password)
        advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertFalse(state.isLoading)
        assertFalse(state.isLoggedIn)
        assertEquals(errorMessage, state.error)
    }

    @Test
    fun `logout clears state`() = runTest {
        viewModel.logout()
        advanceUntilIdle()

        verify(authRepository).logout()
        val state = viewModel.uiState.first()
        assertFalse(state.isLoggedIn)
    }
}
