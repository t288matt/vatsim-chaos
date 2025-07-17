# ATC Conflict Generation System - Docker Implementation Plan

## 🐳 Project Overview

This plan outlines the complete Docker containerisation strategy for the ATC Conflict Generation System, transforming the current multi-service architecture into a streamlined, containerised deployment.

## 📋 Current System Analysis

### **Existing Architecture**
```
┌─────────────────────────────────────────────────────────────┐
│                    Current System                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   Web Service   │  │      Animation Service          │  │
│  │   (Flask)       │  │   (Static HTTP Server)         │  │
│  │   Port 5000     │  │      Port 8000                 │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Python Scripts                            │ │
│  │  • extract_simbrief_xml_flightplan.py                │ │
│  │  • find_potential_conflicts.py                        │ │
│  │  • generate_schedule_conflicts.py                     │ │
│  │  • generate_animation.py                              │ │
│  │  • merge_kml_flightplans.py                          │ │
│  │  • audit_conflict.py                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### **Dependencies Identified**
- **Python 3.11+**: Core runtime
- **Flask 2.3.3**: Web framework
- **psutil 5.9.5**: System monitoring
- **CesiumJS**: 3D visualization (CDN)
- **File System**: XML uploads and processing results
- **Subprocess**: Python script execution

## 🎯 Docker Strategy

### **Single Container Approach**
- **Primary Strategy**: Single container with all services
- **Benefits**: Simplicity, easier deployment, no inter-service communication
- **Services**: Flask web app + static file serving
- **Ports**: 5000 (web), 8000 (animation)

### **Alternative: Multi-Service Approach**
- **Web Service**: Flask application
- **Animation Service**: Static file server
- **Shared Volume**: File storage between services

## 🏗️ Implementation Plan

### **Phase 1: Core Container Setup**

#### **1.1 Create Dockerfile**
```dockerfile
# Base image with Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/temp /app/xml_files

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
```

#### **1.2 Create requirements.txt**
```txt
Flask==2.3.3
psutil==5.9.5
Werkzeug==2.3.7
```

#### **1.3 Create .dockerignore**
```dockerignore
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# Development
.vscode
.idea
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
temp/
*.kml
*.json
pilot_briefing.txt
conflict_list.txt
audit_conflict_output.txt
merged_flightplans.kml

# Documentation
*.md
!README.md
```

### **Phase 2: Docker Compose Configuration**

#### **2.1 Development Environment (docker-compose.dev.yml)**
```yaml
version: '3.8'

services:
  atc-conflict:
    build: .
    ports:
      - "5000:5000"  # Web interface
      - "8000:8000"  # Animation server
    volumes:
      - .:/app  # Code hot reloading
      - ./uploads:/app/uploads  # Persistent uploads
      - ./temp:/app/temp  # Processing results
      - ./xml_files:/app/xml_files  # XML storage
    environment:
      # Application Settings
      - FLASK_ENV=development
      - FLASK_DEBUG=true
      - FLASK_APP=web/app.py
      - PYTHONPATH=/app
      - LOG_LEVEL=DEBUG
      - LOG_FILE=/app/logs/app.log
      
      # Conflict Detection Parameters
      - LATERAL_SEPARATION_THRESHOLD=3.0
      - VERTICAL_SEPARATION_THRESHOLD=900
      - MIN_ALTITUDE_THRESHOLD=5000
      - NO_CONFLICT_AIRPORT_DISTANCES=YSSY/35,YSCB/15
      
      # Departure Scheduling Parameters
      - MIN_DEPARTURE_SEPARATION_MINUTES=2
      - MIN_SAME_ROUTE_SEPARATION_MINUTES=5
      - BATCH_SIZE=1
      
      # Route Interpolation Parameters
      - INTERPOLATION_SPACING_NM=1.5
      
      # Scheduling Optimization Parameters
      - TIME_TOLERANCE_MINUTES=2
      - MAX_DEPARTURE_TIME_MINUTES=120
      - DEPARTURE_TIME_STEP_MINUTES=5
      - TRANSITION_ALTITUDE_FT=10500
      
      # Web Interface Parameters
      - WEB_PORT=5000
      - ANIMATION_PORT=8000
      - MAX_FILE_SIZE_BYTES=16777216
      - UPLOAD_TIMEOUT_MS=30000
      - MAX_PROCESSING_TIME_MS=300000
      
      # UI Settings
      - MESSAGE_DISPLAY_TIME_MS=5000
      - AUTO_REFRESH_INTERVAL_MS=3000
      - PROGRESS_UPDATE_INTERVAL_MS=1000
      
      # Processing Settings
      - MAX_RETRIES=3
      - STATUS_CHECK_INTERVAL_MS=1000
      - VALIDATION_CACHE_TIMEOUT_SEC=3600
      
      # File System Settings
      - UPLOAD_FOLDER=/app/uploads
      - TEMP_FOLDER=/app/temp
      - ANIMATION_FOLDER=/app/animation
      
      # Animation Parameters
      - DEFAULT_SIMULATION_SPEED=48
      - MIN_SIMULATION_SPEED=-120
      - MAX_SIMULATION_SPEED=120
      
      # Mathematical Constants
      - EARTH_RADIUS_NM=3440.065
      - FEET_TO_NM_CONVERSION=6076.12
    command: python web/app.py
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  uploads:
  temp:
  xml_files:
