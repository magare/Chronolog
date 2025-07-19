# ChronoLog

A frictionless, local-first version control system for creative workflows.

## Installation

```bash
pip install -e .
```

## Usage

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

## Features

- Automatic file versioning on save
- Lightweight background daemon
- Content-addressable storage
- Fast diffing between versions
- Cross-platform support (Windows, macOS, Linux)