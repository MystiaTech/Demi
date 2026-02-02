# Demi Android Client

Kotlin/Jetpack Compose mobile client for the Demi AI companion app.

## Tech Stack

- **Language**: Kotlin
- **UI**: Jetpack Compose with Material3
- **Architecture**: MVVM with StateFlow
- **DI**: Hilt (Dagger)
- **Networking**: Retrofit + OkHttp + WebSocket
- **Security**: EncryptedSharedPreferences, BiometricPrompt
- **Min SDK**: 31 (Android 12+)
- **Target SDK**: 34

## Project Structure

```
app/src/main/kotlin/com/demi/chat/
├── api/
│   ├── DemiApiClient.kt       # Retrofit API client
│   └── WebSocketManager.kt    # Real-time WebSocket connection
├── data/
│   ├── models/                # Data classes (User, Message, EmotionalState)
│   └── repository/            # AuthRepository, ChatRepository
├── di/
│   └── AppModule.kt           # Hilt dependency injection
├── ui/
│   ├── chat/                  # Chat screen with message bubbles
│   ├── dashboard/             # Dashboard with emotional state visualization
│   ├── login/                 # Login screen
│   └── theme/                 # Material3 theme
├── utils/
│   ├── TokenManager.kt        # Secure token storage
│   ├── BiometricManager.kt    # Biometric authentication
│   ├── NotificationHelper.kt  # Push notifications
│   └── DataExporter.kt        # GDPR data export
├── viewmodel/                 # ViewModels for each screen
├── DemiApplication.kt         # Hilt app entry point
└── MainActivity.kt            # Main activity with navigation

app/src/test/kotlin/           # Unit tests
```

## Features

- **Authentication**: Login with email/password, JWT token management, session timeout (30min)
- **Real-time Chat**: WebSocket-based messaging with Demi
- **Emotional State**: 9-dimension emotional state visualization
- **Read Receipts**: Message status (sent, delivered, read)
- **Typing Indicator**: Real-time typing feedback
- **Push Notifications**: Message and check-in notifications
- **Biometric Auth**: Fingerprint/Face unlock support
- **Data Export**: GDPR-compliant JSON export
- **Session Management**: View and revoke active sessions

## Setup

### Prerequisites

- Android Studio Arctic Fox or later
- Android SDK (API 31+)
- JDK 17

### Backend Configuration

The app connects to the FastAPI backend. Update the API URL in `app/build.gradle.kts`:

```kotlin
buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000\"")
```

- Use `http://10.0.2.2:8000` for Android emulator (maps to `localhost:8000`)
- Use `http://<YOUR_IP>:8000` for physical device
- Use `https://api.yourdomain.com` for production

### Build & Run

```bash
# Install dependencies and build
./gradlew build

# Run on emulator/device
./gradlew installDebug

# Run tests
./gradlew test
```

## API Endpoints

The app communicates with these FastAPI backend endpoints:

- `POST /api/v1/auth/login` - Authenticate user
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/sessions` - List active sessions
- `DELETE /api/v1/auth/sessions/{id}` - Revoke session
- `WS /api/v1/chat/ws?token={token}` - WebSocket for real-time chat
- `GET /api/v1/messages` - Fetch message history

## WebSocket Events

The client handles these WebSocket events:

**Received from backend:**
- `message` - New message from Demi
- `history` - Message history on connection
- `typing` - Demi typing indicator
- `delivered` - Message delivery confirmation
- `read_receipt` - Message read confirmation
- `pong` - Keep-alive response

**Sent to backend:**
- `message` - Send user message
- `read_receipt` - Mark message as read
- `ping` - Keep-alive ping

## Testing

Unit tests cover:
- `AuthViewModel` - Login flow, error handling
- `TokenManager` - Secure storage, session timeout
- `EmotionalState` - Dominant emotion, mood descriptions

Run tests:
```bash
./gradlew test
./gradlew connectedAndroidTest  # Instrumented tests
```

## Security

- **Token Storage**: AES256-GCM encrypted SharedPreferences via Android KeyStore
- **Network**: TLS for production, cleartext allowed for development
- **Biometric**: Strong biometric + device credential authentication
- **Session Timeout**: 30-minute inactivity timeout

## Known Limitations

- Notification icon placeholder (uses Android builtin)
- Export feature UI not fully wired (DataExporter ready)
- WebSocketService stub (needs foreground service implementation)
- No offline message queue (messages require connection)

## Next Steps

1. Add notification icons (ic_notification, ic_launcher)
2. Wire up data export button to share intent
3. Implement WebSocketService for background connectivity
4. Add offline message persistence (Room database)
5. Add message retry logic for failed sends
6. Add pull-to-refresh for message history
7. Add image/file attachment support
8. Add voice message recording