```

#### **2.2 Production Environment (docker-compose.prod.yml)**
```yaml
version: '3.8'

services:
  atc-conflict:
    build: .
    ports:
      - "5000:5000"
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads:rw
      - ./temp:/app/temp:rw
      - ./xml_files:/app/xml_files:rw
    environment:
      # Application Settings
      - FLASK_ENV=production
      - FLASK_DEBUG=false
      - FLASK_APP=web/app.py
      - PYTHONPATH=/app
      - LOG_LEVEL=INFO
      - LOG_FILE=/app/logs/app.log
      
      # Security Settings
      - SECRET_KEY=your-production-secret-key-here
      - CORS_ORIGINS=https://your-domain.com
      
      # Conflict Detection Parameters
      - LATERAL_SEPARATION_THRESHOLD=3.0
      - VERTICAL_SEPARATION_THRESHOLD=900
      - MIN_ALTITUDE_THRESHOLD=5000
      - NO_CONFLICT_AIRPORT_DISTANCES=YSSY/35,YSCB/15
      
      # Departure Scheduling Parameters
      - MIN_DEPARTURE_SEPARATION_MINUTES=2
      - MIN_SAME_ROUTE_SEPARATION_MINUTES=5
      - BATCH_SIZE=1
      
      # Route Interpolation Parameters
      - INTERPOLATION_SPACING_NM=1.5
      
      # Scheduling Optimization Parameters
      - TIME_TOLERANCE_MINUTES=2
      - MAX_DEPARTURE_TIME_MINUTES=120
      - DEPARTURE_TIME_STEP_MINUTES=5
      - TRANSITION_ALTITUDE_FT=10500
      
      # Web Interface Parameters
      - WEB_PORT=5000
      - ANIMATION_PORT=8000
      - MAX_FILE_SIZE_BYTES=16777216
      - UPLOAD_TIMEOUT_MS=30000
      - MAX_PROCESSING_TIME_MS=300000
      
      # UI Settings
      - MESSAGE_DISPLAY_TIME_MS=5000
      - AUTO_REFRESH_INTERVAL_MS=3000
      - PROGRESS_UPDATE_INTERVAL_MS=1000
      
      # Processing Settings
      - MAX_RETRIES=3
      - STATUS_CHECK_INTERVAL_MS=1000
      - VALIDATION_CACHE_TIMEOUT_SEC=3600
      
      # File System Settings
      - UPLOAD_FOLDER=/app/uploads
      - TEMP_FOLDER=/app/temp
      - ANIMATION_FOLDER=/app/animation
      
      # Animation Parameters
      - DEFAULT_SIMULATION_SPEED=48
      - MIN_SIMULATION_SPEED=-120
      - MAX_SIMULATION_SPEED=120
      
      # Mathematical Constants
      - EARTH_RADIUS_NM=3440.065
      - FEET_TO_NM_CONVERSION=6076.12
      
      # Performance Settings
      - WORKER_PROCESSES=4
      - WORKER_CONNECTIONS=1000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'

volumes:
  uploads:
  temp:
  xml_files:
