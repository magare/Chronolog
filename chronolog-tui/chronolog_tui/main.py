"""Main application entry point for ChronoLog TUI."""

import signal
import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label, DataTable, Input
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal

from .views.dashboard_view import DashboardView
from .views.history_view import HistoryView
from .api_bridge import ChronologBridge


class DashboardScreen(Screen):
    """Main dashboard screen showing repository status."""
    
    BINDINGS = [
        Binding("h", "show_history", "History"),
        Binding("i", "init_repo", "Initialize"),
        Binding("d", "toggle_daemon", "Toggle Daemon"),
        Binding("b", "show_branches", "Branches"),
        Binding("t", "show_tags", "Tags"),
        Binding("s", "show_search", "Search"),
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
    
    def action_show_branches(self):
        """Show the branches view."""
        status = self.bridge.get_repository_status()
        if not status.is_repository:
            self.notify("No repository found", severity="error")
            return
        self.app.push_screen(BranchScreen(self.bridge))
    
    def action_show_tags(self):
        """Show the tags view."""
        status = self.bridge.get_repository_status()
        if not status.is_repository:
            self.notify("No repository found", severity="error")
            return
        self.app.push_screen(TagScreen(self.bridge))
    
    def action_show_search(self):
        """Show the search view."""
        status = self.bridge.get_repository_status()
        if not status.is_repository:
            self.notify("No repository found", severity="error")
            return
        self.app.push_screen(SearchScreen(self.bridge))


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


class BranchScreen(Screen):
    """Screen for managing branches."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("n", "new_branch", "New Branch"),
        Binding("s", "switch_branch", "Switch"),
        Binding("d", "delete_branch", "Delete"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
    
    def compose(self) -> ComposeResult:
        from textual.widgets import DataTable
        from textual.containers import Container
        
        yield Header()
        yield Container(
            Label("Branch Management", id="branch-title"),
            DataTable(id="branches-table"),
            Label("Actions: [n]ew • [s]witch • [d]elete • [Esc]ape", id="branch-actions"),
            id="branch-container"
        )
        yield Footer()
    
    def on_mount(self):
        """Set up the branches table when mounted."""
        table = self.query_one("#branches-table", DataTable)
        table.add_columns("Branch Name", "Created", "Parent", "Status")
        table.cursor_type = "row"
        self._load_branches()
    
    def _load_branches(self):
        """Load branches into the table."""
        table = self.query_one("#branches-table", DataTable)
        table.clear()
        
        current, branches = self.bridge.get_branches()
        for branch in branches:
            created_at = datetime.fromisoformat(branch['created_at']).strftime('%Y-%m-%d %H:%M')
            parent = branch['parent'] or "none"
            status = "* Current" if branch['name'] == current else ""
            table.add_row(branch['name'], created_at, parent, status)
    
    def action_back(self):
        """Go back to the dashboard."""
        self.app.pop_screen()
    
    def action_new_branch(self):
        """Create a new branch."""
        from textual.widgets import Input
        from textual.containers import Container
        from textual.screen import ModalScreen
        
        class NewBranchModal(ModalScreen):
            def __init__(self, parent_screen):
                super().__init__()
                self.parent_screen = parent_screen
            
            def compose(self) -> ComposeResult:
                yield Container(
                    Label("Create New Branch"),
                    Input(placeholder="Branch name", id="branch-name"),
                    Label("Press Enter to create, Escape to cancel"),
                    id="modal-container"
                )
            
            def on_input_submitted(self, event):
                branch_name = event.value.strip()
                if branch_name:
                    success, message = self.parent_screen.bridge.create_branch(branch_name)
                    self.parent_screen.notify(message, severity="information" if success else "error")
                    if success:
                        self.parent_screen._load_branches()
                self.app.pop_screen()
        
        self.app.push_screen(NewBranchModal(self))
    
    def action_switch_branch(self):
        """Switch to selected branch."""
        table = self.query_one("#branches-table", DataTable)
        if table.row_count > 0:
            row_data = table.get_row(table.cursor_row)
            branch_name = str(row_data[0])
            success, message = self.bridge.switch_branch(branch_name)
            self.notify(message, severity="information" if success else "error")
            if success:
                self._load_branches()
    
    def action_delete_branch(self):
        """Delete selected branch."""
        table = self.query_one("#branches-table", DataTable)
        if table.row_count > 0:
            row_data = table.get_row(table.cursor_row)
            branch_name = str(row_data[0])
            success, message = self.bridge.delete_branch(branch_name)
            self.notify(message, severity="information" if success else "error")
            if success:
                self._load_branches()


class TagScreen(Screen):
    """Screen for managing tags."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("n", "new_tag", "New Tag"),
        Binding("d", "delete_tag", "Delete"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
    
    def compose(self) -> ComposeResult:
        from textual.widgets import DataTable
        from textual.containers import Container
        
        yield Header()
        yield Container(
            Label("Tag Management", id="tag-title"),
            DataTable(id="tags-table"),
            Label("Actions: [n]ew • [d]elete • [Esc]ape", id="tag-actions"),
            id="tag-container"
        )
        yield Footer()
    
    def on_mount(self):
        """Set up the tags table when mounted."""
        table = self.query_one("#tags-table", DataTable)
        table.add_columns("Tag Name", "Version", "Created", "Description")
        table.cursor_type = "row"
        self._load_tags()
    
    def _load_tags(self):
        """Load tags into the table."""
        table = self.query_one("#tags-table", DataTable)
        table.clear()
        
        tags = self.bridge.get_tags()
        if not tags:
            table.add_row("No tags found", "", "", "")
            return
        
        for tag in tags:
            created_at = datetime.fromisoformat(tag['timestamp']).strftime('%Y-%m-%d %H:%M')
            hash_short = tag['hash'][:8]
            description = tag['description'] or ""
            table.add_row(tag['name'], hash_short, created_at, description)
    
    def action_back(self):
        """Go back to the dashboard."""
        self.app.pop_screen()
    
    def action_new_tag(self):
        """Create a new tag."""
        from textual.widgets import Input
        from textual.containers import Container
        from textual.screen import ModalScreen
        
        class NewTagModal(ModalScreen):
            def __init__(self, parent_screen):
                super().__init__()
                self.parent_screen = parent_screen
            
            def compose(self) -> ComposeResult:
                yield Container(
                    Label("Create New Tag"),
                    Input(placeholder="Tag name", id="tag-name"),
                    Input(placeholder="Description (optional)", id="tag-description"),
                    Label("Press Enter to create, Escape to cancel"),
                    id="modal-container"
                )
            
            def on_input_submitted(self, event):
                if event.input.id == "tag-name":
                    self.query_one("#tag-description", Input).focus()
                elif event.input.id == "tag-description":
                    tag_name = self.query_one("#tag-name", Input).value.strip()
                    description = event.value.strip() or None
                    if tag_name:
                        success, message = self.parent_screen.bridge.create_tag(tag_name, None, description)
                        self.parent_screen.notify(message, severity="information" if success else "error")
                        if success:
                            self.parent_screen._load_tags()
                    self.app.pop_screen()
        
        self.app.push_screen(NewTagModal(self))
    
    def action_delete_tag(self):
        """Delete selected tag."""
        table = self.query_one("#tags-table", DataTable)
        if table.row_count > 0:
            row_data = table.get_row(table.cursor_row)
            tag_name = str(row_data[0])
            if tag_name != "No tags found":
                success, message = self.bridge.delete_tag(tag_name)
                self.notify(message, severity="information" if success else "error")
                if success:
                    self._load_tags()


class SearchScreen(Screen):
    """Screen for searching content in the repository."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "perform_search", "Search", show=False),
        Binding("r", "toggle_regex", "Regex"),
        Binding("c", "toggle_case", "Case"),
        Binding("w", "toggle_words", "Words"),
        Binding("v", "view_result", "View"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
        self.search_options = {
            "regex": False,
            "case_sensitive": False,
            "whole_words": False
        }
        self.results = []
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Search Repository", id="search-title"),
            Horizontal(
                Input(placeholder="Enter search query...", id="search-input"),
                Label("[r]egex [c]ase [w]ords", id="search-options"),
                id="search-bar"
            ),
            DataTable(id="search-results"),
            Label("Enter to search • Arrow keys to navigate • [v]iew result • [Esc]ape", 
                  id="search-instructions"),
            id="search-container"
        )
        yield Footer()
    
    def on_mount(self):
        """Set up the search screen when mounted."""
        table = self.query_one("#search-results", DataTable)
        table.add_columns("Hash", "File", "Timestamp", "Match")
        table.cursor_type = "row"
        
        # Focus on search input
        self.query_one("#search-input", Input).focus()
        self._update_options_display()
    
    def on_input_submitted(self, event):
        """Handle search input submission."""
        self.action_perform_search()
    
    def action_perform_search(self):
        """Perform the search."""
        search_input = self.query_one("#search-input", Input)
        query = search_input.value.strip()
        
        if not query:
            return
        
        # Clear previous results
        table = self.query_one("#search-results", DataTable)
        table.clear()
        
        # Use advanced search if any options are enabled
        if any(self.search_options.values()):
            self.results = self.bridge.advanced_search(
                query,
                regex=self.search_options["regex"],
                case_sensitive=self.search_options["case_sensitive"],
                whole_words=self.search_options["whole_words"]
            )
        else:
            # Use simple search
            self.results = self.bridge.search_content(query)
        
        if not self.results:
            table.add_row("No results found", "", "", "")
            return
        
        # Display results
        for result in self.results:
            timestamp = datetime.fromisoformat(result['timestamp']).strftime('%Y-%m-%d %H:%M')
            hash_short = result['hash'][:8]
            file_path = result['file_path']
            
            # Truncate long file paths
            if len(file_path) > 30:
                file_path = "..." + file_path[-27:]
            
            table.add_row(hash_short, file_path, timestamp, f"Found '{query}'")
    
    def action_toggle_regex(self):
        """Toggle regex search option."""
        self.search_options["regex"] = not self.search_options["regex"]
        self._update_options_display()
        self.notify(f"Regex search: {'ON' if self.search_options['regex'] else 'OFF'}", 
                   severity="information")
    
    def action_toggle_case(self):
        """Toggle case sensitive option."""
        self.search_options["case_sensitive"] = not self.search_options["case_sensitive"]
        self._update_options_display()
        self.notify(f"Case sensitive: {'ON' if self.search_options['case_sensitive'] else 'OFF'}", 
                   severity="information")
    
    def action_toggle_words(self):
        """Toggle whole words option."""
        self.search_options["whole_words"] = not self.search_options["whole_words"]
        self._update_options_display()
        self.notify(f"Whole words: {'ON' if self.search_options['whole_words'] else 'OFF'}", 
                   severity="information")
    
    def _update_options_display(self):
        """Update the options display."""
        options = []
        if self.search_options["regex"]:
            options.append("[R]egex")
        else:
            options.append("[r]egex")
        
        if self.search_options["case_sensitive"]:
            options.append("[C]ase")
        else:
            options.append("[c]ase")
        
        if self.search_options["whole_words"]:
            options.append("[W]ords")
        else:
            options.append("[w]ords")
        
        self.query_one("#search-options", Label).update(" ".join(options))
    
    def action_view_result(self):
        """View the selected search result."""
        table = self.query_one("#search-results", DataTable)
        if table.row_count > 0 and self.results:
            row_index = table.cursor_row
            if row_index < len(self.results):
                result = self.results[row_index]
                # Show the file detail screen for this version
                from .views.history_view import FileDetailScreen
                detail_screen = FileDetailScreen(self.bridge, result['hash'], result['file_path'])
                self.app.push_screen(detail_screen)
    
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
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for proper cleanup."""
        # Handle SIGTSTP (Ctrl+Z) to disable mouse tracking when suspended
        signal.signal(signal.SIGTSTP, self._handle_suspend)
        # Handle SIGCONT to re-enable mouse tracking when resumed
        signal.signal(signal.SIGCONT, self._handle_resume)
    
    def _handle_suspend(self, signum, frame):
        """Handle suspension signal - disable mouse tracking."""
        try:
            # Send escape sequence to disable mouse tracking
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l')
            sys.stdout.flush()
        except:
            pass
        # Continue with default suspension behavior
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        signal.raise_signal(signal.SIGTSTP)
    
    def _handle_resume(self, signum, frame):
        """Handle resume signal - re-enable mouse tracking if app is active."""
        try:
            # Re-enable mouse tracking only if our app is the active one
            sys.stdout.write('\033[?1000h\033[?1002h\033[?1006h')
            sys.stdout.flush()
        except:
            pass
        # Restore our signal handler
        signal.signal(signal.SIGTSTP, self._handle_suspend)
    
    def on_mount(self):
        """Set up the initial screen when the app starts."""
        self.push_screen(DashboardScreen(self.bridge))
    
    def on_app_suspend(self):
        """Called when the app is suspended - disable mouse tracking."""
        try:
            # Disable mouse tracking when app loses focus
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l')
            sys.stdout.flush()
        except:
            pass
    
    def on_app_resume(self):
        """Called when the app is resumed - re-enable mouse tracking."""
        try:
            # Re-enable mouse tracking when app regains focus
            sys.stdout.write('\033[?1000h\033[?1002h\033[?1006h')
            sys.stdout.flush()
        except:
            pass
    
    def on_focus(self) -> None:
        """Called when the application gains focus."""
        try:
            # Re-enable mouse tracking when app gains focus
            sys.stdout.write('\033[?1000h\033[?1002h\033[?1006h')
            sys.stdout.flush()
        except:
            pass
    
    def on_blur(self) -> None:
        """Called when the application loses focus."""
        try:
            # Disable mouse tracking when app loses focus
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l')
            sys.stdout.flush()
        except:
            pass
    
    def action_quit(self) -> None:
        """Override quit action to ensure cleanup."""
        try:
            # Disable mouse tracking before quitting
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l')
            sys.stdout.flush()
        except:
            pass
        super().action_quit()
    
    def exit(self, return_code: int = 0, message: str | None = None) -> None:
        """Override exit to ensure proper cleanup."""
        try:
            # Disable mouse tracking before exiting
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l')
            sys.stdout.flush()
        except:
            pass
        super().exit(return_code, message)
    
    def action_help(self):
        """Show help information."""
        help_text = """
ChronoLog TUI - Keyboard Shortcuts

Dashboard:
  h       - Show file history
  s       - Search content
  i       - Initialize repository
  d       - Toggle daemon on/off
  b       - Manage branches
  t       - Manage tags
  q       - Quit application

History View:
  ↑/↓     - Navigate up/down in active table
  ←/→     - Switch between Files and Versions tables
  Tab     - Switch focus between tables
  Enter   - Select file/version (view details)
  Escape  - Back to dashboard

File Detail View:
  c       - Checkout selected version
  d       - Show diff with current file
  Escape  - Back to history

Search:
  Enter   - Perform search
  r       - Toggle regex mode
  c       - Toggle case sensitive
  w       - Toggle whole words
  v       - View selected result
  Escape  - Back to dashboard

Branch Management:
  n       - Create new branch
  s       - Switch to selected branch
  d       - Delete selected branch
  Escape  - Back to dashboard

Tag Management:
  n       - Create new tag
  d       - Delete selected tag
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
    try:
        app.run()
    finally:
        # Ensure mouse tracking is disabled on exit, even if app crashes
        try:
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l')
            sys.stdout.flush()
        except:
            pass


if __name__ == "__main__":
    main()