# ChronoLog

A frictionless, local-first version control system for creative workflows. ChronoLog can be used both as a command-line tool and as a Python library.

## Installation

```bash
pip install -e .
```

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

## Features

- **Dual Interface**: Use as CLI tool or Python library
- **Automatic Versioning**: Files are automatically versioned on save
- **Lightweight Daemon**: Background process watches for file changes
- **Content-Addressable Storage**: Efficient storage using file hashes
- **Fast Diffing**: Quick comparison between any two versions
- **Short Hash Support**: Use abbreviated hashes for convenience
- **Cross-Platform**: Works on Windows, macOS, and Linux