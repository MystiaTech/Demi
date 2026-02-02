package com.demi.chat.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.demi.chat.data.models.EmotionalState
import com.demi.chat.data.models.Message
import com.demi.chat.data.models.Session
import com.demi.chat.data.repository.AuthRepository
import com.demi.chat.data.repository.AuthResult
import com.demi.chat.data.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val emotionalState: EmotionalState? = null,
    val sessions: List<Session> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val chatRepository: ChatRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        loadSessions()
        observeEmotionalState()
    }

    private fun observeEmotionalState() {
        chatRepository.messages
            .map { messages ->
                // Get most recent Demi message with emotional state
                messages.lastOrNull { it.isFromDemi && it.emotionState != null }?.emotionState
            }
            .onEach { emotionalState ->
                _uiState.value = _uiState.value.copy(emotionalState = emotionalState)
            }
            .launchIn(viewModelScope)
    }

    fun loadSessions() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)

            when (val result = authRepository.getSessions()) {
                is AuthResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        sessions = result.data.sessions
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

    fun revokeSession(sessionId: String) {
        viewModelScope.launch {
            when (authRepository.revokeSession(sessionId)) {
                is AuthResult.Success -> {
                    loadSessions() // Reload after revocation
                }
                is AuthResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        error = "Failed to revoke session"
                    )
                }
                AuthResult.Loading -> {}
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
