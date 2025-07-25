import os
import difflib
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .storage import Storage
from .daemon import Daemon
from .search.searcher import Searcher, SearchFilter
from .diff.word_diff import WordDiffer
from .diff.semantic_diff import SemanticDiffer
from .diff.binary_diff import BinaryDiffer


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
        
        # Create default .chronologignore file
        from .ignore import IgnorePatterns
        IgnorePatterns.create_default_ignore_file(repo_path)

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

    def diff(self, hash1: str, hash2: str = None, current: bool = False, diff_type: str = "line") -> str:
        """
        Computes the diff between two versions or between a version and current file.
        
        Args:
            hash1: First version hash
            hash2: Second version hash (required unless current=True)
            current: Compare with current file instead of hash2
            diff_type: Type of diff - "line", "word", "semantic", or "binary"
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
        
        # Handle binary diff
        if diff_type == "binary":
            differ = BinaryDiffer()
            result = differ.diff_binary(content1, content2, file_path)
            return differ.format_binary_diff(result)
        
        # Try to decode as text
        try:
            text1 = content1.decode('utf-8')
            text2 = content2.decode('utf-8')
        except UnicodeDecodeError:
            # Fall back to binary diff
            differ = BinaryDiffer()
            result = differ.diff_binary(content1, content2, file_path)
            return differ.format_binary_diff(result)
        
        # Handle different diff types
        if diff_type == "word":
            differ = WordDiffer()
            word_diffs = differ.diff_lines_with_words(text1, text2)
            output = []
            for line_num, words in word_diffs:
                formatted = differ.format_word_diff(words, use_color=True)
                output.append(f"{line_num:4d}: {formatted}")
            return '\n'.join(output)
        
        elif diff_type == "semantic":
            differ = SemanticDiffer()
            language = differ.detect_language(file_path)
            if language:
                changes = differ.diff_semantic(text1, text2, language)
                return differ.format_semantic_diff(changes)
            else:
                # Fall back to line diff for unsupported languages
                diff_type = "line"
        
        # Default line diff
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        
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
    
    # Tag system methods
    def tag(self, tag_name: str, version_hash: Optional[str] = None, description: Optional[str] = None):
        """Create a tag pointing to a specific version."""
        if not version_hash:
            # Tag the latest version if no hash provided
            # Get all files with history to find the most recent change
            import sqlite3
            conn = sqlite3.connect(self.storage.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT version_hash FROM versions
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                raise ValueError("No versions found to tag")
            version_hash = result[0]
        else:
            # Resolve short hash if needed
            if len(version_hash) < 64:
                full_hash = self._resolve_short_hash(version_hash)
                if not full_hash:
                    raise ValueError(f"Version '{version_hash}' not found.")
                version_hash = full_hash
        
        if not self.storage.create_tag(tag_name, version_hash, description):
            raise ValueError(f"Tag '{tag_name}' already exists")
    
    def list_tags(self) -> List[Dict]:
        """List all tags in the repository."""
        return self.storage.get_tags()
    
    def delete_tag(self, tag_name: str):
        """Delete a tag."""
        if not self.storage.delete_tag(tag_name):
            raise ValueError(f"Tag '{tag_name}' not found")
    
    # Branch system methods
    def branch(self, branch_name: Optional[str] = None, from_branch: Optional[str] = None) -> Optional[Tuple[str, List[Dict]]]:
        """Create a new branch or list branches if no name provided."""
        if not branch_name:
            # List branches
            branches = self.storage.get_branches()
            current = self.storage.get_current_branch()
            return current, branches
        
        # Create new branch
        if not self.storage.create_branch(branch_name, from_branch):
            raise ValueError(f"Branch '{branch_name}' already exists or parent branch not found")
        return None
    
    def switch_branch(self, branch_name: str):
        """Switch to a different branch."""
        if not self.storage.switch_branch(branch_name):
            raise ValueError(f"Branch '{branch_name}' not found")
    
    def delete_branch(self, branch_name: str):
        """Delete a branch."""
        if branch_name == self.storage.get_current_branch():
            raise ValueError("Cannot delete the current branch")
        
        if not self.storage.delete_branch(branch_name):
            raise ValueError(f"Cannot delete branch '{branch_name}'")
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        return self.storage.get_current_branch()
    
    # Search methods
    def search(self, query: str, file_path: Optional[str] = None) -> List[Dict]:
        """Search for content in the repository."""
        return self.storage.search_content(query, file_path)
    
    def advanced_search(self, filter: SearchFilter) -> List[Dict]:
        """Perform advanced search with filters."""
        searcher = Searcher(self.storage)
        return searcher.search(filter)
    
    def search_changes(self, added: Optional[str] = None, removed: Optional[str] = None) -> List[Dict]:
        """Search for versions where text was added or removed."""
        searcher = Searcher(self.storage)
        return searcher.search_by_content_change(added, removed)
    
    def reindex_search(self, progress_callback=None) -> Tuple[int, int]:
        """Reindex all content for search. Returns (indexed, total)."""
        searcher = Searcher(self.storage)
        return searcher.reindex_all(progress_callback)
    
    def get_search_stats(self) -> Dict:
        """Get statistics about the search index."""
        searcher = Searcher(self.storage)
        return searcher.get_search_stats()

    def status(self) -> Dict:
        """Get repository status including daemon status and recent activity"""
        daemon = self.get_daemon()
        daemon_status = daemon.status()
        
        # Get recent files with versions
        import glob
        files_with_versions = {}
        
        # Scan for tracked files
        for file_path in glob.glob("**/*", recursive=True):
            if os.path.isfile(file_path) and not file_path.startswith('.chronolog'):
                try:
                    history = self.log(file_path)
                    if history:
                        files_with_versions[file_path] = len(history)
                except:
                    # Skip files that can't be processed
                    pass
        
        return {
            'daemon_running': daemon_status.get('running', False) if daemon_status else False,
            'daemon_pid': daemon_status.get('pid') if daemon_status else None,
            'tracked_files': len(files_with_versions),
            'files_with_versions': files_with_versions,
            'current_branch': self.get_current_branch()
        }

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