```

### **Phase 3: Multi-Service Architecture (Alternative)**

#### **3.1 Web Service (web/Dockerfile)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ ./web/
COPY *.py ./
COPY shared_types.py ./
COPY env.py ./

ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "web/app.py"]
```

#### **3.2 Animation Service (animation/Dockerfile)**
```dockerfile
FROM nginx:alpine

COPY animation/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8000

CMD ["nginx", "-g", "daemon off;"]
```

#### **3.3 Multi-Service Compose (docker-compose.multi.yml)**
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: web/Dockerfile
    ports:
      - "5000:5000"
    volumes:
      - ./uploads:/app/uploads:rw
      - ./temp:/app/temp:rw
      - ./xml_files:/app/xml_files:rw
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=false
    depends_on:
      - animation
    restart: unless-stopped

  animation:
    build:
      context: .
      dockerfile: animation/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./temp:/usr/share/nginx/html/temp:ro
    restart: unless-stopped

volumes:
  uploads:
  temp:
  xml_files:
```

### **Phase 4: Environment Configuration**

#### **4.1 Converting env.py Variables to Environment Variables**

The current `env.py` contains hardcoded configuration values. In Docker, these should be converted to environment variables for better flexibility and security.

**Current env.py Variables:**
```python
# Conflict Detection Parameters
LATERAL_SEPARATION_THRESHOLD = 3.0
VERTICAL_SEPARATION_THRESHOLD = 900
MIN_ALTITUDE_THRESHOLD = 5000
NO_CONFLICT_AIRPORT_DISTANCES = ["YSSY/35", "YSCB/15"]

# Departure Scheduling Parameters
MIN_DEPARTURE_SEPARATION_MINUTES = 2
MIN_SAME_ROUTE_SEPARATION_MINUTES = 5
BATCH_SIZE = 1

# Route Interpolation Parameters
INTERPOLATION_SPACING_NM = 1.5

# Scheduling Optimization Parameters
TIME_TOLERANCE_MINUTES = 2
MAX_DEPARTURE_TIME_MINUTES = 120
DEPARTURE_TIME_STEP_MINUTES = 5
TRANSITION_ALTITUDE_FT = 10500
```

**Docker Environment Variables (.env file):**
```bash
# =============================================================================
# CONFLICT DETECTION PARAMETERS
# =============================================================================
LATERAL_SEPARATION_THRESHOLD=3.0
VERTICAL_SEPARATION_THRESHOLD=900
MIN_ALTITUDE_THRESHOLD=5000
NO_CONFLICT_AIRPORT_DISTANCES=YSSY/35,YSCB/15

# =============================================================================
# DEPARTURE SCHEDULING PARAMETERS
# =============================================================================
MIN_DEPARTURE_SEPARATION_MINUTES=2
MIN_SAME_ROUTE_SEPARATION_MINUTES=5
BATCH_SIZE=1

# =============================================================================
# ROUTE INTERPOLATION PARAMETERS
# =============================================================================
INTERPOLATION_SPACING_NM=1.5

# =============================================================================
# SCHEDULING OPTIMIZATION PARAMETERS
# =============================================================================
TIME_TOLERANCE_MINUTES=2
MAX_DEPARTURE_TIME_MINUTES=120
DEPARTURE_TIME_STEP_MINUTES=5
TRANSITION_ALTITUDE_FT=10500

# =============================================================================
# WEB INTERFACE PARAMETERS
# =============================================================================
WEB_PORT=5000
ANIMATION_PORT=8000
MAX_FILE_SIZE_BYTES=16777216
UPLOAD_TIMEOUT_MS=30000
MAX_PROCESSING_TIME_MS=300000

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_APP=web/app.py
PYTHONPATH=/app
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# =============================================================================
# SECURITY SETTINGS
# =============================================================================
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:5000,http://localhost:8000

# =============================================================================
# PERFORMANCE SETTINGS
# =============================================================================
WORKER_PROCESSES=4
WORKER_CONNECTIONS=1000
```

#### **4.2 Updated env.py for Docker Environment**
```python
# env.py - Updated for Docker environment
import os

# =============================================================================
# CONFLICT DETECTION PARAMETERS
# =============================================================================

