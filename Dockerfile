# =============================================================================
# ATC Conflict Analysis System - Dockerfile
# =============================================================================

# Base image with Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/temp /app/xml_files /app/logs

# Fix the upload folder configuration to use environment variables
RUN sed -i "s|UPLOAD_FOLDER = '../xml_files'|UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/xml_files')|g" /app/web/config.py && \
    sed -i "1i import os" /app/web/config.py

# Set environment variables
ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Expose ports
EXPOSE 5000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start command
CMD ["python", "web/app.py"] 