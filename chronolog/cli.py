import os
import sys
import click
import difflib
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style
from .storage import Storage
from .daemon import Daemon

# Initialize colorama for cross-platform colored output
init(autoreset=True)

CHRONOLOG_DIR = ".chronolog"


def get_chronolog_base() -> Path:
    """Find the base directory containing .chronolog"""
    current = Path.cwd()
    while current != current.parent:
        if (current / CHRONOLOG_DIR).exists():
            return current
        current = current.parent
    return None


@click.group()
def main():
    """ChronoLog - Frictionless version control for creative workflows"""
    pass


@main.command()
def init():
    """Initialize ChronoLog in the current directory"""
    base_path = Path.cwd()
    chronolog_dir = base_path / CHRONOLOG_DIR
    
    if chronolog_dir.exists():
        click.echo(f"{Fore.YELLOW}[ChronoLog] Already initialized in this directory")
        return
    
    # Create .chronolog directory
    chronolog_dir.mkdir(exist_ok=True)
    
    # Initialize storage
    storage = Storage(chronolog_dir)
    
    # Start the daemon
    daemon = Daemon(base_path)
    daemon.start()
    
    click.echo(f"{Fore.GREEN}[ChronoLog] Initialized in {base_path}")
    click.echo(f"{Fore.GREEN}[ChronoLog] Background watcher started")


@main.command()
@click.argument('file_path', type=click.Path(exists=True))
def log(file_path):
    """View version history for a file"""
    base_path = get_chronolog_base()
    if not base_path:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory. Run 'chronolog init' first.")
        sys.exit(1)
    
    # Get relative path
    file_path = Path(file_path)
    rel_path = file_path.relative_to(base_path) if file_path.is_absolute() else file_path
    
    storage = Storage(base_path / CHRONOLOG_DIR)
    history = storage.get_file_history(str(rel_path))
    
    if not history:
        click.echo(f"{Fore.YELLOW}[ChronoLog] No history found for {rel_path}")
        return
    
    click.echo(f"\n{Fore.CYAN}Version history for {rel_path}:")
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


@main.command()
@click.argument('version_hash')
def show(version_hash):
    """Show the content of a specific version"""
    base_path = get_chronolog_base()
    if not base_path:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    
    storage = Storage(base_path / CHRONOLOG_DIR)
    
    # Support short hashes
    if len(version_hash) < 64:
        # Find full hash
        conn = storage.db_path.parent / "history.db"
        import sqlite3
        db = sqlite3.connect(conn)
        cursor = db.cursor()
        cursor.execute(
            "SELECT version_hash FROM versions WHERE version_hash LIKE ?",
            (version_hash + '%',)
        )
        results = cursor.fetchall()
        db.close()
        
        if not results:
            click.echo(f"{Fore.RED}[ChronoLog] Version {version_hash} not found")
            sys.exit(1)
        elif len(results) > 1:
            click.echo(f"{Fore.RED}[ChronoLog] Ambiguous version hash. Matches:")
            for r in results[:10]:
                click.echo(f"  {r[0][:16]}")
            sys.exit(1)
        
        version_hash = results[0][0]
    
    content = storage.get_version_content(version_hash)
    if not content:
        click.echo(f"{Fore.RED}[ChronoLog] Version {version_hash[:8]} not found")
        sys.exit(1)
    
    # Print content
    try:
        click.echo(content.decode('utf-8'))
    except UnicodeDecodeError:
        click.echo(f"{Fore.YELLOW}[ChronoLog] Binary content (cannot display)")


