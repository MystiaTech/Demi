package com.demi.chat.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.demi.chat.api.WebSocketState
import com.demi.chat.data.models.Message
import com.demi.chat.viewmodel.ChatViewModel
import kotlinx.coroutines.launch

@Composable
fun ChatScreen(
    viewModel: ChatViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        viewModel.connect()
    }

    // Auto-scroll to bottom on new messages
    LaunchedEffect(uiState.messages.size) {
        if (uiState.messages.isNotEmpty()) {
            scope.launch {
                listState.animateScrollToItem(uiState.messages.size - 1)
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // Connection status banner
        if (uiState.connectionState !is WebSocketState.Connected) {
            ConnectionStatusBanner(uiState.connectionState)
        }

        // Messages list
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(vertical = 16.dp)
        ) {
            items(uiState.messages, key = { it.messageId }) { message ->
                MessageBubble(
                    message = message,
                    onVisible = {
                        if (message.isFromDemi && !message.isRead) {
                            viewModel.markMessageAsRead(message.messageId)
                        }
                    }
                )
            }

            // Typing indicator
            if (uiState.isTyping) {
                item {
                    TypingIndicator()
                }
            }
        }

        // Input field
        MessageInput(
            text = uiState.inputText,
            onTextChange = viewModel::updateInputText,
            onSend = viewModel::sendMessage,
            enabled = uiState.connectionState is WebSocketState.Connected
        )
    }
}

@Composable
fun ConnectionStatusBanner(state: WebSocketState) {
    val (text, color) = when (state) {
        is WebSocketState.Connecting -> "Connecting..." to MaterialTheme.colorScheme.tertiary
        is WebSocketState.Disconnected -> "Disconnected" to MaterialTheme.colorScheme.error
        is WebSocketState.Error -> "Connection error" to MaterialTheme.colorScheme.error
        is WebSocketState.Connected -> return // Don't show banner when connected
    }

    Surface(
        color = color,
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(8.dp),
            color = MaterialTheme.colorScheme.onError,
            style = MaterialTheme.typography.bodySmall
        )
    }
}

@Composable
fun MessageBubble(
    message: Message,
    onVisible: () -> Unit
) {
    LaunchedEffect(message.messageId) {
        onVisible()
    }

    val isFromDemi = message.isFromDemi
    val bubbleColor = if (isFromDemi) {
        MaterialTheme.colorScheme.secondaryContainer
    } else {
        MaterialTheme.colorScheme.primaryContainer
    }
    val alignment = if (isFromDemi) Alignment.Start else Alignment.End

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = alignment
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 280.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(bubbleColor)
                .padding(12.dp)
        ) {
            Text(
                text = message.content,
                color = if (isFromDemi) {
                    MaterialTheme.colorScheme.onSecondaryContainer
                } else {
                    MaterialTheme.colorScheme.onPrimaryContainer
                }
            )
        }

        // Status indicator (for user messages)
        if (!isFromDemi) {
            Text(
                text = when (message.status) {
                    "read" -> "Read"
                    "delivered" -> "Delivered"
                    else -> "Sent"
                },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 2.dp, end = 4.dp)
            )
        }
    }
}

@Composable
fun TypingIndicator() {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.secondaryContainer)
            .padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(
            text = "Demi is thinking...",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSecondaryContainer
        )
    }
}

@Composable
fun MessageInput(
    text: String,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    enabled: Boolean
) {
    Surface(
        tonalElevation = 3.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = text,
                onValueChange = onTextChange,
                placeholder = { Text("Message Demi...") },
                modifier = Modifier.weight(1f),
                enabled = enabled,
                singleLine = false,
                maxLines = 4
            )

            Spacer(modifier = Modifier.width(8.dp))

            IconButton(
                onClick = onSend,
                enabled = enabled && text.isNotBlank()
            ) {
                Icon(
                    imageVector = Icons.Default.Send,
                    contentDescription = "Send",
                    tint = if (enabled && text.isNotBlank()) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    }
                )
            }
        }
    }
}
