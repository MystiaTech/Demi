# Demi Documentation

Complete guides for setting up, running, and extending the Demi AI companion system.

## 📚 Quick Navigation

### Getting Started
- **[00_START_HERE.md](guides/00_START_HERE.md)** - Start here! Navigation guide for all documentation
- **[Quick Setup](setup/QUICK_START.md)** - 5-minute setup to get running
- **[Installation](setup/INSTALLATION.md)** - Detailed installation instructions

### Setup & Deployment
- **[Docker Setup](setup/DOCKER_SETUP.md)** - Complete Docker containerization guide
- **[Environment Variables](setup/SECURE_TOKEN_SETUP.md)** - Securely manage secrets
- **[Discord Bot Setup](setup/DISCORD_SETUP.md)** - Connect Discord bot

### Architecture & Design
- **[System Architecture](architecture/ARCHITECTURE.md)** - System overview and design
- **[Avatar Implementation](architecture/AVATAR_IMPLEMENTATION.md)** - 3D avatar system
- **[Brain Metrics](architecture/BRAIN_METRICS.md)** - Cognitive state tracking
- **[Emotion System](architecture/EMOTIONS.md)** - Emotional state management

### Mobile App
- **[Flutter Setup](guides/FLUTTER_SETUP.md)** - Configure Flutter app
- **[VRM Avatar Quick Start](guides/VRM_QUICK_START.md)** - Avatar integration
- **[3D Controller Notes](guides/3D_CONTROLLER_NOTES.md)** - Animation details

### API & Integration
- **[API Documentation](api/README.md)** - REST & WebSocket endpoints
- **[Mobile API](api/MOBILE_API.md)** - Flutter app integration
- **[Dashboard API](api/DASHBOARD_API.md)** - Monitoring endpoints

### Reference
- **[Troubleshooting](guides/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Security](SECURITY.md)** - Security best practices
- **[Contributing](../CONTRIBUTING.md)** - How to contribute

---

## 📖 By Use Case

### I want to...

**...get Demi running locally**
1. Read: [00_START_HERE.md](guides/00_START_HERE.md)
2. Follow: [QUICK_START.md](setup/QUICK_START.md)
3. Reference: [DOCKER_SETUP.md](setup/DOCKER_SETUP.md)

**...add the 3D avatar**
1. Read: [VRM_QUICK_START.md](guides/VRM_QUICK_START.md)
2. Reference: [3D_CONTROLLER_NOTES.md](guides/3D_CONTROLLER_NOTES.md)
3. Deploy: [AVATAR_IMPLEMENTATION.md](architecture/AVATAR_IMPLEMENTATION.md)

**...connect Discord**
1. Follow: [DISCORD_SETUP.md](setup/DISCORD_SETUP.md)
2. Secure: [SECURE_TOKEN_SETUP.md](setup/SECURE_TOKEN_SETUP.md)

**...integrate my own bot**
1. Learn: [SYSTEM_ARCHITECTURE.md](architecture/ARCHITECTURE.md)
2. Reference: [API_DOCUMENTATION.md](api/README.md)
3. Implement: Add to `src/` directory

**...deploy to production**
1. Read: [DOCKER_SETUP.md](setup/DOCKER_SETUP.md)
2. Security: [SECURITY.md](../SECURITY.md)
3. Scale: [DOCKER_SETUP.md](setup/DOCKER_SETUP.md#scaling)

**...understand the emotional system**
1. Overview: [EMOTIONS.md](architecture/EMOTIONS.md)
2. Visualization: [BRAIN_METRICS.md](architecture/BRAIN_METRICS.md)

---

## 🗂️ Directory Structure

```
docs/
├── README.md                    # This file
├── SECURITY.md                  # Security best practices
├── setup/                       # Setup and deployment
│   ├── QUICK_START.md
│   ├── INSTALLATION.md
│   ├── DOCKER_SETUP.md
│   ├── SECURE_TOKEN_SETUP.md
│   └── DISCORD_SETUP.md
├── guides/                      # User guides and tutorials
│   ├── 00_START_HERE.md
│   ├── FLUTTER_SETUP.md
│   ├── VRM_QUICK_START.md
│   ├── 3D_CONTROLLER_NOTES.md
│   ├── TROUBLESHOOTING.md
│   └── FAQ.md
├── architecture/                # Technical architecture
│   ├── ARCHITECTURE.md
│   ├── AVATAR_IMPLEMENTATION.md
│   ├── BRAIN_METRICS.md
│   ├── EMOTIONS.md
│   └── COMPONENTS.md
└── api/                         # API reference
    ├── README.md
    ├── MOBILE_API.md
    └── DASHBOARD_API.md
```

---

## 🚀 Quick Start

**For the impatient:**

```bash
# 1. Clone the repo
git clone <repo-url>
cd Demi

# 2. Copy environment template
cp .env.example .env

# 3. Add your tokens to .env
nano .env

# 4. Start Docker
docker-compose up -d

# 5. Open dashboard
# http://192.168.1.245:8080

# 6. Run Flutter app
cd flutter_app && flutter run
```

**For detailed instructions:** See [QUICK_START.md](setup/QUICK_START.md)

---

## 📋 Features

- ✅ 3D Vroid avatar with lip sync and emotions
- ✅ Real-time emotional state tracking
- ✅ Multi-platform integration (Discord, Telegram, Mobile)
- ✅ Local LLM support (Ollama, LMStudio)
- ✅ Dashboard with cognitive metrics
- ✅ Voice I/O (TTS/STT)
- ✅ Docker containerization
- ✅ Production-ready deployment

---

## 🔗 External Resources

- [Discord Developer Portal](https://discord.com/developers/applications)
- [Flutter Documentation](https://flutter.dev/docs)
- [Ollama](https://ollama.ai)
- [VRM Specification](https://vrm.dev)

---

## ❓ Need Help?

1. **Quick answers:** Check [TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md)
2. **Setup issues:** See [INSTALLATION.md](setup/INSTALLATION.md)
3. **API questions:** Read [API Documentation](api/README.md)
4. **Security concerns:** Review [SECURITY.md](../SECURITY.md)

---

**Last Updated:** February 4, 2026  
**Version:** 1.0.0
