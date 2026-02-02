package com.demi.chat.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.demi.chat.api.WebSocketState
import com.demi.chat.data.models.Message
import com.demi.chat.data.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChatUiState(
    val messages: List<Message> = emptyList(),
    val isTyping: Boolean = false,
    val connectionState: WebSocketState = WebSocketState.Disconnected,
    val inputText: String = "",
    val error: String? = null
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val chatRepository: ChatRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    init {
        observeMessages()
        observeTyping()
        observeConnectionState()
    }

    private fun observeMessages() {
        chatRepository.messages
            .onEach { messages ->
                _uiState.value = _uiState.value.copy(messages = messages)
            }
            .launchIn(viewModelScope)
    }

    private fun observeTyping() {
        chatRepository.isTyping
            .onEach { isTyping ->
                _uiState.value = _uiState.value.copy(isTyping = isTyping)
            }
            .launchIn(viewModelScope)
    }

    private fun observeConnectionState() {
        chatRepository.connectionState
            .onEach { state ->
                _uiState.value = _uiState.value.copy(connectionState = state)
            }
            .launchIn(viewModelScope)
    }

    fun connect() {
        chatRepository.connect()
    }

    fun disconnect() {
        chatRepository.disconnect()
    }

    fun sendMessage() {
        val content = _uiState.value.inputText.trim()
        if (content.isNotEmpty()) {
            chatRepository.sendMessage(content)
            _uiState.value = _uiState.value.copy(inputText = "")
        }
    }

    fun updateInputText(text: String) {
        _uiState.value = _uiState.value.copy(inputText = text)
    }

    fun markMessageAsRead(messageId: String) {
        chatRepository.markAsRead(messageId)
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    override fun onCleared() {
        super.onCleared()
        disconnect()
    }
}
