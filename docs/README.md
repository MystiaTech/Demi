# Demi Documentation

Complete guides for setting up, running, and extending the Demi AI companion system.

---

## 🚀 Quick Start

**New to Demi?** Start here:

1. **[Install Demi](../INSTALL.md)** - Get running in 5 minutes with Docker
2. **[Flutter App](../flutter_app/README.md)** - Set up the mobile app
3. **[Discord Setup](setup/DISCORD_SETUP.md)** - Connect Discord bot (optional)

---

## 📚 Documentation Index

### Getting Started
| Guide | Description |
|-------|-------------|
| **[Main Installation Guide](../INSTALL.md)** | Complete installation (Docker, Manual, Flutter) |
| **[Docker Setup](setup/DOCKER_SETUP.md)** | Detailed Docker configuration |
| **[Discord Bot Setup](setup/DISCORD_SETUP.md)** | Connect Discord integration |
| **[Secure Tokens](setup/SECURE_TOKEN_SETUP.md)** | Managing secrets securely |

### Mobile App
| Guide | Description |
|-------|-------------|
| **[Flutter App README](../flutter_app/README.md)** | Mobile app installation |
| **[Mobile API](api/MOBILE_API.md)** | API endpoints for mobile |
| **[VRM Avatar Setup](guides/VRM_QUICK_START.md)** | 3D avatar integration |

### Architecture & Design
| Guide | Description |
|-------|-------------|
| **[System Architecture](architecture/SYSTEM_ARCHITECTURE.md)** | Technical overview |
| **[Avatar Implementation](architecture/AVATAR_IMPLEMENTATION.md)** | 3D avatar system |
| **[Brain Metrics](architecture/BRAIN_METRICS.md)** | Cognitive state tracking |
| **[Emotion System](architecture/EMOTIONS.md)** | Emotional state management |

### API Reference
| Guide | Description |
|-------|-------------|
| **[API Overview](api/README.md)** | REST & WebSocket endpoints |
| **[Mobile API](api/MOBILE_API.md)** | Flutter app integration |
| **[Dashboard API](api/DASHBOARD_API.md)** | Monitoring endpoints |
| **[Authentication](api/authentication.md)** | Auth flows |

### Configuration
| Guide | Description |
|-------|-------------|
| **[Environment Variables](configuration/environment-variables.md)** | All config options |
| **[Security](configuration/security.md)** | Security settings |
| **[Tuning Guide](configuration/tuning-guide.md)** | Performance optimization |

### Troubleshooting & Reference
| Guide | Description |
|-------|-------------|
| **[Troubleshooting](guides/TROUBLESHOOTING.md)** | Common issues & fixes |
| **[Voice Setup](guides/VOICE_SETUP.md)** | TTS/STT configuration |
| **[Contributing](../CONTRIBUTING.md)** | Development guidelines |
| **[Security](../SECURITY.md)** | Security best practices |

---

## 📖 By Use Case

### I want to...

**...get Demi running locally**
1. Follow: [INSTALL.md](../INSTALL.md)
2. Optional: [Discord Setup](setup/DISCORD_SETUP.md)

**...use the mobile app**
1. Install: [Flutter App](../flutter_app/README.md)
2. Configure: Update server IP in `chat_provider.dart`
3. Optional: [VRM Avatar](guides/VRM_QUICK_START.md)

**...connect Discord**
1. Follow: [Discord Setup](setup/DISCORD_SETUP.md)
2. Secure: [Token Setup](setup/SECURE_TOKEN_SETUP.md)

**...understand how Demi works**
1. Read: [System Architecture](architecture/SYSTEM_ARCHITECTURE.md)
2. Explore: [Emotion System](architecture/EMOTIONS.md)

**...deploy to production**
1. Read: [Docker Setup](setup/DOCKER_SETUP.md)
2. Security: [Security Guide](../SECURITY.md)

---

## 🗂️ Directory Structure

```
docs/
├── README.md                    # This file
├── setup/                       # Installation & deployment
│   ├── DOCKER_SETUP.md
│   ├── DISCORD_SETUP.md
│   ├── SECURE_TOKEN_SETUP.md
│   └── REMOTE_ACCESS.md
├── guides/                      # User guides
│   ├── VRM_QUICK_START.md
│   ├── VOICE_SETUP.md
│   ├── 3D_CONTROLLER_NOTES.md
│   └── TROUBLESHOOTING.md
├── architecture/                # Technical docs
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── AVATAR_IMPLEMENTATION.md
│   ├── BRAIN_METRICS.md
│   └── EMOTIONS.md
├── api/                         # API documentation
│   ├── README.md
│   ├── MOBILE_API.md
│   ├── DASHBOARD_API.md
│   ├── authentication.md
│   └── examples.md
├── configuration/               # Configuration guides
│   ├── environment-variables.md
│   ├── security.md
│   └── tuning-guide.md
└── deployment/                  # Deployment guides
    ├── installation.md
    ├── first-run.md
    └── maintenance.md
```

---

## 🔗 External Resources

- [Discord Developer Portal](https://discord.com/developers/applications)
- [Flutter Documentation](https://flutter.dev/docs)
- [Ollama](https://ollama.ai)
- [Docker Documentation](https://docs.docker.com)

---

## ❓ Need Help?

1. **Quick answers:** Check [TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md)
2. **Setup issues:** See [INSTALL.md](../INSTALL.md)
3. **API questions:** Read [API Documentation](api/README.md)
4. **Security concerns:** Review [SECURITY.md](../SECURITY.md)

---

**Last Updated:** February 7, 2026  
**Version:** 1.0.0
