package com.demi.chat.di

import android.content.Context
import com.demi.chat.api.DemiApiClient
import com.demi.chat.api.WebSocketManager
import com.demi.chat.data.repository.AuthRepository
import com.demi.chat.data.repository.ChatRepository
import com.demi.chat.utils.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideTokenManager(@ApplicationContext context: Context): TokenManager {
        return TokenManager(context)
    }

    @Provides
    @Singleton
    fun provideDemiApiClient(tokenManager: TokenManager): DemiApiClient {
        return DemiApiClient(tokenManager)
    }

    @Provides
    @Singleton
    fun provideWebSocketManager(apiClient: DemiApiClient): WebSocketManager {
        return WebSocketManager(apiClient)
    }

    @Provides
    @Singleton
    fun provideAuthRepository(
        apiClient: DemiApiClient,
        tokenManager: TokenManager
    ): AuthRepository {
        return AuthRepository(apiClient, tokenManager)
    }

    @Provides
    @Singleton
    fun provideChatRepository(webSocketManager: WebSocketManager): ChatRepository {
        return ChatRepository(webSocketManager)
    }

    @Provides
    @Singleton
    fun provideBiometricManager(@ApplicationContext context: Context): DemiBiometricManager {
        return DemiBiometricManager(context)
    }

    @Provides
    @Singleton
    fun provideNotificationHelper(@ApplicationContext context: Context): NotificationHelper {
        return NotificationHelper(context)
    }

    @Provides
    @Singleton
    fun provideDataExporter(
        @ApplicationContext context: Context,
        chatRepository: ChatRepository,
        tokenManager: TokenManager
    ): DataExporter {
        return DataExporter(context, chatRepository, tokenManager)
    }
}
