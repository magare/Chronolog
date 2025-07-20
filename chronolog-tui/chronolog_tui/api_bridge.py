"""API Bridge for ChronoLog TUI.

This module provides a clean abstraction layer between the TUI and the ChronologRepo API.
It handles data formatting and error handling for the UI components.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, NamedTuple
from datetime import datetime

from chronolog import ChronologRepo, NotARepositoryError, RepositoryExistsError


class FileHistoryEntry(NamedTuple):
    """Represents a single entry in file history."""
    hash: str
    timestamp: str
    file_path: str
    annotation: Optional[str] = None


class RepositoryStatus(NamedTuple):
    """Represents the current status of a ChronoLog repository."""
    is_repository: bool
    repo_path: Optional[str]
    daemon_running: bool
    error_message: Optional[str] = None


class ChronologBridge:
    """Bridge class that abstracts ChronologRepo operations for the TUI."""
    
    def __init__(self, path: str = "."):
        """Initialize the bridge with a repository path."""
        self.path = Path(path).resolve()
        self._repo: Optional[ChronologRepo] = None
        self._last_error: Optional[str] = None
    
    @property
    def repo(self) -> Optional[ChronologRepo]:
        """Get the ChronologRepo instance, initializing if needed."""
        if self._repo is None:
            try:
                self._repo = ChronologRepo(str(self.path))
                self._last_error = None
            except NotARepositoryError as e:
                self._last_error = str(e)
                return None
            except Exception as e:
                self._last_error = f"Unexpected error: {e}"
                return None
        return self._repo
    
    def get_repository_status(self) -> RepositoryStatus:
        """Get the current status of the repository."""
        try:
            repo = self.repo
            if repo is None:
                return RepositoryStatus(
                    is_repository=False,
                    repo_path=None,
                    daemon_running=False,
                    error_message=self._last_error
                )
            
            # Check daemon status
            daemon = repo.get_daemon()
            daemon_running = daemon.is_running()
            
            return RepositoryStatus(
                is_repository=True,
                repo_path=str(repo.repo_path),
                daemon_running=daemon_running
            )
        except Exception as e:
            return RepositoryStatus(
                is_repository=False,
                repo_path=None,
                daemon_running=False,
                error_message=str(e)
            )
    
    def initialize_repository(self) -> tuple[bool, str]:
        """Initialize a new ChronoLog repository.
        
        Returns:
            tuple: (success, message)
        """
        try:
            self._repo = ChronologRepo.init(str(self.path))
            return True, f"Repository initialized at {self.path}"
        except RepositoryExistsError:
            return False, "Repository already exists"
        except Exception as e:
            return False, f"Failed to initialize repository: {e}"
    
    def get_file_history(self, filename: str) -> List[FileHistoryEntry]:
        """Get the version history for a specific file."""
        if self.repo is None:
            return []
        
        try:
            history = self.repo.log(filename)
            return [
                FileHistoryEntry(
                    hash=entry['hash'],
                    timestamp=entry['timestamp'],
                    file_path=filename,  # Use the filename parameter since log() doesn't return file_path
                    annotation=entry.get('annotation')
                )
                for entry in history
            ]
        except Exception:
            return []
    
    def get_all_files_with_history(self) -> Dict[str, List[FileHistoryEntry]]:
        """Get all files that have version history."""
        if self.repo is None:
            return {}
        
        try:
            # This is a simplified approach - in a real implementation,
            # you might want to add a method to ChronologRepo to get all tracked files
            import sqlite3
            conn = sqlite3.connect(self.repo.storage.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT file_path FROM versions ORDER BY file_path")
            files = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            result = {}
            for file_path in files:
                result[file_path] = self.get_file_history(file_path)
            
            return result
        except Exception:
            return {}
    
    def show_version_content(self, version_hash: str) -> Optional[str]:
        """Get the content of a specific version."""
        if self.repo is None:
            return None
        
        try:
            content = self.repo.show(version_hash)
            # Try to decode as UTF-8, return None for binary files
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                return "[Binary file content]"
        except Exception:
            return None
    
    def get_version_diff(self, hash1: str, hash2: str = None, current: bool = False) -> Optional[str]:
        """Get diff between two versions or between a version and current file."""
        if self.repo is None:
            return None
        
        try:
            return self.repo.diff(hash1, hash2, current=current)
        except Exception as e:
            return f"Error generating diff: {e}"
    
    def checkout_version(self, version_hash: str, filename: str) -> tuple[bool, str]:
        """Checkout a specific version of a file.
        
        Returns:
            tuple: (success, message)
        """
        if self.repo is None:
            return False, "No repository available"
        
        try:
            self.repo.checkout(version_hash, filename)
            return True, f"Successfully checked out {filename} to version {version_hash[:8]}"
        except Exception as e:
            return False, f"Checkout failed: {e}"
    
    def start_daemon(self) -> tuple[bool, str]:
        """Start the file watching daemon."""
        if self.repo is None:
            return False, "No repository available"
        
        try:
            daemon = self.repo.get_daemon()
            daemon.start()
            return True, "Daemon started successfully"
        except Exception as e:
            return False, f"Failed to start daemon: {e}"
    
    def stop_daemon(self) -> tuple[bool, str]:
        """Stop the file watching daemon."""
        if self.repo is None:
            return False, "No repository available"
        
        try:
            daemon = self.repo.get_daemon()
            daemon.stop()
            return True, "Daemon stopped successfully"
        except Exception as e:
            return False, f"Failed to stop daemon: {e}"
    
    def get_daemon_status(self) -> str:
        """Get a human-readable daemon status."""
        status = self.get_repository_status()
        if not status.is_repository:
            return "No repository"
        return "Running" if status.daemon_running else "Stopped"