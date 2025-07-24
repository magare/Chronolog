#!/usr/bin/env python3
"""
Test script to display help output for all ChronoLog commands
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chronolog.main import main
from click.testing import CliRunner

def test_help_outputs():
    """Test and display help for all commands"""
    runner = CliRunner()
    
    commands = [
        [],  # Main help
        ['init', '--help'],
        ['log', '--help'],
        ['show', '--help'],
        ['diff', '--help'],
        ['checkout', '--help'],
        ['search', '--help'],
        ['reindex', '--help'],
        ['branch', '--help'],
        ['branch', 'create', '--help'],
        ['branch', 'list', '--help'],
        ['branch', 'switch', '--help'],
        ['branch', 'delete', '--help'],
        ['tag', '--help'],
        ['tag', 'create', '--help'],
        ['tag', 'list', '--help'],
        ['tag', 'delete', '--help'],
        ['ignore', '--help'],
        ['ignore', 'show', '--help'],
        ['ignore', 'init', '--help'],
        ['daemon', '--help'],
        ['daemon', 'start', '--help'],
        ['daemon', 'stop', '--help'],
        ['daemon', 'status', '--help'],
    ]
    
    for cmd in commands:
        print("\n" + "="*60)
        print(f"Command: chronolog {' '.join(cmd) if cmd else '--help'}")
        print("="*60)
        
        result = runner.invoke(main, cmd + ['--help'] if not any('--help' in c for c in cmd) else cmd)
        print(result.output)

if __name__ == "__main__":
    test_help_outputs()