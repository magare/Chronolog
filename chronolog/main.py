import sys
import click
from datetime import datetime
from colorama import init, Fore, Style

# Import the new API class and custom exceptions
from .api import ChronologRepo, NotARepositoryError, RepositoryExistsError

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
def diff(hash1, hash2, current):
    """Show differences between two versions"""
    try:
        repo = ChronologRepo()
        
        if current:
            diff_output = repo.diff(hash1, current=True)
        else:
            if not hash2:
                click.echo(f"{Fore.RED}[ChronoLog] Second version hash required (or use --current)")
                sys.exit(1)
            diff_output = repo.diff(hash1, hash2)
        
        # Display colored diff
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


if __name__ == '__main__':
    main()