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
    """ChronoLog - Frictionless version control for creative workflows"""
    pass


@main.command()
def init():
    """Initialize ChronoLog in the current directory"""
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
    """View version history for a file"""
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


if __name__ == '__main__':
    main()