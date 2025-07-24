"""History view for ChronoLog TUI showing file versions and details."""

from textual.widgets import Static, DataTable, Label
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.events import Key

from ..api_bridge import ChronologBridge


class FileDetailScreen(Screen):
    """Screen showing detailed version information and diff."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("c", "checkout", "Checkout"),
        Binding("d", "diff_current", "Diff with Current"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, bridge: ChronologBridge, version_hash: str, file_path: str):
        super().__init__()
        self.bridge = bridge
        self.version_hash = version_hash
        self.file_path = file_path
    
    def compose(self) -> ComposeResult:
        """Create the file detail layout."""
        yield Vertical(
            Label(f"Version Details: {self.file_path}", id="detail-title"),
            Horizontal(
                Vertical(
                    Label(f"Hash: {self.version_hash}"),
                    Label(f"File: {self.file_path}"),
                    Label("Actions: [c]heckout • [d]iff • [Esc]ape"),
                    classes="detail-info"
                ),
                classes="detail-header"
            ),
            Static(self._get_version_content(), id="version-content"),
            classes="detail-content"
        )
    
    def action_back(self):
        """Go back to history view."""
        self.app.pop_screen()
    
    def action_checkout(self):
        """Checkout this version."""
        success, message = self.bridge.checkout_version(self.version_hash, self.file_path)
        if success:
            self.notify(message, severity="information")
        else:
            self.notify(message, severity="error")
    
    def action_diff_current(self):
        """Show diff with current file."""
        diff = self.bridge.get_version_diff(self.version_hash, current=True)
        if diff:
            self.query_one("#version-content", Static).update(diff)
        else:
            self.notify("No differences or error generating diff", severity="warning")
    
    def _get_version_content(self) -> str:
        """Get the content of this version."""
        content = self.bridge.show_version_content(self.version_hash)
        if content is None:
            return "Error: Could not load version content"
        elif content == "[Binary file content]":
            return "This is a binary file. Content cannot be displayed."
        else:
            # Limit content size for display
            lines = content.split('\n')
            if len(lines) > 100:
                displayed_lines = lines[:100]
                displayed_lines.append(f"\n... ({len(lines) - 100} more lines)")
                return '\n'.join(displayed_lines)
            return content


class HistoryView(Static):
    """History view showing files and their versions."""
    
    BINDINGS = [
        Binding("up", "navigate_up", "Navigate up", show=False),
        Binding("down", "navigate_down", "Navigate down", show=False),
        Binding("left", "switch_to_files", "Files table", show=False),
        Binding("right", "switch_to_versions", "Versions table", show=False),
        Binding("tab", "switch_focus", "Switch focus", show=False),
        Binding("shift+tab", "switch_focus_reverse", "Switch focus reverse", show=False),
        Binding("enter", "select_row", "Select", show=False),
    ]
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
        self.files_table = DataTable(id="files-table")
        self.versions_table = DataTable(id="versions-table")
        self.current_file = None
        self.active_table = "files"  # Track which table has focus
    
    def compose(self) -> ComposeResult:
        """Create the history view layout."""
        yield Vertical(
            Label("File History Browser", id="history-title"),
            Horizontal(
                Vertical(
                    Label("Files with History:"),
                    self.files_table,
                    classes="files-panel"
                ),
                Vertical(
                    Label("Versions:"),
                    self.versions_table,
                    classes="versions-panel"
                ),
                classes="history-container"
            ),
            Label("Use ↑/↓ to navigate, ←/→ or Tab to switch tables, Enter to select. Press F1 for help.", 
                  id="history-instructions"),
            classes="history-content"
        )
    
    def on_mount(self):
        """Set up the history view when mounted."""
        self._setup_tables()
        self._load_files()
        self._update_focus_styling()
    
    def _setup_tables(self):
        """Set up the data tables."""
        # Files table
        self.files_table.add_columns("File Path", "Versions")
        self.files_table.cursor_type = "row"
        
        # Versions table
        self.versions_table.add_columns("Hash", "Timestamp", "Annotation")
        self.versions_table.cursor_type = "row"
    
    def _load_files(self):
        """Load files with history into the files table."""
        try:
            all_files = self.bridge.get_all_files_with_history()
            
            if not all_files:
                self.files_table.add_row("No files with history found", "0")
                return
            
            for file_path, history in all_files.items():
                version_count = len(history)
                self.files_table.add_row(file_path, str(version_count))
        
        except Exception as e:
            self.files_table.add_row(f"Error loading files: {e}", "0")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Handle row selection in tables."""
        if event.data_table.id == "files-table":
            self._on_file_selected(event)
        elif event.data_table.id == "versions-table":
            self._on_version_selected(event)
    
    def _on_file_selected(self, event: DataTable.RowSelected):
        """Handle file selection."""
        row_key = event.row_key
        row_data = self.files_table.get_row(row_key)
        file_path = str(row_data[0])
        
        if file_path == "No files with history found" or file_path.startswith("Error"):
            return
        
        self.current_file = file_path
        self._load_versions(file_path)
    
    def _load_versions(self, file_path: str):
        """Load versions for the selected file."""
        self.versions_table.clear()
        
        try:
            history = self.bridge.get_file_history(file_path)
            
            if not history:
                self.versions_table.add_row("No versions found", "", "")
                return
            
            for entry in history:
                hash_short = entry.hash[:8]
                timestamp = entry.timestamp
                annotation = entry.annotation or ""
                self.versions_table.add_row(hash_short, timestamp, annotation)
        
        except Exception as e:
            self.versions_table.add_row(f"Error: {e}", "", "")
    
    def _on_version_selected(self, event: DataTable.RowSelected):
        """Handle version selection."""
        if not self.current_file:
            return
        
        row_key = event.row_key
        row_data = self.versions_table.get_row(row_key)
        hash_short = str(row_data[0])
        
        if hash_short == "No versions found" or hash_short.startswith("Error"):
            return
        
        # Find the full hash
        try:
            history = self.bridge.get_file_history(self.current_file)
            full_hash = None
            for entry in history:
                if entry.hash.startswith(hash_short):
                    full_hash = entry.hash
                    break
            
            if full_hash:
                # Show file detail screen
                detail_screen = FileDetailScreen(self.bridge, full_hash, self.current_file)
                self.app.push_screen(detail_screen)
            else:
                self.app.notify("Could not find full hash for version", severity="error")
        
        except Exception as e:
            self.app.notify(f"Error opening version details: {e}", severity="error")
    
    def action_navigate_up(self):
        """Navigate up in the active table."""
        table = self._get_active_table()
        if table.row_count > 0:
            current_cursor = table.cursor_row
            if current_cursor > 0:
                table.cursor_row = current_cursor - 1
    
    def action_navigate_down(self):
        """Navigate down in the active table."""
        table = self._get_active_table()
        if table.row_count > 0:
            current_cursor = table.cursor_row
            if current_cursor < table.row_count - 1:
                table.cursor_row = current_cursor + 1
    
    def action_switch_to_files(self):
        """Switch focus to the files table."""
        if self.active_table != "files":
            self.active_table = "files"
            self._update_focus_styling()
    
    def action_switch_to_versions(self):
        """Switch focus to the versions table."""
        if self.active_table != "versions":
            self.active_table = "versions"
            self._update_focus_styling()
    
    def action_switch_focus(self):
        """Switch focus between tables."""
        if self.active_table == "files":
            self.active_table = "versions"
        else:
            self.active_table = "files"
        self._update_focus_styling()
    
    def action_switch_focus_reverse(self):
        """Switch focus between tables in reverse direction."""
        # Same as switch_focus for two tables
        self.action_switch_focus()
    
    def action_select_row(self):
        """Select the current row in the active table."""
        table = self._get_active_table()
        if table.row_count > 0:
            # Simulate row selection event
            if self.active_table == "files":
                # Create a mock event-like object for file selection
                class MockEvent:
                    def __init__(self, row_key):
                        self.row_key = row_key
                        self.data_table = table
                
                mock_event = MockEvent(table.cursor_row)
                self._on_file_selected(mock_event)
            else:
                # Create a mock event for version selection
                class MockEvent:
                    def __init__(self, row_key):
                        self.row_key = row_key
                        self.data_table = table
                
                mock_event = MockEvent(table.cursor_row)
                self._on_version_selected(mock_event)
    
    def _get_active_table(self) -> DataTable:
        """Get the currently active table."""
        if self.active_table == "files":
            return self.files_table
        else:
            return self.versions_table
    
    def _update_focus_styling(self):
        """Update the visual styling to show which table has focus."""
        # Remove focus classes from both tables
        self.files_table.remove_class("table-focused")
        self.versions_table.remove_class("table-focused")
        
        # Add focus class to active table
        if self.active_table == "files":
            self.files_table.add_class("table-focused")
        else:
            self.versions_table.add_class("table-focused")