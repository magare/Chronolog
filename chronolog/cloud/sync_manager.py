import json
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from .cloud_provider import CloudProvider
from .s3_provider import S3Provider


class SyncDirection(Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(Enum):
    NEWEST_WINS = "newest_wins"
    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    MANUAL = "manual"


@dataclass
class SyncConfig:
    provider_type: str
    provider_config: Dict[str, any]
    sync_direction: SyncDirection
    conflict_resolution: ConflictResolution
    exclude_patterns: List[str]
    bandwidth_limit: Optional[int] = None  # KB/s
    encryption_enabled: bool = True
    compression_enabled: bool = True


@dataclass
class SyncState:
    last_sync: Optional[datetime] = None
    files_synced: Dict[str, str] = None  # path -> hash
    sync_errors: List[Dict[str, str]] = None
    
    def to_dict(self):
        data = asdict(self)
        if self.last_sync:
            data['last_sync'] = self.last_sync.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        if data.get('last_sync'):
            data['last_sync'] = datetime.fromisoformat(data['last_sync'])
        return cls(**data)


class CloudSyncManager:
    """Manages cloud synchronization for ChronoLog repositories."""
    
    PROVIDER_CLASSES = {
        's3': S3Provider,
        # Future: 'gdrive': GDriveProvider,
        # Future: 'dropbox': DropboxProvider,
    }
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.sync_dir = self.chronolog_dir / "sync"
        self.sync_dir.mkdir(exist_ok=True)
        
        self.config_file = self.sync_dir / "sync_config.json"
        self.state_file = self.sync_dir / "sync_state.json"
        self.conflict_file = self.sync_dir / "conflicts.json"
        
        self.config: Optional[SyncConfig] = None
        self.state: SyncState = SyncState(files_synced={}, sync_errors=[])
        self.provider: Optional[CloudProvider] = None
        self.sync_thread: Optional[threading.Thread] = None
        self.syncing = False
        
        self._load_config()
        self._load_state()
    
    def _load_config(self):
        """Load sync configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    data['sync_direction'] = SyncDirection(data['sync_direction'])
                    data['conflict_resolution'] = ConflictResolution(data['conflict_resolution'])
                    self.config = SyncConfig(**data)
            except:
                self.config = None
    
    def _save_config(self):
        """Save sync configuration."""
        if self.config:
            data = asdict(self.config)
            data['sync_direction'] = self.config.sync_direction.value
            data['conflict_resolution'] = self.config.conflict_resolution.value
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
    
    def _load_state(self):
        """Load sync state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.state = SyncState.from_dict(data)
            except:
                self.state = SyncState(files_synced={}, sync_errors=[])
    
    def _save_state(self):
        """Save sync state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)
    
    def configure(self, provider_type: str, provider_config: Dict[str, any],
                 sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
                 conflict_resolution: ConflictResolution = ConflictResolution.NEWEST_WINS,
                 exclude_patterns: Optional[List[str]] = None):
        """Configure cloud sync."""
        if provider_type not in self.PROVIDER_CLASSES:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        self.config = SyncConfig(
            provider_type=provider_type,
            provider_config=provider_config,
            sync_direction=sync_direction,
            conflict_resolution=conflict_resolution,
            exclude_patterns=exclude_patterns or [
                '.chronolog/*',
                '*.tmp',
                '*.swp',
                '.DS_Store',
                'Thumbs.db'
            ]
        )
        
        self._save_config()
        
        # Initialize provider
        provider_class = self.PROVIDER_CLASSES[provider_type]
        self.provider = provider_class(provider_config)
    
    def connect(self) -> bool:
        """Connect to cloud provider."""
        if not self.provider:
            raise RuntimeError("No provider configured")
        
        return self.provider.connect()
    
    def disconnect(self):
        """Disconnect from cloud provider."""
        if self.provider:
            self.provider.disconnect()
    
    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from sync."""
        rel_path = file_path.relative_to(self.repo_path)
        path_str = str(rel_path)
        
        for pattern in self.config.exclude_patterns:
            if '*' in pattern:
                # Simple glob matching
                import fnmatch
                if fnmatch.fnmatch(path_str, pattern):
                    return True
            else:
                # Exact match or substring
                if pattern in path_str:
                    return True
        
        return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _handle_conflict(self, local_path: Path, remote_path: str,
                        local_modified: datetime, remote_modified: datetime) -> str:
        """
        Handle sync conflict.
        
        Returns:
            'upload', 'download', or 'skip'
        """
        if self.config.conflict_resolution == ConflictResolution.NEWEST_WINS:
            return 'upload' if local_modified > remote_modified else 'download'
        elif self.config.conflict_resolution == ConflictResolution.LOCAL_WINS:
            return 'upload'
        elif self.config.conflict_resolution == ConflictResolution.REMOTE_WINS:
            return 'download'
        else:  # MANUAL
            # Record conflict for manual resolution
            conflicts = []
            if self.conflict_file.exists():
                with open(self.conflict_file, 'r') as f:
                    conflicts = json.load(f)
            
            conflicts.append({
                'local_path': str(local_path),
                'remote_path': remote_path,
                'local_modified': local_modified.isoformat(),
                'remote_modified': remote_modified.isoformat(),
                'detected_at': datetime.now().isoformat()
            })
            
            with open(self.conflict_file, 'w') as f:
                json.dump(conflicts, f, indent=2)
            
            return 'skip'
    
    def sync(self, force: bool = False) -> Dict[str, int]:
        """
        Perform synchronization.
        
        Args:
            force: Force full sync, ignoring state
            
        Returns:
            Statistics dictionary
        """
        if not self.provider or not self.config:
            raise RuntimeError("Sync not configured")
        
        if self.syncing:
            raise RuntimeError("Sync already in progress")
        
        self.syncing = True
        stats = {
            'uploaded': 0,
            'downloaded': 0,
            'conflicts': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Connect if not connected
            if not self.provider.connected:
                self.provider.connect()
            
            # Get local files
            local_files = {}
            for root, dirs, files in self.repo_path.rglob('*'):
                if root.is_file() and not self._should_exclude(root):
                    rel_path = root.relative_to(self.repo_path)
                    local_files[str(rel_path)] = {
                        'path': root,
                        'modified': datetime.fromtimestamp(root.stat().st_mtime),
                        'hash': self._calculate_file_hash(root) if not force else None
                    }
            
            # Get remote files
            remote_files = {f.path: f for f in self.provider.list_files()}
            
            # Sync based on direction
            if self.config.sync_direction in [SyncDirection.UPLOAD, SyncDirection.BIDIRECTIONAL]:
                # Upload local changes
                for rel_path, local_info in local_files.items():
                    try:
                        if rel_path in remote_files:
                            # File exists remotely
                            remote_file = remote_files[rel_path]
                            
                            # Check if sync needed
                            if force or rel_path not in self.state.files_synced:
                                action = self._handle_conflict(
                                    local_info['path'], rel_path,
                                    local_info['modified'], remote_file.modified
                                )
                                
                                if action == 'upload':
                                    self.provider.upload_file(local_info['path'], rel_path)
                                    stats['uploaded'] += 1
                                    self.state.files_synced[rel_path] = local_info['hash']
                                elif action == 'skip':
                                    stats['conflicts'] += 1
                            else:
                                stats['skipped'] += 1
                        else:
                            # File doesn't exist remotely
                            self.provider.upload_file(local_info['path'], rel_path)
                            stats['uploaded'] += 1
                            self.state.files_synced[rel_path] = local_info['hash']
                    
                    except Exception as e:
                        stats['errors'] += 1
                        self.state.sync_errors.append({
                            'file': rel_path,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        })
            
            if self.config.sync_direction in [SyncDirection.DOWNLOAD, SyncDirection.BIDIRECTIONAL]:
                # Download remote changes
                for remote_path, remote_file in remote_files.items():
                    if remote_path not in local_files:
                        try:
                            # File doesn't exist locally
                            local_path = self.repo_path / remote_path
                            self.provider.download_file(remote_path, local_path)
                            stats['downloaded'] += 1
                            
                            # Update state
                            file_hash = self._calculate_file_hash(local_path)
                            self.state.files_synced[remote_path] = file_hash
                        
                        except Exception as e:
                            stats['errors'] += 1
                            self.state.sync_errors.append({
                                'file': remote_path,
                                'error': str(e),
                                'timestamp': datetime.now().isoformat()
                            })
            
            # Update state
            self.state.last_sync = datetime.now()
            self._save_state()
            
            return stats
        
        finally:
            self.syncing = False
    
    def get_sync_status(self) -> Dict[str, any]:
        """Get current sync status."""
        status = {
            'configured': self.config is not None,
            'connected': self.provider and self.provider.connected,
            'syncing': self.syncing,
            'last_sync': self.state.last_sync,
            'files_synced': len(self.state.files_synced),
            'pending_conflicts': 0,
            'recent_errors': len(self.state.sync_errors)
        }
        
        if self.conflict_file.exists():
            with open(self.conflict_file, 'r') as f:
                conflicts = json.load(f)
                status['pending_conflicts'] = len(conflicts)
        
        if self.provider and self.provider.connected:
            try:
                storage_info = self.provider.get_storage_info()
                status['storage_info'] = storage_info
            except:
                pass
        
        return status
    
    def resolve_conflict(self, local_path: str, resolution: str):
        """Resolve a sync conflict."""
        if resolution not in ['upload', 'download', 'skip']:
            raise ValueError("Invalid resolution")
        
        # Load conflicts
        if not self.conflict_file.exists():
            return
        
        with open(self.conflict_file, 'r') as f:
            conflicts = json.load(f)
        
        # Find and resolve conflict
        remaining_conflicts = []
        for conflict in conflicts:
            if conflict['local_path'] == local_path:
                if resolution == 'upload':
                    self.provider.upload_file(
                        Path(conflict['local_path']),
                        conflict['remote_path']
                    )
                elif resolution == 'download':
                    self.provider.download_file(
                        conflict['remote_path'],
                        Path(conflict['local_path'])
                    )
            else:
                remaining_conflicts.append(conflict)
        
        # Save remaining conflicts
        with open(self.conflict_file, 'w') as f:
            json.dump(remaining_conflicts, f, indent=2)
    
    def start_auto_sync(self, interval_seconds: int = 300):
        """Start automatic sync in background."""
        def sync_loop():
            while self.syncing:
                try:
                    self.sync()
                except:
                    pass
                
                # Wait for interval
                for _ in range(interval_seconds):
                    if not self.syncing:
                        break
                    threading.Event().wait(1)
        
        if not self.sync_thread or not self.sync_thread.is_alive():
            self.syncing = True
            self.sync_thread = threading.Thread(target=sync_loop, daemon=True)
            self.sync_thread.start()
    
    def stop_auto_sync(self):
        """Stop automatic sync."""
        self.syncing = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)