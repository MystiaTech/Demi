package com.demi.chat.api

import android.util.Log
import com.demi.chat.data.models.*
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.*
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

sealed class WebSocketState {
    object Disconnected : WebSocketState()
    object Connecting : WebSocketState()
    object Connected : WebSocketState()
    data class Error(val message: String) : WebSocketState()
}

sealed class ChatEvent {
    data class MessageReceived(val message: Message) : ChatEvent()
    data class HistoryLoaded(val messages: List<Message>) : ChatEvent()
    data class TypingIndicator(val isTyping: Boolean) : ChatEvent()
    data class ReadReceipt(val messageId: String) : ChatEvent()
    data class DeliveryReceipt(val messageId: String) : ChatEvent()
    data class Error(val message: String) : ChatEvent()
}

@Singleton
class WebSocketManager @Inject constructor(
    private val apiClient: DemiApiClient
) {
    private val TAG = "WebSocketManager"
    private val gson = Gson()
    private val scope = CoroutineScope(Dispatchers.IO)

    private var webSocket: WebSocket? = null
    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 5

    private val _connectionState = MutableStateFlow<WebSocketState>(WebSocketState.Disconnected)
    val connectionState: StateFlow<WebSocketState> = _connectionState

    private val _events = MutableSharedFlow<ChatEvent>(replay = 0)
    val events: SharedFlow<ChatEvent> = _events

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS) // No timeout for WebSocket
        .writeTimeout(10, TimeUnit.SECONDS)
        .pingInterval(30, TimeUnit.SECONDS) // Keep-alive
        .build()

    fun connect() {
        if (_connectionState.value == WebSocketState.Connected ||
            _connectionState.value == WebSocketState.Connecting) {
            return
        }

        _connectionState.value = WebSocketState.Connecting
        val wsUrl = apiClient.getWebSocketUrl()
        Log.d(TAG, "Connecting to WebSocket: $wsUrl")

        val request = Request.Builder()
            .url(wsUrl)
            .build()

        webSocket = client.newWebSocket(request, createListener())
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
        _connectionState.value = WebSocketState.Disconnected
        reconnectAttempts = 0
    }

    fun sendMessage(content: String) {
        val event = mapOf(
            "event" to "message",
            "data" to mapOf("content" to content)
        )
        val json = gson.toJson(event)
        webSocket?.send(json)
        Log.d(TAG, "Sent message: $content")
    }

    fun sendReadReceipt(messageId: String) {
        val event = mapOf(
            "event" to "read_receipt",
            "data" to mapOf("message_id" to messageId)
        )
        val json = gson.toJson(event)
        webSocket?.send(json)
    }

    fun sendPing() {
        val event = mapOf("event" to "ping")
        val json = gson.toJson(event)
        webSocket?.send(json)
    }

    private fun createListener() = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Log.d(TAG, "WebSocket connected")
            _connectionState.value = WebSocketState.Connected
            reconnectAttempts = 0
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            Log.d(TAG, "Received: $text")
            parseEvent(text)
        }

        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            Log.d(TAG, "WebSocket closing: $code $reason")
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.d(TAG, "WebSocket closed: $code $reason")
            _connectionState.value = WebSocketState.Disconnected
            if (code != 1000) {
                attemptReconnect()
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Log.e(TAG, "WebSocket error: ${t.message}", t)
            _connectionState.value = WebSocketState.Error(t.message ?: "Unknown error")
            attemptReconnect()
        }
    }

    /**
     * Parse incoming WebSocket events and emit to event flow.
     * Handles: message, history, typing, read_receipt, delivered, error, pong
     */
    private fun parseEvent(json: String) {
        try {
            val eventType = object : TypeToken<Map<String, Any>>() {}.type
            val eventMap: Map<String, Any> = gson.fromJson(json, eventType)

            when (eventMap["event"]) {
                "message" -> {
                    val dataJson = gson.toJson(eventMap["data"])
                    val message = gson.fromJson(dataJson, Message::class.java)
                    scope.launch { _events.emit(ChatEvent.MessageReceived(message)) }
                }
                "history" -> {
                    val dataMap = eventMap["data"] as? Map<*, *>
                    val messagesJson = gson.toJson(dataMap?.get("messages"))
                    val listType = object : TypeToken<List<Message>>() {}.type
                    val messages: List<Message> = gson.fromJson(messagesJson, listType)
                    scope.launch { _events.emit(ChatEvent.HistoryLoaded(messages)) }
                }
                "typing" -> {
                    val dataMap = eventMap["data"] as? Map<*, *>
                    val isTyping = dataMap?.get("is_typing") as? Boolean ?: false
                    scope.launch { _events.emit(ChatEvent.TypingIndicator(isTyping)) }
                }
                "read_receipt" -> {
                    val dataMap = eventMap["data"] as? Map<*, *>
                    val messageId = dataMap?.get("message_id") as? String ?: return
                    scope.launch { _events.emit(ChatEvent.ReadReceipt(messageId)) }
                }
                "delivered" -> {
                    val dataMap = eventMap["data"] as? Map<*, *>
                    val messageId = dataMap?.get("message_id") as? String ?: return
                    scope.launch { _events.emit(ChatEvent.DeliveryReceipt(messageId)) }
                }
                "error" -> {
                    val dataMap = eventMap["data"] as? Map<*, *>
                    val message = dataMap?.get("message") as? String ?: "Unknown error"
                    scope.launch { _events.emit(ChatEvent.Error(message)) }
                }
                "pong" -> {
                    Log.d(TAG, "Pong received")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing event: ${e.message}", e)
        }
    }

    /**
     * Exponential backoff reconnection strategy.
     * Max 5 attempts with delays: 2s, 4s, 8s, 16s, 30s (capped)
     */
    private fun attemptReconnect() {
        if (reconnectAttempts >= maxReconnectAttempts) {
            Log.e(TAG, "Max reconnect attempts reached")
            _connectionState.value = WebSocketState.Error("Connection failed after $maxReconnectAttempts attempts")
            return
        }

        reconnectAttempts++
        val delayMs = (1000L * (1 shl reconnectAttempts)).coerceAtMost(30000L) // Exponential backoff, max 30s

        Log.d(TAG, "Reconnecting in ${delayMs}ms (attempt $reconnectAttempts)")

        scope.launch {
            delay(delayMs)
            connect()
        }
    }
}
