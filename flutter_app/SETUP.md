# Demi Mobile App - Setup Guide

## Quick Start

### 1. Start the Backend Server

First, make sure the Demi backend is running:

```bash
cd /home/mystiatech/projects/Demi
source .venv/bin/activate
python main.py
```

The server will start on port 8081 by default.

### 2. Configure the Server URL

The Flutter app needs to know where to find the backend server. Edit the server URL in:

**File:** `lib/providers/chat_provider.dart`

```dart
// Line ~13 - Change this to your server's IP
static const String serverUrl = 'http://YOUR_SERVER_IP:8081';
```

#### Server URL Options:

| Scenario | URL | Notes |
|----------|-----|-------|
| Android Emulator | `http://10.0.2.2:8081` | Default - maps to host localhost |
| Physical Device (same WiFi) | `http://192.168.1.x:8081` | Your computer's LAN IP |
| USB Debugging | `http://localhost:8081` | With port forwarding |

**To find your computer's IP:**
```bash
# Linux/Mac
ip addr | grep inet

# Windows
ipconfig
```

### 3. Run the App

```bash
# Navigate to flutter app
cd flutter_app

# Get dependencies
flutter pub get

# Run on connected device
flutter run
```

## Troubleshooting

### Connection Error / 404

If you see "Login endpoint not ready (404)" or "Connection Error":

1. **Check server is running:**
   ```bash
   curl http://YOUR_SERVER_IP:8081/api/health
   ```
   Should return: `{"status": "healthy", ...}`

2. **Verify same network:**
   - Phone and computer must be on the **same WiFi network**
   - Disable mobile data on the phone to force WiFi usage

3. **Check firewall:**
   ```bash
   # Linux - allow port 8081
   sudo ufw allow 8081/tcp
   ```

4. **Verify IP address:**
   - The IP in `chat_provider.dart` must match your computer's current IP
   - IPs can change when reconnecting to WiFi

### "Connection refused" Error

This usually means the server isn't running or the IP is wrong:

1. Restart the backend: `python main.py`
2. Double-check the IP address in `chat_provider.dart`
3. Try accessing from phone's browser: `http://YOUR_IP:8081/api/health`

### Android 9+ HTTP Issues

The app includes `android:usesCleartextTraffic="true"` in `AndroidManifest.xml` to allow HTTP connections. If you're using Android 9+ (API 28+), this should work automatically.

## Architecture

```
┌─────────────────┐      HTTP/WebSocket      ┌─────────────────┐
│  Flutter App    │ ◄──────────────────────► │  Demi Backend   │
│  (Android/iOS)  │   Port 8081              │  (Python)       │
└─────────────────┘                          └─────────────────┘
       │                                            │
       │         Real-time chat                     │
       │         Emotion updates                    │
       │         Audio/Lip sync                     │
       │                                            │
```

## API Endpoints

The mobile app uses these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | Create/get user session |
| `/api/health` | GET | Check server status |
| `/api/user/emotions` | GET | Get Demi's emotional state |
| `/ws/chat/{user_id}` | WebSocket | Real-time chat |

## Environment Variables (Advanced)

You can also set the server URL via environment variable during build:

```bash
flutter run --dart-define=SERVER_URL=http://192.168.1.100:8081
```

## Need Help?

1. Check the server logs for errors
2. Verify network connectivity with `ping`
3. Test API directly with `curl`
4. Check firewall settings
