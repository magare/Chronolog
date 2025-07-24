import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import fnmatch

from .cloud_provider import CloudProvider, CloudFile


class S3Provider(CloudProvider):
    """AWS S3 cloud storage provider."""
    
    def __init__(self, config: Dict[str, any]):
        """
        Initialize S3 provider.
        
        Config should include:
        - bucket_name: S3 bucket name
        - aws_access_key_id: AWS access key (optional if using IAM role)
        - aws_secret_access_key: AWS secret key (optional if using IAM role)
        - region: AWS region (default: us-east-1)
        - prefix: Optional prefix for all operations
        - encryption: Enable server-side encryption (default: True)
        """
        self.config = config
        self.bucket_name = config['bucket_name']
        self.prefix = config.get('prefix', '')
        self.region = config.get('region', 'us-east-1')
        self.encryption = config.get('encryption', True)
        self.s3_client = None
        self.connected = False
        
        # Note: boto3 is optional dependency
        try:
            import boto3
            self.boto3 = boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 support. "
                "Install it with: pip install chronolog[s3]"
            )
    
    def connect(self) -> bool:
        """Establish connection to S3."""
        try:
            # Create S3 client
            if 'aws_access_key_id' in self.config:
                self.s3_client = self.boto3.client(
                    's3',
                    aws_access_key_id=self.config['aws_access_key_id'],
                    aws_secret_access_key=self.config['aws_secret_access_key'],
                    region_name=self.region
                )
            else:
                # Use default credentials (IAM role, env vars, etc.)
                self.s3_client = self.boto3.client('s3', region_name=self.region)
            
            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.connected = True
            return True
            
        except Exception as e:
            self.connected = False
            raise ConnectionError(f"Failed to connect to S3: {e}")
    
    def disconnect(self):
        """Close S3 connection."""
        self.s3_client = None
        self.connected = False
    
    def _get_full_key(self, remote_path: str) -> str:
        """Get full S3 key including prefix."""
        if self.prefix:
            return f"{self.prefix.rstrip('/')}/{remote_path.lstrip('/')}"
        return remote_path
    
    def upload_file(self, local_path: Path, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to S3."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            key = self._get_full_key(remote_path)
            
            # Prepare upload arguments
            extra_args = {}
            
            if self.encryption:
                extra_args['ServerSideEncryption'] = 'AES256'
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Calculate content hash
            with open(local_path, 'rb') as f:
                content_hash = hashlib.md5(f.read()).hexdigest()
                extra_args['Metadata'] = extra_args.get('Metadata', {})
                extra_args['Metadata']['content-hash'] = content_hash
            
            # Upload file
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            return True
            
        except Exception as e:
            raise IOError(f"Failed to upload file to S3: {e}")
    
    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """Download a file from S3."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            key = self._get_full_key(remote_path)
            
            # Create parent directory if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                key,
                str(local_path)
            )
            
            return True
            
        except Exception as e:
            raise IOError(f"Failed to download file from S3: {e}")
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from S3."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            key = self._get_full_key(remote_path)
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return True
            
        except Exception as e:
            raise IOError(f"Failed to delete file from S3: {e}")
    
    def list_files(self, prefix: str = "") -> List[CloudFile]:
        """List files in S3."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            files = []
            
            # Combine provider prefix with listing prefix
            full_prefix = self._get_full_key(prefix) if prefix else self.prefix
            
            # Use paginator for large buckets
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=full_prefix
            )
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Skip directories (keys ending with /)
                        if obj['Key'].endswith('/'):
                            continue
                        
                        # Remove provider prefix from path
                        path = obj['Key']
                        if self.prefix:
                            path = path[len(self.prefix):].lstrip('/')
                        
                        files.append(CloudFile(
                            path=path,
                            size=obj['Size'],
                            modified=obj['LastModified'],
                            etag=obj.get('ETag', '').strip('"')
                        ))
            
            return files
            
        except Exception as e:
            raise IOError(f"Failed to list files from S3: {e}")
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in S3."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            key = self._get_full_key(remote_path)
            
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            raise IOError(f"Failed to check file existence in S3: {e}")
    
    def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get information about a file in S3."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            key = self._get_full_key(remote_path)
            
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return CloudFile(
                path=remote_path,
                size=response['ContentLength'],
                modified=response['LastModified'],
                etag=response.get('ETag', '').strip('"'),
                metadata=response.get('Metadata', {})
            )
            
        except self.s3_client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            raise IOError(f"Failed to get file info from S3: {e}")
    
    def create_directory(self, remote_path: str) -> bool:
        """Create a directory in S3 (creates a zero-byte object with trailing /)."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            key = self._get_full_key(remote_path.rstrip('/') + '/')
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=b''
            )
            
            return True
            
        except Exception as e:
            raise IOError(f"Failed to create directory in S3: {e}")
    
    def sync_directory(self, local_dir: Path, remote_dir: str,
                      exclude_patterns: Optional[List[str]] = None) -> Dict[str, int]:
        """Sync entire directory to S3."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        stats = {
            'uploaded': 0,
            'downloaded': 0,
            'skipped': 0,
            'errors': 0
        }
        
        exclude_patterns = exclude_patterns or []
        
        try:
            # Get local files
            local_files = {}
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(local_dir)
                    
                    # Check exclusions
                    excluded = False
                    for pattern in exclude_patterns:
                        if fnmatch.fnmatch(str(rel_path), pattern):
                            excluded = True
                            break
                    
                    if not excluded:
                        local_files[str(rel_path)] = datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        )
            
            # Get remote files
            remote_files = self.list_files(remote_dir)
            
            # Calculate sync delta
            to_upload, to_download, to_delete = self.calculate_sync_delta(
                local_files, remote_files
            )
            
            # Upload files
            for rel_path in to_upload:
                try:
                    local_path = local_dir / rel_path
                    remote_path = f"{remote_dir}/{rel_path}" if remote_dir else rel_path
                    self.upload_file(local_path, remote_path)
                    stats['uploaded'] += 1
                except Exception as e:
                    stats['errors'] += 1
            
            # Download files
            for rel_path in to_download:
                try:
                    local_path = local_dir / rel_path
                    remote_path = f"{remote_dir}/{rel_path}" if remote_dir else rel_path
                    self.download_file(remote_path, local_path)
                    stats['downloaded'] += 1
                except Exception as e:
                    stats['errors'] += 1
            
            # Skip files that are already in sync
            stats['skipped'] = len(local_files) - stats['uploaded'] - stats['errors']
            
            return stats
            
        except Exception as e:
            raise IOError(f"Failed to sync directory with S3: {e}")
    
    def get_storage_info(self) -> Dict[str, any]:
        """Get storage usage for the bucket."""
        if not self.connected:
            raise ConnectionError("Not connected to S3")
        
        try:
            # Get bucket size and object count
            total_size = 0
            object_count = 0
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.prefix
            )
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        object_count += 1
            
            # Get bucket location
            location_response = self.s3_client.get_bucket_location(
                Bucket=self.bucket_name
            )
            location = location_response.get('LocationConstraint', 'us-east-1')
            
            return {
                'provider': 'AWS S3',
                'bucket': self.bucket_name,
                'prefix': self.prefix,
                'region': location,
                'total_size': total_size,
                'object_count': object_count,
                'connected': self.connected
            }
            
        except Exception as e:
            raise IOError(f"Failed to get storage info from S3: {e}")