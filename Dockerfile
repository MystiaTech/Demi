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
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN pip install --upgrade pip setuptools wheel

# Copy requirements
COPY requirements.txt .

# Install Python dependencies with verbose output for debugging
RUN pip install -r requirements.txt || (cat /proc/*/fd/1 2>/dev/null; exit 1)

# Install voice dependencies
RUN pip install webrtcvad>=2.0.10

# Copy application code
COPY . .

# Install the package in editable mode to register entry points
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/voices/piper /app/data /tmp/demi_audio

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Set Python to unbuffered mode
ENV PYTHONUNBUFFERED=1

# Run application
CMD ["python", "main.py"]
