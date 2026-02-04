# Docker - Quick Start

## Prerequisites

Install Docker Desktop: https://www.docker.com/products/docker-desktop

Or on Linux:
```bash
sudo apt-get install docker.io docker-compose
```

---

## Run DEMI

### Start Everything

```bash
# Navigate to project root
cd /path/to/Demi

# Start all services (backend, database, Ollama)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### Access Services

- **Backend API**: http://localhost:8080
- **Mobile API**: http://localhost:8081
- **Database**: localhost:5432 (user: demi, password: demi_secure_password)
- **Ollama**: http://localhost:11434

### Stop Everything

```bash
docker-compose down
```

### Clean Up (Remove Data)

```bash
docker-compose down -v
```

---

## Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres

# Last 50 lines
docker-compose logs --tail=50
```

### Enter Container Shell

```bash
# Backend
docker-compose exec backend bash

# Database
docker-compose exec postgres psql -U demi -d demi
```

### Health Check

```bash
# Backend
curl http://localhost:8080/api/health

# Mobile API
curl http://localhost:8081/api/health
```

### Restart Services

```bash
# All
docker-compose restart

# Specific
docker-compose restart backend
```

### Rebuild (After Code Changes)

```bash
docker-compose up -d --build backend
```

---

## Database

### Run Migrations

```bash
docker-compose exec backend python -m alembic upgrade head
```

### Access Database

```bash
docker-compose exec postgres psql -U demi -d demi

# List tables
\dt

# Exit
\q
```

### Backup Database

```bash
docker-compose exec postgres pg_dump -U demi demi > backup.sql
```

### Restore Database

```bash
docker-compose exec -T postgres psql -U demi demi < backup.sql
```

---

## Ollama (LLM)

### Pull Model

```bash
docker-compose exec ollama ollama pull mistral
```

### Check Models

```bash
curl http://localhost:11434/api/tags
```

### Run Model

```bash
docker-compose exec ollama ollama run mistral "Hello"
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check Docker daemon
docker info

# Restart Docker
systemctl restart docker  # Linux
open -a Docker  # Mac
```

### Port Already in Use

```bash
# Change port in docker-compose.yml
# Or find and stop existing service:
lsof -i :8080  # Find what's using port 8080
kill -9 <PID>
```

### Database Connection Failed

```bash
# Check postgres is running
docker-compose ps | grep postgres

# Wait for postgres to be healthy
docker-compose logs postgres | tail -20

# Test connection
docker-compose exec postgres pg_isready -U demi
```

### Out of Disk Space

```bash
docker system prune        # Remove unused containers/images
docker system prune -a     # More aggressive
docker volume prune        # Remove unused volumes
df -h                      # Check disk space
```

---

## Performance Tips

### Increase Resources (Mac/Windows)

- Docker Desktop → Preferences → Resources
- Increase CPU, Memory, Disk

### Check Container Resource Usage

```bash
docker stats
docker-compose exec backend top
```

### Build Cache

```bash
# Force rebuild without cache
docker-compose build --no-cache
```

---

## Development Mode

### With Live Code Reload

Edit `docker-compose.yml`:

```yaml
services:
  backend:
    volumes:
      - ./src:/app/src  # Mount source code
    command: watchmedo auto-restart -d src -p '*.py' -- python main.py
```

Then:
```bash
docker-compose up -d
```

Changes to Python files auto-reload!

---

## Production Deployment

### Environment Variables

Create `.env`:
```bash
DATABASE_URL=postgresql://demi:your_secure_password@postgres:5432/demi
OLLAMA_BASE_URL=http://ollama:11434
DEBUG=False
```

Load in docker-compose.yml:
```yaml
env_file: .env
```

### SSL/HTTPS

Add Nginx reverse proxy (see DOCKER_SETUP.md for full example)

### Scaling

```bash
# Scale backend to 3 instances
docker-compose up -d --scale backend=3
```

---

## Useful Commands Reference

```bash
# List all containers
docker ps -a

# View image layers
docker history demi-backend:latest

# Push to registry
docker tag demi-backend:latest username/demi-backend:latest
docker push username/demi-backend:latest

# Run one-off command
docker-compose run backend python -m pytest

# Clean everything (WARNING: removes all containers/images/volumes)
docker system prune -a --volumes
```

---

## Questions?

See full Docker guide: `DOCKER_SETUP.md`

**Quick Help:**
- Logs not clear? → `docker-compose logs --follow backend`
- Connection fails? → `docker-compose exec postgres pg_isready -U demi`
- Needs rebuild? → `docker-compose up -d --build`
- Something broken? → `docker-compose down -v && docker-compose up -d`

Happy Dockering! 🐳
