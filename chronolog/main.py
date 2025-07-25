import sys
import click
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style

# Import the new API class and custom exceptions
from .api import ChronologRepo, NotARepositoryError, RepositoryExistsError
from .organization.organizer import FileOrganizer
from .organization.bulk_operations import BulkOperations
from .backup.backup_manager import BackupManager
from .backup.scheduler import BackupScheduler, ScheduleFrequency
from .cloud.sync_manager import CloudSyncManager, SyncDirection, ConflictResolution
from .git_integration.git_exporter import GitExporter
from .git_integration.git_importer import GitImporter

# Import Phase 4 & 5 features
from .analytics.performance_analytics import PerformanceAnalytics
from .analytics.visualization import Visualization
from .analytics.metrics_collector import MetricsCollector
from .optimization.storage_optimizer import StorageOptimizer
from .optimization.garbage_collector import GarbageCollector
from .hooks.hook_manager import HookManager
from .hooks.scripting_api import ChronoLogAPI
from .users.user_manager import UserManager
from .users.auth import AuthenticationManager
from .users.permissions import PermissionManager
from .merge.merge_engine import MergeEngine
from .merge.conflict_resolver import ConflictResolver
from .web.app import WebServer

# Initialize colorama for cross-platform colored output
init(autoreset=True)


@click.group()
def main():
    """ChronoLog - Frictionless version control for creative workflows
    
    ChronoLog automatically tracks changes to your files without manual commits.
    It provides powerful search, branching, and tagging features for managing
    your creative projects.
    
    Common commands:
      chronolog init              Initialize a new repository
      chronolog log <file>        View file history
      chronolog search <query>    Search content across versions
      chronolog branch create     Create a new branch
      chronolog tag create        Tag a version
    
    Use 'chronolog COMMAND --help' for more information on a command.
    """
    pass


@main.command()
def init():
    """Initialize ChronoLog in the current directory
    
    This creates a .chronolog directory and starts automatic file tracking.
    All files in the directory (except those matching ignore patterns) will
    be versioned automatically whenever they change.
    """
    try:
        repo = ChronologRepo.init()
        click.echo(f"{Fore.GREEN}[ChronoLog] Initialized in {repo.repo_path}")
        click.echo(f"{Fore.GREEN}[ChronoLog] Background watcher started")
    except RepositoryExistsError:
        click.echo(f"{Fore.YELLOW}[ChronoLog] Already initialized in this directory")
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] An unexpected error occurred: {e}")
        sys.exit(1)


