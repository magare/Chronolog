from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CloudFile:
    path: str
    size: int
    modified: datetime
    etag: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class CloudProvider(ABC):
    """Abstract base class for cloud storage providers."""
    
    @abstractmethod
    def __init__(self, config: Dict[str, any]):
        """Initialize with provider-specific configuration."""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to cloud provider."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection to cloud provider."""
        pass
    
    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to cloud storage."""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """Download a file from cloud storage."""
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from cloud storage."""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> List[CloudFile]:
        """List files in cloud storage."""
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in cloud storage."""
        pass
    
    @abstractmethod
    def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get information about a file."""
        pass
    
    @abstractmethod
    def create_directory(self, remote_path: str) -> bool:
        """Create a directory in cloud storage (if supported)."""
        pass
    
    @abstractmethod
    def sync_directory(self, local_dir: Path, remote_dir: str,
                      exclude_patterns: Optional[List[str]] = None) -> Dict[str, int]:
        """Sync entire directory to cloud storage."""
        pass
    
    @abstractmethod
    def get_storage_info(self) -> Dict[str, any]:
        """Get storage usage and limits."""
        pass
    
    def calculate_sync_delta(self, local_files: Dict[str, datetime],
                           remote_files: List[CloudFile]) -> Tuple[List[str], List[str], List[str]]:
        """
        Calculate what needs to be synced.
        
        Returns:
            (files_to_upload, files_to_download, files_to_delete)
        """
        remote_dict = {f.path: f for f in remote_files}
        
        files_to_upload = []
        files_to_download = []
        files_to_delete = []
        
        # Check local files
        for local_path, local_modified in local_files.items():
            if local_path in remote_dict:
                # File exists in both places
                remote_file = remote_dict[local_path]
                if local_modified > remote_file.modified:
                    files_to_upload.append(local_path)
                elif local_modified < remote_file.modified:
                    files_to_download.append(local_path)
            else:
                # File only exists locally
                files_to_upload.append(local_path)
        
        # Check remote files
        for remote_path, remote_file in remote_dict.items():
            if remote_path not in local_files:
                # File only exists remotely
                files_to_download.append(remote_path)
        
        return files_to_upload, files_to_download, files_to_delete