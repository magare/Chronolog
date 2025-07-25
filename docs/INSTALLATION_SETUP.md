# ChronoLog Installation & Setup Guide

Complete guide for installing, configuring, and setting up ChronoLog for different use cases.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Methods](#installation-methods)
3. [Initial Configuration](#initial-configuration)
4. [Component Setup](#component-setup)
5. [Development Setup](#development-setup)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)
8. [Verification](#verification)

## System Requirements

### Minimum Requirements

- **Operating System**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+, CentOS 7+)
- **Python**: 3.9 or higher
- **Memory**: 512 MB RAM available
- **Storage**: 100 MB free disk space (minimum)
- **Network**: Internet connection for installation and updates

### Recommended Requirements

- **Operating System**: Latest stable versions
- **Python**: 3.10 or 3.11
- **Memory**: 2 GB RAM available
- **Storage**: 1 GB free disk space
- **CPU**: Multi-core processor for better performance

### Dependencies

#### Core Dependencies (Automatically Installed)
- `watchdog >= 2.1.6` - File system monitoring
- `click >= 8.0.0` - Command-line interface
- `colorama >= 0.4.4` - Terminal colors
- `psutil >= 5.8.0` - System utilities

#### Optional Dependencies
- `textual >= 0.20.0` - Terminal User Interface
- `flask >= 2.2.0` - Web interface
- `flask-cors >= 3.0.0` - CORS support
- `graphene >= 3.0.0` - GraphQL API
- `PyJWT >= 2.4.0` - Authentication tokens
- `bcrypt >= 3.2.0` - Password hashing

## Installation Methods

### Method 1: Development Installation (Recommended)

For development, testing, or contributing to ChronoLog:

```bash
# Clone the repository
git clone https://github.com/your-org/chronolog.git
cd chronolog

# Install core package in development mode
pip install -e .

# Install optional TUI component
cd chronolog-tui
pip install -e .
cd ..

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### Method 2: PyPI Installation (Production)

*Note: Not yet available on PyPI*

```bash
# Install core ChronoLog
pip install chronolog

# Install with optional components
pip install chronolog[tui,web,api]

# Install all components
pip install chronolog[all]
```

### Method 3: Virtual Environment Installation

Recommended for isolated environments:

```bash
# Create virtual environment
python -m venv chronolog-env

# Activate virtual environment
# On Linux/macOS:
source chronolog-env/bin/activate
# On Windows:
chronolog-env\Scripts\activate

# Install ChronoLog
pip install -e .

# Verify installation
chronolog --version
```

### Method 4: Docker Installation

For containerized deployment:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .
RUN pip install -e chronolog-tui/

EXPOSE 5000
CMD ["chronolog", "web", "start", "--host", "0.0.0.0"]
```

```bash
# Build and run
docker build -t chronolog .
docker run -p 5000:5000 -v $(pwd)/data:/app/data chronolog
```

## Initial Configuration

### First-Time Setup

1. **Initialize Repository**
   ```bash
   # Navigate to your project directory
   cd /path/to/your/project
   
   # Initialize ChronoLog
   chronolog init
   ```

2. **Verify Installation**
   ```bash
   # Check version
   chronolog --version
   
   # Check status
   chronolog status
   ```

3. **Start Daemon**
   ```bash
   # Start background daemon
   chronolog daemon start
   
   # Verify daemon is running
   chronolog daemon status
   ```

### Configuration Files

ChronoLog creates configuration files in the `.chronolog/` directory:

```
.chronolog/
├── config.json          # Main configuration
├── database.db          # SQLite database
├── storage/             # Version storage
├── hooks/               # Custom hooks
└── logs/                # Log files
```

#### Main Configuration (`config.json`)

```json
{
  "repository": {
    "version": "1.0.0",
    "created_at": "2024-01-01T12:00:00Z",
    "storage_format": "content-addressable"
  },
  "daemon": {
    "enabled": true,
    "watch_interval": 1.0,
    "ignore_patterns": [".git", "node_modules", "__pycache__"]
  },
  "storage": {
    "compression": "gzip",
    "compression_level": 6,
    "max_file_size_mb": 100
  },
  "web": {
    "host": "localhost",
    "port": 5000,
    "debug": false,
    "secret_key": "auto-generated"
  },
  "analytics": {
    "collect_metrics": true,
    "retention_days": 90
  }
}
```

### Global Configuration

Create global configuration in user home directory:

```bash
# Create global config directory
mkdir -p ~/.chronolog

# Create global config file
cat > ~/.chronolog/config.json << EOF
{
  "user": {
    "name": "Your Name",
    "email": "your.email@example.com"
  },
  "defaults": {
    "daemon_auto_start": true,
    "web_auto_start": false,
    "log_level": "INFO"
  }
}
EOF
```

## Component Setup

### Terminal User Interface (TUI)

1. **Install TUI Component**
   ```bash
   cd chronolog-tui
   pip install -e .
   ```

2. **Launch TUI**
   ```bash
   # Start TUI in current directory
   chronolog-tui
   
   # Start in specific directory
   chronolog-tui /path/to/project
   ```

3. **TUI Configuration**
   ```json
   {
     "tui": {
       "theme": "dark",
       "refresh_interval": 2.0,
       "auto_refresh": true,
       "max_history_items": 1000
     }
   }
   ```

### Web Interface

1. **Install Web Dependencies**
   ```bash
   pip install flask flask-cors
   ```

2. **Start Web Server**
   ```bash
   # Start on default port (5000)
   chronolog web start
   
   # Start on custom port
   chronolog web start --port 8080
   
   # Start in background
   chronolog web start --daemon
   ```

3. **Web Configuration**
   ```json
   {
     "web": {
       "host": "0.0.0.0",
       "port": 5000,
       "debug": false,
       "ssl_enabled": false,
       "ssl_cert": "/path/to/cert.pem",
       "ssl_key": "/path/to/key.pem",
       "cors_origins": ["*"],
       "session_timeout": 3600
     }
   }
   ```

### User Management System

1. **Create Admin User**
   ```bash
   # Create first admin user
   chronolog users create-admin admin_user
   
   # Set password when prompted
   # Enter email when prompted
   ```

2. **Configure Authentication**
   ```json
   {
     "authentication": {
       "jwt_secret": "your-secret-key",
       "token_expiry_hours": 24,
       "password_min_length": 8,
       "require_email": true,
       "enable_api_keys": true
     }
   }
   ```

3. **Set Up Permissions**
   ```bash
   # Grant repository admin permissions
   chronolog users permissions grant admin_user repository "*" admin
   
   # Create regular user
   chronolog users create dev_user
   
   # Grant file permissions
   chronolog users permissions grant dev_user files "*.py" write
   ```

### Analytics and Metrics

1. **Enable Analytics**
   ```json
   {
     "analytics": {
       "enabled": true,
       "collect_performance_metrics": true,
       "collect_usage_metrics": true,
       "generate_reports": true,
       "visualization_enabled": true
     }
   }
   ```

2. **Configure Metrics Collection**
   ```bash
   # Test analytics
   chronolog analytics stats
   
   # Generate visualization
   chronolog analytics visualize --type timeline
   ```

## Development Setup

### Development Environment

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/chronolog.git
   cd chronolog
   ```

2. **Create Development Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate   # Windows
   
   # Install in development mode
   pip install -e .
   pip install -e chronolog-tui/
   
   # Install development dependencies
   pip install -r requirements-dev.txt
   ```

3. **Set Up Pre-commit Hooks**
   ```bash
   # Install pre-commit
   pip install pre-commit
   
   # Install hooks
   pre-commit install
   
   # Test hooks
   pre-commit run --all-files
   ```

### Testing Setup

1. **Run Test Suite**
   ```bash
   # Run all tests
   python run_all_tests.py
   
   # Run specific test suite
   python tests/test_analytics.py
   
   # Run with coverage
   pip install coverage
   coverage run run_all_tests.py
   coverage report
   ```

2. **Development Configuration**
   ```json
   {
     "development": {
       "debug": true,
       "log_level": "DEBUG",
       "auto_reload": true,
       "test_data_enabled": true
     }
   }
   ```

### IDE Setup

#### VS Code Configuration

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.testing.unittestEnabled": true,
  "python.testing.unittestArgs": [
    "-v",
    "-s",
    "./tests",
    "-p",
    "test_*.py"
  ],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black"
}
```

#### PyCharm Configuration

1. Set Python interpreter to your virtual environment
2. Configure test runner: `Settings > Tools > Python Integrated Tools`
3. Set default test runner to `unittest`
4. Add project root to Python path

## Production Deployment

### Systemd Service (Linux)

1. **Create Service File**
   ```ini
   # /etc/systemd/system/chronolog.service
   [Unit]
   Description=ChronoLog Version Control System
   After=network.target
   
   [Service]
   Type=forking
   User=chronolog
   Group=chronolog
   WorkingDirectory=/opt/chronolog
   ExecStart=/opt/chronolog/venv/bin/chronolog daemon start
   ExecStop=/opt/chronolog/venv/bin/chronolog daemon stop
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable Service**
   ```bash
   sudo systemctl enable chronolog
   sudo systemctl start chronolog
   sudo systemctl status chronolog
   ```

### Web Service Deployment

1. **Nginx Configuration**
   ```nginx
   # /etc/nginx/sites-available/chronolog
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       location /static {
           alias /opt/chronolog/static;
       }
   }
   ```

2. **SSL Configuration**
   ```bash
   # Install certbot
   sudo apt install certbot python3-certbot-nginx
   
   # Get SSL certificate
   sudo certbot --nginx -d your-domain.com
   ```

### Docker Deployment

1. **Production Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       && rm -rf /var/lib/apt/lists/*
   
   # Create app user
   RUN useradd -m -u 1000 chronolog
   
   # Set working directory
   WORKDIR /app
   
   # Copy requirements and install
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application
   COPY . .
   RUN pip install -e .
   RUN pip install -e chronolog-tui/
   
   # Set permissions
   RUN chown -R chronolog:chronolog /app
   USER chronolog
   
   # Expose port
   EXPOSE 5000
   
   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
     CMD chronolog status || exit 1
   
   # Start application
   CMD ["chronolog", "web", "start", "--host", "0.0.0.0"]
   ```

2. **Docker Compose**
   ```yaml
   # docker-compose.yml
   version: '3.8'
   
   services:
     chronolog:
       build: .
       ports:
         - "5000:5000"
       volumes:
         - ./data:/app/data
         - ./config:/app/config
       environment:
         - CHRONOLOG_CONFIG_FILE=/app/config/production.json
         - CHRONOLOG_LOG_LEVEL=INFO
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "chronolog", "status"]
         interval: 30s
         timeout: 10s
         retries: 3
   
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/nginx/ssl
       depends_on:
         - chronolog
       restart: unless-stopped
   ```

### Environment Variables

Production environment variables:

```bash
# Application settings
export CHRONOLOG_ENV=production
export CHRONOLOG_CONFIG_FILE=/opt/chronolog/config/production.json
export CHRONOLOG_LOG_LEVEL=INFO
export CHRONOLOG_LOG_FILE=/var/log/chronolog/app.log

# Database settings
export CHRONOLOG_DB_PATH=/opt/chronolog/data/database.db
export CHRONOLOG_STORAGE_PATH=/opt/chronolog/data/storage

# Web server settings
export CHRONOLOG_WEB_HOST=127.0.0.1
export CHRONOLOG_WEB_PORT=5000
export CHRONOLOG_SECRET_KEY=your-production-secret-key

# Security settings
export CHRONOLOG_JWT_SECRET=your-jwt-secret
export CHRONOLOG_API_RATE_LIMIT=1000
```

## Troubleshooting

### Common Installation Issues

#### 1. Python Version Compatibility

```bash
# Check Python version
python --version

# If too old, install newer version
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# macOS with Homebrew:
brew install python@3.11

# Windows: Download from python.org
```

#### 2. Permission Errors

```bash
# Linux/macOS: Use user install
pip install --user -e .

# Or fix permissions
sudo chown -R $USER:$USER ~/.local
```

#### 3. Missing Dependencies

```bash
# Install build tools
# Ubuntu/Debian:
sudo apt install build-essential python3-dev

# CentOS/RHEL:
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# macOS:
xcode-select --install
```

#### 4. Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### Runtime Issues

#### 1. Daemon Won't Start

```bash
# Check daemon status
chronolog daemon status

# Check logs
tail -f ~/.chronolog/logs/daemon.log

# Reset daemon
chronolog daemon stop
rm -f ~/.chronolog/daemon.pid
chronolog daemon start
```

#### 2. Web Server Issues

```bash
# Check port availability
netstat -tlnp | grep :5000

# Start on different port
chronolog web start --port 8080

# Check web server logs
tail -f ~/.chronolog/logs/web.log
```

#### 3. Database Issues

```bash
# Verify database integrity
chronolog optimize verify

# Rebuild database (last resort)
chronolog optimize gc --rebuild-index
```

### Performance Issues

#### 1. Slow File Watching

```bash
# Increase watch interval
chronolog config set daemon.watch_interval 2.0

# Reduce monitored files
echo "*.log" >> .chronolog_ignore
echo "node_modules/" >> .chronolog_ignore
```

#### 2. Large Repository Performance

```bash
# Run optimization
chronolog optimize storage

# Clean up old data
chronolog optimize gc

# Archive old versions
chronolog export --before "2023-01-01" --output archive.zip
```

## Verification

### Installation Verification

```bash
# 1. Check version
chronolog --version

# 2. Check components
chronolog status
chronolog daemon status

# 3. Test basic functionality
echo "test content" > test.txt
chronolog log test.txt

# 4. Test web interface (if installed)
chronolog web start --daemon
curl http://localhost:5000/api/v1/health

# 5. Test TUI (if installed)
chronolog-tui --help
```

### Health Check Script

Create `health_check.sh`:

```bash
#!/bin/bash

echo "ChronoLog Health Check"
echo "====================="

# Check Python version
echo -n "Python version: "
python --version

# Check ChronoLog installation
echo -n "ChronoLog version: "
chronolog --version

# Check daemon
echo -n "Daemon status: "
chronolog daemon status

# Check repository
echo -n "Repository status: "
chronolog status --porcelain | wc -l | xargs echo "files tracked"

# Check web server (if running)
if curl -s http://localhost:5000/api/v1/health > /dev/null; then
    echo "Web server: Running"
else
    echo "Web server: Not running"
fi

echo "Health check complete!"
```

```bash
chmod +x health_check.sh
./health_check.sh
```

### Performance Benchmark

```bash
# Create test repository
mkdir chronolog-benchmark
cd chronolog-benchmark
chronolog init

# Create test files
for i in {1..100}; do
    echo "Test content $i" > "file_$i.txt"
done

# Measure performance
time chronolog analytics stats
time chronolog log --limit 50
time chronolog optimize analyze

# Cleanup
cd ..
rm -rf chronolog-benchmark
```

For additional help and support, see the [Troubleshooting Guide](TROUBLESHOOTING.md) or visit the project documentation.