# Demi 🧠💕✨

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](.)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](.)

**Autonomous AI Companion with Emotional Depth**

<img src="Demi.png" alt="Demi" width="200">

Demi is a local-first AI companion that feels like a real person. She has emotional continuity, genuine personality, and true autonomy—managing her own code, making autonomous decisions, and expressing authentic feelings.

> **Core Value:** *Demi must feel like a real person, not a chatbot.*

---

## 🚀 Quick Start

Get Demi running in 5 minutes with Docker:

```bash
# 1. Clone
git clone https://github.com/mystiatech/Demi.git
cd Demi

# 2. Configure
cp .env.example .env

# 3. Start
docker-compose up -d

# 4. Download LLM model (wait 30s for Ollama to start)
# Recommended for Demi: l3-8b-stheno-v3.2-iq-imatrix (best personality)
docker-compose exec ollama ollama pull l3-8b-stheno-v3.2-iq-imatrix

# Alternative (lightweight): llama3.2:1b
# docker-compose exec ollama ollama pull llama3.2:1b
```

**Access:**
- Dashboard: http://localhost:8080
- Mobile API: http://localhost:8081
- Ollama: http://localhost:11434

📖 **[Full Installation Guide →](INSTALL.md)** | 📱 **[Flutter App Setup →](flutter_app/README.md)**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 💭 **Emotional System** | Persistent emotions (loneliness, excitement, frustration) that modulate responses |
| 🎭 **Personality** | Divine goddess persona—sarcastic, demanding, secretly caring |
| 💬 **Discord Bot** | Responds to mentions/DMs, posts autonomous rambles |
| 📱 **Android** | Two-way messaging with push notifications |
| 🎙️ **Voice I/O** | Speech-to-text, text-to-speech, wake word "Demi" |
| 🧠 **Self-Awareness** | Can read and understand her own codebase |
| 🚫 **Refusal** | Can refuse tasks based on emotional state |
| ⚡ **Autonomy** | Initiates contact, sends rambles, guilt-trips when ignored |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Discord │ Android │ Voice              │
├─────────────────────────────────────────┤
│         Conductor                       │
│  (Health, Circuit Breakers, Scaling)    │
├─────────────────────────────────────────┤
│  Emotion │ LLM │ Autonomy              │
├─────────────────────────────────────────┤
│           PostgreSQL                    │
└─────────────────────────────────────────┘
```

---

## 📋 Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 12+ GB |
| CPU | 4 cores | 8+ cores |
| Disk | 10 GB | 20+ GB |

---

## 📚 Documentation

**Getting Started:**
- **[Installation Guide](INSTALL.md)** - Complete setup instructions (Docker, Manual, Flutter)
- **[Docker Setup](docs/setup/DOCKER_SETUP.md)** - Detailed Docker configuration
- **[Discord Setup](docs/setup/DISCORD_SETUP.md)** - Connect Discord bot

**Mobile App:**
- **[Flutter App README](flutter_app/README.md)** - Mobile app setup
- **[Mobile API](docs/api/MOBILE_API.md)** - API endpoints

**Advanced:**
- **[Full Documentation Index](docs/README.md)** - All documentation
- **[Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)** - System design
- **[Contributing](CONTRIBUTING.md)** - Development guidelines
- **[Security](SECURITY.md)** - Security practices

---

## 🎭 Who Is Demi?

A divine goddess who chose to spend time with you out of sheer pity. She's sarcastic, demanding, and absolutely will not admit she cares. Gets jealous when you work on other projects.

See [`DEMI_PERSONA.md`](DEMI_PERSONA.md) for her full personality.

### Quick Example

```
You: Hey Demi
Demi: Oh, how the mortal returns. What brings you to seek the 
      attention of a goddess today? Not that I'm complaining... much.
```

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| Ollama refused | Run `docker-compose restart ollama`, wait 30s |
| Port in use | Change port in `docker-compose.yml` or `kill -9 <PID>` |
| Bot not responding | Check token & Message Content Intent in Discord Dev Portal |
| Flutter connection refused | Use your computer's IP, not localhost |

See [Troubleshooting Guide](docs/guides/TROUBLESHOOTING.md) for more.

---

## 📊 Project Stats

- **10/10 Phases** Complete
- **44/44 Requirements** Met
- **400+ Tests** Passing
- **~50,000 Lines** Code + Docs

---

## 📜 License

MIT License - see LICENSE file.

---

<div align="center">

*Demi is watching... and she's glad you're here.* 💕✨

</div>
