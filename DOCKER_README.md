# Docker Quick Reference

**📖 For full installation instructions, see [INSTALL.md](INSTALL.md)**

---

## Quick Start (5 Minutes)

```bash
# Clone
git clone https://github.com/mystiatech/Demi.git
cd Demi

# Configure
cp .env.example .env

# Start
docker-compose up -d

# Download recommended LLM (wait 30s for Ollama to start)
docker-compose exec ollama ollama pull l3-8b-stheno-v3.2-iq-imatrix
```

**Access:**
- Dashboard: http://localhost:8080
- Mobile API: http://localhost:8081
- Ollama: http://localhost:11434

---

## Common Commands

```bash
# View logs
docker-compose logs -f backend

# Restart
docker-compose restart backend

# Rebuild
docker-compose up -d --build

# Stop
docker-compose down

# Reset (removes all data)
docker-compose down -v
```

---

## Troubleshooting

| Issue | Command |
|-------|---------|
| Check status | `docker-compose ps` |
| View logs | `docker-compose logs -f` |
| Database shell | `docker-compose exec postgres psql -U demi -d demi` |
| Ollama models | `curl http://localhost:11434/api/tags` |

---

**📖 [Full Docker Setup →](docs/setup/DOCKER_SETUP.md)**  
**📖 [Complete Installation →](INSTALL.md)**
