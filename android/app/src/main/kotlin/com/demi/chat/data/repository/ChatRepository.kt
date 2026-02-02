package com.demi.chat.data.repository

import com.demi.chat.api.ChatEvent
import com.demi.chat.api.WebSocketManager
import com.demi.chat.api.WebSocketState
import com.demi.chat.data.models.Message
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val webSocketManager: WebSocketManager
) {
    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    private val _isTyping = MutableStateFlow(false)
    val isTyping: StateFlow<Boolean> = _isTyping.asStateFlow()

    val connectionState: StateFlow<WebSocketState> = webSocketManager.connectionState

    init {
        // Observe WebSocket events
        webSocketManager.events.onEach { event ->
            handleEvent(event)
        }.launchIn(CoroutineScope(Dispatchers.Default))
    }

    private fun handleEvent(event: ChatEvent) {
        when (event) {
            is ChatEvent.HistoryLoaded -> {
                _messages.value = event.messages
            }
            is ChatEvent.MessageReceived -> {
                val current = _messages.value.toMutableList()
                current.add(event.message)
                _messages.value = current
                _isTyping.value = false
            }
            is ChatEvent.TypingIndicator -> {
                _isTyping.value = event.isTyping
            }
            is ChatEvent.ReadReceipt -> {
                updateMessageStatus(event.messageId, "read")
            }
            is ChatEvent.DeliveryReceipt -> {
                updateMessageStatus(event.messageId, "delivered")
            }
            is ChatEvent.Error -> {
                // Handle error (could emit to error flow)
            }
        }
    }

    private fun updateMessageStatus(messageId: String, status: String) {
        val updated = _messages.value.map { msg ->
            if (msg.messageId == messageId) {
                msg.copy(status = status)
            } else msg
        }
        _messages.value = updated
    }

    fun connect() = webSocketManager.connect()

    fun disconnect() = webSocketManager.disconnect()

    fun sendMessage(content: String) {
        webSocketManager.sendMessage(content)
    }

    fun markAsRead(messageId: String) {
        webSocketManager.sendReadReceipt(messageId)
    }
}
