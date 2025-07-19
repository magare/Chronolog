import os
import difflib
from pathlib import Path
from typing import List, Dict, Optional

from .storage import Storage
from .daemon import Daemon


class ChronologRepo:
    """
    The main API for interacting with a Chronolog repository.
    """
    def __init__(self, path: str = "."):
        self.repo_path = self._find_chronolog_base(Path(path).resolve())
        if not self.repo_path:
            raise NotARepositoryError("Not a Chronolog repository.")
        
        self.chronolog_dir = self.repo_path / ".chronolog"
        self.storage = Storage(self.chronolog_dir)

    @staticmethod
    def init(path: str = ".") -> 'ChronologRepo':
        """
        Initializes a new Chronolog repository at the given path.
        """
        repo_path = Path(path).resolve()
        chronolog_dir = repo_path / ".chronolog"

        if chronolog_dir.exists():
            raise RepositoryExistsError(f"Chronolog repository already exists at {chronolog_dir}")

        # Create .chronolog directory
        chronolog_dir.mkdir(exist_ok=True)

        # Initialize storage
        storage = Storage(chronolog_dir)

        # Start the daemon
        daemon = Daemon(repo_path)
        daemon.start()

        return ChronologRepo(path)

    def log(self, filename: str) -> List[Dict]:
        """
        Gets the version history for a specific file.
        """
        file_path = Path(filename).resolve()
        if file_path.is_absolute():
            relative_path = file_path.relative_to(self.repo_path)
        else:
            relative_path = Path(filename)
        
        return self.storage.get_file_history(str(relative_path))

    def show(self, version_hash: str) -> bytes:
        """
        Shows the content of a specific version.
        """
        # Support short hashes
        if len(version_hash) < 64:
            full_hash = self._resolve_short_hash(version_hash)
            if not full_hash:
                raise ValueError(f"Version '{version_hash}' not found.")
            version_hash = full_hash

        content = self.storage.get_version_content(version_hash)
        if not content:
            raise ValueError(f"Version '{version_hash}' not found.")
        
        return content

    def diff(self, hash1: str, hash2: str = None, current: bool = False) -> str:
        """
        Computes the diff between two versions or between a version and current file.
        """
        # Get content for first hash
        content1 = self.show(hash1)
        
        # Get version info to find file path
        info1 = self.storage.get_version_info(hash1)
        if not info1:
            raise ValueError(f"Version '{hash1}' not found.")
        
        file_path = info1['file_path']
        
        if current:
            # Compare with current file
            current_file = self.repo_path / file_path
            if not current_file.exists():
                raise ValueError(f"Current file {file_path} not found.")
            content2 = current_file.read_bytes()
            label2 = "current"
        else:
            if not hash2:
                raise ValueError("Second version hash required (or use current=True)")
            
            content2 = self.show(hash2)
            label2 = hash2[:8]
        
        # Convert to lines for diff
        try:
            lines1 = content1.decode('utf-8').splitlines(keepends=True)
            lines2 = content2.decode('utf-8').splitlines(keepends=True)
        except UnicodeDecodeError:
            raise ValueError("Cannot diff binary files")
        
        # Generate diff
        diff_lines = difflib.unified_diff(
            lines1, lines2,
            fromfile=f"{file_path} ({hash1[:8]})",
            tofile=f"{file_path} ({label2})",
            lineterm=''
        )
        
        return '\n'.join(diff_lines)

    def checkout(self, version_hash: str, filename: str):
        """
        Reverts a file to a specific version.
        """
        content = self.show(version_hash)
        file_path = Path(filename)
        
        if not file_path.is_absolute():
            file_path = self.repo_path / filename
        
        # Backup current content first
        if file_path.exists():
            current_content = file_path.read_bytes()
            rel_path = file_path.relative_to(self.repo_path)
            self.storage.store_version(
                str(rel_path),
                current_content,
                annotation=f"Before checkout to {version_hash[:8]}"
            )
        
        # Write the old version
        file_path.write_bytes(content)
        
        # Record this checkout as a new version
        rel_path = file_path.relative_to(self.repo_path)
        self.storage.store_version(
            str(rel_path),
            content,
            parent_hash=version_hash,
            annotation=f"Checked out from {version_hash[:8]}"
        )

    def get_daemon(self) -> Daemon:
        """
        Returns a Daemon instance for this repository.
        """
        return Daemon(self.repo_path)

    def _resolve_short_hash(self, short_hash: str) -> Optional[str]:
        """
        Resolves a short hash to a full hash.
        """
        import sqlite3
        
        conn = sqlite3.connect(self.storage.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version_hash FROM versions WHERE version_hash LIKE ?",
            (short_hash + '%',)
        )
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return None
        elif len(results) > 1:
            raise ValueError(f"Ambiguous version hash '{short_hash}'. Multiple matches found.")
        
        return results[0][0]

    def _find_chronolog_base(self, start_path: Path = None) -> Optional[Path]:
        """
        Find the base directory containing .chronolog starting from given path.
        """
        if start_path is None:
            start_path = Path.cwd()
        
        current = start_path.resolve()
        while current != current.parent:
            if (current / ".chronolog").exists():
                return current
            current = current.parent
        return None


# Custom exceptions for the library
class NotARepositoryError(Exception):
    """Raised when trying to operate on a directory that's not a Chronolog repository."""
    pass


class RepositoryExistsError(Exception):
    """Raised when trying to initialize a repository that already exists."""
    pass