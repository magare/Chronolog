# ChronoLog Troubleshooting Guide

Comprehensive troubleshooting guide for common issues, error messages, and performance problems.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Runtime Errors](#runtime-errors)
4. [Performance Issues](#performance-issues)
5. [Web Interface Problems](#web-interface-problems)
6. [Database Issues](#database-issues)
7. [Daemon Problems](#daemon-problems)
8. [User Management Issues](#user-management-issues)
9. [Diagnostic Tools](#diagnostic-tools)
10. [Getting Help](#getting-help)

## Common Issues

### Repository Not Initialized

**Symptoms:**
- `Error: Not a ChronoLog repository`
- Commands fail with "repository not found"

**Solution:**
```bash
# Check if you're in the right directory
pwd

# Initialize repository if needed
chronolog init

# Verify initialization
ls -la .chronolog/
```

### Daemon Not Running

**Symptoms:**
- Files not being automatically versioned
- `chronolog daemon status` shows "stopped"

**Solution:**
```bash
# Start the daemon
chronolog daemon start

# Check status
chronolog daemon status

# If still not working, check logs
tail -f ~/.chronolog/logs/daemon.log

# Restart daemon
chronolog daemon restart
```

### Permission Denied Errors

**Symptoms:**
- `PermissionError: [Errno 13] Permission denied`
- Cannot write to repository directory

**Solution:**
```bash
# Check directory permissions
ls -la .chronolog/

# Fix permissions
chmod 755 .chronolog/
chmod 644 .chronolog/config.json
chmod 755 .chronolog/storage/

# Check file ownership
sudo chown -R $USER:$USER .chronolog/
```

### Version Hash Not Found

**Symptoms:**
- `Error: Version hash 'abc123' not found`
- Commands fail when referencing versions

**Solution:**
```bash
# Check if hash exists
chronolog log | grep abc123

# Use full hash instead of short hash
chronolog show abc1234567890abcdef...

# Verify repository integrity
chronolog optimize verify

# If corrupted, run repair
chronolog optimize gc --verify
```

## Installation Problems

### Python Version Too Old

**Symptoms:**
- `SyntaxError` during installation
- Features not working properly

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.9+
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.11 python3.11-venv

# macOS with Homebrew:
brew install python@3.11

# Windows: Download from python.org
```

### Missing Dependencies

**Symptoms:**
- `ModuleNotFoundError: No module named 'watchdog'`
- Import errors during startup

**Solution:**
```bash
# Install missing dependencies
pip install -r requirements.txt

# Or install specific packages
pip install watchdog click colorama psutil

# For development
pip install -r requirements-dev.txt

# Verify installation
pip list | grep chronolog
```

### Virtual Environment Issues

**Symptoms:**
- Package conflicts
- Installation fails

**Solution:**
```bash
# Create fresh virtual environment
rm -rf venv
python -m venv venv

# Activate environment
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Upgrade pip
pip install --upgrade pip

# Install ChronoLog
pip install -e .
```

### Build Errors on Windows

**Symptoms:**
- `Microsoft Visual C++ 14.0 is required`
- Compilation errors during installation

**Solution:**
```bash
# Install Microsoft C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Or use conda
conda install -c conda-forge watchdog click colorama psutil

# Alternative: Use pre-compiled wheels
pip install --only-binary=all -e .
```

## Runtime Errors

### Database Lock Errors

**Symptoms:**
- `database is locked`
- Operations hang or timeout

**Solution:**
```bash
# Check for running processes
ps aux | grep chronolog

# Stop daemon
chronolog daemon stop

# Remove lock files
rm -f .chronolog/database.db-wal
rm -f .chronolog/database.db-shm

# Restart daemon
chronolog daemon start

# If persistent, backup and restore database
cp .chronolog/database.db .chronolog/database.db.backup
chronolog optimize gc --rebuild-index
```

### File System Monitoring Errors

**Symptoms:**
- `[Errno 28] No space left on device`
- File watching stops working

**Solution:**
```bash
# Check disk space
df -h

# Check inotify limits (Linux)
cat /proc/sys/fs/inotify/max_user_watches

# Increase limits
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Restart daemon
chronolog daemon restart
```

### Memory Issues

**Symptoms:**
- `MemoryError`
- System becomes unresponsive
- Large memory usage

**Solution:**
```bash
# Check memory usage
ps aux | grep chronolog
free -h

# Reduce daemon watch interval
chronolog config set daemon.watch_interval 5.0

# Add file patterns to ignore
echo "*.log" >> .chronolog_ignore
echo "node_modules/" >> .chronolog_ignore
echo "__pycache__/" >> .chronolog_ignore

# Run garbage collection
chronolog optimize gc

# Restart with limited memory
ulimit -v 1048576  # 1GB limit
chronolog daemon start
```

### Unicode/Encoding Errors

**Symptoms:**
- `UnicodeDecodeError`
- Garbled text in diffs
- Files not displaying correctly

**Solution:**
```bash
# Set environment variables
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8

# Configure git (if using both)
git config --global core.quotepath false

# Force encoding in chronolog
chronolog config set storage.default_encoding utf-8

# For specific files
chronolog show --encoding utf-8 abc123
```

## Performance Issues

### Slow Repository Operations

**Symptoms:**
- Commands take a long time to complete
- High CPU usage
- Unresponsive interface

**Diagnosis:**
```bash
# Profile repository
chronolog analytics metrics --performance

# Check repository size
chronolog analytics stats

# Identify large files
chronolog optimize analyze --details
```

**Solutions:**
```bash
# Run storage optimization
chronolog optimize storage

# Increase database performance
chronolog config set database.wal_mode true
chronolog config set database.synchronous normal

# Reduce watch frequency
chronolog config set daemon.watch_interval 2.0

# Add ignore patterns
echo "*.tmp" >> .chronolog_ignore
echo "build/" >> .chronolog_ignore
```

### Large File Handling

**Symptoms:**
- Operations timeout on large files
- Excessive memory usage
- Slow diff generation

**Solution:**
```bash
# Set file size limits
chronolog config set storage.max_file_size_mb 50

# Use streaming for large files
chronolog config set storage.streaming_threshold_mb 10

# Exclude large files
echo "*.iso" >> .chronolog_ignore
echo "*.dmg" >> .chronolog_ignore
echo "*.exe" >> .chronolog_ignore

# Compress storage
chronolog optimize storage --compress
```

### Database Performance

**Symptoms:**
- Slow queries
- Database growing too large
- Long startup times

**Solution:**
```bash
# Analyze database
chronolog optimize analyze --database

# Vacuum database
chronolog optimize gc --vacuum

# Rebuild indexes
chronolog optimize gc --rebuild-index

# Archive old data
chronolog export --before "2023-01-01" --output archive.zip

# Configure database settings
chronolog config set database.cache_size_mb 64
chronolog config set database.temp_store memory
```

## Web Interface Problems

### Server Won't Start

**Symptoms:**
- `Address already in use`
- Web server fails to start
- Connection refused errors

**Solution:**
```bash
# Check port usage
netstat -tlnp | grep :5000
lsof -i :5000  # macOS/Linux

# Kill existing process
sudo kill -9 $(lsof -t -i:5000)

# Start on different port
chronolog web start --port 8080

# Check firewall settings
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-ports  # CentOS/RHEL
```

### Authentication Issues

**Symptoms:**
- Login fails with correct credentials
- "Invalid token" errors
- Sessions expire immediately

**Solution:**
```bash
# Check user exists
chronolog users list

# Reset password
chronolog users update username --password

# Check token settings
chronolog config show authentication

# Clear expired tokens
chronolog auth logout --all

# Regenerate secret key
chronolog config set web.secret_key $(openssl rand -hex 32)
```

### API Errors

**Symptoms:**
- 500 Internal Server Error
- API endpoints not responding
- CORS errors

**Solution:**
```bash
# Check web server logs
tail -f .chronolog/logs/web.log

# Test API health
curl http://localhost:5000/api/v1/health

# Enable debug mode
chronolog web start --debug

# Fix CORS issues
chronolog config set web.cors_origins "*"

# Restart web server
chronolog web stop
chronolog web start
```

## Database Issues

### Corruption Detection

**Symptoms:**
- "database disk image is malformed"
- Inconsistent data
- Operations fail randomly

**Diagnosis:**
```bash
# Check database integrity
sqlite3 .chronolog/database.db "PRAGMA integrity_check;"

# Check for corruption
chronolog optimize verify

# Analyze database
sqlite3 .chronolog/database.db ".schema"
```

**Recovery:**
```bash
# Backup corrupted database
cp .chronolog/database.db .chronolog/database.db.corrupted

# Try to recover
sqlite3 .chronolog/database.db ".recover" | sqlite3 .chronolog/database_recovered.db

# If recovery works, replace database
mv .chronolog/database.db .chronolog/database.db.old
mv .chronolog/database_recovered.db .chronolog/database.db

# Restart daemon
chronolog daemon restart
```

### Migration Issues

**Symptoms:**
- "database schema version mismatch"
- Missing tables or columns
- Migration fails

**Solution:**
```bash
# Check schema version
chronolog config show database.schema_version

# Force migration
chronolog migrate --force

# If migration fails, backup and reinitialize
cp .chronolog/database.db database_backup.db
rm .chronolog/database.db
chronolog init
# Then restore data from backup if possible
```

## Daemon Problems

### Daemon Won't Start

**Symptoms:**
- Process exits immediately
- No PID file created
- No log entries

**Diagnosis:**
```bash
# Check daemon logs
tail -f .chronolog/logs/daemon.log

# Check permissions
ls -la .chronolog/

# Verify Python path
which python
python -c "import chronolog; print('OK')"
```

**Solutions:**
```bash
# Fix permissions
chmod 755 .chronolog/
chmod 644 .chronolog/config.json

# Clear stale PID file
rm -f .chronolog/daemon.pid

# Start in foreground for debugging
python -m chronolog.daemon.main --foreground

# Check system limits
ulimit -a
```

### File Watching Not Working

**Symptoms:**
- Files not automatically versioned
- Changes not detected
- Daemon running but inactive

**Solution:**
```bash
# Check watched directories
chronolog daemon status --verbose

# Test file watching
touch test_file.txt
sleep 2
chronolog log test_file.txt

# Check ignore patterns
cat .chronolog_ignore

# Restart with debugging
chronolog daemon stop
chronolog daemon start --debug
```

### High Resource Usage

**Symptoms:**
- High CPU usage
- Excessive memory consumption
- System slowdown

**Solution:**
```bash
# Check daemon resource usage
ps aux | grep chronolog
top -p $(pgrep chronolog)

# Reduce watch frequency
chronolog config set daemon.watch_interval 5.0

# Add more ignore patterns
echo "*.log" >> .chronolog_ignore
echo "*~" >> .chronolog_ignore
echo ".DS_Store" >> .chronolog_ignore

# Limit watched file types
chronolog config set daemon.watch_extensions "py,js,html,css"

# Restart daemon
chronolog daemon restart
```

## User Management Issues

### Cannot Create Admin User

**Symptoms:**
- "Admin user already exists"
- Permission denied creating users
- Authentication system not initialized

**Solution:**
```bash
# Check existing users
chronolog users list

# Reset user system (DANGER: loses all users)
rm .chronolog/database.db
chronolog init
chronolog users create-admin admin

# Or reset specific tables
sqlite3 .chronolog/database.db "DELETE FROM users WHERE role='admin';"
chronolog users create-admin admin
```

### Permission Errors

**Symptoms:**
- "Insufficient permissions"
- Users cannot access resources
- API returns 403 Forbidden

**Solution:**
```bash
# Check user permissions
chronolog users info username --permissions

# Grant necessary permissions
chronolog users permissions grant username files "*" read
chronolog users permissions grant username repository "*" write

# Check permission system
chronolog config show authentication

# Reset permissions (if needed)
chronolog users permissions reset username
```

### Token Issues

**Symptoms:**
- "Invalid or expired token"
- Frequent re-authentication required
- API authentication fails

**Solution:**
```bash
# Check token expiration
chronolog auth info

# Create new token
chronolog auth logout
chronolog auth login username

# Check JWT secret
chronolog config show authentication.jwt_secret

# If secret changed, invalidate all tokens
chronolog auth logout --all
```

## Diagnostic Tools

### Health Check Script

Create a comprehensive health check:

```bash
#!/bin/bash
# health_check.sh

echo "ChronoLog Health Check"
echo "====================="

# Basic system info
echo "Python version: $(python --version)"
echo "ChronoLog version: $(chronolog --version)"

# Repository status
if [ -d ".chronolog" ]; then
    echo "Repository: Initialized"
    echo "Config: $(test -f .chronolog/config.json && echo 'Present' || echo 'Missing')"
    echo "Database: $(test -f .chronolog/database.db && echo 'Present' || echo 'Missing')"
else
    echo "Repository: Not initialized"
    exit 1
fi

# Daemon status
daemon_status=$(chronolog daemon status 2>/dev/null)
echo "Daemon: $daemon_status"

# Database integrity
echo -n "Database integrity: "
if chronolog optimize verify --quiet >/dev/null 2>&1; then
    echo "OK"
else
    echo "ISSUES FOUND"
fi

# Storage stats
storage_stats=$(chronolog analytics stats --format json 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "Storage: OK"
else
    echo "Storage: Cannot read stats"
fi

# Web server
if curl -s http://localhost:5000/api/v1/health >/dev/null 2>&1; then
    echo "Web server: Running"
else
    echo "Web server: Not running"
fi

echo "Health check complete"
```

### Debug Information Collection

```bash
#!/bin/bash
# collect_debug_info.sh

DEBUG_DIR="chronolog_debug_$(date +%Y%m%d_%H%M%S)"
mkdir "$DEBUG_DIR"

echo "Collecting debug information..."

# System information
python --version > "$DEBUG_DIR/python_version.txt"
pip list > "$DEBUG_DIR/pip_packages.txt"
uname -a > "$DEBUG_DIR/system_info.txt"

# ChronoLog information
chronolog --version > "$DEBUG_DIR/chronolog_version.txt"
chronolog status > "$DEBUG_DIR/repository_status.txt" 2>&1
chronolog daemon status > "$DEBUG_DIR/daemon_status.txt" 2>&1
chronolog config show > "$DEBUG_DIR/config.txt" 2>&1

# Log files
if [ -d ".chronolog/logs" ]; then
    cp .chronolog/logs/* "$DEBUG_DIR/"
fi

# Configuration
if [ -f ".chronolog/config.json" ]; then
    cp .chronolog/config.json "$DEBUG_DIR/"
fi

# Database info
if [ -f ".chronolog/database.db" ]; then
    sqlite3 .chronolog/database.db ".schema" > "$DEBUG_DIR/database_schema.sql"
    sqlite3 .chronolog/database.db "SELECT COUNT(*) as version_count FROM versions;" > "$DEBUG_DIR/database_stats.txt"
fi

# Process information
ps aux | grep chronolog > "$DEBUG_DIR/processes.txt"

# Network information (for web server)
netstat -tlnp | grep :5000 > "$DEBUG_DIR/network.txt" 2>/dev/null || \
lsof -i :5000 > "$DEBUG_DIR/network.txt" 2>/dev/null

echo "Debug information collected in $DEBUG_DIR/"
echo "Please include this directory when reporting issues"
```

### Performance Profiling

```bash
# Profile ChronoLog operations
chronolog analytics metrics --performance > performance_report.txt

# Monitor resource usage
top -p $(pgrep chronolog) -n 5 > resource_usage.txt

# Profile specific operations
time chronolog log --limit 100
time chronolog analytics stats
time chronolog optimize analyze
```

## Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide**
2. **Run the health check script**
3. **Collect debug information**
4. **Check logs for error messages**
5. **Try to reproduce the issue**

### Reporting Issues

When reporting issues, please include:

1. **System Information:**
   - Operating system and version
   - Python version
   - ChronoLog version

2. **Problem Description:**
   - What you were trying to do
   - What happened instead
   - Error messages (exact text)

3. **Debug Information:**
   - Configuration files
   - Log files
   - Health check results

4. **Steps to Reproduce:**
   - Minimal example that reproduces the issue
   - Command line invocations used

### Getting Support

- **Documentation**: Check the User Guide and API Reference
- **GitHub Issues**: Report bugs and request features
- **Community Discussions**: Ask questions and share solutions
- **Debug Mode**: Run commands with `--verbose` or `--debug` flags

### Emergency Recovery

If ChronoLog is completely broken:

```bash
# Backup your data
cp -r .chronolog .chronolog_backup

# Reset to factory defaults
rm -rf .chronolog
chronolog init

# Try to restore from backup
# (Manual process - depends on what's corrupted)
```

Remember: Always backup your repository before attempting major fixes!