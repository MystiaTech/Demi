package com.demi.chat.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.demi.chat.data.repository.AuthRepository
import com.demi.chat.data.repository.AuthResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val isLoggedIn: Boolean = false,
    val error: String? = null,
    val email: String = "",
    val requiresBiometric: Boolean = false
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    init {
        checkLoginStatus()
    }

    private fun checkLoginStatus() {
        val loggedIn = authRepository.isLoggedIn()
        val timedOut = authRepository.isSessionTimedOut()

        _uiState.value = _uiState.value.copy(
            isLoggedIn = loggedIn && !timedOut,
            requiresBiometric = loggedIn && timedOut
        )
    }

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)

            when (val result = authRepository.login(email, password)) {
                is AuthResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isLoggedIn = true,
                        email = email
                    )
                }
                is AuthResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.message
                    )
                }
                AuthResult.Loading -> {}
            }
        }
    }

    fun logout() {
        authRepository.logout()
        _uiState.value = AuthUiState()
    }

    fun updateActivity() {
        authRepository.updateActivity()
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    fun onBiometricSuccess() {
        authRepository.updateActivity()
        _uiState.value = _uiState.value.copy(
            isLoggedIn = true,
            requiresBiometric = false
        )
    }
}
