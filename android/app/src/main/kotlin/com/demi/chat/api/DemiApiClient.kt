package com.demi.chat.api

import com.demi.chat.BuildConfig
import com.demi.chat.data.models.*
import com.demi.chat.utils.TokenManager
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

interface DemiApi {
    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(@Body request: RefreshTokenRequest): Response<TokenResponse>

    @GET("api/v1/auth/sessions")
    suspend fun getSessions(): Response<SessionListResponse>

    @DELETE("api/v1/auth/sessions/{session_id}")
    suspend fun revokeSession(@Path("session_id") sessionId: String): Response<Unit>

    @GET("api/v1/messages")
    suspend fun getMessages(): Response<List<Message>>

    @GET("api/v1/health")
    suspend fun healthCheck(): Response<Map<String, String>>
}

@Singleton
class DemiApiClient @Inject constructor(
    private val tokenManager: TokenManager
) {
    private val baseUrl = BuildConfig.API_BASE_URL

    private val authInterceptor = Interceptor { chain ->
        val request = chain.request().newBuilder()
        tokenManager.accessToken?.let { token ->
            request.addHeader("Authorization", "Bearer $token")
        }
        chain.proceed(request.build())
    }

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BODY
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    val api: DemiApi = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(DemiApi::class.java)

    fun getWebSocketUrl(): String {
        val wsProtocol = if (baseUrl.startsWith("https")) "wss" else "ws"
        val host = baseUrl.removePrefix("https://").removePrefix("http://")
        return "$wsProtocol://$host/api/v1/chat/ws?token=${tokenManager.accessToken}"
    }
}
