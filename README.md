# Demi 🧠📱✨
<img src="Demi.png" alt="Demi" width="200" height="300">

Local-first AI companion (Flutter + Python) with optional Discord/Telegram integrations.

## Repo layout
- `app/`    → Flutter client (Android first)
- `server/` → Python backend (FastAPI via uv)

## Requirements
### System
- Windows + WSL2 (Ubuntu)
- Android phone on same Wi-Fi network (for wireless debugging)
- Flutter SDK installed in WSL
- Android SDK / platform-tools available (`adb` on PATH)
- `uv` installed in WSL

## Android wireless debugging (WSL)
On your phone:
1. Developer options → **Wireless debugging** ON
2. Tap **Pair device with pairing code**

In WSL:
```bash
adb kill-server
adb start-server

# Pair with the pairing port shown on the pairing screen
adb pair <PHONE_IP>:<PAIRING_PORT>
# Enter the 6-digit code when prompted

# Connect using the connect port shown on the Wireless debugging main screen
adb connect <PHONE_IP>:<CONNECT_PORT>

adb devices
flutter devices
