package com.demi.chat.utils

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.demi.chat.MainActivity
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NotificationHelper @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        const val CHANNEL_MESSAGES = "demi_messages"
        const val CHANNEL_CHECKINS = "demi_checkins"
        const val NOTIFICATION_ID_MESSAGE = 1001
        const val NOTIFICATION_ID_CHECKIN = 1002
    }

    init {
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        val messageChannel = NotificationChannel(
            CHANNEL_MESSAGES,
            "Messages",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "New messages from Demi"
        }

        val checkinChannel = NotificationChannel(
            CHANNEL_CHECKINS,
            "Check-ins",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Autonomous check-ins and important messages from Demi"
        }

        val notificationManager = context.getSystemService(NotificationManager::class.java)
        notificationManager.createNotificationChannel(messageChannel)
        notificationManager.createNotificationChannel(checkinChannel)
    }

    fun showMessageNotification(title: String, content: String, isCheckin: Boolean = false) {
        if (ActivityCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            context, 0, intent,
            PendingIntent.FLAG_IMMUTABLE
        )

        val channelId = if (isCheckin) CHANNEL_CHECKINS else CHANNEL_MESSAGES
        val notificationId = if (isCheckin) NOTIFICATION_ID_CHECKIN else NOTIFICATION_ID_MESSAGE

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info) // Using Android builtin
            .setContentTitle(title)
            .setContentText(content)
            .setPriority(if (isCheckin) NotificationCompat.PRIORITY_HIGH else NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(context).notify(notificationId, notification)
    }

    fun cancelAllNotifications() {
        NotificationManagerCompat.from(context).cancelAll()
    }
}
