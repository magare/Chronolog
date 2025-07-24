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
    
    # Tag system methods
    def create_tag(self, tag_name: str, version_hash: Optional[str] = None, description: Optional[str] = None) -> tuple[bool, str]:
        """Create a new tag.
        
        Returns:
            tuple: (success, message)
        """
        if self.repo is None:
            return False, "No repository available"
        
        try:
            self.repo.tag(tag_name, version_hash, description)
            return True, f"Tag '{tag_name}' created successfully"
        except Exception as e:
            return False, str(e)
    
    def get_tags(self) -> List[dict]:
        """Get all tags in the repository."""
        if self.repo is None:
            return []
        
        try:
            return self.repo.list_tags()
        except Exception:
            return []
    
    def delete_tag(self, tag_name: str) -> tuple[bool, str]:
        """Delete a tag.
        
        Returns:
            tuple: (success, message)
        """
        if self.repo is None:
            return False, "No repository available"
        
        try:
            self.repo.delete_tag(tag_name)
            return True, f"Tag '{tag_name}' deleted successfully"
        except Exception as e:
            return False, str(e)
    
    # Branch system methods
    def get_branches(self) -> tuple[str, List[dict]]:
        """Get current branch and list of all branches."""
        if self.repo is None:
            return "main", []
        
        try:
            return self.repo.branch()
        except Exception:
            return "main", []
    
    def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> tuple[bool, str]:
        """Create a new branch.
        
        Returns:
            tuple: (success, message)
        """
        if self.repo is None:
            return False, "No repository available"
        
        try:
            self.repo.branch(branch_name, from_branch)
            return True, f"Branch '{branch_name}' created successfully"
        except Exception as e:
            return False, str(e)
    
    def switch_branch(self, branch_name: str) -> tuple[bool, str]:
        """Switch to a different branch.
        
        Returns:
            tuple: (success, message)
        """
        if self.repo is None:
            return False, "No repository available"
        
        try:
            self.repo.switch_branch(branch_name)
            return True, f"Switched to branch '{branch_name}'"
        except Exception as e:
            return False, str(e)
    
    def delete_branch(self, branch_name: str) -> tuple[bool, str]:
        """Delete a branch.
        
        Returns:
            tuple: (success, message)
        """
        if self.repo is None:
            return False, "No repository available"
        
        try:
            self.repo.delete_branch(branch_name)
            return True, f"Branch '{branch_name}' deleted successfully"
        except Exception as e:
            return False, str(e)
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        if self.repo is None:
            return "main"
        
        try:
            return self.repo.get_current_branch()
        except Exception:
            return "main"
    
    # Search methods
    def search_content(self, query: str, file_path: Optional[str] = None) -> List[dict]:
        """Search for content in the repository."""
        if self.repo is None:
            return []
        
        try:
            return self.repo.search(query, file_path)
        except Exception:
            return []
    
    def advanced_search(self, query: str, regex: bool = False, case_sensitive: bool = False, 
                       whole_words: bool = False, file_types: Optional[List[str]] = None,
                       recent_days: Optional[int] = None) -> List[dict]:
        """Perform advanced search with filters."""
        if self.repo is None:
            return []
        
        try:
            from chronolog.search.searcher import SearchFilter
            
            filter = SearchFilter()
            filter.query = query
            filter.regex = regex
            filter.case_sensitive = case_sensitive
            filter.whole_words = whole_words
            
            if file_types:
                for ext in file_types:
                    filter.add_file_type(ext)
            
            if recent_days:
                filter.set_recent(recent_days)
            
            return self.repo.advanced_search(filter)
        except Exception:
            return []