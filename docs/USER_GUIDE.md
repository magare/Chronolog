# ChronoLog User Guide

A comprehensive guide to using ChronoLog for version control, analytics, user management, and collaboration.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Version Control](#core-version-control)
3. [Analytics and Metrics](#analytics-and-metrics)
4. [Storage Management](#storage-management)
5. [User Management](#user-management)
6. [Merge Operations](#merge-operations)
7. [Web Interface](#web-interface)
8. [Hooks and Automation](#hooks-and-automation)
9. [Advanced Features](#advanced-features)
10. [Best Practices](#best-practices)

## Getting Started

### Installation

#### Core ChronoLog
```bash
# Development installation
pip install -e .

# Production installation (when available)
pip install chronolog
```

#### Terminal User Interface (Optional)
```bash
cd chronolog-tui
pip install -e .
```

### Initializing a Repository

```bash
# Initialize in current directory
chronolog init

# Initialize with custom settings
chronolog init --config-file custom_config.json
```

### Basic Configuration

ChronoLog automatically creates a `.chronolog` directory with:
- `database.db` - SQLite database for metadata
- `storage/` - Content-addressable storage for file versions
- `config.json` - Repository configuration
- `hooks/` - Custom hooks directory

## Core Version Control

### Automatic Versioning

ChronoLog automatically tracks file changes when the daemon is running:

```bash
# Start the daemon
chronolog daemon start

# Check daemon status
chronolog daemon status

# Stop the daemon
chronolog daemon stop
```

### Viewing History

```bash
# View all file history
chronolog log

# View history for specific file
chronolog log myfile.txt

# View with detailed output
chronolog log --verbose myfile.txt

# Limit number of entries
chronolog log --limit 10 myfile.txt
```

### Examining Versions

```bash
# Show content of a specific version
chronolog show abc12345

# Show version metadata
chronolog show --metadata abc12345

# Show version with file path
chronolog show abc12345 --file myfile.txt
```

### Comparing Versions

```bash
# Compare two versions
chronolog diff abc12345 def67890

# Compare version with current file
chronolog diff abc12345 --current

# Show unified diff format
chronolog diff --unified abc12345 def67890

# Show side-by-side diff
chronolog diff --side-by-side abc12345 def67890
```

### Reverting Files

```bash
# Revert file to specific version
chronolog checkout abc12345 myfile.txt

# Revert multiple files
chronolog checkout abc12345 file1.txt file2.txt

# Revert with confirmation
chronolog checkout --confirm abc12345 myfile.txt
```

### Repository Status

```bash
# Show repository status
chronolog status

# Show detailed status
chronolog status --verbose

# Show file-specific status
chronolog status myfile.txt
```

## Analytics and Metrics

### Repository Statistics

```bash
# Show basic repository stats
chronolog analytics stats

# Export stats to JSON
chronolog analytics stats --format json

# Show historical trends
chronolog analytics stats --trends
```

### Performance Metrics

```bash
# Show performance metrics
chronolog analytics metrics

# Show storage performance
chronolog analytics metrics --storage

# Show daemon performance
chronolog analytics metrics --daemon
```

### Code Metrics

```bash
# Analyze code complexity
chronolog metrics code

# Show language statistics
chronolog metrics languages

# Analyze specific files
chronolog metrics code --files "*.py"

# Generate complexity report
chronolog metrics complexity --output report.json
```

### Visualizations

```bash
# Generate activity visualization
chronolog analytics visualize

# Create timeline chart
chronolog analytics visualize --type timeline

# Export visualization
chronolog analytics visualize --output chart.png
```

## Storage Management

### Storage Optimization

```bash
# Analyze storage usage
chronolog optimize analyze

# Optimize storage
chronolog optimize storage

# Compress repository data
chronolog optimize compress

# Show optimization recommendations
chronolog optimize recommendations
```

### Garbage Collection

```bash
# Run garbage collection
chronolog optimize gc

# Show what would be cleaned
chronolog optimize gc --dry-run

# Verify database integrity
chronolog optimize verify

# Clean temporary files
chronolog optimize clean-temp
```

### Storage Statistics

```bash
# Show storage usage
chronolog optimize stats

# Show file size distribution
chronolog optimize stats --distribution

# Identify large files
chronolog optimize stats --largest
```

## User Management

### Creating Users

```bash
# Create admin user
chronolog users create-admin admin_user

# Create regular user
chronolog users create regular_user

# Create user with specific role
chronolog users create dev_user --role developer
```

### Managing Users

```bash
# List all users
chronolog users list

# Show user information
chronolog users info username

# Update user details
chronolog users update username --email new@email.com

# Deactivate user
chronolog users deactivate username
```

### Permissions

```bash
# Show user permissions
chronolog users permissions username

# Grant file permissions
chronolog users grant username files "*.py" read

# Grant repository admin
chronolog users grant username repository "*" admin

# Revoke permissions
chronolog users revoke username files "test.txt"
```

### Authentication

```bash
# Login (creates session token)
chronolog auth login username

# Logout (invalidates token)
chronolog auth logout

# Create API key
chronolog auth create-api-key "My API Key"

# List active sessions
chronolog auth sessions
```

## Merge Operations

### Three-Way Merge

```bash
# Preview merge operation
chronolog merge preview base_hash our_hash their_hash

# Execute merge
chronolog merge execute base_hash our_hash their_hash

# Merge with strategy
chronolog merge execute base_hash our_hash their_hash --strategy ours
```

### Conflict Resolution

```bash
# Show conflicts in file
chronolog merge conflicts conflicted_file.txt

# Resolve conflicts automatically
chronolog merge resolve conflicted_file.txt --strategy theirs

# Interactive conflict resolution
chronolog merge resolve conflicted_file.txt --interactive

# Mark conflicts as resolved
chronolog merge resolved conflicted_file.txt
```

### Merge Strategies

Available merge strategies:
- `auto` - Automatic resolution where possible
- `ours` - Use our version for conflicts
- `theirs` - Use their version for conflicts
- `interactive` - Manual conflict resolution

## Web Interface

### Starting Web Server

```bash
# Start on default port (5000)
chronolog web start

# Start on custom port
chronolog web start --port 8080

# Start with specific host
chronolog web start --host 0.0.0.0 --port 8080

# Start in background
chronolog web start --daemon
```

### Web Features

Access the web interface at `http://localhost:5000` (or your configured port):

- **Dashboard**: Repository overview and quick stats
- **History Browser**: Visual timeline of all versions
- **File Browser**: Navigate repository files and directories
- **Diff Viewer**: Side-by-side version comparisons
- **User Management**: Admin interface for users and permissions
- **Analytics**: Interactive charts and metrics
- **Merge Center**: Conflict resolution interface
- **Settings**: Configuration management

### API Usage

#### REST API Examples

```bash
# Get repository status
curl http://localhost:5000/api/v1/repository/status

# List versions with pagination
curl "http://localhost:5000/api/v1/versions?limit=10&offset=0"

# Create new version
curl -X POST http://localhost:5000/api/v1/versions \
  -H "Content-Type: application/json" \
  -d '{"message": "Manual version", "description": "Created via API"}'

# Get analytics data
curl http://localhost:5000/api/v1/analytics/stats
```

#### GraphQL API Examples

```graphql
# Query versions
{
  versions(limit: 10) {
    id
    hash
    timestamp
    message
    author
  }
}

# Query user information
{
  user(id: "user123") {
    username
    email
    role
    permissions {
      resourceType
      resourceId
      level
    }
  }
}

# Mutation: Create user
mutation {
  createUser(input: {
    username: "newuser"
    email: "new@example.com"
    password: "password123"
  }) {
    user {
      id
      username
    }
    success
  }
}
```

## Hooks and Automation

### Installing Hooks

```bash
# List available hooks
chronolog hooks list

# Install pre-version hook
chronolog hooks install pre-version my_hook.py

# Install post-version hook
chronolog hooks install post-version notify.py

# Test hook execution
chronolog hooks test pre-version my_hook.py
```

### Writing Custom Hooks

Create a Python script for your hook:

```python
#!/usr/bin/env python3
"""
Example pre-version hook
"""
import sys
import json

def main():
    # Hook receives context via stdin
    context = json.loads(sys.stdin.read())
    
    file_path = context['file_path']
    event_type = context['event_type']
    
    # Your custom logic here
    print(f"Processing {event_type} for {file_path}")
    
    # Return 0 for success, non-zero for failure
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Hook Types

- **pre-version**: Before creating a new version
- **post-version**: After creating a new version
- **pre-checkout**: Before checking out a version
- **post-checkout**: After checking out a version

## Advanced Features

### Configuration Management

```bash
# Show current configuration
chronolog config show

# Set configuration value
chronolog config set daemon.watch_interval 2.0

# Reset configuration
chronolog config reset

# Export configuration
chronolog config export config_backup.json
```

### Search and Query

```bash
# Search repository content
chronolog search "function main"

# Search with file filters
chronolog search "TODO" --files "*.py"

# Search version messages
chronolog search --messages "bug fix"

# Search by date range
chronolog search --after "2024-01-01" --before "2024-12-31"
```

### Export and Import

```bash
# Export repository data
chronolog export --output backup.zip

# Import repository data
chronolog import backup.zip

# Export specific file history
chronolog export --file myfile.txt --output myfile_history.json
```

### Performance Monitoring

```bash
# Monitor daemon performance
chronolog monitor daemon

# Monitor storage usage
chronolog monitor storage

# Monitor with live updates
chronolog monitor --live --interval 5
```

## Best Practices

### Repository Organization

1. **Initialize Early**: Set up ChronoLog at project start
2. **Configure Ignores**: Use `.chronolog_ignore` for temporary files
3. **Regular Optimization**: Run garbage collection periodically
4. **Monitor Storage**: Keep track of repository size

### Version Control Workflow

1. **Meaningful Messages**: Add descriptive version messages
2. **Regular Commits**: Don't let daemon create too many auto-versions
3. **Strategic Checkouts**: Test thoroughly before reverting
4. **Branch Planning**: Use different directories for major variations

### Performance Optimization

1. **Storage Management**: Run optimization monthly
2. **Daemon Tuning**: Adjust watch intervals for your workflow
3. **Index Maintenance**: Rebuild indexes if queries slow down
4. **Archive Old Data**: Export and remove old versions if needed

### Security Considerations

1. **User Permissions**: Follow principle of least privilege
2. **API Security**: Use authentication for web API access
3. **Backup Strategy**: Regular exports to secure locations
4. **Access Logging**: Monitor user activity in multi-user setups

### Troubleshooting

1. **Check Daemon**: Ensure daemon is running for auto-versioning
2. **Database Issues**: Run `chronolog optimize verify` for corruption
3. **Permission Problems**: Check file system permissions
4. **Performance Issues**: Monitor with `chronolog monitor`

For additional help, run `chronolog --help` or visit the troubleshooting guide.