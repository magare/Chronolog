import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ExportStats:
    commits_created: int
    files_exported: int
    branches_created: int
    tags_created: int
    errors: List[str]


class GitExporter:
    """Export ChronoLog repository history to Git."""
    
    def __init__(self, chronolog_repo):
        self.chronolog_repo = chronolog_repo
        self.repo_path = Path(chronolog_repo.repo_path)
    
    def export_to_git(self, git_repo_path: Path, 
                     export_branches: bool = True,
                     export_tags: bool = True,
                     author_name: str = "ChronoLog",
                     author_email: str = "chronolog@localhost") -> ExportStats:
        """
        Export entire ChronoLog repository to Git.
        
        Args:
            git_repo_path: Path where Git repository will be created
            export_branches: Whether to export branches
            export_tags: Whether to export tags
            author_name: Git author name
            author_email: Git author email
            
        Returns:
            Export statistics
        """
        stats = ExportStats(0, 0, 0, 0, [])
        
        try:
            # Create Git repository
            git_repo_path.mkdir(parents=True, exist_ok=True)
            self._run_git_command(["init"], git_repo_path)
            
            # Configure Git
            self._run_git_command(["config", "user.name", author_name], git_repo_path)
            self._run_git_command(["config", "user.email", author_email], git_repo_path)
            
            # Export main branch first
            main_commits = self._export_branch("main", git_repo_path, stats)
            
            # Export other branches if requested
            if export_branches:
                branches = self.chronolog_repo.list_branches()
                for branch in branches:
                    if branch['name'] != 'main':
                        try:
                            self._export_branch(branch['name'], git_repo_path, stats)
                            stats.branches_created += 1
                        except Exception as e:
                            stats.errors.append(f"Failed to export branch {branch['name']}: {e}")
            
            # Export tags if requested
            if export_tags:
                try:
                    self._export_tags(git_repo_path, stats)
                except Exception as e:
                    stats.errors.append(f"Failed to export tags: {e}")
            
            return stats
            
        except Exception as e:
            stats.errors.append(f"Export failed: {e}")
            return stats
    
    def _export_branch(self, branch_name: str, git_repo_path: Path, stats: ExportStats) -> Dict[str, str]:
        """
        Export a specific branch to Git.
        
        Returns:
            Dictionary mapping ChronoLog version hashes to Git commit hashes
        """
        commit_mapping = {}
        
        # Switch to branch
        if branch_name != 'main':
            try:
                self._run_git_command(["checkout", "-b", branch_name], git_repo_path)
            except:
                # Branch might already exist
                self._run_git_command(["checkout", branch_name], git_repo_path)
        
        # Get all file histories in this branch
        all_files = self._get_all_tracked_files(branch_name)
        
        # Build timeline of all changes
        timeline = []
        for file_path in all_files:
            history = self.chronolog_repo.log(file_path)
            for version in history:
                timeline.append({
                    'timestamp': datetime.fromisoformat(version['timestamp']),
                    'file_path': file_path,
                    'version_hash': version['version_hash'],
                    'annotation': version.get('annotation', ''),
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        # Group by timestamp to create commits
        commits = {}
        for item in timeline:
            timestamp_key = item['timestamp'].isoformat()
            if timestamp_key not in commits:
                commits[timestamp_key] = {
                    'timestamp': item['timestamp'],
                    'files': [],
                    'message': item['annotation'] or f"ChronoLog update at {item['timestamp']}"
                }
            commits[timestamp_key]['files'].append(item)
        
        # Create Git commits
        for timestamp_key, commit_data in sorted(commits.items()):
            try:
                commit_hash = self._create_git_commit(
                    commit_data['files'],
                    commit_data['message'],
                    commit_data['timestamp'],
                    git_repo_path
                )
                
                # Map all version hashes to this Git commit
                for file_data in commit_data['files']:
                    commit_mapping[file_data['version_hash']] = commit_hash
                
                stats.commits_created += 1
                
            except Exception as e:
                stats.errors.append(f"Failed to create commit at {timestamp_key}: {e}")
        
        return commit_mapping
    
    def _create_git_commit(self, files: List[Dict], message: str, 
                          timestamp: datetime, git_repo_path: Path) -> str:
        """Create a single Git commit."""
        # Copy files to Git repository
        for file_data in files:
            src_path = self.repo_path / file_data['file_path']
            dst_path = git_repo_path / file_data['file_path']
            
            # Get file content from ChronoLog
            content = self.chronolog_repo.show(file_data['version_hash'])
            
            # Create directory structure
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            dst_path.write_bytes(content)
        
        # Add files to Git
        self._run_git_command(["add", "."], git_repo_path)
        
        # Create commit with specific timestamp
        env = os.environ.copy()
        env['GIT_AUTHOR_DATE'] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        env['GIT_COMMITTER_DATE'] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        result = self._run_git_command(
            ["commit", "-m", message],
            git_repo_path,
            env=env
        )
        
        # Get commit hash
        commit_hash = self._run_git_command(
            ["rev-parse", "HEAD"],
            git_repo_path
        ).strip()
        
        return commit_hash
    
    def _export_tags(self, git_repo_path: Path, stats: ExportStats):
        """Export ChronoLog tags to Git."""
        tags = self.chronolog_repo.list_tags()
        
        for tag in tags:
            try:
                # Find corresponding Git commit
                # This is simplified - in practice, you'd need to map version hashes to commits
                tag_name = tag['tag_name']
                description = tag.get('description', f"ChronoLog tag: {tag_name}")
                
                # Create annotated tag
                self._run_git_command([
                    "tag", "-a", tag_name, "-m", description
                ], git_repo_path)
                
                stats.tags_created += 1
                
            except Exception as e:
                stats.errors.append(f"Failed to create tag {tag['tag_name']}: {e}")
    
    def _get_all_tracked_files(self, branch_name: str = None) -> List[str]:
        """Get all files tracked by ChronoLog."""
        # This is a simplified implementation
        # In practice, you'd query the storage for all files in the branch
        all_files = set()
        
        for root, dirs, files in os.walk(self.repo_path):
            if '.chronolog' in root:
                continue
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.repo_path)
                all_files.add(str(rel_path))
        
        return list(all_files)
    
    def _run_git_command(self, cmd: List[str], cwd: Path, env: Optional[Dict] = None) -> str:
        """Run a Git command and return output."""
        full_cmd = ["git"] + cmd
        
        result = subprocess.run(
            full_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env or os.environ
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(full_cmd)}\n{result.stderr}")
        
        return result.stdout
    
    def export_specific_files(self, files: List[str], git_repo_path: Path,
                            include_history: bool = True) -> ExportStats:
        """
        Export specific files to Git repository.
        
        Args:
            files: List of file paths to export
            git_repo_path: Target Git repository path
            include_history: Whether to include full history
            
        Returns:
            Export statistics
        """
        stats = ExportStats(0, 0, 0, 0, [])
        
        try:
            # Ensure Git repo exists
            if not (git_repo_path / ".git").exists():
                git_repo_path.mkdir(parents=True, exist_ok=True)
                self._run_git_command(["init"], git_repo_path)
            
            if include_history:
                # Export with full history
                for file_path in files:
                    try:
                        self._export_file_history(file_path, git_repo_path, stats)
                    except Exception as e:
                        stats.errors.append(f"Failed to export {file_path}: {e}")
            else:
                # Export only current versions
                self._export_current_files(files, git_repo_path, stats)
            
            return stats
            
        except Exception as e:
            stats.errors.append(f"Export failed: {e}")
            return stats
    
    def _export_file_history(self, file_path: str, git_repo_path: Path, stats: ExportStats):
        """Export full history of a single file."""
        history = self.chronolog_repo.log(file_path)
        
        for version in reversed(history):  # Oldest first
            try:
                # Get file content
                content = self.chronolog_repo.show(version['version_hash'])
                
                # Write to Git repo
                target_path = git_repo_path / file_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(content)
                
                # Add and commit
                self._run_git_command(["add", file_path], git_repo_path)
                
                message = version.get('annotation') or f"Update {file_path}"
                timestamp = datetime.fromisoformat(version['timestamp'])
                
                env = os.environ.copy()
                env['GIT_AUTHOR_DATE'] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                env['GIT_COMMITTER_DATE'] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                self._run_git_command(
                    ["commit", "-m", message],
                    git_repo_path,
                    env=env
                )
                
                stats.commits_created += 1
                
            except Exception as e:
                stats.errors.append(f"Failed to export version {version['version_hash']} of {file_path}: {e}")
        
        stats.files_exported += 1
    
    def _export_current_files(self, files: List[str], git_repo_path: Path, stats: ExportStats):
        """Export only current versions of files."""
        try:
            for file_path in files:
                # Get current file
                current_file = self.repo_path / file_path
                if current_file.exists():
                    target_path = git_repo_path / file_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(current_file, target_path)
                    stats.files_exported += 1
            
            # Single commit for all files
            self._run_git_command(["add", "."], git_repo_path)
            self._run_git_command([
                "commit", "-m", "ChronoLog export - current versions"
            ], git_repo_path)
            
            stats.commits_created += 1
            
        except Exception as e:
            stats.errors.append(f"Failed to export current files: {e}")
    
    def create_gitignore(self, git_repo_path: Path):
        """Create a .gitignore file excluding ChronoLog directory."""
        gitignore_path = git_repo_path / ".gitignore"
        
        gitignore_content = """# ChronoLog directory
.chronolog/

# Common files to ignore
*.tmp
*.swp
.DS_Store
Thumbs.db
"""
        
        gitignore_path.write_text(gitignore_content)