@main.command()
@click.argument('file_path', type=click.Path(exists=True))
def log(file_path):
    """View version history for a file
    
    Shows all saved versions of the specified file, including:
    - Version hash (first 8 characters)
    - Timestamp of the save
    - File size
    - Any annotations
    
    Example:
        chronolog log myfile.txt
    """
    try:
        repo = ChronologRepo()
        history = repo.log(file_path)
        
        if not history:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No history found for {file_path}")
            return
        
        click.echo(f"\n{Fore.CYAN}Version history for {file_path}:")
        click.echo(f"{Fore.CYAN}{'-' * 60}")
        
        for entry in history:
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            hash_short = entry['hash'][:8]
            size = entry['size']
            annotation = entry['annotation'] or ""
            
            click.echo(f"{Fore.GREEN}{hash_short}{Style.RESET_ALL} | "
                      f"{timestamp} | "
                      f"{size:>8} bytes | "
                      f"{annotation}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory. Run 'chronolog init' first.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.command()
@click.argument('version_hash')
def show(version_hash):
    """Show the content of a specific version"""
    try:
        repo = ChronologRepo()
        content = repo.show(version_hash)
        
        # Print content
        try:
            click.echo(content.decode('utf-8'))
        except UnicodeDecodeError:
            click.echo(f"{Fore.YELLOW}[ChronoLog] Binary content (cannot display)")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.command()
@click.argument('hash1')
@click.argument('hash2', required=False)
@click.option('--current', is_flag=True, help='Compare with current file')
@click.option('--type', 'diff_type', type=click.Choice(['line', 'word', 'semantic', 'binary']), 
              default='line', help='Type of diff to perform')
def diff(hash1, hash2, current, diff_type):
    """Show differences between two versions"""
    try:
        repo = ChronologRepo()
        
        if current:
            diff_output = repo.diff(hash1, current=True, diff_type=diff_type)
        else:
            if not hash2:
                click.echo(f"{Fore.RED}[ChronoLog] Second version hash required (or use --current)")
                sys.exit(1)
            diff_output = repo.diff(hash1, hash2, diff_type=diff_type)
        
        # For word diff, the output already includes ANSI colors
        if diff_type == "word":
            click.echo(diff_output)
        else:
            # Display colored diff for line diffs
            for line in diff_output.split('\n'):
                if line.startswith('+++'):
                    click.echo(f"{Fore.GREEN}{line}")
                elif line.startswith('---'):
                    click.echo(f"{Fore.RED}{line}")
                elif line.startswith('@@'):
                    click.echo(f"{Fore.CYAN}{line}")
                elif line.startswith('+'):
                    click.echo(f"{Fore.GREEN}{line}")
                elif line.startswith('-'):
                    click.echo(f"{Fore.RED}{line}")
                else:
                    click.echo(line)
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.command()
@click.argument('version_hash')
@click.argument('file_path', type=click.Path())
def checkout(version_hash, file_path):
    """Revert a file to a previous version"""
    try:
        repo = ChronologRepo()
        repo.checkout(version_hash, file_path)
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Checked out {file_path} to version {version_hash[:8]}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def daemon():
    """Manage the ChronoLog daemon"""
    pass


@daemon.command('start')
def daemon_start():
    """Start the background daemon"""
    try:
        repo = ChronologRepo()
        daemon = repo.get_daemon()
        daemon.start()
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@daemon.command('stop')
def daemon_stop():
    """Stop the background daemon"""
    try:
        repo = ChronologRepo()
        daemon = repo.get_daemon()
        daemon.stop()
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@daemon.command('status')
def daemon_status():
    """Check daemon status"""
    try:
        repo = ChronologRepo()
        daemon = repo.get_daemon()
        daemon.status()
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def tag():
    """Manage tags"""
    pass


@tag.command('create')
@click.argument('tag_name')
@click.argument('version_hash', required=False)
@click.option('--description', '-d', help='Tag description')
def tag_create(tag_name, version_hash, description):
    """Create a tag pointing to a version"""
    try:
        repo = ChronologRepo()
        repo.tag(tag_name, version_hash, description)
        
        if version_hash:
            click.echo(f"{Fore.GREEN}[ChronoLog] Created tag '{tag_name}' pointing to {version_hash[:8]}")
        else:
            click.echo(f"{Fore.GREEN}[ChronoLog] Created tag '{tag_name}' pointing to latest version")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@tag.command('list')
def tag_list():
    """List all tags"""
    try:
        repo = ChronologRepo()
        tags = repo.list_tags()
        
        if not tags:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No tags found")
            return
        
        click.echo(f"\n{Fore.CYAN}Tags:")
        click.echo(f"{Fore.CYAN}{'-' * 60}")
        
        for tag in tags:
            timestamp = datetime.fromisoformat(tag['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            hash_short = tag['hash'][:8]
            description = tag['description'] or ""
            
            click.echo(f"{Fore.GREEN}{tag['name']:20}{Style.RESET_ALL} → "
                      f"{hash_short} | "
                      f"{timestamp} | "
                      f"{description}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@tag.command('delete')
@click.argument('tag_name')
def tag_delete(tag_name):
    """Delete a tag"""
    try:
        repo = ChronologRepo()
        repo.delete_tag(tag_name)
        click.echo(f"{Fore.GREEN}[ChronoLog] Deleted tag '{tag_name}'")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def branch():
    """Manage branches"""
    pass


@branch.command('create')
@click.argument('branch_name')
@click.option('--from', 'from_branch', help='Create branch from another branch')
def branch_create(branch_name, from_branch):
    """Create a new branch"""
    try:
        repo = ChronologRepo()
        repo.branch(branch_name, from_branch)
        click.echo(f"{Fore.GREEN}[ChronoLog] Created branch '{branch_name}'")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@branch.command('list')
def branch_list():
    """List all branches"""
    try:
        repo = ChronologRepo()
        current, branches = repo.branch()
        
        click.echo(f"\n{Fore.CYAN}Branches:")
        click.echo(f"{Fore.CYAN}{'-' * 60}")
        
        for branch in branches:
            created_at = datetime.fromisoformat(branch['created_at']).strftime('%Y-%m-%d %H:%M:%S')
            parent = branch['parent'] or "none"
            marker = "*" if branch['name'] == current else " "
            
            click.echo(f"{Fore.GREEN}{marker} {branch['name']:20}{Style.RESET_ALL} | "
                      f"created: {created_at} | "
                      f"parent: {parent}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@branch.command('switch')
@click.argument('branch_name')
def branch_switch(branch_name):
    """Switch to a different branch"""
    try:
        repo = ChronologRepo()
        repo.switch_branch(branch_name)
        click.echo(f"{Fore.GREEN}[ChronoLog] Switched to branch '{branch_name}'")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@branch.command('delete')
@click.argument('branch_name')
def branch_delete(branch_name):
    """Delete a branch"""
    try:
        repo = ChronologRepo()
        repo.delete_branch(branch_name)
        click.echo(f"{Fore.GREEN}[ChronoLog] Deleted branch '{branch_name}'")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.RED}[ChronoLog] {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.command()
@click.argument('query')
@click.option('--file', '-f', help='Search within a specific file')
@click.option('--type', '-t', multiple=True, help='Filter by file type (e.g., py, txt)')
@click.option('--regex', '-r', is_flag=True, help='Use regex pattern')
@click.option('--case-sensitive', '-c', is_flag=True, help='Case sensitive search')
@click.option('--whole-words', '-w', is_flag=True, help='Match whole words only')
@click.option('--recent', '-d', type=int, help='Search only recent N days')
@click.option('--limit', '-l', type=int, help='Limit number of results')
@click.option('--added', help='Find where text was added')
@click.option('--removed', help='Find where text was removed')
def search(query, file, type, regex, case_sensitive, whole_words, recent, limit, added, removed):
    """Search for content in the repository
    
    Search through all versions of files to find specific content.
    Supports simple text search and advanced options including regex,
    file type filtering, and tracking content changes.
    
    Examples:
        chronolog search "TODO"                    # Simple search
        chronolog search "func.*" --regex          # Regex search
        chronolog search "bug" --type py --recent 7  # Recent Python files
        chronolog search --added "new feature"     # Find additions
    """
    try:
        repo = ChronologRepo()
        
        # Handle content change search
        if added or removed:
            results = repo.search_changes(added, removed)
            
            if not results:
                click.echo(f"{Fore.YELLOW}[ChronoLog] No changes found")
                return
            
            click.echo(f"\n{Fore.CYAN}Content change results:")
            click.echo(f"{Fore.CYAN}{'-' * 60}")
            
            for result in results:
                timestamp = datetime.fromisoformat(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                hash_short = result['hash'][:8]
                change_type = result['change_type']
                change_text = result['change_text']
                
                color = Fore.GREEN if change_type == 'added' else Fore.RED
                symbol = '+' if change_type == 'added' else '-'
                
                click.echo(f"{color}{symbol} {hash_short}{Style.RESET_ALL} | "
                          f"{result['file_path']} | "
                          f"{timestamp} | "
                          f"{change_type}: '{change_text[:30]}...'")
            return
        
        # Regular search with advanced filters
        if regex or case_sensitive or whole_words or type or recent or limit:
            # Use advanced search
            from .search.searcher import SearchFilter
            
            filter = SearchFilter()
            filter.query = query
            filter.regex = regex
            filter.case_sensitive = case_sensitive
            filter.whole_words = whole_words
            filter.limit = limit
            
            if file:
                filter.file_paths = [file]
            
            for ext in type:
                filter.add_file_type(ext)
            
            if recent:
                filter.set_recent(recent)
            
            results = repo.advanced_search(filter)
        else:
            # Simple search
            results = repo.search(query, file)
        
        if not results:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No results found for '{query}'")
            return
        
        click.echo(f"\n{Fore.CYAN}Search results for '{query}':")
        click.echo(f"{Fore.CYAN}{'-' * 60}")
        
        for result in results:
            timestamp = datetime.fromisoformat(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            hash_short = result['hash'][:8]
            snippet = result.get('snippet', '')
            
            click.echo(f"{Fore.GREEN}{hash_short}{Style.RESET_ALL} | "
                      f"{result['file_path']} | "
                      f"{timestamp}")
            
            if snippet:
                # Display snippet with highlighted matches
                snippet = snippet.replace('<mark>', f'{Fore.YELLOW}')
                snippet = snippet.replace('</mark>', f'{Style.RESET_ALL}')
                click.echo(f"  {snippet}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.command()
def reindex():
    """Reindex all content for search"""
    try:
        repo = ChronologRepo()
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Reindexing search database...")
        
        def progress(current, total):
            percent = (current / total * 100) if total > 0 else 0
            click.echo(f"\r{Fore.GREEN}Progress: {current}/{total} ({percent:.1f}%)", nl=False)
        
        indexed, total = repo.reindex_search(progress)
        click.echo()  # New line after progress
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Indexed {indexed} out of {total} versions")
        
        # Show search stats
        stats = repo.get_search_stats()
        click.echo(f"\n{Fore.CYAN}Search Index Statistics:")
        click.echo(f"  Coverage: {stats['coverage_percent']:.1f}%")
        click.echo(f"  Index size: {stats['index_size_bytes'] / 1024 / 1024:.2f} MB")
        
        if stats['top_file_types']:
            click.echo(f"\n{Fore.CYAN}Top indexed file types:")
            for ft in stats['top_file_types'][:5]:
                click.echo(f"  {ft['extension']}: {ft['count']} versions")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def ignore():
    """Manage ignore patterns"""
    pass


@ignore.command('show')
def ignore_show():
    """Show current ignore patterns"""
    try:
        repo = ChronologRepo()
        from .ignore import IgnorePatterns
        
        patterns = IgnorePatterns(repo.repo_path)
        pattern_list = patterns.get_patterns()
        
        click.echo(f"\n{Fore.CYAN}Current ignore patterns:")
        click.echo(f"{Fore.CYAN}{'-' * 60}")
        
        for pattern in pattern_list:
            click.echo(f"  {pattern}")
        
        ignore_file = repo.repo_path / ".chronologignore"
        if ignore_file.exists():
            click.echo(f"\n{Fore.GREEN}Patterns loaded from: {ignore_file}")
        else:
            click.echo(f"\n{Fore.YELLOW}Using default patterns only (no .chronologignore file)")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@ignore.command('init')
def ignore_init():
    """Create a default .chronologignore file"""
    try:
        repo = ChronologRepo()
        from .ignore import IgnorePatterns
        
        if IgnorePatterns.create_default_ignore_file(repo.repo_path):
            click.echo(f"{Fore.GREEN}[ChronoLog] Created .chronologignore file")
        else:
            click.echo(f"{Fore.YELLOW}[ChronoLog] .chronologignore file already exists")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def organize():
    """File organization and bulk operations"""
    pass


@organize.command('analyze')
@click.option('--output', '-o', type=click.Path(), help='Output path for analysis report')
def organize_analyze(output):
    """Analyze repository organization and suggest improvements"""
    try:
        repo = ChronologRepo()
        organizer = FileOrganizer(repo.repo_path)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Analyzing repository organization...")
        analysis = organizer.analyze_repository()
        
        click.echo(f"\n{Fore.GREEN}Repository Analysis:")
        click.echo(f"  Project Type: {analysis['project_type'] or 'Unknown'}")
        click.echo(f"  Total Files: {analysis['total_files']}")
        click.echo(f"  Organization Score: {analysis['organization_score']:.1f}/100")
        
        click.echo(f"\n{Fore.YELLOW}File Categories:")
        for category, count in analysis['category_distribution'].items():
            click.echo(f"  {category}: {count} files")
        
        if analysis['suggestions']:
            click.echo(f"\n{Fore.CYAN}Organization Suggestions:")
            for i, suggestion in enumerate(analysis['suggestions'][:10], 1):
                click.echo(f"  {i}. Move {suggestion.file_path.name}")
                click.echo(f"     From: {suggestion.current_location}")
                click.echo(f"     To: {suggestion.suggested_location}")
                click.echo(f"     Reason: {suggestion.reason}")
        
        if output:
            organizer.export_organization_report(analysis, Path(output))
            click.echo(f"\n{Fore.GREEN}[ChronoLog] Report saved to {output}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@organize.command('suggest')
@click.option('--apply', is_flag=True, help='Apply suggestions (move files)')
@click.option('--dry-run', is_flag=True, default=True, help='Show what would be moved without doing it')
def organize_suggest(apply, dry_run):
    """Show and optionally apply organization suggestions"""
    try:
        repo = ChronologRepo()
        organizer = FileOrganizer(repo.repo_path)
        
        analysis = organizer.analyze_repository()
        suggestions = analysis['suggestions']
        
        if not suggestions:
            click.echo(f"{Fore.GREEN}[ChronoLog] Repository is well organized!")
            return
        
        if apply and not dry_run:
            click.echo(f"{Fore.YELLOW}[ChronoLog] Applying organization suggestions...")
            moves = organizer.apply_suggestions(suggestions, dry_run=False)
            for src, dst in moves:
                click.echo(f"  Moved: {src} -> {dst}")
            click.echo(f"{Fore.GREEN}[ChronoLog] Reorganization complete!")
        else:
            click.echo(f"{Fore.CYAN}[ChronoLog] Suggested moves (dry run):")
            moves = organizer.apply_suggestions(suggestions, dry_run=True)
            for src, dst in moves:
                click.echo(f"  Would move: {src} -> {dst}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def bulk():
    """Bulk operations on repository files"""
    pass


@bulk.command('tag')
@click.option('--pattern', '-p', multiple=True, help='File pattern to tag (e.g., "*.py")')
@click.option('--prefix', default='bulk', help='Tag prefix')
def bulk_tag(pattern, prefix):
    """Tag multiple files at once"""
    try:
        repo = ChronologRepo()
        bulk_ops = BulkOperations(repo)
        
        if not pattern:
            click.echo(f"{Fore.RED}[ChronoLog] Please specify file patterns with -p")
            sys.exit(1)
        
        # Create pattern dict
        patterns = {p: p.replace('*', '').replace('.', '') for p in pattern}
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Creating bulk tags...")
        created_tags = bulk_ops.bulk_tag(patterns, prefix)
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Created {len(created_tags)} tags:")
        for tag in created_tags:
            click.echo(f"  - {tag}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@bulk.command('export')
@click.argument('output_dir', type=click.Path())
@click.option('--pattern', '-p', help='File pattern filter')
@click.option('--versions', default='latest', type=click.Choice(['latest', 'all']))
def bulk_export(output_dir, pattern, versions):
    """Export multiple files from repository"""
    try:
        repo = ChronologRepo()
        bulk_ops = BulkOperations(repo)
        
        output_path = Path(output_dir)
        click.echo(f"{Fore.CYAN}[ChronoLog] Exporting files to {output_path}...")
        
        exported = bulk_ops.bulk_export(output_path, pattern, versions)
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Exported {len(exported)} files:")
        for src, dst in exported.items():
            click.echo(f"  {src} -> {dst}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def backup():
    """Backup and restore operations"""
    pass


@backup.command('create')
@click.argument('destination', type=click.Path())
@click.option('--type', 'backup_type', type=click.Choice(['full', 'incremental']), 
              default='full', help='Type of backup')
@click.option('--compression', type=click.Choice(['gzip', 'bzip2', 'none']), 
              default='gzip', help='Compression method')
@click.option('--from', 'parent_backup', help='Parent backup ID for incremental backup')
def backup_create(destination, backup_type, compression, parent_backup):
    """Create a repository backup"""
    try:
        repo = ChronologRepo()
        backup_manager = BackupManager(repo.repo_path)
        
        dest_path = Path(destination)
        click.echo(f"{Fore.CYAN}[ChronoLog] Creating {backup_type} backup...")
        
        backup_id = backup_manager.create_backup(
            destination=dest_path,
            backup_type=backup_type,
            compression=compression,
            incremental_from=parent_backup
        )
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Backup created: {backup_id}")
        
        # Show backup info
        backups = backup_manager.list_backups(dest_path)
        latest_backup = next((b for b in backups if b.backup_id == backup_id), None)
        if latest_backup:
            size_mb = latest_backup.size / (1024 * 1024)
            click.echo(f"  Size: {size_mb:.1f} MB")
            click.echo(f"  Files: {latest_backup.file_count}")
            click.echo(f"  Compression: {latest_backup.compression}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@backup.command('list')
@click.option('--destination', '-d', type=click.Path(), help='Backup destination directory')
def backup_list(destination):
    """List available backups"""
    try:
        repo = ChronologRepo()
        backup_manager = BackupManager(repo.repo_path)
        
        dest_path = Path(destination) if destination else None
        backups = backup_manager.list_backups(dest_path)
        
        if not backups:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No backups found")
            return
        
        click.echo(f"{Fore.GREEN}Available backups:")
        for backup in backups:
            size_mb = backup.size / (1024 * 1024)
            click.echo(f"  {backup.backup_id}")
            click.echo(f"    Date: {backup.timestamp}")
            click.echo(f"    Type: {backup.backup_type}")
            click.echo(f"    Size: {size_mb:.1f} MB")
            click.echo(f"    Files: {backup.file_count}")
            if backup.parent_backup_id:
                click.echo(f"    Parent: {backup.parent_backup_id}")
            click.echo()
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@backup.command('restore')
@click.argument('backup_file', type=click.Path(exists=True))
@click.argument('restore_path', type=click.Path())
@click.option('--selective', '-s', multiple=True, help='File patterns to restore')
def backup_restore(backup_file, restore_path, selective):
    """Restore from backup"""
    try:
        repo = ChronologRepo()
        backup_manager = BackupManager(repo.repo_path)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Restoring backup...")
        
        success = backup_manager.restore_backup(
            backup_file=Path(backup_file),
            restore_path=Path(restore_path),
            selective=list(selective) if selective else None
        )
        
        if success:
            click.echo(f"{Fore.GREEN}[ChronoLog] Backup restored successfully")
        else:
            click.echo(f"{Fore.RED}[ChronoLog] Restore failed")
    
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def cloud():
    """Cloud synchronization operations"""
    pass


@cloud.command('configure')
@click.option('--provider', type=click.Choice(['s3']), required=True, help='Cloud provider')
@click.option('--bucket', help='S3 bucket name')
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--prefix', help='S3 key prefix')
def cloud_configure(provider, bucket, region, prefix):
    """Configure cloud sync"""
    try:
        repo = ChronologRepo()
        sync_manager = CloudSyncManager(repo.repo_path)
        
        if provider == 's3':
            config = {
                'bucket_name': bucket,
                'region': region,
                'prefix': prefix or ''
            }
            
            sync_manager.configure(
                provider_type='s3',
                provider_config=config,
                sync_direction=SyncDirection.BIDIRECTIONAL
            )
            
            click.echo(f"{Fore.GREEN}[ChronoLog] Cloud sync configured for S3")
            click.echo(f"  Bucket: {bucket}")
            click.echo(f"  Region: {region}")
            if prefix:
                click.echo(f"  Prefix: {prefix}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@cloud.command('sync')
@click.option('--force', is_flag=True, help='Force full sync')
def cloud_sync(force):
    """Synchronize with cloud storage"""
    try:
        repo = ChronologRepo()
        sync_manager = CloudSyncManager(repo.repo_path)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Connecting to cloud provider...")
        sync_manager.connect()
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Synchronizing...")
        stats = sync_manager.sync(force=force)
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Sync completed:")
        click.echo(f"  Uploaded: {stats['uploaded']} files")
        click.echo(f"  Downloaded: {stats['downloaded']} files")
        click.echo(f"  Conflicts: {stats['conflicts']} files")
        click.echo(f"  Errors: {stats['errors']} files")
        
        if stats['conflicts'] > 0:
            click.echo(f"{Fore.YELLOW}[ChronoLog] Use 'chronolog cloud status' to see conflicts")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@cloud.command('status')
def cloud_status():
    """Show cloud sync status"""
    try:
        repo = ChronologRepo()
        sync_manager = CloudSyncManager(repo.repo_path)
        
        status = sync_manager.get_sync_status()
        
        click.echo(f"{Fore.GREEN}Cloud Sync Status:")
        click.echo(f"  Configured: {'Yes' if status['configured'] else 'No'}")
        click.echo(f"  Connected: {'Yes' if status['connected'] else 'No'}")
        click.echo(f"  Last sync: {status['last_sync'] or 'Never'}")
        click.echo(f"  Files synced: {status['files_synced']}")
        click.echo(f"  Pending conflicts: {status['pending_conflicts']}")
        click.echo(f"  Recent errors: {status['recent_errors']}")
        
        if 'storage_info' in status:
            info = status['storage_info']
            size_mb = info.get('total_size', 0) / (1024 * 1024)
            click.echo(f"\nStorage Info:")
            click.echo(f"  Provider: {info.get('provider', 'Unknown')}")
            click.echo(f"  Total size: {size_mb:.1f} MB")
            click.echo(f"  Object count: {info.get('object_count', 0)}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def git():
    """Git integration operations"""
    pass


@git.command('export')
@click.argument('git_repo_path', type=click.Path())
@click.option('--branches', is_flag=True, default=True, help='Export branches')
@click.option('--tags', is_flag=True, default=True, help='Export tags')
@click.option('--author-name', default='ChronoLog', help='Git author name')
@click.option('--author-email', default='chronolog@localhost', help='Git author email')
def git_export(git_repo_path, branches, tags, author_name, author_email):
    """Export ChronoLog history to Git repository"""
    try:
        repo = ChronologRepo()
        exporter = GitExporter(repo)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Exporting to Git repository...")
        
        stats = exporter.export_to_git(
            git_repo_path=Path(git_repo_path),
            export_branches=branches,
            export_tags=tags,
            author_name=author_name,
            author_email=author_email
        )
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Export completed:")
        click.echo(f"  Commits created: {stats.commits_created}")
        click.echo(f"  Files exported: {stats.files_exported}")
        click.echo(f"  Branches created: {stats.branches_created}")
        click.echo(f"  Tags created: {stats.tags_created}")
        
        if stats.errors:
            click.echo(f"{Fore.YELLOW}Errors encountered:")
            for error in stats.errors:
                click.echo(f"  - {error}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@git.command('import')
@click.argument('git_repo_path', type=click.Path(exists=True))
@click.option('--branches', is_flag=True, default=True, help='Import branches')
@click.option('--tags', is_flag=True, default=True, help='Import tags')
@click.option('--preserve-timestamps', is_flag=True, default=True, help='Preserve commit timestamps')
def git_import(git_repo_path, branches, tags, preserve_timestamps):
    """Import Git repository into ChronoLog"""
    try:
        repo = ChronologRepo()
        importer = GitImporter(repo)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Importing from Git repository...")
        
        stats = importer.import_from_git(
            git_repo_path=Path(git_repo_path),
            import_branches=branches,
            import_tags=tags,
            preserve_timestamps=preserve_timestamps
        )
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Import completed:")
        click.echo(f"  Commits imported: {stats.commits_imported}")
        click.echo(f"  Files imported: {stats.files_imported}")
        click.echo(f"  Branches imported: {stats.branches_imported}")
        click.echo(f"  Tags imported: {stats.tags_imported}")
        
        if stats.errors:
            click.echo(f"{Fore.YELLOW}Errors encountered:")
            for error in stats.errors:
                click.echo(f"  - {error}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


# =====================================================================
# Phase 4 & 5 CLI Commands
# =====================================================================

@main.group()
def analytics():
    """Analytics and performance metrics"""
    pass


@analytics.command('stats')
@click.option('--format', 'output_format', type=click.Choice(['text', 'json']), 
              default='text', help='Output format')
def analytics_stats(output_format):
    """Show repository statistics and analytics"""
    try:
        repo = ChronologRepo()
        analytics = PerformanceAnalytics(repo.repo_path)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Collecting repository statistics...")
        stats = analytics.collect_repository_stats()
        
        if output_format == 'json':
            import json
            stats_dict = {
                'total_versions': stats.total_versions,
                'total_files': stats.total_files,
                'total_size_mb': stats.total_size_mb,
                'unique_authors': stats.unique_authors,
                'language_stats': stats.language_stats,
                'first_version_date': stats.first_version_date.isoformat() if stats.first_version_date else None,
                'last_version_date': stats.last_version_date.isoformat() if stats.last_version_date else None,
                'most_active_author': stats.most_active_author,
                'compression_ratio': stats.compression_ratio,
                'growth_rate_mb_per_day': stats.growth_rate_mb_per_day
            }
            click.echo(json.dumps(stats_dict, indent=2))
        else:
            click.echo(f"\n{Fore.GREEN}Repository Statistics:")
            click.echo(f"  Total Versions: {stats.total_versions}")
            click.echo(f"  Total Files: {stats.total_files}")
            click.echo(f"  Total Size: {stats.total_size_mb:.2f} MB")
            click.echo(f"  Unique Authors: {len(stats.unique_authors)}")
            click.echo(f"  Most Active Author: {stats.most_active_author or 'N/A'}")
            click.echo(f"  Compression Ratio: {stats.compression_ratio:.2f}")
            click.echo(f"  Growth Rate: {stats.growth_rate_mb_per_day:.2f} MB/day")
            
            if stats.language_stats:
                click.echo(f"\n{Fore.CYAN}Language Statistics:")
                for lang, count in sorted(stats.language_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                    click.echo(f"  {lang}: {count} files")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@analytics.command('metrics')
@click.option('--days', default=7, help='Number of days to analyze')
@click.option('--limit', default=100, help='Maximum number of operations to show')
def analytics_metrics(days, limit):
    """Show performance metrics"""
    try:
        repo = ChronologRepo()
        analytics = PerformanceAnalytics(repo.repo_path)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Collecting performance metrics...")
        metrics = analytics.get_operation_metrics(days=days, limit=limit)
        
        if not metrics:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No metrics found for the last {days} days")
            return
        
        click.echo(f"\n{Fore.GREEN}Performance Metrics (Last {days} days):")
        click.echo(f"{'-' * 80}")
        click.echo(f"{'Operation':<15} {'Duration':<10} {'Files':<8} {'Timestamp':<20} {'Status':<8}")
        click.echo(f"{'-' * 80}")
        
        for metric in metrics[-20:]:  # Show last 20 operations
            duration = f"{metric.get('duration', 0):.3f}s"
            files = str(metric.get('files_processed', 0))
            timestamp = metric.get('timestamp', '')[:19] if metric.get('timestamp') else 'N/A'
            status = 'OK' if metric.get('success', True) else 'ERROR'
            operation = metric.get('operation_type', 'unknown')[:14]
            
            color = Fore.GREEN if status == 'OK' else Fore.RED
            click.echo(f"{operation:<15} {duration:<10} {files:<8} {timestamp:<20} {color}{status}{Style.RESET_ALL}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@analytics.command('code-metrics')
@click.option('--file-pattern', help='File pattern to analyze (e.g., "*.py")')
@click.option('--output', type=click.Path(), help='Output file for detailed report')
def analytics_code_metrics(file_pattern, output):
    """Analyze code complexity and quality metrics"""
    try:
        repo = ChronologRepo()
        metrics_collector = MetricsCollector(repo.repo_path)
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Analyzing code metrics...")
        
        if file_pattern:
            # Analyze specific pattern
            from pathlib import Path
            files = list(Path(repo.repo_path).glob(file_pattern))
            results = []
            for file_path in files:
                if file_path.is_file():
                    metrics = metrics_collector.analyze_file(file_path)
                    results.append(metrics)
        else:
            # Analyze entire repository
            results = metrics_collector.analyze_repository()
        
        if not results:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No code files found to analyze")
            return
        
        # Calculate summary statistics
        total_loc = sum(m.lines_of_code for m in results)
        avg_complexity = sum(m.cyclomatic_complexity for m in results) / len(results)
        avg_maintainability = sum(m.maintainability_index for m in results) / len(results)
        
        click.echo(f"\n{Fore.GREEN}Code Quality Summary:")
        click.echo(f"  Files Analyzed: {len(results)}")
        click.echo(f"  Total Lines of Code: {total_loc}")
        click.echo(f"  Average Complexity: {avg_complexity:.2f}")
        click.echo(f"  Average Maintainability: {avg_maintainability:.2f}")
        
        # Show top complex files
        complex_files = sorted(results, key=lambda x: x.cyclomatic_complexity, reverse=True)[:5]
        click.echo(f"\n{Fore.YELLOW}Most Complex Files:")
        for metric in complex_files:
            click.echo(f"  {metric.file_path.name}: {metric.cyclomatic_complexity:.1f} complexity")
        
        if output:
            metrics_collector.export_metrics_report(results, Path(output))
            click.echo(f"\n{Fore.GREEN}[ChronoLog] Detailed report saved to {output}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@analytics.command('visualize')
@click.argument('metric_type', type=click.Choice(['activity', 'languages', 'complexity', 'growth']))
@click.option('--days', default=30, help='Number of days for time-based charts')
@click.option('--width', default=60, help='Chart width in characters')
def analytics_visualize(metric_type, days, width):
    """Create text-based visualizations of repository metrics"""
    try:
        repo = ChronologRepo()
        analytics = PerformanceAnalytics(repo.repo_path)
        visualization = Visualization()
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Creating {metric_type} visualization...")
        
        if metric_type == 'activity':
            metrics = analytics.get_operation_metrics(days=days)
            if metrics:
                # Create activity calendar
                dates = [m.get('timestamp', '')[:10] for m in metrics if m.get('timestamp')]
                chart = visualization.create_activity_calendar(dates, width=width)
                click.echo(f"\n{Fore.GREEN}Activity Calendar (Last {days} days):")
                click.echo(chart)
            else:
                click.echo(f"{Fore.YELLOW}[ChronoLog] No activity data found")
        
        elif metric_type == 'languages':
            stats = analytics.collect_repository_stats()
            if stats.language_stats:
                languages = list(stats.language_stats.keys())[:10]
                counts = [stats.language_stats[lang] for lang in languages]
                chart = visualization.create_bar_chart(languages, counts, title="Language Distribution")
                click.echo(f"\n{Fore.GREEN}Language Distribution:")
                click.echo(chart)
            else:
                click.echo(f"{Fore.YELLOW}[ChronoLog] No language statistics available")
        
        elif metric_type == 'complexity':
            from .analytics.metrics_collector import MetricsCollector
            metrics_collector = MetricsCollector(repo.repo_path)
            results = metrics_collector.analyze_repository()
            
            if results:
                files = [r.file_path.name[:20] for r in results[:10]]
                complexities = [r.cyclomatic_complexity for r in results[:10]]
                chart = visualization.create_bar_chart(files, complexities, title="Code Complexity")
                click.echo(f"\n{Fore.GREEN}Code Complexity (Top 10 Files):")
                click.echo(chart)
            else:
                click.echo(f"{Fore.YELLOW}[ChronoLog] No code complexity data available")
        
        elif metric_type == 'growth':
            stats = analytics.collect_repository_stats()
            # Create sparkline for repository growth
            sparkline = visualization.create_sparkline([stats.growth_rate_mb_per_day] * 7, width=width)
            click.echo(f"\n{Fore.GREEN}Repository Growth Trend:")
            click.echo(f"Growth Rate: {stats.growth_rate_mb_per_day:.2f} MB/day")
            click.echo(sparkline)
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def optimize():
    """Storage optimization and maintenance"""
    pass


@optimize.command('storage')
@click.option('--dry-run', is_flag=True, help='Show what would be optimized without doing it')
@click.option('--algorithm', type=click.Choice(['zlib', 'lzma', 'bz2']), 
              default='zlib', help='Compression algorithm to use')
def optimize_storage(dry_run, algorithm):
    """Optimize repository storage and compression"""
    try:
        repo = ChronologRepo()
        optimizer = StorageOptimizer(repo.repo_path)
        
        if dry_run:
            click.echo(f"{Fore.CYAN}[ChronoLog] Analyzing storage optimization opportunities...")
            recommendations = optimizer.get_storage_recommendations()
            
            if not recommendations:
                click.echo(f"{Fore.GREEN}[ChronoLog] Storage is already well optimized!")
                return
            
            click.echo(f"\n{Fore.YELLOW}Storage Optimization Recommendations:")
            for rec in recommendations:
                click.echo(f"  {rec.description}")
                click.echo(f"    Potential savings: {rec.potential_savings_mb:.2f} MB")
                click.echo(f"    Priority: {rec.priority}")
        else:
            click.echo(f"{Fore.CYAN}[ChronoLog] Optimizing storage with {algorithm} compression...")
            results = optimizer.optimize_storage()
            
            click.echo(f"\n{Fore.GREEN}Storage Optimization Results:")
            click.echo(f"  Original size: {results['original_size_mb']:.2f} MB")
            click.echo(f"  Optimized size: {results['optimized_size_mb']:.2f} MB")
            click.echo(f"  Space saved: {results['space_saved_mb']:.2f} MB")
            click.echo(f"  Compression ratio: {results['compression_ratio']:.2f}")
            click.echo(f"  Files processed: {results['files_processed']}")
            click.echo(f"  Duplicates removed: {results['duplicates_removed']}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@optimize.command('gc')
@click.option('--aggressive', is_flag=True, help='Perform aggressive garbage collection')
@click.option('--verify', is_flag=True, help='Verify database integrity before cleanup')
def optimize_gc(aggressive, verify):
    """Run garbage collection to clean up orphaned data"""
    try:
        repo = ChronologRepo()
        gc = GarbageCollector(repo.repo_path)
        
        if verify:
            click.echo(f"{Fore.CYAN}[ChronoLog] Verifying database integrity...")
            integrity_results = gc.verify_database_integrity()
            
            if integrity_results['corrupted_versions']:
                click.echo(f"{Fore.RED}Found {len(integrity_results['corrupted_versions'])} corrupted versions")
                for version_id in integrity_results['corrupted_versions']:
                    click.echo(f"  - {version_id}")
            else:
                click.echo(f"{Fore.GREEN}Database integrity check passed")
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Running garbage collection...")
        results = gc.collect_garbage()
        
        click.echo(f"\n{Fore.GREEN}Garbage Collection Results:")
        click.echo(f"  Orphaned objects removed: {results['orphaned_objects_removed']}")
        click.echo(f"  Temporary files cleaned: {results['temp_files_cleaned']}")
        click.echo(f"  Empty directories removed: {results['empty_dirs_removed']}")
        click.echo(f"  Database space reclaimed: {results['database_space_reclaimed_mb']:.2f} MB")
        click.echo(f"  Storage space reclaimed: {results['storage_space_reclaimed_mb']:.2f} MB")
        
        if results['errors']:
            click.echo(f"\n{Fore.YELLOW}Warnings/Errors:")
            for error in results['errors']:
                click.echo(f"  - {error}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def hooks():
    """Manage repository hooks and automation"""
    pass


@hooks.command('list')
def hooks_list():
    """List all registered hooks"""
    try:
        repo = ChronologRepo()
        hook_manager = HookManager(repo.repo_path)
        
        all_hooks = hook_manager.list_hooks()
        
        if not all_hooks:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No hooks registered")
            return
        
        click.echo(f"\n{Fore.GREEN}Registered Hooks:")
        for event, hooks in all_hooks.items():
            click.echo(f"\n{Fore.CYAN}{event}:")
            for hook in hooks:
                click.echo(f"  - {hook['name']}: {hook['script_path']}")
                if hook.get('description'):
                    click.echo(f"    {hook['description']}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@hooks.command('add')
@click.argument('event', type=click.Choice(['pre_version', 'post_version', 'pre_checkout', 'post_checkout']))
@click.argument('script_path', type=click.Path(exists=True))
@click.option('--name', help='Hook name')
@click.option('--description', help='Hook description')
def hooks_add(event, script_path, name, description):
    """Add a new hook for the specified event"""
    try:
        repo = ChronologRepo()
        hook_manager = HookManager(repo.repo_path)
        
        from .hooks.hook_manager import HookEvent
        hook_event = getattr(HookEvent, event.upper())
        
        hook_name = name or Path(script_path).stem
        success = hook_manager.register_script_hook(
            event=hook_event,
            script_path=Path(script_path),
            name=hook_name,
            description=description
        )
        
        if success:
            click.echo(f"{Fore.GREEN}[ChronoLog] Hook '{hook_name}' added for {event}")
        else:
            click.echo(f"{Fore.RED}[ChronoLog] Failed to add hook")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@hooks.command('remove')
@click.argument('event', type=click.Choice(['pre_version', 'post_version', 'pre_checkout', 'post_checkout']))
@click.argument('hook_name')
def hooks_remove(event, hook_name):
    """Remove a hook"""
    try:
        repo = ChronologRepo()
        hook_manager = HookManager(repo.repo_path)
        
        from .hooks.hook_manager import HookEvent
        hook_event = getattr(HookEvent, event.upper())
        
        success = hook_manager.unregister_hook(hook_event, hook_name)
        
        if success:
            click.echo(f"{Fore.GREEN}[ChronoLog] Hook '{hook_name}' removed from {event}")
        else:
            click.echo(f"{Fore.RED}[ChronoLog] Hook not found")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@hooks.command('test')
@click.argument('event', type=click.Choice(['pre_version', 'post_version', 'pre_checkout', 'post_checkout']))
@click.option('--hook-name', help='Test specific hook by name')
def hooks_test(event, hook_name):
    """Test hooks for the specified event"""
    try:
        repo = ChronologRepo()
        hook_manager = HookManager(repo.repo_path)
        
        from .hooks.hook_manager import HookEvent, HookContext
        hook_event = getattr(HookEvent, event.upper())
        
        # Create test context
        test_context = HookContext(
            event=hook_event,
            repository_path=repo.repo_path,
            file_path=None,
            version_id="test",
            metadata={"test": True}
        )
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Testing {event} hooks...")
        results = hook_manager.trigger_hooks(hook_event, test_context)
        
        for result in results:
            status = "✓" if result.success else "✗"
            color = Fore.GREEN if result.success else Fore.RED
            click.echo(f"{color}{status} {result.hook_name}: {result.message}{Style.RESET_ALL}")
            
            if result.output:
                click.echo(f"    Output: {result.output}")
            if not result.success and result.error:
                click.echo(f"    Error: {result.error}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def users():
    """User management and authentication"""
    pass


@users.command('init')
@click.option('--admin-username', default='admin', help='Admin username')
@click.option('--admin-password', prompt=True, hide_input=True, help='Admin password')
@click.option('--admin-email', help='Admin email address')
def users_init(admin_username, admin_password, admin_email):
    """Initialize user management system"""
    try:
        repo = ChronologRepo()
        user_manager = UserManager(repo.repo_path)
        
        if user_manager.has_users():
            click.echo(f"{Fore.YELLOW}[ChronoLog] User system already initialized")
            return
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Initializing user management system...")
        admin_id = user_manager.create_admin_user(
            username=admin_username,
            password=admin_password,
            email=admin_email
        )
        
        if admin_id:
            click.echo(f"{Fore.GREEN}[ChronoLog] User system initialized with admin user '{admin_username}'")
        else:
            click.echo(f"{Fore.RED}[ChronoLog] Failed to initialize user system")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@users.command('list')
def users_list():
    """List all users"""
    try:
        repo = ChronologRepo()
        user_manager = UserManager(repo.repo_path)
        
        users = user_manager.list_users()
        
        if not users:
            click.echo(f"{Fore.YELLOW}[ChronoLog] No users found. Run 'chronolog users init' first.")
            return
        
        click.echo(f"\n{Fore.GREEN}Users:")
        click.echo(f"{'-' * 80}")
        click.echo(f"{'Username':<20} {'Role':<10} {'Email':<30} {'Status':<8} {'Last Active'}")
        click.echo(f"{'-' * 80}")
        
        for user in users:
            status = 'Active' if user.is_active else 'Inactive'
            last_active = user.last_active.strftime('%Y-%m-%d') if user.last_active else 'Never'
            email = user.email or 'N/A'
            
            click.echo(f"{user.username:<20} {user.role.value:<10} {email:<30} {status:<8} {last_active}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@users.command('create')
@click.argument('username')
@click.option('--password', prompt=True, hide_input=True, help='User password')
@click.option('--email', help='User email address')
@click.option('--full-name', help='User full name')
@click.option('--role', type=click.Choice(['admin', 'user', 'readonly']), default='user', help='User role')
def users_create(username, password, email, full_name, role):
    """Create a new user"""
    try:
        repo = ChronologRepo()
        user_manager = UserManager(repo.repo_path)
        
        from .users.user_manager import UserRole
        user_role = getattr(UserRole, role.upper())
        
        user_id = user_manager.create_user(
            username=username,
            password=password,
            email=email,
            full_name=full_name,
            role=user_role
        )
        
        if user_id:
            click.echo(f"{Fore.GREEN}[ChronoLog] User '{username}' created successfully")
        else:
            click.echo(f"{Fore.RED}[ChronoLog] Failed to create user (username may already exist)")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@users.command('delete')
@click.argument('username')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
def users_delete(username, force):
    """Delete a user"""
    try:
        repo = ChronologRepo()
        user_manager = UserManager(repo.repo_path)
        
        user = user_manager.get_user_by_username(username)
        if not user:
            click.echo(f"{Fore.RED}[ChronoLog] User '{username}' not found")
            sys.exit(1)
        
        if not force:
            if not click.confirm(f"Are you sure you want to delete user '{username}'?"):
                click.echo("Cancelled")
                return
        
        success = user_manager.delete_user(user.id)
        
        if success:
            click.echo(f"{Fore.GREEN}[ChronoLog] User '{username}' deleted successfully")
        else:
            click.echo(f"{Fore.RED}[ChronoLog] Failed to delete user")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def merge():
    """Merge operations and conflict resolution"""
    pass


@merge.command('preview')
@click.argument('base_version')
@click.argument('our_version')
@click.argument('their_version')
@click.option('--file-path', help='Preview merge for specific file')
def merge_preview(base_version, our_version, their_version, file_path):
    """Preview a three-way merge operation"""
    try:
        repo = ChronologRepo()
        merge_engine = MergeEngine()
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Previewing merge...")
        click.echo(f"  Base: {base_version[:8]}")
        click.echo(f"  Ours: {our_version[:8]}")
        click.echo(f"  Theirs: {their_version[:8]}")
        
        # Get version data (simplified - in real implementation would handle file-by-file)
        from .storage.storage import ChronoLogStorage
        storage = ChronoLogStorage(repo.repo_path)
        
        base_data = storage.get_version(base_version)
        our_data = storage.get_version(our_version)
        their_data = storage.get_version(their_version)
        
        if not all([base_data, our_data, their_data]):
            click.echo(f"{Fore.RED}[ChronoLog] One or more versions not found")
            sys.exit(1)
        
        # Perform merge preview
        merge_result = merge_engine.three_way_merge(
            base=str(base_data).encode(),
            ours=str(our_data).encode(),
            theirs=str(their_data).encode()
        )
        
        if merge_result.success:
            click.echo(f"{Fore.GREEN}[ChronoLog] ✓ Merge can be performed automatically")
            click.echo(f"  Result size: {len(merge_result.content)} bytes")
        else:
            click.echo(f"{Fore.YELLOW}[ChronoLog] ⚠ Merge has conflicts")
            click.echo(f"  Conflicts found: {len(merge_result.conflicts)}")
            
            for i, conflict in enumerate(merge_result.conflicts[:5], 1):
                click.echo(f"\n  Conflict {i}:")
                click.echo(f"    Type: {conflict.conflict_type}")
                click.echo(f"    Lines: {conflict.start_line}-{conflict.end_line}")
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@merge.command('resolve')
@click.argument('conflict_file', type=click.Path(exists=True))
@click.option('--strategy', type=click.Choice(['ours', 'theirs', 'manual']), 
              default='manual', help='Conflict resolution strategy')
def merge_resolve(conflict_file, strategy):
    """Resolve merge conflicts in a file"""
    try:
        repo = ChronologRepo()
        conflict_resolver = ConflictResolver()
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Resolving conflicts in {conflict_file}...")
        
        with open(conflict_file, 'r') as f:
            content = f.read()
        
        if strategy == 'manual':
            click.echo(f"{Fore.YELLOW}[ChronoLog] Manual conflict resolution not implemented in CLI")
            click.echo(f"Please use the web interface or TUI for interactive resolution")
        else:
            resolved_content = conflict_resolver.auto_resolve_conflicts(content, strategy)
            
            if resolved_content:
                with open(conflict_file, 'w') as f:
                    f.write(resolved_content)
                click.echo(f"{Fore.GREEN}[ChronoLog] Conflicts resolved using '{strategy}' strategy")
            else:
                click.echo(f"{Fore.RED}[ChronoLog] Failed to resolve conflicts automatically")
    
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@main.group()
def web():
    """Web server management"""
    pass


@web.command('start')
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=5000, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def web_start(host, port, debug):
    """Start the web server"""
    try:
        repo = ChronologRepo()
        
        click.echo(f"{Fore.CYAN}[ChronoLog] Starting web server...")
        click.echo(f"  Host: {host}")
        click.echo(f"  Port: {port}")
        click.echo(f"  Debug: {debug}")
        
        web_server = WebServer(repo.repo_path, host=host, port=port)
        
        click.echo(f"{Fore.GREEN}[ChronoLog] Web server starting at http://{host}:{port}")
        click.echo(f"{Fore.YELLOW}Press Ctrl+C to stop the server")
        
        web_server.start(debug=debug)
    
    except NotARepositoryError:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo(f"\n{Fore.YELLOW}[ChronoLog] Web server stopped")
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error: {e}")
        sys.exit(1)


@web.command('status')
def web_status():
    """Check web server status"""
    try:
        import requests
        response = requests.get('http://127.0.0.1:5000/api/v1/health', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            click.echo(f"{Fore.GREEN}[ChronoLog] Web server is running")
            click.echo(f"  Status: {data.get('status', 'unknown')}")
            click.echo(f"  Version: {data.get('version', 'unknown')}")
        else:
            click.echo(f"{Fore.YELLOW}[ChronoLog] Web server responded with status {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        click.echo(f"{Fore.RED}[ChronoLog] Web server is not running")
    except Exception as e:
        click.echo(f"{Fore.RED}[ChronoLog] Error checking server status: {e}")


if __name__ == '__main__':
    main()