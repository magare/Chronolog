# ChronoLog CLI Reference

Complete command-line interface reference for all ChronoLog commands and options.

## Table of Contents

1. [Global Options](#global-options)
2. [Core Commands](#core-commands)
3. [Analytics Commands](#analytics-commands)
4. [Storage Commands](#storage-commands)
5. [User Management](#user-management)
6. [Merge Commands](#merge-commands)
7. [Web Server](#web-server)
8. [Hooks System](#hooks-system)
9. [Configuration](#configuration)
10. [Examples](#examples)

## Global Options

These options are available for all commands:

```bash
chronolog [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### Global Options

- `--help`, `-h`: Show help message and exit
- `--version`: Show version information
- `--verbose`, `-v`: Enable verbose output
- `--quiet`, `-q`: Suppress non-error output
- `--config FILE`: Use custom configuration file
- `--repo-path PATH`: Specify repository path (default: current directory)
- `--no-daemon`: Disable daemon operations
- `--format FORMAT`: Output format (text, json, yaml)

### Environment Variables

```bash
export CHRONOLOG_REPO_PATH=/path/to/repo     # Default repository path
export CHRONOLOG_CONFIG_FILE=config.json    # Configuration file
export CHRONOLOG_LOG_LEVEL=INFO            # Logging level
export CHRONOLOG_NO_DAEMON=1               # Disable daemon
```

## Core Commands

### `chronolog init`

Initialize a new ChronoLog repository.

```bash
chronolog init [OPTIONS] [PATH]
```

**Options:**
- `--force`, `-f`: Force initialization even if directory exists
- `--bare`: Create bare repository (no working directory)
- `--template DIR`: Use template directory for initialization
- `--config FILE`: Use specific configuration file

**Examples:**
```bash
# Initialize in current directory
chronolog init

# Initialize in specific directory
chronolog init /path/to/project

# Force initialization
chronolog init --force

# Initialize with custom config
chronolog init --config my_config.json
```

### `chronolog status`

Show repository status and file information.

```bash
chronolog status [OPTIONS] [FILES...]
```

**Options:**
- `--all`, `-a`: Show all files, including ignored
- `--short`, `-s`: Show short status format
- `--porcelain`: Machine-readable output
- `--ignored`: Show only ignored files
- `--modified`: Show only modified files

**Examples:**
```bash
# Show overall status
chronolog status

# Show specific files
chronolog status file1.py file2.py

# Show all files including ignored
chronolog status --all

# Machine-readable output
chronolog status --porcelain
```

### `chronolog log`

Display version history.

```bash
chronolog log [OPTIONS] [FILE_PATH]
```

**Options:**
- `--limit N`, `-n N`: Limit number of entries (default: 50)
- `--since DATE`: Show versions since date
- `--until DATE`: Show versions until date
- `--author USER`: Filter by author
- `--oneline`: Show condensed one-line format
- `--graph`: Show ASCII art commit graph
- `--all`: Show all branches/files
- `--format FORMAT`: Custom output format

**Examples:**
```bash
# Show all version history
chronolog log

# Show history for specific file
chronolog log src/main.py

# Show last 10 versions
chronolog log --limit 10

# Show versions since yesterday
chronolog log --since yesterday

# One-line format
chronolog log --oneline

# Show graph
chronolog log --graph
```

### `chronolog show`

Display version content and metadata.

```bash
chronolog show [OPTIONS] VERSION_HASH
```

**Options:**
- `--file FILE`: Show specific file from version
- `--metadata`: Show only metadata, not content
- `--raw`: Show raw content without formatting
- `--binary`: Force display of binary content
- `--encoding ENC`: Specify text encoding

**Examples:**
```bash
# Show version content
chronolog show abc12345

# Show metadata only
chronolog show --metadata abc12345

# Show specific file from version
chronolog show --file src/main.py abc12345

# Raw output
chronolog show --raw abc12345
```

### `chronolog diff`

Compare versions or files.

```bash
chronolog diff [OPTIONS] [VERSION1] [VERSION2]
chronolog diff [OPTIONS] VERSION --current
```

**Options:**
- `--unified N`, `-u N`: Unified diff with N context lines
- `--side-by-side`, `-y`: Side-by-side diff format
- `--ignore-whitespace`, `-w`: Ignore whitespace changes
- `--ignore-case`, `-i`: Ignore case changes
- `--color WHEN`: Color output (always, never, auto)
- `--word-diff`: Show word-level differences
- `--stat`: Show diffstat summary

**Examples:**
```bash
# Compare two versions
chronolog diff abc12345 def67890

# Compare version with current file
chronolog diff abc12345 --current

# Side-by-side diff
chronolog diff --side-by-side abc12345 def67890

# Ignore whitespace
chronolog diff --ignore-whitespace abc12345 def67890

# Show statistics
chronolog diff --stat abc12345 def67890
```

### `chronolog checkout`

Restore files to specific versions.

```bash
chronolog checkout [OPTIONS] VERSION_HASH [FILES...]
```

**Options:**
- `--force`, `-f`: Force checkout, overwriting local changes
- `--backup`: Create backup before checkout
- `--dry-run`: Show what would be checked out
- `--all`: Checkout all files from version

**Examples:**
```bash
# Checkout specific file
chronolog checkout abc12345 src/main.py

# Checkout multiple files
chronolog checkout abc12345 src/main.py src/utils.py

# Force checkout with backup
chronolog checkout --force --backup abc12345 src/main.py

# Dry run
chronolog checkout --dry-run abc12345 src/main.py
```

### `chronolog daemon`

Manage background daemon process.

```bash
chronolog daemon [start|stop|status|restart]
```

**Subcommands:**
- `start`: Start the daemon
- `stop`: Stop the daemon
- `status`: Show daemon status
- `restart`: Restart the daemon

**Examples:**
```bash
# Start daemon
chronolog daemon start

# Check status
chronolog daemon status

# Stop daemon
chronolog daemon stop

# Restart daemon
chronolog daemon restart
```

## Analytics Commands

### `chronolog analytics`

Analytics and performance metrics.

```bash
chronolog analytics COMMAND [OPTIONS]
```

#### `chronolog analytics stats`

Show repository statistics.

```bash
chronolog analytics stats [OPTIONS]
```

**Options:**
- `--format FORMAT`: Output format (text, json, csv)
- `--period PERIOD`: Time period (day, week, month, year, all)
- `--output FILE`: Save output to file
- `--trends`: Show historical trends

**Examples:**
```bash
# Basic stats
chronolog analytics stats

# JSON format
chronolog analytics stats --format json

# Weekly stats
chronolog analytics stats --period week

# Show trends
chronolog analytics stats --trends
```

#### `chronolog analytics metrics`

Show performance metrics.

```bash
chronolog analytics metrics [OPTIONS]
```

**Options:**
- `--storage`: Show storage metrics
- `--daemon`: Show daemon performance
- `--api`: Show API performance
- `--live`: Show live updating metrics

**Examples:**
```bash
# All metrics
chronolog analytics metrics

# Storage metrics only
chronolog analytics metrics --storage

# Live metrics
chronolog analytics metrics --live
```

#### `chronolog analytics visualize`

Generate visualizations.

```bash
chronolog analytics visualize [OPTIONS]
```

**Options:**
- `--type TYPE`: Chart type (timeline, heatmap, pie, bar)
- `--output FILE`: Output file path
- `--size WxH`: Chart size (e.g., 800x600)
- `--theme THEME`: Chart theme

**Examples:**
```bash
# Generate timeline
chronolog analytics visualize --type timeline

# Save to file
chronolog analytics visualize --output chart.png

# Custom size
chronolog analytics visualize --size 1200x800
```

### `chronolog metrics`

Code and developer metrics.

```bash
chronolog metrics COMMAND [OPTIONS]
```

#### `chronolog metrics code`

Analyze code complexity and quality.

```bash
chronolog metrics code [OPTIONS] [FILES...]
```

**Options:**
- `--complexity`: Show complexity metrics
- `--languages`: Show language statistics
- `--files PATTERN`: File pattern to analyze
- `--output FILE`: Save report to file

**Examples:**
```bash
# Analyze all code
chronolog metrics code

# Specific files
chronolog metrics code src/*.py

# Complexity analysis
chronolog metrics code --complexity

# Language stats
chronolog metrics code --languages
```

#### `chronolog metrics complexity`

Detailed complexity analysis.

```bash
chronolog metrics complexity [OPTIONS] [FILES...]
```

**Options:**
- `--threshold N`: Complexity threshold for warnings
- `--functions`: Show function-level complexity
- `--classes`: Show class-level complexity
- `--report FORMAT`: Report format (text, json, html)

**Examples:**
```bash
# Basic complexity
chronolog metrics complexity

# With threshold
chronolog metrics complexity --threshold 10

# HTML report
chronolog metrics complexity --report html
```

## Storage Commands

### `chronolog optimize`

Storage optimization and maintenance.

```bash
chronolog optimize COMMAND [OPTIONS]
```

#### `chronolog optimize analyze`

Analyze storage usage and opportunities.

```bash
chronolog optimize analyze [OPTIONS]
```

**Options:**
- `--recommendations`: Show optimization recommendations
- `--details`: Show detailed analysis
- `--format FORMAT`: Output format

**Examples:**
```bash
# Basic analysis
chronolog optimize analyze

# With recommendations
chronolog optimize analyze --recommendations

# JSON output
chronolog optimize analyze --format json
```

#### `chronolog optimize storage`

Optimize repository storage.

```bash
chronolog optimize storage [OPTIONS]
```

**Options:**
- `--compress`: Enable compression
- `--deduplicate`: Enable deduplication
- `--level N`: Compression level (1-9)
- `--dry-run`: Show what would be optimized

**Examples:**
```bash
# Full optimization
chronolog optimize storage

# Compression only
chronolog optimize storage --compress

# Dry run
chronolog optimize storage --dry-run
```

#### `chronolog optimize gc`

Run garbage collection.

```bash
chronolog optimize gc [OPTIONS]
```

**Options:**
- `--aggressive`: Aggressive garbage collection
- `--verify`: Verify integrity after cleanup
- `--dry-run`: Show what would be cleaned

**Examples:**
```bash
# Standard garbage collection
chronolog optimize gc

# Aggressive cleanup
chronolog optimize gc --aggressive

# Dry run
chronolog optimize gc --dry-run
```

## User Management

### `chronolog users`

User management commands.

```bash
chronolog users COMMAND [OPTIONS]
```

#### `chronolog users list`

List all users.

```bash
chronolog users list [OPTIONS]
```

**Options:**
- `--role ROLE`: Filter by role
- `--active`: Show only active users
- `--inactive`: Show only inactive users
- `--format FORMAT`: Output format

**Examples:**
```bash
# List all users
chronolog users list

# Active users only
chronolog users list --active

# Admins only
chronolog users list --role admin
```

#### `chronolog users create`

Create new user.

```bash
chronolog users create [OPTIONS] USERNAME
```

**Options:**
- `--email EMAIL`: User email address
- `--password PASSWORD`: User password (will prompt if not provided)
- `--role ROLE`: User role (user, admin, developer)
- `--full-name NAME`: Full name

**Examples:**
```bash
# Create user (will prompt for password)
chronolog users create john_doe

# Create with email
chronolog users create --email john@example.com john_doe

# Create admin user
chronolog users create --role admin admin_user
```

#### `chronolog users info`

Show user information.

```bash
chronolog users info [OPTIONS] USERNAME
```

**Options:**
- `--permissions`: Show user permissions
- `--sessions`: Show active sessions
- `--activity`: Show recent activity

**Examples:**
```bash
# Basic user info
chronolog users info john_doe

# With permissions
chronolog users info --permissions john_doe

# With activity
chronolog users info --activity john_doe
```

#### `chronolog users permissions`

Manage user permissions.

```bash
chronolog users permissions COMMAND [OPTIONS]
```

**Grant permissions:**
```bash
chronolog users permissions grant USERNAME RESOURCE_TYPE RESOURCE_ID LEVEL
```

**Revoke permissions:**
```bash
chronolog users permissions revoke USERNAME RESOURCE_TYPE RESOURCE_ID
```

**Examples:**
```bash
# Grant file read permission
chronolog users permissions grant john_doe files "*.py" read

# Grant repository admin
chronolog users permissions grant admin_user repository "*" admin

# Revoke permission
chronolog users permissions revoke john_doe files "test.txt"
```

### `chronolog auth`

Authentication commands.

```bash
chronolog auth COMMAND [OPTIONS]
```

#### `chronolog auth login`

Login and create session.

```bash
chronolog auth login [OPTIONS] [USERNAME]
```

**Options:**
- `--password PASSWORD`: Password (will prompt if not provided)
- `--api-key`: Login with API key instead
- `--expires DURATION`: Token expiration duration

**Examples:**
```bash
# Interactive login
chronolog auth login

# Login specific user
chronolog auth login john_doe

# API key login
chronolog auth login --api-key
```

#### `chronolog auth logout`

Logout and invalidate session.

```bash
chronolog auth logout [OPTIONS]
```

**Options:**
- `--all`: Logout from all sessions

**Examples:**
```bash
# Logout current session
chronolog auth logout

# Logout all sessions
chronolog auth logout --all
```

## Merge Commands

### `chronolog merge`

Merge operations and conflict resolution.

```bash
chronolog merge COMMAND [OPTIONS]
```

#### `chronolog merge preview`

Preview merge operation.

```bash
chronolog merge preview [OPTIONS] BASE_HASH OUR_HASH THEIR_HASH
```

**Options:**
- `--strategy STRATEGY`: Merge strategy (auto, ours, theirs)
- `--format FORMAT`: Output format
- `--conflicts-only`: Show only conflicts

**Examples:**
```bash
# Preview merge
chronolog merge preview base123 ours456 theirs789

# Show only conflicts
chronolog merge preview --conflicts-only base123 ours456 theirs789
```

#### `chronolog merge execute`

Execute merge operation.

```bash
chronolog merge execute [OPTIONS] BASE_HASH OUR_HASH THEIR_HASH
```

**Options:**
- `--strategy STRATEGY`: Merge strategy
- `--message MESSAGE`: Merge commit message
- `--no-commit`: Don't create merge commit

**Examples:**
```bash
# Execute merge
chronolog merge execute base123 ours456 theirs789

# Use 'ours' strategy
chronolog merge execute --strategy ours base123 ours456 theirs789

# Custom message
chronolog merge execute --message "Merge feature branch" base123 ours456 theirs789
```

#### `chronolog merge conflicts`

Show merge conflicts in file.

```bash
chronolog merge conflicts [OPTIONS] FILE_PATH
```

**Options:**
- `--context N`: Number of context lines
- `--format FORMAT`: Output format

**Examples:**
```bash
# Show conflicts
chronolog merge conflicts src/main.py

# With more context
chronolog merge conflicts --context 5 src/main.py
```

#### `chronolog merge resolve`

Resolve merge conflicts.

```bash
chronolog merge resolve [OPTIONS] FILE_PATH
```

**Options:**
- `--strategy STRATEGY`: Resolution strategy (ours, theirs, interactive)
- `--editor EDITOR`: Editor for interactive resolution

**Examples:**
```bash
# Interactive resolution
chronolog merge resolve src/main.py

# Use 'ours' strategy
chronolog merge resolve --strategy ours src/main.py

# Use specific editor
chronolog merge resolve --editor vim src/main.py
```

## Web Server

### `chronolog web`

Web server management.

```bash
chronolog web COMMAND [OPTIONS]
```

#### `chronolog web start`

Start web server.

```bash
chronolog web start [OPTIONS]
```

**Options:**
- `--host HOST`: Server host (default: localhost)
- `--port PORT`: Server port (default: 5000)
- `--daemon`, `-d`: Run in background
- `--debug`: Enable debug mode
- `--ssl-cert FILE`: SSL certificate file
- `--ssl-key FILE`: SSL private key file

**Examples:**
```bash
# Start on default port
chronolog web start

# Custom host and port
chronolog web start --host 0.0.0.0 --port 8080

# Background daemon
chronolog web start --daemon

# With SSL
chronolog web start --ssl-cert cert.pem --ssl-key key.pem
```

#### `chronolog web stop`

Stop web server.

```bash
chronolog web stop [OPTIONS]
```

**Examples:**
```bash
# Stop web server
chronolog web stop
```

#### `chronolog web status`

Show web server status.

```bash
chronolog web status [OPTIONS]
```

**Options:**
- `--health`: Show health check information
- `--stats`: Show server statistics

**Examples:**
```bash
# Basic status
chronolog web status

# With health info
chronolog web status --health

# With statistics
chronolog web status --stats
```

## Hooks System

### `chronolog hooks`

Hook management commands.

```bash
chronolog hooks COMMAND [OPTIONS]
```

#### `chronolog hooks list`

List installed hooks.

```bash
chronolog hooks list [OPTIONS]
```

**Options:**
- `--type TYPE`: Filter by hook type (pre-version, post-version, etc.)
- `--enabled`: Show only enabled hooks
- `--disabled`: Show only disabled hooks

**Examples:**
```bash
# List all hooks
chronolog hooks list

# Pre-version hooks only
chronolog hooks list --type pre-version

# Enabled hooks only
chronolog hooks list --enabled
```

#### `chronolog hooks install`

Install hook script.

```bash
chronolog hooks install [OPTIONS] HOOK_TYPE SCRIPT_PATH
```

**Options:**
- `--name NAME`: Hook name
- `--priority N`: Hook priority (execution order)
- `--enabled`: Enable hook after installation

**Examples:**
```bash
# Install pre-version hook
chronolog hooks install pre-version ./my_hook.py

# Install with custom name
chronolog hooks install --name "lint-check" pre-version ./lint.py

# Install and enable
chronolog hooks install --enabled post-version ./notify.py
```

#### `chronolog hooks remove`

Remove installed hook.

```bash
chronolog hooks remove [OPTIONS] HOOK_NAME
```

**Examples:**
```bash
# Remove hook
chronolog hooks remove my-hook

# Remove all pre-version hooks
chronolog hooks remove --type pre-version --all
```

#### `chronolog hooks test`

Test hook execution.

```bash
chronolog hooks test [OPTIONS] HOOK_NAME
```

**Options:**
- `--context CONTEXT`: Test context (JSON string or file)
- `--verbose`: Show detailed output

**Examples:**
```bash
# Test hook
chronolog hooks test my-hook

# Test with context
chronolog hooks test --context '{"file_path": "test.py"}' my-hook

# Verbose output
chronolog hooks test --verbose my-hook
```

## Configuration

### `chronolog config`

Configuration management.

```bash
chronolog config COMMAND [OPTIONS]
```

#### `chronolog config show`

Show current configuration.

```bash
chronolog config show [OPTIONS] [KEY]
```

**Options:**
- `--format FORMAT`: Output format (text, json, yaml)
- `--global`: Show global configuration
- `--local`: Show local repository configuration

**Examples:**
```bash
# Show all configuration
chronolog config show

# Show specific key
chronolog config show daemon.watch_interval

# JSON format
chronolog config show --format json
```

#### `chronolog config set`

Set configuration value.

```bash
chronolog config set [OPTIONS] KEY VALUE
```

**Options:**
- `--global`: Set global configuration
- `--local`: Set local repository configuration
- `--type TYPE`: Value type (string, int, float, bool)

**Examples:**
```bash
# Set string value
chronolog config set user.name "John Doe"

# Set integer value
chronolog config set --type int daemon.watch_interval 5

# Set boolean value
chronolog config set --type bool web.debug true
```

#### `chronolog config reset`

Reset configuration to defaults.

```bash
chronolog config reset [OPTIONS] [KEY]
```

**Options:**
- `--global`: Reset global configuration
- `--local`: Reset local configuration
- `--all`: Reset all configuration

**Examples:**
```bash
# Reset specific key
chronolog config reset daemon.watch_interval

# Reset all local config
chronolog config reset --local --all

# Reset global config
chronolog config reset --global --all
```

## Examples

### Basic Workflow

```bash
# Initialize repository
chronolog init

# Check status
chronolog status

# View history
chronolog log

# Compare versions
chronolog diff abc123 def456

# Checkout previous version
chronolog checkout abc123 file.txt
```

### Analytics Workflow

```bash
# Repository statistics
chronolog analytics stats

# Performance metrics
chronolog analytics metrics --storage

# Generate visualization
chronolog analytics visualize --type timeline --output timeline.png

# Code analysis
chronolog metrics code --complexity
```

### User Management Workflow

```bash
# Create admin user
chronolog users create --role admin --email admin@example.com admin_user

# Login
chronolog auth login admin_user

# Grant permissions
chronolog users permissions grant dev_user files "*.py" write

# Check permissions
chronolog users info --permissions dev_user
```

### Web Interface Workflow

```bash
# Start web server
chronolog web start --host 0.0.0.0 --port 8080

# Check status
chronolog web status --health

# Access web interface at http://localhost:8080

# Stop server
chronolog web stop
```

### Merge Workflow

```bash
# Preview merge
chronolog merge preview base123 ours456 theirs789

# Execute merge
chronolog merge execute --strategy auto base123 ours456 theirs789

# Resolve conflicts
chronolog merge conflicts src/main.py
chronolog merge resolve --strategy interactive src/main.py
```

### Optimization Workflow

```bash
# Analyze storage
chronolog optimize analyze --recommendations

# Optimize storage
chronolog optimize storage --compress --deduplicate

# Run garbage collection
chronolog optimize gc --verify

# Check results
chronolog analytics stats
```

For more detailed information on specific commands, use `chronolog COMMAND --help`.