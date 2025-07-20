# ChronoLog TUI

A terminal user interface for the ChronoLog file version control system. This TUI provides an interactive way to manage your file versions, view history, and control the ChronoLog daemon.

## Features

- **Interactive Dashboard** - View repository status and daemon information
- **File History Browser** - Navigate through tracked files and their versions
- **Version Details** - View file content for any version
- **Diff Viewer** - Compare versions or diff against current files
- **One-Click Checkout** - Revert files to previous versions
- **Daemon Control** - Start/stop file watching from the interface

## Installation

From the `chronolog-tui` directory:

```bash
pip install -e .
```

This will install the TUI along with its dependencies, including the ChronoLog library.

## Usage

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

## Screenshots

### Dashboard
The main dashboard shows repository status, daemon information, and available actions.

### History Browser
Navigate through all tracked files and their version history in an interactive table format.

### Version Details
View file content for any version and perform actions like checkout or diff comparison.

## Requirements

- Python 3.9+
- Textual framework
- ChronoLog library

## Architecture

The TUI is built using the [Textual](https://textual.textualize.io/) framework and follows a clean architecture:

- `main.py` - Application entry point and screen management
- `api_bridge.py` - Abstraction layer for ChronoLog operations
- `views/` - Individual view components (dashboard, history, etc.)
- `styles.css` - TUI styling and theming

This separation ensures the TUI remains maintainable and can easily adapt to changes in the ChronoLog library API.