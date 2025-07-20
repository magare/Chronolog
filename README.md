# ChronoLog

A frictionless, local-first version control system for creative workflows. ChronoLog can be used both as a command-line tool and as a Python library, with an optional terminal user interface (TUI) for interactive management.

## Features

- **Dual Interface**: Use as CLI tool or Python library
- **Terminal UI**: Interactive TUI for visual file management
- **Automatic Versioning**: Files are automatically versioned on save
- **Lightweight Daemon**: Background process watches for file changes
- **Content-Addressable Storage**: Efficient storage using file hashes
- **Fast Diffing**: Quick comparison between any two versions
- **Short Hash Support**: Use abbreviated hashes for convenience
- **Annotations**: Add notes to versions for better organization
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### Core ChronoLog (CLI + Library)

For development installation:

```bash
pip install -e .
```

For regular installation (when published):

```bash
pip install chronolog
```

### Terminal User Interface (Optional)

The TUI provides an interactive interface for managing your ChronoLog repositories:

```bash
cd chronolog-tui
pip install -e .
```

## Project Structure

ChronoLog consists of two main components:

- **`chronolog/`** - Core CLI and library functionality
- **`chronolog-tui/`** - Terminal user interface for interactive management

## CLI Usage

### Initialize ChronoLog in your project directory

```bash
chronolog init
```

### View version history for a file

```bash
chronolog log <file_path>
```

### Show content of a specific version

```bash
chronolog show <version_hash>
```

### Compare versions

```bash
# Compare two versions
chronolog diff <hash1> <hash2>

# Compare with current file
chronolog diff <hash1> --current
```

### Revert to a previous version

```bash
chronolog checkout <version_hash> <file_path>
```

### Manage the background daemon

```bash
# Check status
chronolog daemon status

# Stop daemon
chronolog daemon stop

# Start daemon
chronolog daemon start
```

## TUI Usage

### Starting the TUI

```bash
# Run in current directory
chronolog-tui

# Run in specific directory
chronolog-tui /path/to/project
```

### Keyboard Shortcuts

#### Dashboard

- `h` - Show file history browser
- `i` - Initialize repository (if not already initialized)
- `d` - Toggle daemon on/off
- `q` - Quit application

#### History View

- `↑/↓` - Navigate through files and versions
- `Enter` - View detailed version information
- `Escape` - Return to dashboard

#### Version Details

- `c` - Checkout the selected version
- `d` - Show diff with current file
- `Escape` - Return to history view

#### Global

- `F1` - Show help
- `Ctrl+C` - Quit application

## Library Usage

ChronoLog can also be used as a Python library in your applications:

```python
from chronolog import ChronologRepo, NotARepositoryError

# Initialize a new repository
repo = ChronologRepo.init("/path/to/project")

# Or connect to an existing repository
try:
    repo = ChronologRepo("/path/to/project")
except NotARepositoryError:
    print("Not a ChronoLog repository")

# Get file history
history = repo.log("myfile.txt")
for entry in history:
    print(f"Version {entry['hash'][:8]} at {entry['timestamp']}")
    if entry['annotation']:
        print(f"  Note: {entry['annotation']}")

# Show content of a specific version
content = repo.show("abc12345")
print(content.decode('utf-8'))

# Compare versions
diff = repo.diff("abc12345", "def67890")
print(diff)

# Compare with current file
diff = repo.diff("abc12345", current=True)
print(diff)

# Checkout a previous version
repo.checkout("abc12345", "myfile.txt")

# Access daemon controls
daemon = repo.get_daemon()
daemon.start()
daemon.status()
daemon.stop()
```

### Exception Handling

```python
from chronolog import ChronologRepo, NotARepositoryError, RepositoryExistsError

try:
    # This will raise RepositoryExistsError if already initialized
    repo = ChronologRepo.init("/existing/repo")
except RepositoryExistsError:
    # Connect to existing repo instead
    repo = ChronologRepo("/existing/repo")

try:
    content = repo.show("invalid_hash")
except ValueError as e:
    print(f"Error: {e}")
```

## Advanced Features

### Short Hash Support

ChronoLog supports abbreviated hashes for convenience:

```bash
# Use full hash
chronolog show abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Or use short hash (first 8 characters)
chronolog show abc12345
```

### Annotations

Versions can include annotations for better organization:

```python
# Annotations are automatically added for certain operations
# - "Before checkout to <hash>" when reverting files
# - "Checked out from <hash>" after reverting
# - Custom annotations can be added in future versions
```

## Requirements

- Python 3.9+
- Core dependencies: watchdog, click, colorama, psutil
- TUI dependencies: textual (optional)

## Development

### Project Structure

```
Chronolog/
├── chronolog/           # Core CLI and library
│   ├── api.py          # Main API interface
│   ├── main.py         # CLI entry point
│   ├── storage/        # Data storage layer
│   ├── daemon/         # Background process management
│   └── watcher/        # File system monitoring
├── chronolog-tui/      # Terminal user interface
│   ├── main.py         # TUI entry point
│   ├── api_bridge.py   # ChronoLog API integration
│   └── views/          # TUI screen components
└── README.md
```

### Contributing

1. Install both components in development mode
2. Run tests (when available)
3. Follow the existing code style and architecture

## License

MIT License - see LICENSE file for details.
