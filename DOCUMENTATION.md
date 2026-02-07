# 📚 Documentation Organization

Complete guide to Demi's documentation structure and where to find information.

---

## 🎯 Start Here

**New to Demi?** Follow this order:

1. **[README.md](README.md)** - Project overview
2. **[INSTALL.md](INSTALL.md)** - Get running in 5 minutes
3. **[Flutter App](flutter_app/README.md)** - Mobile app setup
4. **[docs/README.md](docs/README.md)** - Full documentation index

---

## 📋 Main Documentation Files

| File | Purpose |
|------|---------|
| **[README.md](README.md)** | Project overview, quick start |
| **[INSTALL.md](INSTALL.md)** | **Complete installation guide** |
| **[DOCUMENTATION.md](DOCUMENTATION.md)** | This file - documentation map |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | How to contribute |
| **[SECURITY.md](SECURITY.md)** | Security best practices |
| **[DOCKER_README.md](DOCKER_README.md)** | Docker quick reference |

---

## 🗂️ Directory Structure

```
Demi/
├── README.md                    # Main project README
├── INSTALL.md                   # ⭐ Complete installation guide
├── DOCUMENTATION.md             # This file
├── CONTRIBUTING.md              # How to contribute
├── SECURITY.md                  # Security best practices
├── DOCKER_README.md             # Docker quick reference
├── .env.example                 # Environment variables template
├── docker-compose.yml           # Docker configuration
│
├── docs/                        # Full documentation
│   ├── README.md                # Documentation index
│   ├── setup/                   # Setup and deployment
│   │   ├── QUICK_START.md       # → Links to INSTALL.md
│   │   ├── INSTALLATION.md      # → Links to INSTALL.md
│   │   ├── DOCKER_SETUP.md      # Detailed Docker guide
│   │   ├── SECURE_TOKEN_SETUP.md
│   │   └── DISCORD_SETUP.md
│   ├── guides/                  # User guides
│   │   ├── VRM_QUICK_START.md
│   │   ├── VOICE_SETUP.md
│   │   └── TROUBLESHOOTING.md
│   ├── architecture/            # Technical docs
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── AVATAR_IMPLEMENTATION.md
│   │   └── BRAIN_METRICS.md
│   ├── api/                     # API reference
│   │   ├── README.md
│   │   ├── MOBILE_API.md
│   │   └── DASHBOARD_API.md
│   └── deployment/              # Deployment guides
│       ├── installation.md      # → Links to INSTALL.md
│       └── maintenance.md
│
├── flutter_app/                 # Flutter mobile app
│   └── README.md                # Mobile app setup
│
├── src/                         # Source code
├── scripts/                     # Utility scripts
├── data/                        # Data files
└── tests/                       # Tests
```

---

## 🚀 Quick Navigation

### For First-Time Users
1. **[INSTALL.md](INSTALL.md)** - Installation guide
2. **[Flutter App](flutter_app/README.md)** - Mobile app
3. **[Docker Setup](docs/setup/DOCKER_SETUP.md)** - Docker details

### For Discord Integration
1. **[Discord Setup](docs/setup/DISCORD_SETUP.md)**
2. **[Secure Tokens](docs/setup/SECURE_TOKEN_SETUP.md)**

### For Development
1. **[Contributing](CONTRIBUTING.md)**
2. **[Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)**
3. **[API Docs](docs/api/)**

---

## 🔍 Finding Information

### By Task
- **Install Demi** → [INSTALL.md](INSTALL.md)
- **Set up mobile app** → [flutter_app/README.md](flutter_app/README.md)
- **Connect Discord** → [docs/setup/DISCORD_SETUP.md](docs/setup/DISCORD_SETUP.md)
- **Troubleshoot** → [docs/guides/TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)
- **Understand architecture** → [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md)

### By Keyword
Use GitHub's search or look in relevant directory.

---

## 📝 Contributing Documentation

When adding new documentation:

1. **Choose the right location:**
   - Setup info → `docs/setup/`
   - User guides → `docs/guides/`
   - Architecture → `docs/architecture/`
   - API reference → `docs/api/`

2. **Update indexes:**
   - Add to [docs/README.md](docs/README.md)
   - Update [DOCUMENTATION.md](DOCUMENTATION.md) if needed

3. **Link from main INSTALL.md if relevant to installation**

---

## 📞 Support

- **Questions?** Check [docs/guides/TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)
- **Lost?** Start at [INSTALL.md](INSTALL.md)
- **Contributing?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security?** Read [SECURITY.md](SECURITY.md)

---

**Last Updated:** February 7, 2026  
**Organization Version:** 1.1.0
