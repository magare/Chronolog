# ChronoLog

A comprehensive, local-first version control system designed for creative workflows and collaborative development. ChronoLog provides a complete ecosystem with CLI tools, Python library, TUI interface, web UI, and advanced features including user management, merge capabilities, analytics, and more.

## 🚀 Key Features

### Core Version Control
- **Dual Interface**: Use as CLI tool or Python library
- **Terminal UI**: Interactive TUI for visual file management
- **Web Interface**: Full-featured web UI with repository browser
- **Automatic Versioning**: Files are automatically versioned on save
- **Lightweight Daemon**: Background process watches for file changes
- **Content-Addressable Storage**: Efficient storage using file hashes
- **Fast Diffing**: Quick comparison between any two versions
- **Short Hash Support**: Use abbreviated hashes for convenience
- **Annotations**: Add notes to versions for better organization

### Advanced Features (Phase 4 & 5)
- **Performance Analytics**: Repository statistics, metrics, and visualizations
- **Storage Optimization**: Compression, deduplication, and garbage collection
- **Code Metrics**: Lines of code, complexity analysis, language statistics
- **User Management**: Multi-user support with authentication and permissions
- **Merge Engine**: Three-way merge with conflict detection and resolution
- **Hooks System**: Pre/post version event triggers and automation
- **RESTful API**: Complete HTTP API for integration
- **GraphQL API**: Advanced query interface with subscriptions
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

## 📋 Quick Start

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

## 🔧 CLI Commands Reference

### Core Commands
```bash
# Repository management
chronolog init                    # Initialize repository
chronolog status                  # Show repository status
chronolog log [file]              # View version history
chronolog show <hash>             # Show version content
chronolog diff <hash1> <hash2>    # Compare versions
chronolog checkout <hash> <file>  # Revert to version

# Daemon management
chronolog daemon status           # Check daemon status
chronolog daemon start            # Start background daemon
chronolog daemon stop             # Stop background daemon
```

### Analytics Commands (Phase 4)
```bash
# Performance analytics
chronolog analytics stats         # Repository statistics
chronolog analytics metrics       # Performance metrics
chronolog analytics visualize     # Generate visualizations

# Code metrics
chronolog metrics code            # Code analysis
chronolog metrics complexity      # Complexity metrics
chronolog metrics languages       # Language statistics
```

### Storage Commands (Phase 4)
```bash
# Storage optimization
chronolog optimize storage        # Optimize storage usage
chronolog optimize compress       # Compress repository data
chronolog optimize gc             # Run garbage collection
```

### User Management (Phase 5)
```bash
# User operations
chronolog users list              # List all users
chronolog users create <username> # Create new user
chronolog users info <user>       # Show user information
chronolog users permissions <user> # Show user permissions
```

### Merge Commands (Phase 5)
```bash
# Merge operations
chronolog merge preview <base> <ours> <theirs>  # Preview merge
chronolog merge execute <base> <ours> <theirs>  # Execute merge
chronolog merge conflicts <file>                # Show conflicts
chronolog merge resolve <file> --strategy=<strategy> # Resolve conflicts
```

### Web Server (Phase 5)
```bash
# Web interface
chronolog web start               # Start web server
chronolog web stop                # Stop web server
chronolog web status              # Check web server status
```

### Hooks System (Phase 4)
```bash
# Hook management
chronolog hooks list              # List installed hooks
chronolog hooks install <hook>    # Install hook
chronolog hooks remove <hook>     # Remove hook
chronolog hooks test <hook>       # Test hook execution
```

## 🖥️ TUI Usage

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

## 🌐 Web Interface

### Starting the Web Server

```bash
# Start web server on default port (5000)
chronolog web start

# Start on custom port
chronolog web start --port 8080

# Start with custom host
chronolog web start --host 0.0.0.0 --port 8080
```

### Web Features
- **Repository Browser**: Navigate files and directories
- **History Viewer**: Visual timeline of all versions
- **Diff Viewer**: Side-by-side version comparison
- **User Management**: Admin interface for users and permissions
- **Analytics Dashboard**: Performance metrics and visualizations
- **Merge Interface**: Interactive conflict resolution
- **Settings Panel**: Configuration management

### API Endpoints

