package com.demi.chat.data.models

import com.google.gson.annotations.SerializedName

data class Session(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("last_activity") val lastActivity: String,
    @SerializedName("expires_at") val expiresAt: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("is_current") val isCurrent: Boolean
)

data class SessionListResponse(
    @SerializedName("sessions") val sessions: List<Session>,
    @SerializedName("total_count") val totalCount: Int
)
