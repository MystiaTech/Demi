package com.demi.chat.data.repository

import com.demi.chat.api.DemiApiClient
import com.demi.chat.data.models.*
import com.demi.chat.utils.TokenManager
import javax.inject.Inject
import javax.inject.Singleton

sealed class AuthResult<out T> {
    data class Success<T>(val data: T) : AuthResult<T>()
    data class Error(val message: String, val code: Int? = null) : AuthResult<Nothing>()
    object Loading : AuthResult<Nothing>()
}

@Singleton
class AuthRepository @Inject constructor(
    private val apiClient: DemiApiClient,
    private val tokenManager: TokenManager
) {
    suspend fun login(email: String, password: String): AuthResult<TokenResponse> {
        return try {
            val request = LoginRequest(email = email, password = password)
            val response = apiClient.api.login(request)

            if (response.isSuccessful && response.body() != null) {
                val tokens = response.body()!!
                saveTokens(tokens)
                AuthResult.Success(tokens)
            } else {
                val errorMsg = when (response.code()) {
                    401 -> "Invalid email or password"
                    403 -> "Account locked. Try again later."
                    else -> "Login failed: ${response.message()}"
                }
                AuthResult.Error(errorMsg, response.code())
            }
        } catch (e: Exception) {
            AuthResult.Error("Network error: ${e.message}")
        }
    }

    suspend fun refreshAccessToken(): AuthResult<TokenResponse> {
        val refreshToken = tokenManager.refreshToken
            ?: return AuthResult.Error("No refresh token")

        return try {
            val request = RefreshTokenRequest(refreshToken)
            val response = apiClient.api.refreshToken(request)

            if (response.isSuccessful && response.body() != null) {
                val tokens = response.body()!!
                saveTokens(tokens)
                AuthResult.Success(tokens)
            } else {
                AuthResult.Error("Token refresh failed", response.code())
            }
        } catch (e: Exception) {
            AuthResult.Error("Network error: ${e.message}")
        }
    }

    suspend fun getSessions(): AuthResult<SessionListResponse> {
        return try {
            val response = apiClient.api.getSessions()
            if (response.isSuccessful && response.body() != null) {
                AuthResult.Success(response.body()!!)
            } else {
                AuthResult.Error("Failed to get sessions", response.code())
            }
        } catch (e: Exception) {
            AuthResult.Error("Network error: ${e.message}")
        }
    }

    suspend fun revokeSession(sessionId: String): AuthResult<Unit> {
        return try {
            val response = apiClient.api.revokeSession(sessionId)
            if (response.isSuccessful) {
                AuthResult.Success(Unit)
            } else {
                AuthResult.Error("Failed to revoke session", response.code())
            }
        } catch (e: Exception) {
            AuthResult.Error("Network error: ${e.message}")
        }
    }

    fun logout() {
        tokenManager.clearAll()
    }

    fun isLoggedIn(): Boolean = tokenManager.isLoggedIn()

    fun isSessionTimedOut(): Boolean = tokenManager.isSessionTimedOut()

    fun updateActivity() = tokenManager.updateActivity()

    private fun saveTokens(tokens: TokenResponse) {
        tokenManager.accessToken = tokens.accessToken
        tokenManager.refreshToken = tokens.refreshToken
        tokenManager.userId = tokens.userId
        tokenManager.email = tokens.email
        tokenManager.sessionId = tokens.sessionId
        tokenManager.tokenExpiry = System.currentTimeMillis() + (tokens.expiresIn * 1000L)
        tokenManager.updateActivity()
    }
}
