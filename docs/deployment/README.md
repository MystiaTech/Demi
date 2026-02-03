# Demi Deployment Guide 🚀

Welcome to the Demi deployment documentation. This guide will help you install, configure, and maintain Demi on your system.

## Overview

Demi is an autonomous AI companion with emotional depth, designed to run locally on your hardware. She integrates with Discord, Android, and supports voice interactions.

## Quick Start Options

Choose the installation method that best fits your needs:

| Method | Best For | Time Required |
|--------|----------|---------------|
| **[Quick Install Script](./installation.md#quick-install)** | Linux/macOS users who want automation | 10 minutes |
| **[Manual Installation](./installation.md)** | Users who want full control | 30 minutes |
| **[Docker](./installation.md#docker-installation-optional)** | Advanced users, server deployments | 15 minutes |

## System Requirements

### Minimum Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| RAM | 8 GB | 12+ GB | More RAM = better models |
| CPU | 4 cores | 8+ cores | Affects response speed |
| Disk | 10 GB free | 20+ GB | Models + logs + data |
| Network | Broadband | Stable | For Discord, model download |

### Model Size vs RAM

| Model | Minimum RAM | Recommended |
|-------|-------------|-------------|
| llama3.2:1b | 8 GB | 12 GB |
| llama3.2:3b | 12 GB | 16 GB |
| llama2:7b | 16 GB | 24 GB |
| 13b+ models | 24+ GB | 32+ GB |

### Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| Linux (Ubuntu 22.04+) | ✅ Fully Supported | Primary development platform |
| Linux (Debian 11+) | ✅ Supported | Tested and working |
| macOS (12+) | ✅ Supported | Apple Silicon recommended |
| Windows (WSL2) | ⚠️ Supported with caveats | See [WSL2 notes](./installation.md#windows-wsl2) |
| Native Windows | ❌ Not Supported | Use WSL2 instead |
| Docker | ✅ Supported | For server deployments |

## Installation Steps

### 1. Quick Install (Recommended for Linux/macOS)

```bash
# Download and run the install script
curl -fsSL https://raw.githubusercontent.com/yourusername/demi/main/docs/deployment/quick-install.sh | bash
```

The script will:
- ✅ Check system requirements
- ✅ Install Python 3.10+ if needed
- ✅ Install Ollama and download default model
- ✅ Clone the Demi repository
- ✅ Set up Python virtual environment
- ✅ Install all dependencies
- ✅ Generate secure JWT secrets
- ✅ Create initial configuration
- ✅ Guide you through Discord bot setup

### 2. Manual Installation

See the [Installation Guide](./installation.md) for detailed step-by-step instructions.

## Post-Installation

After installation, follow the [First Run Guide](./first-run.md) to:
1. Start Demi for the first time
2. Set up Discord integration
3. Configure the Android app
4. Have your first conversation

## Maintenance

For ongoing maintenance tasks:
- [Backup and Restore](./maintenance.md#backups)
- [Updating Demi](./maintenance.md#updates)
- [Monitoring](./maintenance.md#monitoring)
- [Troubleshooting](./maintenance.md#troubleshooting)

## Directory Structure

After installation, your Demi installation will look like:

```
~/demi/                     # Installation directory
├── main.py                 # Entry point
├── src/                    # Source code
├── requirements.txt        # Python dependencies
├── .env                    # Configuration (created during install)
├── venv/                   # Python virtual environment
└── logs/                   # Log files

~/.demi/                    # Data directory
├── emotions.db             # Emotional state database
├── demi.db                 # Messages and data
└── backups/                # Backup files (if configured)
```

## Quick Commands Reference

```bash
# Start Demi
cd ~/demi && source venv/bin/activate && python main.py

# Check status
curl http://localhost:8000/api/v1/status

# View logs
tail -f logs/demi.log

# Update Demi
git pull && pip install -r requirements.txt

# Backup data
./scripts/backup.sh
```

## Getting Help

- **Installation Issues**: See [Troubleshooting](./maintenance.md#troubleshooting)
- **Discord Setup**: See [First Run Guide](./first-run.md#discord-setup)
- **Android Connection**: See [First Run Guide](./first-run.md#android-setup)
- **General Questions**: Check the [User Guide](../user-guide/)

## Security Notes

⚠️ **Important Security Reminders:**

1. Never commit your `.env` file to version control
2. Use strong, unique JWT secrets in production
3. Restrict `ALLOWED_ORIGINS` to your actual domains
4. Run behind a reverse proxy (nginx/traefik) for production
5. Keep your system and dependencies updated

See [SECURITY.md](../../SECURITY.md) for detailed security guidelines.

## Next Steps

1. ✅ Complete the [Installation](./installation.md)
2. ✅ Follow the [First Run Guide](./first-run.md)
3. ✅ Read the [User Guide](../user-guide/) to learn how to interact with Demi
4. ✅ Review [API Documentation](../api/) for integration details

---

**Ready to install?** Start with the [Installation Guide](./installation.md) 🚀
