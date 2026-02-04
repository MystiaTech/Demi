# Docker Setup for DEMI

## Overview

Containerizing DEMI makes it easy for anyone to run the full system without installation hassles.

---

## Architecture

```
┌─────────────────────────────────────────┐
│        Docker Compose (Orchestration)    │
├─────────────────────────────────────────┤
│                                         │
├─ demi-backend (Python)                │
│  ├─ Ollama/LMStudio integration       │
│  ├─ Piper TTS (GPU-optimized)        │
│  ├─ PostgreSQL database               │
│  └─ FastAPI mobile server              │
│                                         │
├─ demi-database (PostgreSQL)            │
│  └─ Persistent storage                │
│                                         │
└─ Optional: demi-frontend (Nginx)      │
   └─ Serves static dashboard           │
```

---

## Quick Start (Docker Compose)

### 1. Prerequisites

```bash
# Install Docker Desktop
# https://www.docker.com/products/docker-desktop

# Or on Linux:
sudo apt-get install docker.io docker-compose
```

### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: demi-postgres
    environment:
      POSTGRES_USER: demi
      POSTGRES_PASSWORD: demi_secure_password
      POSTGRES_DB: demi
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U demi"]
      interval: 10s
      timeout: 5s
      retries: 5

  # DEMI Backend
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: demi-backend
    environment:
      DATABASE_URL: postgresql://demi:demi_secure_password@postgres:5432/demi
      OLLAMA_BASE_URL: http://ollama:11434
      PIPER_VOICES_DIR: /app/voices/piper
    ports:
      - "8080:8080"  # Main API
      - "8081:8081"  # Mobile API
    volumes:
      - ./src:/app/src
      - piper_voices:/app/voices/piper
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  # Optional: Ollama LLM Server
  ollama:
    image: ollama/ollama:latest
    container_name: demi-ollama
    environment:
      OLLAMA_HOST: 0.0.0.0:11434
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  postgres_data:
  piper_voices:
  ollama_data:
```

### 3. Create Dockerfile

```dockerfile
# Use Python 3.11 slim image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    espeak-ng \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/voices/piper /app/data /tmp/demi_audio

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run application
CMD ["python", "main.py"]
```

### 4. Create .dockerignore

```
__pycache__
*.pyc
.git
.gitignore
.env
.env.local
.DS_Store
node_modules
build
dist
*.egg-info
.pytest_cache
.venv
venv
flutter_app/build
flutter_app/android/build
```

### 5. Run It

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Remove data volumes (fresh start)
docker-compose down -v
```

---

## Mobile App in Docker (Optional)

If you want to containerize Flutter web (though Flutter native is better):

```dockerfile
# Build stage
FROM cirrusci/flutter:latest AS builder

WORKDIR /app
COPY flutter_app .

RUN flutter pub get
RUN flutter build web --release

# Serve stage
FROM nginx:alpine

COPY --from=builder /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## Production Deployment

### AWS ECS

```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker tag demi-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/demi-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/demi-backend:latest

# Deploy with ECS
aws ecs create-service --cluster demi-cluster --service-name demi-backend --task-definition demi-backend:1
```

### Kubernetes (K8s)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demi-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demi-backend
  template:
    metadata:
      labels:
        app: demi-backend
    spec:
      containers:
      - name: demi-backend
        image: demi-backend:latest
        ports:
        - containerPort: 8080
        - containerPort: 8081
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: demi-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml demi

# Check status
docker service ls
docker stack services demi
```

---

## Development Setup

### Local Development with Hot Reload

```yaml
version: '3.8'

services:
  backend-dev:
    build:
      context: .
      target: development
    volumes:
      - ./src:/app/src  # Hot reload Python code
      - ./data:/app/data
    environment:
      PYTHONUNBUFFERED: 1
    ports:
      - "8080:8080"
      - "8081:8081"
    command: python -m pip install watchdog[watchmedo] && watchmedo auto-restart -d src -p '*.py' -- python main.py

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: demi
      POSTGRES_PASSWORD: demi_dev
      POSTGRES_DB: demi
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev:/var/lib/postgresql/data

volumes:
  postgres_dev:
```

---

## Common Commands

### Build
```bash
docker build -t demi-backend:latest .
docker build -f Dockerfile.mobile -t demi-mobile:latest flutter_app
```

### Run
```bash
# Single container
docker run -p 8080:8080 -p 8081:8081 demi-backend:latest

# With compose
docker-compose up -d
docker-compose logs backend
```

### Manage
```bash
# List containers
docker ps -a

# Enter container shell
docker exec -it demi-backend bash

# View logs
docker logs demi-backend
docker logs -f demi-backend  # Follow logs

# Stop/Remove
docker stop demi-backend
docker remove demi-backend
docker-compose down -v  # Remove all + volumes
```

### Push to Registry
```bash
# Docker Hub
docker tag demi-backend:latest username/demi-backend:latest
docker push username/demi-backend:latest

# Private Registry
docker tag demi-backend:latest registry.example.com/demi-backend:latest
docker push registry.example.com/demi-backend:latest
```

---

## Environment Variables

### .env File

```bash
# Database
DATABASE_URL=postgresql://demi:secure_password@postgres:5432/demi
POSTGRES_PASSWORD=secure_password

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=mistral

# Piper TTS
PIPER_VOICE=en_US-lessac-medium
PIPER_VOICES_DIR=/app/voices/piper

# Flask/FastAPI
FLASK_ENV=production
DEBUG=False

# Mobile API
MOBILE_API_HOST=0.0.0.0
MOBILE_API_PORT=8081

# Discord (if needed)
DISCORD_TOKEN=your_token_here
```

---

## Performance Optimization

### GPU Support (NVIDIA)

```yaml
services:
  backend:
    build: .
    runtime: nvidia
    environment:
      NVIDIA_VISIBLE_DEVICES: all
    volumes:
      - /usr/local/cuda:/usr/local/cuda
```

### Resource Limits

```yaml
services:
  backend:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

### Caching

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Health Checks

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Monitoring

### With Prometheus + Grafana

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

---

## Testing in Docker

```bash
# Run tests
docker-compose run backend pytest

# Run with coverage
docker-compose run backend pytest --cov=src

# Run specific test
docker-compose run backend pytest tests/test_api.py
```

---

## Troubleshooting

### Container won't start
```bash
docker logs container_name
docker inspect container_name  # See environment
```

### Database connection fails
```bash
# Check postgres is running
docker ps | grep postgres

# Test connection
docker-compose exec postgres psql -U demi -d demi

# Reset database
docker-compose down -v
docker-compose up -d
```

### Out of disk space
```bash
# Clean up
docker system prune
docker system prune -a --volumes
```

---

## Deployment Checklist

- [ ] Dockerfile created and tested
- [ ] docker-compose.yml configured
- [ ] Environment variables in .env
- [ ] Database migrations run
- [ ] Piper voices downloaded
- [ ] Health checks passing
- [ ] Logs configured
- [ ] Monitoring setup
- [ ] Backup strategy defined
- [ ] Security hardened (secrets, firewalls)

---

## Next Steps

1. **Create Dockerfile** (copy from above)
2. **Test locally** with `docker-compose up -d`
3. **Deploy to cloud** (AWS ECS, K8s, or Heroku)
4. **Monitor and scale** as needed

---

## Benefits

✅ Reproducible environment
✅ Easy installation for users
✅ Scalable deployment
✅ Consistent across machines
✅ Isolated dependencies
✅ Version control
✅ CI/CD ready

**Result:** Anyone can run DEMI with one command! 🚀

```bash
docker-compose up -d
```

Done!
