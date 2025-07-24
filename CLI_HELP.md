# ChronoLog CLI Reference

ChronoLog is a frictionless, local-first version control system for creative workflows.

## Installation

```bash
pip install chronolog
```

## Basic Usage

```bash
chronolog [COMMAND] [OPTIONS]
```

## Commands

### Repository Management

#### `chronolog init`
Initialize ChronoLog in the current directory
```bash
chronolog init
```

### File Operations

#### `chronolog log <file_path>`
View version history for a file
```bash
chronolog log myfile.txt
```

#### `chronolog show <version_hash>`
Show the content of a specific version
```bash
chronolog show abc123def
```

#### `chronolog diff <hash1> [hash2]`
Show differences between two versions
```bash
# Compare two versions
chronolog diff abc123 def456

# Compare with current file
chronolog diff abc123 --current
```

#### `chronolog checkout <version_hash> <file_path>`
Revert a file to a previous version
```bash
chronolog checkout abc123def myfile.txt
```

### Search Operations

#### `chronolog search <query>`
Search for content in the repository
```bash
# Simple search
chronolog search "TODO"

# Search in specific file
chronolog search "function" --file mycode.py

# Advanced search options
chronolog search "pattern" \
  --type py \
  --regex \
  --case-sensitive \
  --whole-words \
  --recent 7 \
  --limit 10

# Search for content changes
chronolog search --added "new feature"
chronolog search --removed "deprecated"
```

Options:
- `--file, -f`: Search within a specific file
- `--type, -t`: Filter by file type (can be used multiple times)
- `--regex, -r`: Use regex pattern
- `--case-sensitive, -c`: Case sensitive search
- `--whole-words, -w`: Match whole words only
- `--recent, -d`: Search only recent N days
- `--limit, -l`: Limit number of results
- `--added`: Find where text was added
- `--removed`: Find where text was removed

#### `chronolog reindex`
Reindex all content for search
```bash
chronolog reindex
```

### Branch Management

#### `chronolog branch create <branch_name>`
Create a new branch
```bash
# Create from current branch
chronolog branch create feature-x

# Create from another branch
chronolog branch create feature-y --from main
```

#### `chronolog branch list`
List all branches
```bash
chronolog branch list
```

#### `chronolog branch switch <branch_name>`
Switch to a different branch
```bash
chronolog branch switch feature-x
```

#### `chronolog branch delete <branch_name>`
Delete a branch
```bash
chronolog branch delete feature-x
```

### Tag Management

#### `chronolog tag create <tag_name> [version_hash]`
Create a tag pointing to a version
```bash
# Tag latest version
chronolog tag create v1.0

# Tag specific version
chronolog tag create v1.0 abc123def

# Add description
chronolog tag create v1.0 --description "First stable release"
```

#### `chronolog tag list`
List all tags
```bash
chronolog tag list
```

#### `chronolog tag delete <tag_name>`
Delete a tag
```bash
chronolog tag delete v1.0
```

### Ignore Patterns

#### `chronolog ignore show`
Show current ignore patterns
```bash
chronolog ignore show
```

#### `chronolog ignore init`
Create a default .chronologignore file
```bash
chronolog ignore init
```

### Daemon Management

#### `chronolog daemon start`
Start the background daemon
```bash
chronolog daemon start
```

#### `chronolog daemon stop`
Stop the background daemon
```bash
chronolog daemon stop
```

#### `chronolog daemon status`
Check daemon status
```bash
chronolog daemon status
```

## .chronologignore File

ChronoLog uses a `.chronologignore` file to specify patterns for files and directories that should not be tracked. The syntax is similar to `.gitignore`:

```
# Comments start with #
*.pyc
__pycache__/
.DS_Store
node_modules/
.git/
*.tmp
*.log
.env
.venv/
```

## Examples

### Basic Workflow

```bash
# Initialize repository
chronolog init

# Create ignore file
chronolog ignore init

# Work on files (automatic tracking)
echo "Hello World" > hello.txt

# View history
chronolog log hello.txt

# Search for content
chronolog search "Hello"

# Create a branch for new feature
chronolog branch create feature-greeting

# Tag a version
chronolog tag create v1.0 --description "Initial version"
```

### Advanced Search

```bash
# Search Python files for TODO comments
chronolog search "TODO" --type py

# Find where a function was added
chronolog search --added "def process_data"

# Regex search for email patterns
chronolog search "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" --regex

# Search recent changes only
chronolog search "bug" --recent 7 --limit 20
```

### Version Management

```bash
# View file history
chronolog log src/main.py

# Show specific version
chronolog show abc123def

# Compare versions
chronolog diff abc123 def456

# Revert to previous version
chronolog checkout abc123def src/main.py
```

## Tips

1. **Automatic Tracking**: ChronoLog automatically tracks changes to all files in the repository (except ignored patterns)

2. **Branch Isolation**: Each branch maintains its own version history

3. **Lightweight Tags**: Tags are pointers to specific versions, useful for marking releases or milestones

4. **Search Index**: The search index is automatically maintained but can be manually reindexed if needed

5. **Performance**: Use `.chronologignore` to exclude large files or directories that don't need version control