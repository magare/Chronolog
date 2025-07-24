"""File tree view for ChronoLog TUI."""

from pathlib import Path
from typing import List, Optional, Dict, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from textual.app import ComposeResult
from textual.widgets import Tree, Input, Label, Button, Static
from textual.widget import Widget
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.message import Message
from textual.events import Key

from ..api_bridge import ChronologBridge


class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass
class FileNode:
    path: Path
    file_type: FileType
    size: Optional[int] = None
    modified: Optional[datetime] = None
    has_changes: bool = False
    is_ignored: bool = False


class FileTreeView(Widget):
    """Interactive file tree widget for repository navigation."""
    
    BINDINGS = [
        ("enter", "select_item", "Select"),
        ("space", "toggle_expand", "Toggle"),
        ("r", "refresh", "Refresh"),
        ("f", "filter", "Filter"),
        ("c", "show_changed_only", "Changed Only"),
    ]
    
    show_hidden = reactive(False)
    show_changed_only = reactive(False)
    filter_pattern = reactive("")
    
    class FileSelected(Message):
        """Message sent when a file is selected."""
        def __init__(self, path: Path):
            self.path = path
            super().__init__()
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
        self.repo_path = Path(bridge.repo_path) if bridge.is_initialized() else Path.cwd()
        self.expanded_dirs: Set[Path] = set()
        self.file_cache: Dict[Path, FileNode] = {}
        self.ignored_patterns = set()
        self._load_ignored_patterns()
    
    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(classes="file-tree-controls"):
                yield Input(
                    placeholder="Filter files...",
                    id="file-filter",
                    classes="file-filter-input"
                )
                yield Button("Hidden", id="toggle-hidden", variant="primary")
                yield Button("Changed", id="toggle-changed", variant="primary")
                yield Label("", id="file-count")
            
            yield Tree("Repository", id="file-tree", classes="file-tree")
    
    def on_mount(self):
        """Initialize the tree when mounted."""
        self.refresh_tree()
    
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "toggle-hidden":
            self.show_hidden = not self.show_hidden
            event.button.variant = "success" if self.show_hidden else "primary"
            self.refresh_tree()
        elif event.button.id == "toggle-changed":
            self.show_changed_only = not self.show_changed_only
            event.button.variant = "success" if self.show_changed_only else "primary"
            self.refresh_tree()
    
    def on_input_changed(self, event: Input.Changed):
        """Handle filter input changes."""
        if event.input.id == "file-filter":
            self.filter_pattern = event.value.lower()
            self.refresh_tree()
    
    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Handle tree node selection."""
        node_data = event.node.data
        if node_data and isinstance(node_data, FileNode):
            if node_data.file_type == FileType.FILE:
                self.post_message(self.FileSelected(node_data.path))
            else:
                # Toggle directory expansion
                event.node.toggle()
                if node_data.path in self.expanded_dirs:
                    self.expanded_dirs.remove(node_data.path)
                else:
                    self.expanded_dirs.add(node_data.path)
    
    def _load_ignored_patterns(self):
        """Load ignore patterns from .chronologignore."""
        ignore_file = self.repo_path / ".chronologignore"
        if ignore_file.exists():
            try:
                patterns = ignore_file.read_text().splitlines()
                self.ignored_patterns = {p.strip() for p in patterns if p.strip() and not p.startswith('#')}
            except:
                self.ignored_patterns = set()
    
    def _is_ignored(self, path: Path) -> bool:
        """Check if a path matches any ignore pattern."""
        # Simple pattern matching - could be enhanced with glob patterns
        path_str = str(path.relative_to(self.repo_path))
        for pattern in self.ignored_patterns:
            if pattern in path_str:
                return True
        return False
    
    def _should_show_file(self, node: FileNode) -> bool:
        """Determine if a file should be shown based on filters."""
        # Check hidden files
        if not self.show_hidden and node.path.name.startswith('.'):
            return False
        
        # Check changed files only
        if self.show_changed_only and not node.has_changes:
            return False
        
        # Check filter pattern
        if self.filter_pattern:
            if self.filter_pattern not in node.path.name.lower():
                return False
        
        return True
    
    def _get_file_node(self, path: Path) -> FileNode:
        """Get or create a FileNode for a path."""
        if path in self.file_cache:
            return self.file_cache[path]
        
        try:
            stat = path.stat()
            node = FileNode(
                path=path,
                file_type=FileType.DIRECTORY if path.is_dir() else FileType.FILE,
                size=stat.st_size if path.is_file() else None,
                modified=datetime.fromtimestamp(stat.st_mtime),
                has_changes=self._has_changes(path),
                is_ignored=self._is_ignored(path)
            )
            self.file_cache[path] = node
            return node
        except:
            return FileNode(
                path=path,
                file_type=FileType.FILE,
                is_ignored=True
            )
    
    def _has_changes(self, path: Path) -> bool:
        """Check if a file has uncommitted changes."""
        if not self.bridge.is_initialized():
            return False
        
        # Check if file has changes in the repository
        # This would need to be implemented in the bridge
        return False  # Placeholder
    
    def _add_directory_to_tree(self, tree_node, dir_path: Path, level: int = 0):
        """Recursively add directory contents to tree."""
        if level > 10:  # Prevent deep recursion
            return
        
        try:
            items = list(dir_path.iterdir())
            # Sort directories first, then files
            items.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
            
            file_count = 0
            for item in items:
                node = self._get_file_node(item)
                
                if not self._should_show_file(node):
                    continue
                
                # Skip .chronolog directory
                if item.name == ".chronolog":
                    continue
                
                label = self._format_node_label(node)
                
                if node.file_type == FileType.DIRECTORY:
                    dir_node = tree_node.add(label, data=node)
                    dir_node.allow_expand = True
                    
                    # Expand if previously expanded or if showing changed only
                    if item in self.expanded_dirs or self.show_changed_only:
                        dir_node.expand()
                        self._add_directory_to_tree(dir_node, item, level + 1)
                else:
                    tree_node.add_leaf(label, data=node)
                    file_count += 1
            
            return file_count
        except PermissionError:
            tree_node.add_leaf("[Permission Denied]", data=None)
            return 0
    
    def _format_node_label(self, node: FileNode) -> str:
        """Format the label for a tree node."""
        name = node.path.name
        
        # Add indicators
        indicators = []
        if node.file_type == FileType.DIRECTORY:
            indicators.append("📁")
        else:
            # File type icons based on extension
            ext = node.path.suffix.lower()
            if ext in ['.py', '.pyw']:
                indicators.append("🐍")
            elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                indicators.append("📜")
            elif ext in ['.md', '.txt', '.rst']:
                indicators.append("📄")
            elif ext in ['.json', '.yaml', '.yml', '.toml']:
                indicators.append("⚙️")
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
                indicators.append("🖼️")
            else:
                indicators.append("📄")
        
        if node.has_changes:
            indicators.append("●")
        
        if node.is_ignored:
            indicators.append("🚫")
        
        label = f"{' '.join(indicators)} {name}"
        
        # Add size for files
        if node.file_type == FileType.FILE and node.size is not None:
            size_str = self._format_size(node.size)
            label += f" [{size_str}]"
        
        return label
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
    
    def refresh_tree(self):
        """Refresh the entire file tree."""
        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        
        # Clear cache to get fresh data
        self.file_cache.clear()
        
        # Add root directory
        root_node = self._get_file_node(self.repo_path)
        tree.root.data = root_node
        tree.root.label = f"📁 {self.repo_path.name}"
        
        # Add contents
        file_count = self._add_directory_to_tree(tree.root, self.repo_path)
        
        # Update file count
        count_label = self.query_one("#file-count", Label)
        count_label.update(f"{file_count} files")
    
    def action_refresh(self):
        """Refresh the tree."""
        self.refresh_tree()
    
    def action_filter(self):
        """Focus on the filter input."""
        self.query_one("#file-filter", Input).focus()
    
    def action_show_changed_only(self):
        """Toggle showing only changed files."""
        button = self.query_one("#toggle-changed", Button)
        button.action_press()


class FileTreeScreen(Screen):
    """Screen containing the file tree view."""
    
    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]
    
    def __init__(self, bridge: ChronologBridge):
        super().__init__()
        self.bridge = bridge
    
    def compose(self) -> ComposeResult:
        yield FileTreeView(self.bridge)
    
    def action_close(self):
        """Close the screen."""
        self.app.pop_screen()
    
    def on_file_tree_view_file_selected(self, event: FileTreeView.FileSelected):
        """Handle file selection."""
        # Could open file history or other actions
        self.notify(f"Selected: {event.path.name}", severity="information")