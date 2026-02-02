package com.demi.chat.data.models

import com.google.gson.annotations.SerializedName

data class Message(
    @SerializedName("message_id") val messageId: String,
    @SerializedName("conversation_id") val conversationId: String,
    @SerializedName("sender") val sender: String, // "user" or "demi"
    @SerializedName("content") val content: String,
    @SerializedName("emotion_state") val emotionState: EmotionalState? = null,
    @SerializedName("status") val status: String = "sent", // sent, delivered, read
    @SerializedName("delivered_at") val deliveredAt: String? = null,
    @SerializedName("read_at") val readAt: String? = null,
    @SerializedName("created_at") val createdAt: String
) {
    val isFromDemi: Boolean get() = sender == "demi"
    val isRead: Boolean get() = status == "read"
    val isDelivered: Boolean get() = status == "delivered" || status == "read"
}

data class SendMessageRequest(
    @SerializedName("content") val content: String
)

data class WebSocketEvent(
    @SerializedName("event") val event: String,
    @SerializedName("data") val data: Map<String, Any>?,
    @SerializedName("timestamp") val timestamp: String? = null
)

data class HistoryResponse(
    @SerializedName("messages") val messages: List<Message>,
    @SerializedName("count") val count: Int
)
