package com.demi.chat.ui.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.demi.chat.data.models.EmotionalState
import com.demi.chat.data.models.Session
import com.demi.chat.viewmodel.DashboardViewModel

@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel = hiltViewModel(),
    onExportData: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadSessions()
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp)
    ) {
        // Emotional State Section
        item {
            Text(
                text = "Demi's Emotional State",
                style = MaterialTheme.typography.headlineSmall
            )
        }

        item {
            uiState.emotionalState?.let { state ->
                EmotionalStateCard(state)
            } ?: run {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "No emotional data yet. Start chatting!",
                        modifier = Modifier.padding(16.dp),
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }

        // Sessions Section
        item {
            Text(
                text = "Active Sessions",
                style = MaterialTheme.typography.headlineSmall
            )
        }

        if (uiState.isLoading) {
            item {
                CircularProgressIndicator(modifier = Modifier.padding(16.dp))
            }
        } else {
            items(uiState.sessions) { session ->
                SessionCard(
                    session = session,
                    onRevoke = { viewModel.revokeSession(session.sessionId) }
                )
            }
        }

        // Export Data Button
        item {
            Spacer(modifier = Modifier.height(16.dp))
            OutlinedButton(
                onClick = onExportData,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Export All Data (GDPR)")
            }
        }
    }
}

@Composable
fun EmotionalStateCard(state: EmotionalState) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Mood: ${state.moodDescription()}",
                style = MaterialTheme.typography.titleMedium
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Emotion bars
            EmotionBar("Happiness", state.happiness, Color(0xFF4CAF50))
            EmotionBar("Affection", state.affection, Color(0xFFE91E63))
            EmotionBar("Excitement", state.excitement, Color(0xFFFF9800))
            EmotionBar("Trust", state.trust, Color(0xFF2196F3))
            EmotionBar("Loneliness", state.loneliness, Color(0xFF9C27B0))
            EmotionBar("Sadness", state.sadness, Color(0xFF607D8B))
            EmotionBar("Frustration", state.frustration, Color(0xFFF44336))
            EmotionBar("Anger", state.anger, Color(0xFFD32F2F))
            EmotionBar("Fear", state.fear, Color(0xFF795548))
        }
    }
}

@Composable
fun EmotionBar(name: String, value: Float, color: Color) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(text = name, style = MaterialTheme.typography.bodySmall)
            Text(text = "${(value * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
        }
        LinearProgressIndicator(
            progress = { value },
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp),
            color = color,
            trackColor = color.copy(alpha = 0.2f)
        )
    }
}

@Composable
fun SessionCard(session: Session, onRevoke: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = session.deviceName,
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = if (session.isCurrent) "This device" else "Last active: ${session.lastActivity.take(10)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            if (!session.isCurrent) {
                IconButton(onClick = onRevoke) {
                    Icon(
                        imageVector = Icons.Default.Delete,
                        contentDescription = "Revoke session",
                        tint = MaterialTheme.colorScheme.error
                    )
                }
            }
        }
    }
}
