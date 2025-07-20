"""Dashboard view for ChronoLog TUI."""

from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from textual.reactive import reactive

from ..api_bridge import ChronologBridge, RepositoryStatus


class DashboardView(Static):
    """Main dashboard view showing repository status and information."""
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
        self._status: RepositoryStatus = bridge.get_repository_status()
    
    def compose(self) -> ComposeResult:
        """Create the dashboard layout."""
        yield Vertical(
            Static("ChronoLog Repository Dashboard", id="dashboard-title"),
            Horizontal(
                Vertical(
                    Label("Repository Status:", classes="label"),
                    Label(self._get_repo_status_text(), id="repo-status"),
                    Label("Repository Path:", classes="label"),
                    Label(self._get_repo_path_text(), id="repo-path"),
                    classes="status-column"
                ),
                Vertical(
                    Label("Daemon Status:", classes="label"),
                    Label(self._get_daemon_status_text(), id="daemon-status"),
                    Label("Actions Available:", classes="label"),
                    Label(self._get_actions_text(), id="available-actions"),
                    classes="status-column"
                ),
                classes="status-container"
            ),
            Static(self._get_instructions_text(), id="instructions"),
            classes="dashboard-content"
        )
    
    def on_mount(self):
        """Set up the dashboard when mounted."""
        self.refresh_status()
    
    def refresh_status(self):
        """Refresh the repository status and update display."""
        self._status = self.bridge.get_repository_status()
        
        # Update status labels
        repo_status_label = self.query_one("#repo-status", Label)
        repo_path_label = self.query_one("#repo-path", Label)
        daemon_status_label = self.query_one("#daemon-status", Label)
        actions_label = self.query_one("#available-actions", Label)
        
        repo_status_label.update(self._get_repo_status_text())
        repo_path_label.update(self._get_repo_path_text())
        daemon_status_label.update(self._get_daemon_status_text())
        actions_label.update(self._get_actions_text())
        
        # Update status colors
        if self._status.is_repository:
            repo_status_label.add_class("status-good")
            repo_status_label.remove_class("status-error")
        else:
            repo_status_label.add_class("status-error")
            repo_status_label.remove_class("status-good")
        
        if self._status.daemon_running:
            daemon_status_label.add_class("status-good")
            daemon_status_label.remove_class("status-warning")
        else:
            daemon_status_label.add_class("status-warning")
            daemon_status_label.remove_class("status-good")
    
    def _get_repo_status_text(self) -> str:
        """Get repository status text."""
        if self._status.is_repository:
            return "✓ Repository Found"
        else:
            error = self._status.error_message or "Not a ChronoLog repository"
            return f"✗ {error}"
    
    def _get_repo_path_text(self) -> str:
        """Get repository path text."""
        if self._status.repo_path:
            return str(self._status.repo_path)
        else:
            return "No repository detected"
    
    def _get_daemon_status_text(self) -> str:
        """Get daemon status text."""
        if not self._status.is_repository:
            return "N/A (No repository)"
        elif self._status.daemon_running:
            return "✓ Running (File watching active)"
        else:
            return "⚠ Stopped (Files not being tracked)"
    
    def _get_actions_text(self) -> str:
        """Get available actions text."""
        if self._status.is_repository:
            return "View History [h] • Toggle Daemon [d]"
        else:
            return "Initialize Repository [i]"
    
    def _get_instructions_text(self) -> str:
        """Get instructions text based on current state."""
        if not self._status.is_repository:
            return (
                "Welcome to ChronoLog TUI!\n\n"
                "This directory is not yet a ChronoLog repository. "
                "Press [i] to initialize a new repository, or navigate to "
                "an existing ChronoLog repository.\n\n"
                "ChronoLog will automatically track file changes once initialized."
            )
        else:
            files_info = self._get_tracked_files_info()
            return (
                f"Repository is ready! {files_info}\n\n"
                "• Press [h] to view file history and versions\n"
                "• Press [d] to start/stop the file watching daemon\n"
                "• Press [q] to quit the application\n\n"
                "The daemon automatically creates new versions when files change."
            )
    
    def _get_tracked_files_info(self) -> str:
        """Get information about tracked files."""
        try:
            all_files = self.bridge.get_all_files_with_history()
            file_count = len(all_files)
            total_versions = sum(len(history) for history in all_files.values())
            
            if file_count == 0:
                return "No files tracked yet."
            elif file_count == 1:
                return f"Tracking 1 file with {total_versions} version(s)."
            else:
                return f"Tracking {file_count} files with {total_versions} total versions."
        except Exception:
            return "Repository status unknown."