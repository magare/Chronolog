"""Ignore pattern handling for ChronoLog."""

import os
import re
from pathlib import Path
from typing import List, Optional
import fnmatch


class IgnorePatterns:
    """Handles .chronologignore file parsing and pattern matching."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.patterns: List[str] = []
        self.regex_patterns: List[re.Pattern] = []
        self._load_patterns()
    
    def _load_patterns(self):
        """Load patterns from .chronologignore file."""
        ignore_file = self.repo_path / ".chronologignore"
        
        # Default patterns to always ignore
        default_patterns = [
            ".chronolog/",
            ".chronolog/*",
            ".git/",
            ".git/*",
            "*.pyc",
            "__pycache__/",
            "__pycache__/*",
            ".DS_Store",
            "Thumbs.db",
            "*.swp",
            "*.swo",
            "*~",
            ".#*",
            "#*#"
        ]
        
        # Add default patterns
        for pattern in default_patterns:
            self._add_pattern(pattern)
        
        # Load user patterns if file exists
        if ignore_file.exists():
            try:
                with open(ignore_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if line and not line.startswith('#'):
                            self._add_pattern(line)
            except Exception:
                # If we can't read the ignore file, just use defaults
                pass
    
    def _add_pattern(self, pattern: str):
        """Add a pattern to the ignore list."""
        self.patterns.append(pattern)
        
        # Convert glob pattern to regex
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            # Match directory and everything inside
            regex_pattern = fnmatch.translate(pattern[:-1])
            regex_pattern = regex_pattern.replace(r'\Z', r'(?:/.*)?$')
        else:
            regex_pattern = fnmatch.translate(pattern)
        
        self.regex_patterns.append(re.compile(regex_pattern))
    
    def should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on patterns."""
        # Convert to relative path from repo root
        try:
            if file_path.is_absolute():
                rel_path = file_path.relative_to(self.repo_path)
            else:
                rel_path = file_path
        except ValueError:
            # Path is outside repo, ignore it
            return True
        
        # Convert to string with forward slashes
        path_str = str(rel_path).replace(os.sep, '/')
        
        # Check each pattern
        for pattern, regex in zip(self.patterns, self.regex_patterns):
            # Check if pattern matches the path
            if regex.match(path_str):
                return True
            
            # For directory patterns, also check if path is inside the directory
            if pattern.endswith('/'):
                dir_pattern = pattern[:-1]
                if path_str.startswith(dir_pattern + '/'):
                    return True
        
        return False
    
    def reload(self):
        """Reload patterns from file."""
        self.patterns.clear()
        self.regex_patterns.clear()
        self._load_patterns()
    
    def get_patterns(self) -> List[str]:
        """Get the list of ignore patterns."""
        return self.patterns.copy()
    
    @staticmethod
    def create_default_ignore_file(repo_path: Path):
        """Create a default .chronologignore file."""
        ignore_file = repo_path / ".chronologignore"
        
        if not ignore_file.exists():
            default_content = """# ChronoLog ignore patterns
# This file uses gitignore-style patterns

# ChronoLog and version control
.chronolog/
.git/

# Python
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
*.egg-info/
*.egg

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.eslintcache

# IDE and editors
.idea/
.vscode/
*.swp
*.swo
*~
.project
.classpath
.settings/

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Build outputs
dist/
build/
out/
target/
*.o
*.so
*.dll
*.exe

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
.tmp/
.temp/

# Large binary files (add specific extensions as needed)
*.zip
*.tar.gz
*.rar
*.7z
*.dmg
*.iso
*.jar
*.war

# Custom patterns (add your own below)
"""
            
            ignore_file.write_text(default_content)
            return True
        return False