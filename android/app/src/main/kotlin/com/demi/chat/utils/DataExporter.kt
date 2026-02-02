package com.demi.chat.utils

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.FileProvider
import com.demi.chat.data.models.Message
import com.demi.chat.data.repository.ChatRepository
import com.google.gson.GsonBuilder
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.first
import java.io.File
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject
import javax.inject.Singleton

data class ExportData(
    val exportedAt: String,
    val userId: String?,
    val email: String?,
    val messages: List<Message>,
    val totalMessages: Int
)

@Singleton
class DataExporter @Inject constructor(
    @ApplicationContext private val context: Context,
    private val chatRepository: ChatRepository,
    private val tokenManager: TokenManager
) {
    private val gson = GsonBuilder()
        .setPrettyPrinting()
        .setDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
        .create()

    suspend fun exportToJson(): File {
        val messages = chatRepository.messages.first()

        val exportData = ExportData(
            exportedAt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
                .format(Date()),
            userId = tokenManager.userId,
            email = tokenManager.email,
            messages = messages,
            totalMessages = messages.size
        )

        val json = gson.toJson(exportData)

        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val fileName = "demi_export_$timestamp.json"
        val file = File(context.cacheDir, fileName)
        file.writeText(json)

        return file
    }

    fun shareExportedFile(file: File): Intent {
        val uri: Uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )

        return Intent(Intent.ACTION_SEND).apply {
            type = "application/json"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
    }
}
