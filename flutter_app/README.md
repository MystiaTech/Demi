# Demi Mobile App - Flutter

A cross-platform mobile app for communicating with Demi AI in real-time.

## Features

✨ **Real-time Chat**
- Send and receive messages instantly via WebSocket
- Message history within the session
- Auto-reconnect on connection loss

💭 **Emotional State Visualization**
- View Demi's current emotional state
- Color-coded emotion indicator
- Emotion intensity meter

🔗 **Smart Connection Management**
- Automatic connection status display
- Reconnection with exponential backoff
- Offline message queueing (coming soon)

🎨 **Modern UI**
- Material Design 3
- Dark mode support
- Responsive layout
- Smooth animations

## Prerequisites

- Flutter 3.0+
- Dart 3.0+
- Android API level 21+
- iOS 11.0+ (for future iOS support)

## Installation

### 1. Setup Flutter (if not already installed)

```bash
# Download Flutter from https://flutter.dev/docs/get-started/install
# Or use your package manager:
brew install flutter  # macOS
choco install flutter  # Windows
```

### 2. Clone and Setup

```bash
cd flutter_app
flutter pub get
```

### 3. Configure Server URL

Update the server URL in `lib/providers/chat_provider.dart`:

```dart
final ApiService apiService = ApiService(
  baseUrl: 'http://YOUR_SERVER_IP:8081'
);
```

## Running

### Android

```bash
# Connect an Android device via USB or use an emulator
flutter run

# Or build APK for distribution
flutter build apk --split-per-abi
```

### iOS (Future)

```bash
flutter run -d ios
```

### Web (Future)

```bash
flutter run -d chrome
```

## Project Structure

```
flutter_app/
├── lib/
│   ├── main.dart              # App entry point
│   ├── models/                # Data models
│   │   ├── message.dart
│   │   └── emotion.dart
│   ├── screens/               # UI screens
│   │   └── chat_screen.dart
│   ├── widgets/               # Reusable widgets
│   │   ├── message_bubble.dart
│   │   ├── emotion_display.dart
│   │   └── connection_status.dart
│   ├── providers/             # State management
│   │   └── chat_provider.dart
│   └── services/              # API & WebSocket services
│       ├── api_service.dart
│       └── websocket_service.dart
├── android/                   # Android configuration
├── ios/                       # iOS configuration (future)
├── web/                       # Web configuration (future)
└── pubspec.yaml              # Dependencies
```

## API Integration

The app connects to the backend mobile API at:

- **REST API**: `http://server:8081/api/`
- **WebSocket**: `ws://server:8081/ws/chat/{user_id}`

### Endpoints

- `POST /api/auth/login` - Create/get user session
- `GET /api/health` - Server health check
- `GET /api/user/emotions` - Get emotional state
- `WS /ws/chat/{user_id}` - Real-time chat

## Message Format

### Sending
```json
{
  "message": "Hello, Demi!"
}
```

### Receiving
```json
{
  "type": "message",
  "content": "Hello! How are you?",
  "from": "demi",
  "timestamp": "2024-02-03T12:34:56.789Z"
}
```

## Configuration

### Chat Provider Settings

In `lib/providers/chat_provider.dart`:

- `baseUrl` - Backend server URL
- Message retry logic
- Reconnection parameters
- Emotion update frequency

## Development

### Adding New Features

1. **New API Endpoint**: Add to `ApiService`
2. **New Message Type**: Handle in `_handleWebSocketMessage`
3. **New Emotion State**: Update `EmotionState` model
4. **New UI Widget**: Create in `widgets/` directory
5. **State Management**: Update `ChatProvider`

### Testing

```bash
# Run tests
flutter test

# Run with coverage
flutter test --coverage
```

### Building for Distribution

```bash
# Android APK
flutter build apk --release

# Android App Bundle (Google Play)
flutter build appbundle --release

# iOS
flutter build ios --release
```

## Troubleshooting

### Connection Issues

1. Check server is running: `http://localhost:8081/api/health`
2. Verify network connectivity: Settings → WiFi
3. Check server IP in `chat_provider.dart`
4. Look at console logs: `flutter logs`

### Build Errors

```bash
# Clean and rebuild
flutter clean
flutter pub get
flutter run
```

### Android-Specific

- Ensure `usesCleartextTraffic="true"` in `AndroidManifest.xml` for development
- Use HTTPS in production (requires proper certificates)
- Check Android API level >= 21

## Future Enhancements

- 📱 iOS support
- 🌐 Web support
- 💾 Message persistence
- 🔐 Authentication improvements
- 🎤 Voice messages
- 📸 Image sharing
- 👥 Multi-user chat
- 🔔 Push notifications
- ⚡ Offline message queue
- 🌙 Enhanced dark mode

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the main Demi documentation
2. Review the backend API logs
3. Check Flutter console logs: `flutter logs`
4. Open an issue on the project repository
