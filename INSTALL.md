# 🚀 Demi Installation Guide

Get Demi running in minutes with Docker, or set up a custom installation.

## 📋 Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 12+ GB |
| CPU | 4 cores | 8+ cores |
| Disk | 10 GB | 20+ GB |
| Docker | 20.10+ | Latest |

**Software:** Docker Desktop (or Docker Engine on Linux)

---

## 🐳 Method 1: Docker (Recommended - 5 Minutes)\n
The fastest way to get Demi running. No Python dependencies to install!

### Step 1: Clone the Repository

```bash
git clone https://github.com/mystiatech/Demi.git
cd Demi
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your settings (optional for first run)
nano .env  # or use VS Code: code .env
```

**Optional:** Add your Discord bot token for Discord integration (see [Discord Setup](docs/setup/DISCORD_SETUP.md)).

### Step 3: Start Demi

```bash
docker-compose up -d
```

This starts:
- **Demi Backend** on port 8080 (API) and 8081 (Mobile API)
- **PostgreSQL Database** on port 5433
- **Ollama LLM** on port 11434

### Step 4: Download an LLM Model

**Recommended for Demi:** `l3-8b-stheno-v3.2-iq-imatrix`
- Best personality match (creative, roleplay-focused, uncensored)
- 8B parameters, ~5GB download
- IQ-imatrix quantized for quality

```bash
# Wait 30 seconds for Ollama to start, then:
docker-compose exec ollama ollama pull l3-8b-stheno-v3.2-iq-imatrix
```

**Alternative models:**
| Model | Size | Best For |
|-------|------|----------|
| `l3-8b-stheno-v3.2-iq-imatrix` | ~5GB | **Recommended** - Best personality |
| `llama3.2:1b` | ~1.3GB | Lightweight, faster responses |
| `llama3.2:3b` | ~2GB | Balanced quality/speed |
| `mistral` | ~4GB | General purpose |

### Step 5: Access Demi

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:8080 |
| Mobile API | http://localhost:8081 |
| Ollama API | http://localhost:11434 |

### Step 6: View Logs

```bash
# All services
docker-compose logs -f

# Just Demi backend
docker-compose logs -f backend

# Just Ollama
docker-compose logs -f ollama
```

### Stop Demi

```bash
docker-compose down
```

To remove all data (fresh start):
```bash
docker-compose down -v
```

---

## 🛠️ Method 2: Manual Installation (Advanced)

For developers who want full control or don't want to use Docker.

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ (or SQLite for simple setup)
- Ollama (for LLM)
- FFmpeg & espeak (for voice features)

### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev ffmpeg espeak git
```

**macOS:**
```bash
brew install python@3.11 ffmpeg espeak git
```

**Windows (WSL2):**
```bash
# In WSL2 terminal
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev ffmpeg espeak git
```

### Step 2: Install Ollama

```bash
# Linux/WSL2
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Start Ollama
ollama serve
```

In another terminal, pull a model:
```bash
ollama pull llama3.2:1b
```

### Step 3: Clone and Setup

```bash
git clone https://github.com/mystiatech/Demi.git
cd Demi

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
cp .env.example .env

# Generate secure JWT secrets
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_REFRESH_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Add these to your .env file
nano .env
```

### Step 5: Run Demi

```bash
python main.py
```

The API will be available at:
- Dashboard: http://localhost:8080
- Mobile API: http://localhost:8081

---

## 📱 Method 3: Flutter Mobile App

The mobile app lets you chat with Demi from your Android device.

### Prerequisites

- Flutter 3.0+ ([Install Flutter](https://flutter.dev/docs/get-started/install))
- Android Studio or VS Code with Flutter extension
- Android device or emulator (API 21+)

### Step 1: Setup Flutter

```bash
# Verify Flutter installation
flutter doctor

# Should show no issues for Android toolchain
```

### Step 2: Configure the App

```bash
cd flutter_app

# Install dependencies
flutter pub get
```

### Step 3: Set Your Server IP

Edit `lib/providers/chat_provider.dart`:

```dart
// Find this line and replace with your computer's IP
final ApiService apiService = ApiService(
  baseUrl: 'http://YOUR_COMPUTER_IP:8081'  // Not localhost!
);
```

**Find your IP:**
- Linux/macOS: `ip addr show` or `ifconfig`
- Windows: `ipconfig`
- Look for your WiFi/Ethernet IP (usually 192.168.x.x)

### Step 4: Run the App

```bash
# Connect your Android device via USB
# Enable USB debugging on your device

# Run the app
flutter run
```

Or build an APK:
```bash
flutter build apk --release
```

The APK will be at `build/app/outputs/flutter-apk/app-release.apk`

### Troubleshooting Flutter

| Issue | Solution |
|-------|----------|
| "Connection refused" | Use your computer's IP, not localhost |
| "Network error" | Ensure phone and computer are on same WiFi |
| Build fails | Run `flutter clean && flutter pub get` |

---

## 🎮 First Time Setup

### 1. Test the API

```bash
# Health check
curl http://localhost:8080/api/health

# Should return: {"status":"healthy","version":"1.0.0"}
```

### 2. Set Up Discord (Optional)

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application → Bot → Add Bot
3. Copy the token to your `.env` file
4. Enable "Message Content Intent" in Bot settings
5. Invite bot to your server with OAuth2 URL Generator

See [Discord Setup Guide](docs/setup/DISCORD_SETUP.md) for detailed steps.

### 3. Try the Mobile App

1. Install the Flutter app on your Android device
2. Make sure your phone and computer are on the same WiFi
3. Open the app and start chatting!

---

## 🔧 Common Commands

### Docker Commands

```bash
# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build backend

# Access database
docker-compose exec postgres psql -U demi -d demi

# Reset everything (WARNING: deletes all data)
docker-compose down -v
```

### Ollama Commands

```bash
# List models
curl http://localhost:11434/api/tags

# Pull recommended model (best for Demi)
docker-compose exec ollama ollama pull l3-8b-stheno-v3.2-iq-imatrix

# Pull alternative models
docker-compose exec ollama ollama pull llama3.2:3b
docker-compose exec ollama ollama pull mistral

# Run a model
docker-compose exec ollama ollama run l3-8b-stheno-v3.2-iq-imatrix "Hello!"
```

---

## 🐛 Troubleshooting

### "Port already in use"

```bash
# Find what's using port 8080
lsof -i :8080
# Kill it
kill -9 <PID>
```

Or change ports in `docker-compose.yml`:
```yaml
ports:
  - "8082:8080"  # Use 8082 instead of 8080
```

### "Database connection failed"

```bash
# Check postgres is running
docker-compose ps

# Check logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
```

### "Ollama connection refused"

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
docker-compose restart ollama

# Wait 30 seconds, then pull recommended model
docker-compose exec ollama ollama pull l3-8b-stheno-v3.2-iq-imatrix
```

### Flutter "Connection refused"

- Make sure you're using your computer's IP, not `localhost`
- Ensure both devices are on the same network
- Check Windows Firewall (allow port 8081)

---

## 📚 Next Steps

- **[Full Documentation](docs/README.md)** - Explore all features
- **[Discord Setup](docs/setup/DISCORD_SETUP.md)** - Connect Discord bot
- **[Flutter Setup](flutter_app/README.md)** - Mobile app details
- **[Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)** - How Demi works
- **[Contributing](CONTRIBUTING.md)** - Help improve Demi

---

## 💡 Quick Reference

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop everything
docker-compose down

# Update after git pull
docker-compose up -d --build
```

**You're all set!** Demi is ready to chat. 💕✨