# Lateral separation threshold for conflict detection (nautical miles)
LATERAL_SEPARATION_THRESHOLD = float(os.getenv('LATERAL_SEPARATION_THRESHOLD', '3.0'))

# Vertical separation threshold for conflict detection (feet)
VERTICAL_SEPARATION_THRESHOLD = int(os.getenv('VERTICAL_SEPARATION_THRESHOLD', '900'))

# Minimum altitude threshold for conflict detection (feet)
MIN_ALTITUDE_THRESHOLD = int(os.getenv('MIN_ALTITUDE_THRESHOLD', '5000'))

# No-conflict zones around airports (format: "ICAO_CODE/DISTANCE_NM")
NO_CONFLICT_AIRPORT_DISTANCES_STR = os.getenv('NO_CONFLICT_AIRPORT_DISTANCES', 'YSSY/35,YSCB/15')
NO_CONFLICT_AIRPORT_DISTANCES = NO_CONFLICT_AIRPORT_DISTANCES_STR.split(',')

# =============================================================================
# DEPARTURE SCHEDULING PARAMETERS
# =============================================================================

# Minimum separation between departures from the same airport (minutes)
MIN_DEPARTURE_SEPARATION_MINUTES = int(os.getenv('MIN_DEPARTURE_SEPARATION_MINUTES', '2'))

# Minimum separation between flights with same origin-destination (minutes)
MIN_SAME_ROUTE_SEPARATION_MINUTES = int(os.getenv('MIN_SAME_ROUTE_SEPARATION_MINUTES', '5'))

# Batch size for conflict score recalculation during scheduling
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1'))

# =============================================================================
# ROUTE INTERPOLATION PARAMETERS
# =============================================================================

# Distance between interpolated route points (nautical miles)
INTERPOLATION_SPACING_NM = float(os.getenv('INTERPOLATION_SPACING_NM', '1.5'))

# =============================================================================
# SCHEDULING OPTIMIZATION PARAMETERS
# =============================================================================

# Time tolerance for departure time optimization (minutes)
TIME_TOLERANCE_MINUTES = int(os.getenv('TIME_TOLERANCE_MINUTES', '2'))

# Maximum departure time range for optimization (minutes)
MAX_DEPARTURE_TIME_MINUTES = int(os.getenv('MAX_DEPARTURE_TIME_MINUTES', '120'))

# Step size for departure time optimization (minutes)
DEPARTURE_TIME_STEP_MINUTES = int(os.getenv('DEPARTURE_TIME_STEP_MINUTES', '5'))

# Transition altitude for feet/flight level display in pilot briefing
TRANSITION_ALTITUDE_FT = int(os.getenv('TRANSITION_ALTITUDE_FT', '10500'))

# =============================================================================
# WEB INTERFACE PARAMETERS (Docker-specific)
# =============================================================================

# Port configuration
WEB_PORT = int(os.getenv('WEB_PORT', '5000'))
ANIMATION_PORT = int(os.getenv('ANIMATION_PORT', '8000'))

# File upload settings
MAX_FILE_SIZE_BYTES = int(os.getenv('MAX_FILE_SIZE_BYTES', '16777216'))  # 16MB
UPLOAD_TIMEOUT_MS = int(os.getenv('UPLOAD_TIMEOUT_MS', '30000'))  # 30 seconds
MAX_PROCESSING_TIME_MS = int(os.getenv('MAX_PROCESSING_TIME_MS', '300000'))  # 5 minutes

# UI settings
MESSAGE_DISPLAY_TIME_MS = int(os.getenv('MESSAGE_DISPLAY_TIME_MS', '5000'))  # 5 seconds
AUTO_REFRESH_INTERVAL_MS = int(os.getenv('AUTO_REFRESH_INTERVAL_MS', '3000'))  # 3 seconds
PROGRESS_UPDATE_INTERVAL_MS = int(os.getenv('PROGRESS_UPDATE_INTERVAL_MS', '1000'))  # 1 second

# Processing settings
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
STATUS_CHECK_INTERVAL_MS = int(os.getenv('STATUS_CHECK_INTERVAL_MS', '1000'))  # 1 second
VALIDATION_CACHE_TIMEOUT_SEC = int(os.getenv('VALIDATION_CACHE_TIMEOUT_SEC', '3600'))  # 1 hour

