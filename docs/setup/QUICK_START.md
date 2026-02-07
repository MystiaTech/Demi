# Quick Start

**➡️ See the [Installation Guide](../../INSTALL.md) for complete setup instructions.**

## 5-Minute Docker Quick Start

```bash
# 1. Clone
git clone https://github.com/mystiatech/Demi.git
cd Demi

# 2. Configure
cp .env.example .env

# 3. Start
docker-compose up -d

# 4. Download LLM (wait 30s for Ollama to start)
docker-compose exec ollama ollama pull llama3.2:1b
```

**Access:**
- Dashboard: http://localhost:8080
- Mobile API: http://localhost:8081

---

For detailed instructions including:
- Manual installation
- Flutter app setup
- Discord configuration
- Troubleshooting

**📖 [Full Installation Guide →](../../INSTALL.md)**