#### REST API
```
GET    /api/v1/health              # Health check
GET    /api/v1/repository/status   # Repository status
GET    /api/v1/versions            # List versions
POST   /api/v1/versions            # Create version
GET    /api/v1/versions/{id}       # Get specific version
GET    /api/v1/users               # List users (admin only)
POST   /api/v1/users               # Create user (admin only)
GET    /api/v1/analytics/stats     # Analytics data
GET    /api/v1/search              # Search repository
POST   /api/v1/merge/preview       # Preview merge
POST   /api/v1/optimize/storage    # Optimize storage
```

#### GraphQL API
```
# Available at /graphql
# Includes queries for users, versions, analytics, and more
# Supports subscriptions for real-time updates
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

## 🧪 Testing

ChronoLog includes comprehensive test suites for all components:

### Running All Tests

```bash
# Run the master test suite
python run_all_tests.py
```

### Running Individual Test Suites

```bash
# Core features
python test_phase1_features.py
python test_phase2_phase3_features.py
python test_phase4_phase5_features.py

# Component-specific tests
python tests/test_analytics.py
python tests/test_optimization.py
python tests/test_users.py
python tests/test_merge.py
python tests/test_web_api.py
```

### Test Coverage
- **Phase 1-3**: Core version control functionality
- **Phase 4**: Analytics, optimization, metrics, hooks
- **Phase 5**: User management, merge engine, web API
- **Integration**: End-to-end workflow testing
- **Web API**: REST and GraphQL endpoint testing

## 📦 Requirements

### Core Dependencies
- Python 3.9+
- watchdog (file system monitoring)
- click (CLI framework)
- colorama (terminal colors)
- psutil (system utilities)

### Optional Dependencies
- textual (TUI interface)
- flask (web interface)
- flask-cors (CORS support)
- graphene (GraphQL API)
- jwt (authentication)
- bcrypt (password hashing)

### Development Dependencies
- unittest (testing framework)
- tempfile (test environments)
- pathlib (file system utilities)

## 🏗️ Architecture

### Project Structure

```
Chronolog/
├── chronolog/                    # Core CLI and library
│   ├── api.py                   # Main API interface
│   ├── main.py                  # CLI entry point
│   ├── storage/                 # Data storage layer
│   ├── daemon/                  # Background process management
│   ├── watcher/                 # File system monitoring
│   ├── analytics/               # Performance analytics (Phase 4)
│   ├── optimization/            # Storage optimization (Phase 4)
│   ├── metrics/                 # Code and developer metrics (Phase 4)
│   ├── hooks/                   # Event hooks system (Phase 4)
│   ├── users/                   # User management (Phase 5)
│   ├── merge/                   # Merge engine (Phase 5)
│   └── web/                     # Web interface (Phase 5)
├── chronolog-tui/               # Terminal user interface
│   ├── main.py                  # TUI entry point
│   ├── api_bridge.py            # ChronoLog API integration
│   └── views/                   # TUI screen components
├── tests/                       # Test suites
│   ├── test_analytics.py        # Analytics tests
│   ├── test_optimization.py     # Optimization tests
│   ├── test_users.py            # User management tests
│   ├── test_merge.py            # Merge engine tests
│   └── test_web_api.py          # Web API tests
├── run_all_tests.py             # Master test runner
├── IMPLEMENTATION_ROADMAP.md    # Development roadmap
└── README.md                    # This file
```

### Design Principles
- **Local-First**: All data stored locally with optional sync
- **Content-Addressable**: Efficient storage using content hashes
- **Modular Architecture**: Clear separation of concerns
- **API-First Design**: All features accessible via API
- **Extensible**: Plugin system via hooks
- **Performance**: Optimized for large repositories
- **Security**: Authentication and authorization built-in

## 🚀 Development

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd Chronolog

# Install core package
pip install -e .

# Install TUI package (optional)
cd chronolog-tui
pip install -e .
cd ..

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
python run_all_tests.py

# Run specific test suite
python tests/test_analytics.py

# Run with verbose output
python -m unittest tests.test_web_api -v
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Install in development mode
4. Write tests for new features
5. Run the test suite
6. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write comprehensive docstrings
- Maintain test coverage above 80%

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Documentation**: See docs/ directory for detailed guides
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join community discussions
- **API Reference**: Available at `/docs` when web server is running
