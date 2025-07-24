import os
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from ..storage import Storage
from ..ignore import IgnorePatterns


class DebouncedFileHandler(FileSystemEventHandler):
    def __init__(self, storage: Storage, base_path: Path, debounce_seconds: float = 0.5):
        self.storage = storage
        self.base_path = base_path
        self.debounce_seconds = debounce_seconds
        self.pending_files: Dict[str, float] = {}
        self.lock = threading.Lock()
        self.ignore_patterns = IgnorePatterns(base_path)
        
        # Start the processing thread
        self.processing_thread = threading.Thread(target=self._process_pending_files, daemon=True)
        self.processing_thread.start()
    
    def should_ignore(self, file_path: str) -> bool:
        path = Path(file_path)
        
        # Check if path should be ignored based on patterns
        if self.ignore_patterns.should_ignore(path):
            return True
        
        # Additionally check if file is binary
        try:
            if not path.exists():  # File might have been deleted/moved
                return True
                
            with open(file_path, 'rb') as f:
                # Read first 1KB to check if it's likely a text file
                chunk = f.read(1024)
                if b'\x00' in chunk:  # Binary file
                    return True
        except:
            return True
        
        return False
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Special handling for .chronologignore file
        if Path(event.src_path).name == '.chronologignore':
            print(f"[ChronoLog] Reloading ignore patterns from .chronologignore")
            sys.stdout.flush()
            self.ignore_patterns.reload()
            return
        
        if self.should_ignore(event.src_path):
            return
        
        print(f"[ChronoLog] File modified: {event.src_path}")
        sys.stdout.flush()
        
        with self.lock:
            self.pending_files[event.src_path] = time.time()
    
    def _process_pending_files(self):
        while True:
            time.sleep(0.1)  # Check every 100ms
            
            with self.lock:
                current_time = time.time()
                files_to_process = []
                
                for file_path, last_modified in list(self.pending_files.items()):
                    if current_time - last_modified >= self.debounce_seconds:
                        files_to_process.append(file_path)
                        del self.pending_files[file_path]
            
            for file_path in files_to_process:
                self._commit_file(file_path)
    
    def _commit_file(self, file_path: str):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Get relative path from base directory
            rel_path = os.path.relpath(file_path, self.base_path)
            
            # Get parent hash if exists
            parent_hash = self.storage.get_latest_version_hash(rel_path)
            
            # Store the new version
            version_hash = self.storage.store_version(
                rel_path, 
                content, 
                parent_hash=parent_hash,
                annotation="Auto-saved"
            )
            
            print(f"[ChronoLog] Versioned: {rel_path} -> {version_hash[:8]}")
            sys.stdout.flush()  # Ensure output is written
            
        except Exception as e:
            print(f"[ChronoLog] Error versioning {file_path}: {e}")


class Watcher:
    def __init__(self, base_path: Path, storage: Storage):
        self.base_path = base_path
        self.storage = storage
        self.observer = Observer()
        self.handler = DebouncedFileHandler(storage, base_path)
    
    def start(self):
        self.observer.schedule(self.handler, str(self.base_path), recursive=True)
        self.observer.start()
        print(f"[ChronoLog] Watching directory: {self.base_path}")
        sys.stdout.flush()
    
    def stop(self):
        self.observer.stop()
        self.observer.join()
        print("[ChronoLog] Stopped watching")