@main.command()
@click.argument('hash1')
@click.argument('hash2', required=False)
@click.option('--current', is_flag=True, help='Compare with current file')
def diff(hash1, hash2, current):
    """Show differences between two versions"""
    base_path = get_chronolog_base()
    if not base_path:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    
    storage = Storage(base_path / CHRONOLOG_DIR)
    
    # Get content for first hash
    content1 = storage.get_version_content(hash1)
    if not content1:
        # Try to find by short hash
        if len(hash1) < 64:
            import sqlite3
            db = sqlite3.connect(storage.db_path)
            cursor = db.cursor()
            cursor.execute(
                "SELECT version_hash FROM versions WHERE version_hash LIKE ?",
                (hash1 + '%',)
            )
            results = cursor.fetchall()
            db.close()
            
            if results:
                hash1 = results[0][0]
                content1 = storage.get_version_content(hash1)
    
    if not content1:
        click.echo(f"{Fore.RED}[ChronoLog] Version {hash1} not found")
        sys.exit(1)
    
    # Get version info to find file path
    info1 = storage.get_version_info(hash1)
    file_path = info1['file_path']
    
    # Get content for comparison
    if current:
        # Compare with current file
        current_file = base_path / file_path
        if not current_file.exists():
            click.echo(f"{Fore.RED}[ChronoLog] Current file {file_path} not found")
            sys.exit(1)
        content2 = current_file.read_bytes()
        label2 = "current"
    else:
        # Compare with second hash
        if not hash2:
            click.echo(f"{Fore.RED}[ChronoLog] Second version hash required (or use --current)")
            sys.exit(1)
        
        content2 = storage.get_version_content(hash2)
        if not content2:
            # Try short hash
            if len(hash2) < 64:
                import sqlite3
                db = sqlite3.connect(storage.db_path)
                cursor = db.cursor()
                cursor.execute(
                    "SELECT version_hash FROM versions WHERE version_hash LIKE ?",
                    (hash2 + '%',)
                )
                results = cursor.fetchall()
                db.close()
                
                if results:
                    hash2 = results[0][0]
                    content2 = storage.get_version_content(hash2)
        
        if not content2:
            click.echo(f"{Fore.RED}[ChronoLog] Version {hash2} not found")
            sys.exit(1)
        label2 = hash2[:8]
    
    # Convert to lines for diff
    try:
        lines1 = content1.decode('utf-8').splitlines(keepends=True)
        lines2 = content2.decode('utf-8').splitlines(keepends=True)
    except UnicodeDecodeError:
        click.echo(f"{Fore.YELLOW}[ChronoLog] Cannot diff binary files")
        sys.exit(1)
    
    # Generate diff
    diff_lines = difflib.unified_diff(
        lines1, lines2,
        fromfile=f"{file_path} ({hash1[:8]})",
        tofile=f"{file_path} ({label2})",
        lineterm=''
    )
    
    # Display colored diff
    for line in diff_lines:
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


@main.command()
@click.argument('version_hash')
@click.argument('file_path', type=click.Path())
def checkout(version_hash, file_path):
    """Revert a file to a previous version"""
    base_path = get_chronolog_base()
    if not base_path:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    
    storage = Storage(base_path / CHRONOLOG_DIR)
    
    # Get version content
    content = storage.get_version_content(version_hash)
    if not content:
        # Try short hash
        if len(version_hash) < 64:
            import sqlite3
            db = sqlite3.connect(storage.db_path)
            cursor = db.cursor()
            cursor.execute(
                "SELECT version_hash FROM versions WHERE version_hash LIKE ?",
                (version_hash + '%',)
            )
            results = cursor.fetchall()
            db.close()
            
            if results:
                version_hash = results[0][0]
                content = storage.get_version_content(version_hash)
    
    if not content:
        click.echo(f"{Fore.RED}[ChronoLog] Version {version_hash} not found")
        sys.exit(1)
    
    # Write content to file
    file_path = Path(file_path)
    if not file_path.is_absolute():
        file_path = base_path / file_path
    
    # Backup current content first
    if file_path.exists():
        current_content = file_path.read_bytes()
        rel_path = file_path.relative_to(base_path)
        storage.store_version(
            str(rel_path),
            current_content,
            annotation=f"Before checkout to {version_hash[:8]}"
        )
    
    # Write the old version
    file_path.write_bytes(content)
    
    # Record this checkout as a new version
    rel_path = file_path.relative_to(base_path)
    storage.store_version(
        str(rel_path),
        content,
        parent_hash=version_hash,
        annotation=f"Checked out from {version_hash[:8]}"
    )
    
    click.echo(f"{Fore.GREEN}[ChronoLog] Checked out {rel_path} to version {version_hash[:8]}")


@main.group()
def daemon():
    """Manage the ChronoLog daemon"""
    pass


@daemon.command('start')
def daemon_start():
    """Start the background daemon"""
    base_path = get_chronolog_base()
    if not base_path:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    
    d = Daemon(base_path)
    d.start()


@daemon.command('stop')
def daemon_stop():
    """Stop the background daemon"""
    base_path = get_chronolog_base()
    if not base_path:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    
    d = Daemon(base_path)
    d.stop()


@daemon.command('status')
def daemon_status():
    """Check daemon status"""
    base_path = get_chronolog_base()
    if not base_path:
        click.echo(f"{Fore.RED}[ChronoLog] Not in a ChronoLog directory")
        sys.exit(1)
    
    d = Daemon(base_path)
    d.status()


if __name__ == '__main__':
    main()