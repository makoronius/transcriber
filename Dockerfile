# Use NVIDIA CUDA base image for GPU support
# If you don't have a GPU, you can use: FROM python:3.11-slim
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    ffmpeg \
    git \
    wget \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

# Install pip for Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN python3.11 -m pip install --upgrade pip && \
    python3.11 -m pip install -r requirements.txt

# Install PyTorch with CUDA support
# For CPU-only: pip install torch torchvision torchaudio
RUN python3.11 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p yt_downloads uploads logs backups

# Expose port for Flask app
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "web_app.py", "--port", "5000"]