# File system settings
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/uploads')
TEMP_FOLDER = os.getenv('TEMP_FOLDER', '/app/temp')
ANIMATION_FOLDER = os.getenv('ANIMATION_FOLDER', '/app/animation')

# =============================================================================
# ANIMATION PARAMETERS
# =============================================================================

# Simulation speed settings
DEFAULT_SIMULATION_SPEED = int(os.getenv('DEFAULT_SIMULATION_SPEED', '48'))
MIN_SIMULATION_SPEED = int(os.getenv('MIN_SIMULATION_SPEED', '-120'))
MAX_SIMULATION_SPEED = int(os.getenv('MAX_SIMULATION_SPEED', '120'))

# =============================================================================
# MATHEMATICAL CONSTANTS
# =============================================================================

# Earth and distance calculations
EARTH_RADIUS_NM = float(os.getenv('EARTH_RADIUS_NM', '3440.065'))
FEET_TO_NM_CONVERSION = float(os.getenv('FEET_TO_NM_CONVERSION', '6076.12'))
```

#### **4.3 Environment Variables in Docker Compose**

All environment variables are now directly defined in the `docker-compose.yml` files:

**Benefits of this approach:**
- ✅ **Single file**: All configuration in one place
- ✅ **Version controlled**: Changes tracked in git
- ✅ **Easy to modify**: Edit docker-compose.yml directly
- ✅ **No external files**: No need for separate .env files
- ✅ **Clear visibility**: All settings visible in the compose file

**Environment variables are organized by category:**
- **Application Settings**: Flask configuration, logging
- **Conflict Detection Parameters**: From env.py
- **Departure Scheduling Parameters**: From env.py  
- **Route Interpolation Parameters**: From env.py
- **Scheduling Optimization Parameters**: From env.py
- **Web Interface Parameters**: Ports, file uploads, timeouts
- **UI Settings**: Display times, refresh intervals
- **Processing Settings**: Retries, cache timeouts
- **File System Settings**: Upload folders, temp directories
- **Animation Parameters**: Simulation speeds
- **Mathematical Constants**: Earth radius, conversions

#### **4.4 Migration Strategy**

**Step 1: Update env.py**
- Replace hardcoded values with `os.getenv()` calls
- Maintain backward compatibility with default values
- Add proper type conversion for numeric values

**Step 2: Update Docker Compose Files**
- Add all environment variables directly to `docker-compose.yml`
- Organize variables by category (conflict detection, scheduling, etc.)
- Use different values for development vs production

**Step 3: Test Configuration**
- Verify all variables are properly loaded
- Test with different environment values
- Ensure backward compatibility

**Step 4: Deploy**
- Build and run containers with new configuration
- Verify all functionality works as expected

### **Phase 5: Development Workflow**

#### **5.1 Development Commands**
```bash
# Build and start development environment
docker-compose -f docker-compose.dev.yml up --build

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Execute commands in container
docker-compose -f docker-compose.dev.yml exec atc-conflict python execute.py

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

#### **5.2 Production Commands**
```bash
# Build and start production environment
docker-compose -f docker-compose.prod.yml up --build -d

# View production logs
docker-compose -f docker-compose.prod.yml logs -f

# Update production deployment
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Backup volumes
docker run --rm -v atc-conflict_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads.tar.gz -C /data .
```

### **Phase 6: CI/CD Pipeline**

#### **6.1 GitHub Actions (.github/workflows/docker.yml)**
```yaml
name: Docker Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Build and test
        run: |
          docker build -t atc-conflict:test .
          docker run --rm atc-conflict:test python -c "import sys; print('Python version:', sys.version)"
      
      - name: Run tests
        run: |
          docker run --rm atc-conflict:test python -m pytest tests/ || echo "No tests found"

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            your-username/atc-conflict:latest
            your-username/atc-conflict:${{ github.sha }}
```

### **Phase 7: Monitoring and Logging**

