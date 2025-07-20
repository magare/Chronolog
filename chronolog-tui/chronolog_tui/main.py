"""Main application entry point for ChronoLog TUI."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.screen import Screen
from textual.binding import Binding

from .views.dashboard_view import DashboardView
from .views.history_view import HistoryView
from .api_bridge import ChronologBridge


class DashboardScreen(Screen):
    """Main dashboard screen showing repository status."""
    
    BINDINGS = [
        Binding("h", "show_history", "History"),
        Binding("i", "init_repo", "Initialize"),
        Binding("d", "toggle_daemon", "Toggle Daemon"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield DashboardView(self.bridge)
        yield Footer()
    
    def action_show_history(self):
        """Show the history view."""
        self.app.push_screen(HistoryScreen(self.bridge))
    
    def action_init_repo(self):
        """Initialize a new repository."""
        success, message = self.bridge.initialize_repository()
        if success:
            self.notify(message, severity="information")
            self.query_one(DashboardView).refresh_status()
        else:
            self.notify(message, severity="error")
    
    def action_toggle_daemon(self):
        """Toggle the daemon on/off."""
        status = self.bridge.get_repository_status()
        if not status.is_repository:
            self.notify("No repository found", severity="error")
            return
        
        if status.daemon_running:
            success, message = self.bridge.stop_daemon()
        else:
            success, message = self.bridge.start_daemon()
        
        if success:
            self.notify(message, severity="information")
            self.query_one(DashboardView).refresh_status()
        else:
            self.notify(message, severity="error")


class HistoryScreen(Screen):
    """Screen showing file history and version details."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield HistoryView(self.bridge)
        yield Footer()
    
    def action_back(self):
        """Go back to the dashboard."""
        self.app.pop_screen()


class ChronologTUIApp(App):
    """Main TUI application for ChronoLog."""
    
    CSS_PATH = "styles.css"
    TITLE = "ChronoLog TUI"
    SUB_TITLE = "File Version Control System"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("F1", "help", "Help"),
    ]
    
    def __init__(self, path: str = "."):
        super().__init__()
        self.bridge = ChronologBridge(path)
    
    def on_mount(self):
        """Set up the initial screen when the app starts."""
        self.push_screen(DashboardScreen(self.bridge))
    
    def action_help(self):
        """Show help information."""
        help_text = """
ChronoLog TUI - Keyboard Shortcuts

Dashboard:
  h       - Show file history
  i       - Initialize repository
  d       - Toggle daemon on/off
  q       - Quit application

History View:
  ↑/↓     - Navigate files/versions
  Enter   - View version details
  c       - Checkout selected version
  Escape  - Back to dashboard

General:
  F1      - Show this help
  Ctrl+C  - Quit application
        """
        self.notify(help_text.strip(), title="Help", timeout=10)


def main():
    """Main entry point for the TUI application."""
    import sys
    
    # Get the path from command line arguments or use current directory
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    app = ChronologTUIApp(path)
    app.run()


if __name__ == "__main__":
    main()