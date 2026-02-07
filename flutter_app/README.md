# Demi Mobile App - Flutter

A cross-platform mobile app for chatting with Demi AI in real-time.

---

## 📋 Prerequisites

- **Flutter 3.0+** - [Install Flutter](https://flutter.dev/docs/get-started/install)
- **Dart 3.0+** (comes with Flutter)
- **Android Studio** or **VS Code** with Flutter extension
- **Android device** or emulator (API 21+)

---

## 🚀 Quick Start

### Step 1: Verify Flutter Setup

```bash
flutter doctor
```

Ensure Android toolchain shows no issues.

### Step 2: Install Dependencies

```bash
cd flutter_app
flutter pub get
```

### Step 3: Configure Server Connection

**⚠️ IMPORTANT:** You must use your computer's IP address, NOT `localhost`!

Edit `lib/providers/chat_provider.dart`:

```dart
// Line ~12: Replace with your computer's IP
final ApiService apiService = ApiService(
  baseUrl: 'http://192.168.1.100:8081'  // Your computer's IP
);
```

**Find your IP:**
```bash
# Linux/macOS
ip addr show | grep "inet "

# Windows
ipconfig

# Look for WiFi/Ethernet IP (usually 192.168.x.x)
```

### Step 4: Start Demi Backend

Make sure Demi is running on your computer:

```bash
# From project root
docker-compose up -d
```

Test the API:
```bash
curl http://localhost:8081/api/health
```

### Step 5: Run the App

**Option A: USB Debugging (Recommended)**

1. Enable USB debugging on your Android device:
   - Settings → About Phone → Tap "Build Number" 7 times
   - Settings → Developer Options → USB Debugging → ON

2. Connect device via USB

3. Run:
   ```bash
   flutter run
   ```

**Option B: Build APK**

```bash
flutter build apk --release
```

Install `build/app/outputs/flutter-apk/app-release.apk` on your device.

---

## 🔧 Configuration

### Server URL

Update in `lib/providers/chat_provider.dart`:

```dart
final ApiService apiService = ApiService(
  baseUrl: 'http://YOUR_IP:8081'  // Must match your computer's IP!
);
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Use your computer's IP, not localhost |
| "Network error" | Ensure phone and computer are on same WiFi |
| Build fails | `flutter clean && flutter pub get` |
| App crashes | Check `flutter logs` for errors |

---

## 📱 Features

✨ **Real-time Chat**
- Send and receive messages instantly via WebSocket
- Auto-reconnect on connection loss

💭 **Emotional State**
- View Demi's current emotions
- Color-coded emotion indicator

🎨 **Modern UI**
- Material Design 3
- Dark mode support
- Smooth animations

---

## 🏗️ Project Structure

```
flutter_app/
├── lib/
│   ├── main.dart                 # App entry point
│   ├── models/                   # Data models
│   │   ├── message.dart
│   │   └── emotion.dart
│   ├── screens/                  # UI screens
│   │   └── chat_screen.dart
│   ├── widgets/                  # Reusable widgets
│   │   ├── message_bubble.dart
│   │   ├── emotion_display.dart
│   │   └── connection_status.dart
│   ├── providers/                # State management
│   │   └── chat_provider.dart    # ← Update server IP here
│   └── services/                 # API services
│       ├── api_service.dart
│       └── websocket_service.dart
├── android/                      # Android configuration
├── pubspec.yaml                  # Dependencies
└── README.md                     # This file
```

---

## 🔌 API Integration

The app connects to Demi's mobile API:

- **REST API**: `http://your-ip:8081/api/`
- **WebSocket**: `ws://your-ip:8081/ws/chat/{user_id}`

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `POST /api/auth/login` | Create user session |
| `GET /api/health` | Check server status |
| `GET /api/user/emotions` | Get emotional state |
| `WS /ws/chat/{id}` | Real-time chat |

---

## 🐛 Troubleshooting

### Connection Issues

1. **Check server is running:**
   ```bash
   curl http://YOUR_IP:8081/api/health
   ```

2. **Verify same network:**
   - Phone and computer must be on same WiFi
   - Try pinging your phone from computer

3. **Check Windows Firewall:**
   - Allow port 8081 through firewall
   - Or temporarily disable for testing

### Build Issues

```bash
# Clean build
flutter clean
flutter pub get
flutter run

# Update dependencies
flutter pub upgrade

# Check for issues
flutter doctor -v
```

### Android-Specific

- Ensure `usesCleartextTraffic="true"` in `android/app/src/main/AndroidManifest.xml` (for development)
- Use HTTPS in production (requires SSL certificates)
- Minimum Android API level: 21

---

## 🧪 Testing

```bash
# Run tests
flutter test

# Run with coverage
flutter test --coverage

# View logs
flutter logs
```

---

## 📦 Building for Distribution

```bash
# Android APK
flutter build apk --release

# Android App Bundle (Google Play)
flutter build appbundle --release

# iOS (requires macOS + Xcode)
flutter build ios --release
```

---

## 📚 Related Documentation

- **[Main Installation Guide](../INSTALL.md)** - Setting up Demi backend
- **[Mobile API](../docs/api/MOBILE_API.md)** - API reference
- **[VRM Avatar](../docs/guides/VRM_QUICK_START.md)** - 3D avatar setup

---

## 🆘 Getting Help

1. Check [Troubleshooting Guide](../docs/guides/TROUBLESHOOTING.md)
2. Review backend logs: `docker-compose logs -f backend`
3. Check Flutter logs: `flutter logs`
4. Open an issue on GitHub

---

**License:** MIT - See LICENSE file for details
