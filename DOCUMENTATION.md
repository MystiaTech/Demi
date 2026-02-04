# 📚 Documentation Organization

Complete guide to Demi's documentation structure and where to find information.

## 📋 Main Documentation

**→ [Go to Full Documentation Index](docs/README.md)**

This is your main entry point. It contains:
- Navigation guides by use case
- Quick start instructions
- Links to all detailed guides
- Directory structure overview

## 🗂️ Directory Structure

```
Demi/
├── README.md                    # Main project README
├── DOCUMENTATION.md             # This file
├── CONTRIBUTING.md              # How to contribute
├── SECURITY.md                  # Security best practices
├── DOCKER_README.md             # Quick Docker reference
├── LLM_FALLBACK_GUIDE.md        # LLM implementation options
├── .env.example                 # Environment variables template
├── docker-compose.yml           # Docker configuration
├── .gitignore                   # Git ignore rules
│
├── docs/                        # Full documentation
│   ├── README.md                # Documentation index (START HERE!)
│   ├── setup/                   # Setup and deployment
│   │   ├── QUICK_START.md
│   │   ├── INSTALLATION.md
│   │   ├── DOCKER_SETUP.md
│   │   ├── SECURE_TOKEN_SETUP.md
│   │   └── DISCORD_SETUP.md
│   ├── guides/                  # User guides and tutorials
│   │   ├── 00_START_HERE.md
│   │   ├── VRM_QUICK_START.md
│   │   ├── 3D_CONTROLLER_NOTES.md
│   │   └── TROUBLESHOOTING.md
│   ├── architecture/            # Technical architecture
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── AVATAR_IMPLEMENTATION.md
│   │   └── BRAIN_METRICS.md
│   ├── api/                     # API reference
│   │   ├── README.md
│   │   ├── MOBILE_API.md
│   │   └── DASHBOARD_API.md
│   ├── user-guide/              # User guides
│   ├── configuration/           # Configuration guides
│   └── ...
│
├── .archive/                    # Archived interim documentation
│   ├── METRICS_GUIDE.md
│   ├── METRICS_IMPLEMENTATION_SUMMARY.md
│   ├── PROJECT_COMPLETE.md
│   └── ...
│
├── src/                         # Source code
├── flutter_app/                 # Flutter mobile app
├── scripts/                     # Utility scripts
├── data/                        # Data files
└── tests/                       # Tests
```

## 🎯 Quick Navigation

### For First-Time Users
1. **Start here:** [docs/README.md](docs/README.md)
2. **Quick setup:** [docs/setup/QUICK_START.md](docs/setup/QUICK_START.md)
3. **Docker guide:** [DOCKER_README.md](DOCKER_README.md)

### For Avatar Setup
1. **VRM integration:** [docs/guides/VRM_QUICK_START.md](docs/guides/VRM_QUICK_START.md)
2. **Animation details:** [docs/guides/3D_CONTROLLER_NOTES.md](docs/guides/3D_CONTROLLER_NOTES.md)
3. **Architecture:** [docs/architecture/AVATAR_IMPLEMENTATION.md](docs/architecture/AVATAR_IMPLEMENTATION.md)

### For Bot Integration
1. **Discord setup:** [docs/setup/DISCORD_SETUP.md](docs/setup/DISCORD_SETUP.md)
2. **Secure tokens:** [docs/setup/SECURE_TOKEN_SETUP.md](docs/setup/SECURE_TOKEN_SETUP.md)
3. **API docs:** [docs/api/README.md](docs/api/README.md)

### For Development
1. **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
2. **Architecture:** [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md)
3. **Security:** [SECURITY.md](SECURITY.md)

## 📝 Content Organization

### Setup & Deployment (`docs/setup/`)
- Initial installation steps
- Docker containerization
- Environment configuration
- Security and token management
- Platform-specific setup (Discord, Telegram, etc.)

### User Guides (`docs/guides/`)
- Getting started tutorials
- Feature walkthroughs
- Integration guides
- Troubleshooting and FAQs

### Architecture & Design (`docs/architecture/`)
- System architecture overview
- Component descriptions
- Avatar implementation details
- Emotion system design
- Brain metrics visualization

### API Reference (`docs/api/`)
- REST endpoint documentation
- WebSocket communication
- Mobile app API
- Dashboard API
- Example requests/responses

### Configuration (`docs/configuration/`)
- Environment variables
- Configuration files
- Performance tuning
- Voice system upgrades

### User Guides (`docs/user-guide/`)
- Personality customization
- Discord integration
- Android/mobile usage
- Voice commands
- Commands and features

## 🔗 Cross-References

Each guide links to related topics. For example:
- Setup guides link to security information
- API docs link to integration examples
- Troubleshooting links to detailed guides

## 📌 Important Files

### Essential (Read These)
- **[README.md](README.md)** - Project overview
- **[docs/README.md](docs/README.md)** - Documentation index
- **[SECURITY.md](SECURITY.md)** - Security best practices
- **[.env.example](.env.example)** - Environment variables

### Reference (Keep Nearby)
- **[DOCKER_README.md](DOCKER_README.md)** - Quick Docker commands
- **[LLM_FALLBACK_GUIDE.md](LLM_FALLBACK_GUIDE.md)** - LLM configuration
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines

### Archived (Old Interim Docs)
Files in `.archive/` are interim progress documentation from development. Keep for reference but use main docs for current information.

## 🔍 Finding Information

### By Task
Use the "By Use Case" section in [docs/README.md](docs/README.md)

### By Topic
Use the directory structure above to navigate

### By Keyword
Use GitHub's search or look in relevant directory

### By Error
Check [docs/guides/TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)

## ✏️ Contributing Documentation

When adding new documentation:

1. **Choose the right location:**
   - Setup info → `docs/setup/`
   - User guides → `docs/guides/`
   - Architecture → `docs/architecture/`
   - API reference → `docs/api/`
   - Configuration → `docs/configuration/`
   - User features → `docs/user-guide/`

2. **Use consistent format:**
   - Headers with `#`, `##`, `###`
   - Code blocks with language specified
   - Links for cross-references
   - ToC for long documents

3. **Update indexes:**
   - Update [docs/README.md](docs/README.md)
   - Add to `DOCUMENTATION.md`
   - Update relevant category index

4. **Keep it current:**
   - Update when code changes
   - Note dates of major updates
   - Archive old/interim docs

## 🎓 Learning Path

**New to Demi?**
1. Read [README.md](README.md)
2. Follow [docs/setup/QUICK_START.md](docs/setup/QUICK_START.md)
3. Try [docs/guides/00_START_HERE.md](docs/guides/00_START_HERE.md)

**Want to extend Demi?**
1. Read [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md)
2. Review [CONTRIBUTING.md](CONTRIBUTING.md)
3. Check [docs/api/](docs/api/) for integration points

**Need advanced setup?**
1. Read [docs/setup/DOCKER_SETUP.md](docs/setup/DOCKER_SETUP.md)
2. Check [docs/setup/SECURE_TOKEN_SETUP.md](docs/setup/SECURE_TOKEN_SETUP.md)
3. Review [SECURITY.md](SECURITY.md)

## 📞 Support

- **Questions?** Check [docs/guides/TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)
- **Lost?** Start at [docs/README.md](docs/README.md)
- **Contributing?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security?** Read [SECURITY.md](SECURITY.md)

---

**Last Updated:** February 4, 2026  
**Organization Version:** 1.0.0
