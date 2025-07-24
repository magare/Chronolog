import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ImportStats:
    commits_imported: int
    files_imported: int
    branches_imported: int
    tags_imported: int
    errors: List[str]


class GitImporter:
    """Import Git repository history into ChronoLog."""
    
    def __init__(self, chronolog_repo):
        self.chronolog_repo = chronolog_repo
        self.repo_path = Path(chronolog_repo.repo_path)
    
    def import_from_git(self, git_repo_path: Path,
                       import_branches: bool = True,
                       import_tags: bool = True,
                       preserve_timestamps: bool = True) -> ImportStats:
        """
        Import entire Git repository into ChronoLog.
        
        Args:
            git_repo_path: Path to Git repository
            import_branches: Whether to import all branches
            import_tags: Whether to import tags
            preserve_timestamps: Whether to preserve original commit timestamps
            
        Returns:
            Import statistics
        """
        stats = ImportStats(0, 0, 0, 0, [])
        
        if not (git_repo_path / ".git").exists():
            stats.errors.append("Not a Git repository")
            return stats
        
        try:
            # Import main branch first
            self._import_branch("main", git_repo_path, stats, preserve_timestamps)
            
            # Import other branches if requested
            if import_branches:
                branches = self._get_git_branches(git_repo_path)
                for branch in branches:
                    if branch != "main":
                        try:
                            self._import_branch(branch, git_repo_path, stats, preserve_timestamps)
                            stats.branches_imported += 1
                        except Exception as e:
                            stats.errors.append(f"Failed to import branch {branch}: {e}")
            
            # Import tags if requested
            if import_tags:
                try:
                    self._import_tags(git_repo_path, stats)
                except Exception as e:
                    stats.errors.append(f"Failed to import tags: {e}")
            
            return stats
            
        except Exception as e:
            stats.errors.append(f"Import failed: {e}")
            return stats
    
    def _import_branch(self, branch_name: str, git_repo_path: Path, 
                      stats: ImportStats, preserve_timestamps: bool):
        """Import a specific Git branch."""
        # Checkout branch
        self._run_git_command(["checkout", branch_name], git_repo_path)
        
        # Create ChronoLog branch if it doesn't exist
        if branch_name != "main":
            try:
                self.chronolog_repo.create_branch(branch_name)
                self.chronolog_repo.switch_branch(branch_name)
            except:
                pass  # Branch might already exist
        
        # Get commit history (oldest first)
        commit_log = self._run_git_command([
            "log", "--reverse", "--format=%H|%at|%an|%ae|%s"
        ], git_repo_path)
        
        commits = []
        for line in commit_log.strip().split('\n'):
            if line:
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'timestamp': int(parts[1]),
                        'author_name': parts[2],
                        'author_email': parts[3],
                        'message': parts[4]
                    })
        
        # Process each commit
        for commit in commits:
            try:
                self._import_commit(commit, git_repo_path, stats, preserve_timestamps)
            except Exception as e:
                stats.errors.append(f"Failed to import commit {commit['hash']}: {e}")
    
    def _import_commit(self, commit: Dict, git_repo_path: Path, 
                      stats: ImportStats, preserve_timestamps: bool):
        """Import a single Git commit."""
        # Checkout specific commit
        self._run_git_command(["checkout", commit['hash']], git_repo_path)
        
        # Get list of files changed in this commit
        try:
            changed_files = self._run_git_command([
                "diff-tree", "--no-commit-id", "--name-only", "-r", commit['hash']
            ], git_repo_path)
            files = [f.strip() for f in changed_files.split('\n') if f.strip()]
        except:
            # For first commit, get all files
            files = []
            for root, dirs, filenames in os.walk(git_repo_path):
                # Skip .git directory
                if '.git' in root:
                    continue
                
                for filename in filenames:
                    file_path = Path(root) / filename
                    rel_path = file_path.relative_to(git_repo_path)
                    files.append(str(rel_path))
        
        # Copy files to ChronoLog repository
        for file_path in files:
            try:
                src_path = git_repo_path / file_path
                dst_path = self.repo_path / file_path
                
                if src_path.exists() and not src_path.is_dir():
                    # Create directory structure
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(src_path, dst_path)
                    
                    # Set timestamp if preserving
                    if preserve_timestamps:
                        timestamp = commit['timestamp']
                        os.utime(dst_path, (timestamp, timestamp))
                    
                    stats.files_imported += 1
                
            except Exception as e:
                stats.errors.append(f"Failed to import file {file_path} from commit {commit['hash']}: {e}")
        
        stats.commits_imported += 1
    
    def _import_tags(self, git_repo_path: Path, stats: ImportStats):
        """Import Git tags as ChronoLog tags."""
        # Get all tags
        tags_output = self._run_git_command(["tag", "-l"], git_repo_path)
        tags = [tag.strip() for tag in tags_output.split('\n') if tag.strip()]
        
        for tag_name in tags:
            try:
                # Get tag information
                tag_info = self._run_git_command([
                    "show", "--format=%H|%at|%s", "--no-patch", tag_name
                ], git_repo_path)
                
                parts = tag_info.strip().split('|', 2)
                if len(parts) >= 3:
                    commit_hash = parts[0]
                    timestamp = int(parts[1])
                    message = parts[2]
                    
                    # In ChronoLog, we need to find a version hash to tag
                    # This is simplified - in practice, you'd map Git commits to ChronoLog versions
                    
                    # For now, create a tag with description
                    try:
                        # Find latest version to tag (simplified)
                        history = self.chronolog_repo.log(".")
                        if history:
                            latest_version = history[0]['version_hash']
                            self.chronolog_repo.tag(tag_name, latest_version, message)
                            stats.tags_imported += 1
                    except:
                        pass
                
            except Exception as e:
                stats.errors.append(f"Failed to import tag {tag_name}: {e}")
    
    def _get_git_branches(self, git_repo_path: Path) -> List[str]:
        """Get list of all Git branches."""
        try:
            branches_output = self._run_git_command(["branch", "-a"], git_repo_path)
            branches = []
            
            for line in branches_output.split('\n'):
                line = line.strip()
                if line and not line.startswith('*'):
                    # Remove 'origin/' prefix if present
                    branch = line.replace('remotes/origin/', '').strip()
                    if branch and branch not in branches:
                        branches.append(branch)
            
            return branches
            
        except:
            return ["main"]
    
    def _run_git_command(self, cmd: List[str], cwd: Path) -> str:
        """Run a Git command and return output."""
        full_cmd = ["git"] + cmd
        
        result = subprocess.run(
            full_cmd,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(full_cmd)}\n{result.stderr}")
        
        return result.stdout
    
    def import_specific_files(self, git_repo_path: Path, files: List[str],
                            import_history: bool = True) -> ImportStats:
        """
        Import specific files from Git repository.
        
        Args:
            git_repo_path: Path to Git repository
            files: List of file paths to import
            import_history: Whether to import full history of files
            
        Returns:
            Import statistics
        """
        stats = ImportStats(0, 0, 0, 0, [])
        
        if not (git_repo_path / ".git").exists():
            stats.errors.append("Not a Git repository")
            return stats
        
        try:
            if import_history:
                for file_path in files:
                    try:
                        self._import_file_history(git_repo_path, file_path, stats)
                    except Exception as e:
                        stats.errors.append(f"Failed to import history of {file_path}: {e}")
            else:
                self._import_current_files(git_repo_path, files, stats)
            
            return stats
            
        except Exception as e:
            stats.errors.append(f"Import failed: {e}")
            return stats
    
    def _import_file_history(self, git_repo_path: Path, file_path: str, stats: ImportStats):
        """Import full history of a single file from Git."""
        # Get file history
        try:
            history_output = self._run_git_command([
                "log", "--reverse", "--format=%H|%at|%s", "--", file_path
            ], git_repo_path)
        except:
            stats.errors.append(f"No history found for {file_path}")
            return
        
        commits = []
        for line in history_output.strip().split('\n'):
            if line:
                parts = line.split('|', 2)
                if len(parts) >= 3:
                    commits.append({
                        'hash': parts[0],
                        'timestamp': int(parts[1]),
                        'message': parts[2]
                    })
        
        # Import each version
        for commit in commits:
            try:
                # Checkout commit
                self._run_git_command(["checkout", commit['hash']], git_repo_path)
                
                # Copy file if it exists
                src_path = git_repo_path / file_path
                if src_path.exists():
                    dst_path = self.repo_path / file_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    
                    # Set timestamp
                    timestamp = commit['timestamp']
                    os.utime(dst_path, (timestamp, timestamp))
                
                stats.files_imported += 1
                
            except Exception as e:
                stats.errors.append(f"Failed to import {file_path} at commit {commit['hash']}: {e}")
    
    def _import_current_files(self, git_repo_path: Path, files: List[str], stats: ImportStats):
        """Import only current versions of files from Git."""
        # Ensure we're on latest commit
        self._run_git_command(["checkout", "HEAD"], git_repo_path)
        
        for file_path in files:
            try:
                src_path = git_repo_path / file_path
                if src_path.exists() and not src_path.is_dir():
                    dst_path = self.repo_path / file_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    stats.files_imported += 1
                
            except Exception as e:
                stats.errors.append(f"Failed to import {file_path}: {e}")
    
    def create_chronolog_ignore_from_gitignore(self, git_repo_path: Path):
        """Create .chronologignore from .gitignore."""
        gitignore_path = git_repo_path / ".gitignore"
        chronolog_ignore_path = self.repo_path / ".chronologignore"
        
        if gitignore_path.exists():
            # Read .gitignore
            gitignore_content = gitignore_path.read_text()
            
            # Add ChronoLog-specific patterns
            chronolog_content = f"""# Imported from .gitignore
{gitignore_content}

# ChronoLog specific
.chronolog/
"""
            
            chronolog_ignore_path.write_text(chronolog_content)
    
    def sync_with_git(self, git_repo_path: Path, 
                     sync_direction: str = "bidirectional") -> ImportStats:
        """
        Synchronize ChronoLog repository with Git repository.
        
        Args:
            git_repo_path: Path to Git repository
            sync_direction: "import", "export", or "bidirectional"
            
        Returns:
            Sync statistics
        """
        stats = ImportStats(0, 0, 0, 0, [])
        
        if sync_direction in ["import", "bidirectional"]:
            # Import new commits from Git
            try:
                # This is simplified - would need to track what's already imported
                import_stats = self.import_from_git(git_repo_path)
                stats.commits_imported += import_stats.commits_imported
                stats.files_imported += import_stats.files_imported
                stats.errors.extend(import_stats.errors)
            except Exception as e:
                stats.errors.append(f"Import sync failed: {e}")
        
        if sync_direction in ["export", "bidirectional"]:
            # Export new changes to Git
            try:
                from .git_exporter import GitExporter
                exporter = GitExporter(self.chronolog_repo)
                export_stats = exporter.export_to_git(git_repo_path)
                # Note: ImportStats and ExportStats have different fields
                stats.errors.extend(export_stats.errors)
            except Exception as e:
                stats.errors.append(f"Export sync failed: {e}")
        
        return stats