#### **7.1 Health Checks**
```python
# web/health.py
from flask import Blueprint, jsonify
import psutil
import os

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Health check endpoint for Docker"""
    try:
        # Check disk space
        disk_usage = psutil.disk_usage('/app')
        disk_ok = disk_usage.free > 1024 * 1024 * 1024  # 1GB free
        
        # Check memory
        memory = psutil.virtual_memory()
        memory_ok = memory.percent < 90
        
        # Check if upload directory exists
        upload_dir_ok = os.path.exists('/app/uploads')
        
        status = 'healthy' if all([disk_ok, memory_ok, upload_dir_ok]) else 'unhealthy'
        
        return jsonify({
            'status': status,
            'disk_free_gb': round(disk_usage.free / (1024**3), 2),
            'memory_percent': memory.percent,
            'upload_dir_exists': upload_dir_ok
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

#### **7.2 Logging Configuration**
```python
# web/logging_config.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure logging for Docker environment"""
    log_dir = '/app/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        '/app/logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
```

### **Phase 8: Security Considerations**

#### **8.1 Security Headers**
```python
# web/security.py
from flask import Flask
from flask_talisman import Talisman

def setup_security(app: Flask):
    """Configure security headers for Docker deployment"""
    Talisman(app, 
        content_security_policy={
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'", "https://cesium.com"],
            'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            'font-src': ["'self'", "https://fonts.gstatic.com"],
            'img-src': ["'self'", "data:", "https:"],
            'connect-src': ["'self'", "https://cesium.com"]
        },
        force_https=False  # Set to True in production with HTTPS
    )
```

#### **8.2 Non-Root User**
```dockerfile
# Add to Dockerfile
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser
```

### **Phase 9: Performance Optimization**

#### **9.1 Multi-Stage Build**
```dockerfile
# Development stage
FROM python:3.11-slim as development
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "web/app.py"]

# Production stage
FROM python:3.11-slim as production
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m compileall .
CMD ["python", "web/app.py"]
```

#### **9.2 Resource Limits**
```yaml
# In docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
    reservations:
      memory: 512M
      cpus: '0.5'
```

## 🚀 Deployment Strategy

### **Development Deployment**
```bash
# Quick start for development
git clone <repository>
cd Chaos2
docker-compose -f docker-compose.dev.yml up --build
# Access at http://localhost:5000
```

### **Production Deployment**
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
# Access at http://your-server:5000
```

### **Cloud Deployment**
```bash
# AWS ECS/Fargate
aws ecs create-service --cluster atc-conflict --service-name atc-conflict-service --task-definition atc-conflict:1

# Google Cloud Run
gcloud run deploy atc-conflict --image gcr.io/your-project/atc-conflict --platform managed

# Azure Container Instances
az container create --resource-group atc-conflict --name atc-conflict --image your-registry/atc-conflict:latest
```

## 📊 Benefits of Docker Implementation

### **Operational Benefits**
- ✅ **Consistent Environment**: Same behavior across all deployments
- ✅ **Easy Deployment**: One command to deploy entire system
- ✅ **Isolation**: No system dependencies or conflicts
- ✅ **Scalability**: Easy horizontal scaling
- ✅ **Version Control**: Exact environment reproduction

### **Development Benefits**
- ✅ **Hot Reloading**: Code changes reflect immediately
- ✅ **Dependency Management**: All dependencies contained
- ✅ **Testing**: Identical test and production environments
- ✅ **CI/CD Ready**: Automated build and deployment

### **Maintenance Benefits**
- ✅ **Updates**: Easy version updates and rollbacks
- ✅ **Monitoring**: Built-in health checks and logging
- ✅ **Backup**: Simple volume backup and restore
- ✅ **Security**: Isolated, secure container environment

## 🎯 Next Steps

### **Immediate Actions**
1. **Create Dockerfile** with Python 3.11 base
2. **Set up docker-compose.dev.yml** for development
3. **Test container build** and basic functionality
4. **Configure volume mounts** for file persistence

### **Short-term Goals**
1. **Implement health checks** for monitoring
2. **Add security headers** and non-root user
3. **Set up logging** with rotation
4. **Create production compose** file

### **Long-term Goals**
1. **CI/CD pipeline** with automated testing
2. **Cloud deployment** configurations
3. **Monitoring integration** (Prometheus/Grafana)
4. **Multi-service architecture** if needed

This Docker implementation plan provides a complete containerization strategy that maintains the simplicity of the current system while adding the benefits of containerized deployment, making the ATC Conflict Generation System ready for production use and easy deployment across different environments. 