import os
import shutil
import tarfile
import gzip
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class BackupMetadata:
    backup_id: str
    timestamp: datetime
    repo_path: str
    backup_type: str  # 'full' or 'incremental'
    size: int
    file_count: int
    compression: str
    parent_backup_id: Optional[str] = None
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class BackupManager:
    """Manages local backups for ChronoLog repositories."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.backups_dir = self.chronolog_dir / "backups"
        self.backups_dir.mkdir(exist_ok=True)
        self.metadata_file = self.backups_dir / "backup_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load backup metadata from file."""
        self.metadata = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    for backup_id, meta in data.items():
                        self.metadata[backup_id] = BackupMetadata.from_dict(meta)
            except:
                self.metadata = {}
    
    def _save_metadata(self):
        """Save backup metadata to file."""
        data = {
            backup_id: meta.to_dict() 
            for backup_id, meta in self.metadata.items()
        }
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_backup(self, destination: Path, backup_type: str = "full",
                     compression: str = "gzip", incremental_from: Optional[str] = None) -> str:
        """
        Create a backup of the repository.
        
        Args:
            destination: Directory to store the backup
            backup_type: 'full' or 'incremental'
            compression: 'gzip', 'bzip2', or 'none'
            incremental_from: Parent backup ID for incremental backups
            
        Returns:
            Backup ID
        """
        # Generate backup ID
        timestamp = datetime.now()
        backup_id = timestamp.strftime("%Y%m%d_%H%M%S") + "_" + hashlib.md5(
            str(timestamp).encode()
        ).hexdigest()[:8]
        
        # Create destination directory
        destination.mkdir(parents=True, exist_ok=True)
        
        # Determine backup filename
        if compression == "gzip":
            backup_file = destination / f"chronolog_backup_{backup_id}.tar.gz"
            tar_mode = "w:gz"
        elif compression == "bzip2":
            backup_file = destination / f"chronolog_backup_{backup_id}.tar.bz2"
            tar_mode = "w:bz2"
        else:
            backup_file = destination / f"chronolog_backup_{backup_id}.tar"
            tar_mode = "w"
        
        # Create backup
        file_count = 0
        total_size = 0
        
        with tarfile.open(backup_file, tar_mode) as tar:
            if backup_type == "full":
                # Full backup - include everything
                tar.add(self.chronolog_dir, arcname=".chronolog")
                file_count = sum(1 for _ in self.chronolog_dir.rglob("*") if _.is_file())
                total_size = sum(f.stat().st_size for f in self.chronolog_dir.rglob("*") if f.is_file())
                
                # Include tracked files
                for root, dirs, files in os.walk(self.repo_path):
                    if '.chronolog' in root:
                        continue
                    
                    for file in files:
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(self.repo_path)
                        tar.add(file_path, arcname=str(rel_path))
                        file_count += 1
                        total_size += file_path.stat().st_size
            
            elif backup_type == "incremental" and incremental_from:
                # Incremental backup - only changed files since parent backup
                parent_meta = self.metadata.get(incremental_from)
                if not parent_meta:
                    raise ValueError(f"Parent backup {incremental_from} not found")
                
                parent_timestamp = parent_meta.timestamp
                
                # Backup only modified files
                for root, dirs, files in os.walk(self.repo_path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.stat().st_mtime > parent_timestamp.timestamp():
                            rel_path = file_path.relative_to(self.repo_path)
                            tar.add(file_path, arcname=str(rel_path))
                            file_count += 1
                            total_size += file_path.stat().st_size
        
        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=timestamp,
            repo_path=str(self.repo_path),
            backup_type=backup_type,
            size=backup_file.stat().st_size,
            file_count=file_count,
            compression=compression,
            parent_backup_id=incremental_from
        )
        
        # Save metadata
        self.metadata[backup_id] = metadata
        self._save_metadata()
        
        # Create info file
        info_file = destination / f"chronolog_backup_{backup_id}.info"
        with open(info_file, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        return backup_id
    
    def restore_backup(self, backup_file: Path, restore_path: Path,
                      selective: Optional[List[str]] = None) -> bool:
        """
        Restore a backup to specified location.
        
        Args:
            backup_file: Path to backup file
            restore_path: Directory to restore to
            selective: Optional list of file patterns to restore
            
        Returns:
            Success status
        """
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file {backup_file} not found")
        
        # Determine compression from filename
        if backup_file.suffix == ".gz":
            tar_mode = "r:gz"
        elif backup_file.suffix == ".bz2":
            tar_mode = "r:bz2"
        else:
            tar_mode = "r"
        
        # Create restore directory
        restore_path.mkdir(parents=True, exist_ok=True)
        
        # Extract backup
        with tarfile.open(backup_file, tar_mode) as tar:
            if selective:
                # Selective restore
                members = []
                for member in tar.getmembers():
                    for pattern in selective:
                        if pattern in member.name:
                            members.append(member)
                            break
                tar.extractall(restore_path, members=members)
            else:
                # Full restore
                tar.extractall(restore_path)
        
        return True
    
    def list_backups(self, destination: Optional[Path] = None) -> List[BackupMetadata]:
        """List all available backups."""
        backups = []
        
        # List from metadata
        backups.extend(self.metadata.values())
        
        # If destination provided, scan for backup files
        if destination and destination.exists():
            for file in destination.glob("chronolog_backup_*.info"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        backup = BackupMetadata.from_dict(data)
                        if backup.backup_id not in self.metadata:
                            backups.append(backup)
                except:
                    continue
        
        return sorted(backups, key=lambda b: b.timestamp, reverse=True)
    
    def verify_backup(self, backup_file: Path) -> Tuple[bool, str]:
        """
        Verify backup integrity.
        
        Returns:
            (is_valid, message)
        """
        if not backup_file.exists():
            return False, "Backup file not found"
        
        # Check if info file exists
        info_file = backup_file.with_suffix('').with_suffix('.info')
        if not info_file.exists():
            return False, "Backup info file not found"
        
        try:
            # Verify tarfile integrity
            if backup_file.suffix == ".gz":
                tar_mode = "r:gz"
            elif backup_file.suffix == ".bz2":
                tar_mode = "r:bz2"
            else:
                tar_mode = "r"
            
            with tarfile.open(backup_file, tar_mode) as tar:
                # Test extraction without actually extracting
                tar.getmembers()
            
            return True, "Backup is valid"
        
        except Exception as e:
            return False, f"Backup verification failed: {e}"
    
    def prune_backups(self, destination: Path, keep_days: int = 30,
                     keep_count: Optional[int] = None) -> List[str]:
        """
        Remove old backups based on age or count.
        
        Args:
            destination: Backup directory
            keep_days: Keep backups newer than this many days
            keep_count: Keep this many recent backups
            
        Returns:
            List of removed backup IDs
        """
        backups = self.list_backups(destination)
        removed = []
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        
        cutoff_date = datetime.now().timestamp() - (keep_days * 86400)
        
        for i, backup in enumerate(backups):
            should_remove = False
            
            # Check age
            if backup.timestamp.timestamp() < cutoff_date:
                should_remove = True
            
            # Check count
            if keep_count and i >= keep_count:
                should_remove = True
            
            # Don't remove if it's a parent of another backup
            is_parent = any(
                b.parent_backup_id == backup.backup_id 
                for b in backups if b != backup
            )
            
            if should_remove and not is_parent:
                # Remove backup files
                backup_file = destination / f"chronolog_backup_{backup.backup_id}.tar"
                for ext in ['.gz', '.bz2', '']:
                    file = destination / f"chronolog_backup_{backup.backup_id}.tar{ext}"
                    if file.exists():
                        file.unlink()
                        break
                
                # Remove info file
                info_file = destination / f"chronolog_backup_{backup.backup_id}.info"
                if info_file.exists():
                    info_file.unlink()
                
                # Remove from metadata
                if backup.backup_id in self.metadata:
                    del self.metadata[backup.backup_id]
                
                removed.append(backup.backup_id)
        
        # Save updated metadata
        self._save_metadata()
        
        return removed
    
    def get_backup_chain(self, backup_id: str) -> List[BackupMetadata]:
        """Get all backups in the chain (for incremental backups)."""
        chain = []
        current_id = backup_id
        
        while current_id:
            backup = self.metadata.get(current_id)
            if not backup:
                break
            
            chain.append(backup)
            current_id = backup.parent_backup_id
        
        return list(reversed(chain))  # Return oldest first
    
    def estimate_backup_size(self, backup_type: str = "full",
                           compression: str = "gzip") -> int:
        """Estimate the size of a backup."""
        total_size = 0
        
        # Calculate .chronolog directory size
        for file in self.chronolog_dir.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
        
        if backup_type == "full":
            # Add tracked files
            for root, dirs, files in os.walk(self.repo_path):
                if '.chronolog' in root:
                    continue
                
                for file in files:
                    file_path = Path(root) / file
                    if file_path.exists():
                        total_size += file_path.stat().st_size
        
        # Estimate compression ratio
        if compression == "gzip":
            total_size = int(total_size * 0.3)  # ~70% compression
        elif compression == "bzip2":
            total_size = int(total_size * 0.25)  # ~75% compression
        
        return total_size