import os
import subprocess
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class HookEvent(Enum):
    PRE_VERSION = "pre_version"
    POST_VERSION = "post_version"
    PRE_CHECKOUT = "pre_checkout"
    POST_CHECKOUT = "post_checkout"
    PRE_MERGE = "pre_merge"
    POST_MERGE = "post_merge"
    PRE_BRANCH_CREATE = "pre_branch_create"
    POST_BRANCH_CREATE = "post_branch_create"
    PRE_TAG = "pre_tag"
    POST_TAG = "post_tag"
    FILE_CHANGED = "file_changed"
    REPOSITORY_INIT = "repository_init"


@dataclass
class HookContext:
    event: HookEvent
    repository_path: Path
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]


@dataclass
class HookResult:
    success: bool
    output: str
    error: Optional[str] = None
    should_continue: bool = True


class HookManager:
    """Manages hooks for various repository events."""
    
    HOOK_TIMEOUT = 30  # seconds
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        self.hooks_dir = self.chronolog_dir / "hooks"
        self.hooks_dir.mkdir(exist_ok=True)
        
        # In-memory hook registry for Python callbacks
        self.python_hooks: Dict[HookEvent, List[Callable]] = {}
    
    def register_hook(self, event: HookEvent, hook_name: str,
                     script_path: Optional[Path] = None,
                     script_content: Optional[str] = None,
                     python_callback: Optional[Callable] = None) -> bool:
        """Register a new hook."""
        if python_callback:
            # Register Python callback
            if event not in self.python_hooks:
                self.python_hooks[event] = []
            self.python_hooks[event].append(python_callback)
            return True
        
        # Register script hook in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO hooks
                (event_type, hook_name, script_path, script_content, enabled, created_at)
                VALUES (?, ?, ?, ?, TRUE, ?)
            """, (
                event.value,
                hook_name,
                str(script_path) if script_path else None,
                script_content,
                datetime.now()
            ))
            conn.commit()
            return True
            
        except Exception as e:
            return False
        finally:
            conn.close()
    
    def unregister_hook(self, event: HookEvent, hook_name: str) -> bool:
        """Unregister a hook."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM hooks
                WHERE event_type = ? AND hook_name = ?
            """, (event.value, hook_name))
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def enable_hook(self, event: HookEvent, hook_name: str, enabled: bool = True):
        """Enable or disable a hook."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE hooks
                SET enabled = ?
                WHERE event_type = ? AND hook_name = ?
            """, (enabled, event.value, hook_name))
            conn.commit()
            
        finally:
            conn.close()
    
    def trigger_hook(self, event: HookEvent, context_data: Dict[str, Any]) -> List[HookResult]:
        """Trigger all hooks for an event."""
        context = HookContext(
            event=event,
            repository_path=self.repo_path,
            user_id=os.environ.get('CHRONOLOG_USER', 'default'),
            timestamp=datetime.now(),
            data=context_data
        )
        
        results = []
        
        # Execute Python callbacks first
        if event in self.python_hooks:
            for callback in self.python_hooks[event]:
                try:
                    result = callback(context)
                    if isinstance(result, HookResult):
                        results.append(result)
                    else:
                        results.append(HookResult(success=True, output=str(result)))
                except Exception as e:
                    results.append(HookResult(
                        success=False,
                        output="",
                        error=str(e),
                        should_continue=False
                    ))
        
        # Execute script hooks
        script_results = self._execute_script_hooks(event, context)
        results.extend(script_results)
        
        # Check if any hook wants to stop the chain
        for result in results:
            if not result.should_continue:
                break
        
        return results
    
    def _execute_script_hooks(self, event: HookEvent, 
                             context: HookContext) -> List[HookResult]:
        """Execute script-based hooks."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = []
        
        try:
            cursor.execute("""
                SELECT hook_name, script_path, script_content
                FROM hooks
                WHERE event_type = ? AND enabled = TRUE
                ORDER BY hook_name
            """, (event.value,))
            
            for hook_name, script_path, script_content in cursor.fetchall():
                if script_path:
                    result = self._execute_script_file(Path(script_path), context)
                elif script_content:
                    result = self._execute_script_content(script_content, context)
                else:
                    continue
                
                results.append(result)
                
                if not result.should_continue:
                    break
            
            return results
            
        finally:
            conn.close()
    
    def _execute_script_file(self, script_path: Path, 
                            context: HookContext) -> HookResult:
        """Execute a hook script file."""
        if not script_path.exists():
            return HookResult(
                success=False,
                output="",
                error=f"Script file not found: {script_path}"
            )
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            'CHRONOLOG_EVENT': context.event.value,
            'CHRONOLOG_REPO': str(context.repository_path),
            'CHRONOLOG_USER': context.user_id,
            'CHRONOLOG_TIMESTAMP': context.timestamp.isoformat(),
            'CHRONOLOG_DATA': json.dumps(context.data)
        })
        
        try:
            # Determine how to execute based on file extension
            if script_path.suffix == '.py':
                cmd = ['python', str(script_path)]
            elif script_path.suffix in ['.sh', '.bash']:
                cmd = ['bash', str(script_path)]
            else:
                # Try to execute directly
                cmd = [str(script_path)]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.HOOK_TIMEOUT,
                cwd=self.repo_path
            )
            
            return HookResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                should_continue=result.returncode != 100  # Special code to stop chain
            )
            
        except subprocess.TimeoutExpired:
            return HookResult(
                success=False,
                output="",
                error=f"Hook timed out after {self.HOOK_TIMEOUT} seconds"
            )
        except Exception as e:
            return HookResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _execute_script_content(self, script_content: str, 
                               context: HookContext) -> HookResult:
        """Execute inline script content."""
        # Create temporary script file
        script_file = self.hooks_dir / f"temp_{context.timestamp.timestamp()}.py"
        
        try:
            script_file.write_text(script_content)
            result = self._execute_script_file(script_file, context)
            return result
            
        finally:
            if script_file.exists():
                script_file.unlink()
    
    def list_hooks(self, event: Optional[HookEvent] = None) -> List[Dict[str, Any]]:
        """List all registered hooks."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if event:
                cursor.execute("""
                    SELECT event_type, hook_name, script_path, enabled, created_at
                    FROM hooks
                    WHERE event_type = ?
                    ORDER BY hook_name
                """, (event.value,))
            else:
                cursor.execute("""
                    SELECT event_type, hook_name, script_path, enabled, created_at
                    FROM hooks
                    ORDER BY event_type, hook_name
                """)
            
            hooks = []
            for row in cursor.fetchall():
                hooks.append({
                    'event': row[0],
                    'name': row[1],
                    'script_path': row[2],
                    'enabled': bool(row[3]),
                    'created_at': row[4]
                })
            
            return hooks
            
        finally:
            conn.close()
    
    def create_hook_template(self, event: HookEvent, language: str = "python") -> str:
        """Generate a hook template for the given event."""
        if language == "python":
            return f'''#!/usr/bin/env python3
"""
ChronoLog Hook: {event.value}
Generated: {datetime.now().isoformat()}
"""

import os
import sys
import json

# Get hook context from environment
event = os.environ.get('CHRONOLOG_EVENT', '')
repo_path = os.environ.get('CHRONOLOG_REPO', '')
user = os.environ.get('CHRONOLOG_USER', '')
timestamp = os.environ.get('CHRONOLOG_TIMESTAMP', '')
data = json.loads(os.environ.get('CHRONOLOG_DATA', '{{}}'))

print(f"Hook triggered: {{event}}")
print(f"Repository: {{repo_path}}")
print(f"Data: {{data}}")

# Your hook logic here
# Return 0 for success, non-zero for failure
# Return 100 to stop hook chain execution

# Example: Validate file changes
if event == 'pre_version':
    file_path = data.get('file_path', '')
    if file_path.endswith('.py'):
        # Could run linting, tests, etc.
        print(f"Python file changed: {{file_path}}")

sys.exit(0)
'''
        
        elif language == "bash":
            return f'''#!/bin/bash
# ChronoLog Hook: {event.value}
# Generated: {datetime.now().isoformat()}

echo "Hook triggered: $CHRONOLOG_EVENT"
echo "Repository: $CHRONOLOG_REPO"
echo "User: $CHRONOLOG_USER"
echo "Data: $CHRONOLOG_DATA"

# Your hook logic here
# Return 0 for success, non-zero for failure
# Return 100 to stop hook chain execution

# Example: Log the event
echo "[$(date)] $CHRONOLOG_EVENT triggered by $CHRONOLOG_USER" >> hooks.log

exit 0
'''
        
        else:
            return f"# Hook template for {event.value}"
    
    def install_default_hooks(self):
        """Install useful default hooks."""
        # Pre-version validation hook
        validation_hook = '''
import os
import json
import sys

data = json.loads(os.environ.get('CHRONOLOG_DATA', '{}'))
file_path = data.get('file_path', '')

# Skip validation for certain files
skip_patterns = ['.chronolog', '__pycache__', '.git']
if any(pattern in file_path for pattern in skip_patterns):
    sys.exit(0)

# Validate file size
max_size_mb = 100
file_size = data.get('file_size', 0)
if file_size > max_size_mb * 1024 * 1024:
    print(f"Error: File too large ({file_size / 1024 / 1024:.1f} MB > {max_size_mb} MB)")
    sys.exit(1)

print(f"Validation passed for {file_path}")
sys.exit(0)
'''
        
        self.register_hook(
            HookEvent.PRE_VERSION,
            "default_validation",
            script_content=validation_hook
        )
        
        # Post-version metrics collection hook
        metrics_hook = '''
import os
import json

data = json.loads(os.environ.get('CHRONOLOG_DATA', '{}'))
file_path = data.get('file_path', '')
version_hash = data.get('version_hash', '')

# Log version creation
print(f"New version created: {version_hash} for {file_path}")

# Could trigger additional processing here
# - Code analysis
# - Notification
# - Backup
'''
        
        self.register_hook(
            HookEvent.POST_VERSION,
            "default_metrics",
            script_content=metrics_hook
        )