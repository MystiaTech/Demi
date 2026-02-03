# Demi Installation Guide

Complete step-by-step installation instructions for Demi on all supported platforms.

## Table of Contents

- [Quick Install](#quick-install)
- [Manual Installation](#manual-installation)
- [Docker Installation](#docker-installation-optional)
- [Platform-Specific Notes](#platform-specific-notes)
- [Verification Steps](#verification-steps)

---

## Quick Install

The fastest way to get Demi running on Linux or macOS.

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/demi/main/docs/deployment/quick-install.sh | bash
```

Or with `wget`:

```bash
wget -qO- https://raw.githubusercontent.com/yourusername/demi/main/docs/deployment/quick-install.sh | bash
```

### What the Script Does

The install script will:

1. **Check System Requirements**
   - Python version (3.10+)
   - Available RAM (8GB+ recommended)
   - Disk space (10GB+ free)

2. **Install System Dependencies**
   - Python 3.10+ and pip
   - FFmpeg (for voice features)
   - espeak (for TTS)
   - Git

3. **Install Ollama** (if not present)
   - Downloads and installs Ollama
   - Pulls the default model (llama3.2:1b)

4. **Set Up Demi**
   - Clones the repository
   - Creates Python virtual environment
   - Installs Python dependencies
   - Generates secure JWT secrets
   - Creates initial `.env` configuration

5. **Interactive Configuration**
   - Guides you through Discord bot setup
   - Helps configure channel IDs
   - Tests the installation

### Script Options

```bash
# Install to custom directory
curl -fsSL ... | bash -s -- --install-dir /opt/demi

# Skip Discord setup (configure later)
curl -fsSL ... | bash -s -- --skip-discord

# Use specific model
curl -fsSL ... | bash -s -- --model llama3.2:3b

# Dry run (check only, don't install)
curl -fsSL ... | bash -s -- --dry-run
```

---

## Manual Installation

For users who prefer full control over the installation process.

### Prerequisites

Before starting, ensure you have:

- Python 3.10 or higher
- Git
- curl or wget
- At least 8GB RAM (12GB+ recommended)
- 10GB free disk space

### Step 1: Install Python 3.10+

#### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Verify installation
python3 --version  # Should show 3.10 or higher
```

#### macOS

```bash
# Using Homebrew
brew install python@3.11

# Verify installation
python3 --version
```

#### Windows (WSL2)

```bash
# In WSL2 terminal
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Verify installation
python3 --version
```

### Step 2: Install System Dependencies

#### Ubuntu/Debian

```bash
# Required for voice features and audio processing
sudo apt install -y ffmpeg espeak git

# Optional: For better audio quality
sudo apt install -y libespeak1 libespeak-dev
```

#### macOS

```bash
# Using Homebrew
brew install ffmpeg espeak git opus
```

#### Windows (WSL2)

```bash
# Same as Ubuntu
sudo apt install -y ffmpeg espeak git
```

### Step 3: Install Ollama

Ollama provides local LLM inference for Demi.

#### Linux

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

#### macOS

```bash
# Using Homebrew
brew install ollama

# Or download from https://ollama.ai

# Verify installation
ollama --version
```

#### Start Ollama Service

```bash
# Start Ollama (keep this running in a terminal)
ollama serve

# In another terminal, pull the default model
ollama pull llama3.2:1b

# Or pull a larger model if you have more RAM
ollama pull llama3.2:3b
```

### Step 4: Clone Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/demi.git

# Enter the directory
cd demi

# Verify contents
ls -la
```

### Step 5: Set Up Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate on Linux/macOS/WSL
source venv/bin/activate

# Your prompt should now show (venv)
```

### Step 6: Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

This will install:
- FastAPI and Uvicorn (web API)
- discord.py (Discord bot)
- SQLAlchemy (database)
- Voice processing libraries
- Testing and development tools

### Step 7: Configure Environment Variables

```bash
# Copy the example configuration
cp .env.example .env

# Edit the configuration
nano .env  # or use vim, VS Code, etc.
```

#### Required Variables

**Generate JWT Secrets:**
```bash
# Generate two different secure keys
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_REFRESH_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

Add these to your `.env` file.

**Discord Configuration (Optional but recommended):**

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and click "Add Bot"
4. Copy the token and add to `.env`:
   ```
   DISCORD_BOT_TOKEN=your-token-here
   ```
5. Enable "Message Content Intent" in the Bot section

**Database Path:**
```
DEMI_DB_PATH=~/.demi/emotions.db
DATABASE_URL=sqlite:////home/youruser/.demi/demi.db
```

**CORS Origins:**
```
# For development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# For production (update with your domain)
ALLOWED_ORIGINS=https://yourdomain.com
```

### Step 8: Create Data Directory

```bash
# Create the data directory
mkdir -p ~/.demi

# Set appropriate permissions
chmod 755 ~/.demi
```

### Step 9: Verify Installation

```bash
# Test configuration (dry run)
python main.py --dry-run

# Expected output:
# ✓ Configuration valid
```

---

## Docker Installation (Optional)

For advanced users and server deployments.

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  demi:
    build: .
    container_name: demi
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    env_file:
      - .env
    environment:
      - ANDROID_API_HOST=0.0.0.0
    networks:
      - demi-network

  ollama:
    image: ollama/ollama:latest
    container_name: demi-ollama
    restart: unless-stopped
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - demi-network

volumes:
  ollama-data:

networks:
  demi-network:
    driver: bridge
```

Start the services:

```bash
# Pull the default model first
docker-compose exec ollama ollama pull llama3.2:1b

# Start everything
docker-compose up -d

# View logs
docker-compose logs -f demi
```

### Building from Dockerfile

```bash
# Build the image
docker build -t demi:latest .

# Run the container
docker run -d \
  --name demi \
  -p 8000:8000 \
  -v ~/.demi:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  demi:latest
```

---

## Platform-Specific Notes

### Linux (Ubuntu/Debian)

**Systemd Service (Optional):**

Create `/etc/systemd/system/demi.service`:

```ini
[Unit]
Description=Demi AI Companion
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/demi
Environment=PATH=/home/yourusername/demi/venv/bin
ExecStart=/home/yourusername/demi/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable demi
sudo systemctl start demi
sudo systemctl status demi
```

### macOS

**Using launchd (Optional):**

Create `~/Library/LaunchAgents/com.demi.app.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.demi.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/yourusername/demi/venv/bin/python</string>
        <string>/Users/yourusername/demi/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/yourusername/demi</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.demi.app.plist
launchctl start com.demi.app
```

### Windows (WSL2)

**Important Notes:**

1. **Enable WSL2:**
   ```powershell
   # In PowerShell as Administrator
   wsl --install
   ```

2. **WSL2 has full Linux compatibility** - follow the Linux/Ubuntu instructions

3. **Port forwarding for Android app:**
   ```bash
   # In WSL2, find your IP
   ip addr show eth0 | grep 'inet '
   
   # Use this IP in the Android app
   ```

4. **Firewall considerations:**
   - Windows Firewall may block WSL2 connections
   - Allow port 8000 through Windows Firewall

---

## Verification Steps

After installation, verify everything is working:

### 1. Health Check

```bash
# Start Demi
python main.py

# In another terminal, check status
curl http://localhost:8000/api/v1/status
```

Expected response:
```json
{
  "status": "operational",
  "version": "1.0.0",
  "platforms": {
    "discord": "connected",
    "android_api": "running"
  }
}
```

### 2. Test Discord Connection

If you configured Discord:

1. Invite the bot to your server using the OAuth2 URL
2. Mention the bot: `@Demi hello`
3. Check that she responds

### 3. Test API

```bash
# Test login endpoint (if auth is configured)
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "device_name": "Test Device"
  }'

# Test emotions endpoint
curl http://localhost:8000/api/v1/emotions/current
```

### 4. Check Logs

```bash
# View recent logs
tail -f logs/demi.log

# Check for errors
grep -i error logs/demi.log
```

---

## Troubleshooting Installation

### Common Issues

**"Permission denied" when running scripts:**
```bash
chmod +x docs/deployment/quick-install.sh
./docs/deployment/quick-install.sh
```

**"Module not found" errors:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Ollama connection issues:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

**Port 8000 already in use:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or change port in .env
ANDROID_API_PORT=8001
```

### Getting Help

If you encounter issues not covered here:

1. Check [Maintenance & Troubleshooting](./maintenance.md)
2. Review the logs: `tail -f logs/demi.log`
3. Run with debug logging: `python main.py --log-level DEBUG`
4. Open an issue on GitHub with:
   - Your operating system and version
   - Python version (`python3 --version`)
   - Error messages from logs
   - Steps to reproduce

---

## Next Steps

Once installation is complete, proceed to the [First Run Guide](./first-run.md) to:
- Start Demi for the first time
- Configure Discord integration
- Set up the Android app
- Have your first conversation
