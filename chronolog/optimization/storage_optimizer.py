import sqlite3
import hashlib
import zlib
import lzma
import bz2
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class OptimizationResult:
    original_size: int
    optimized_size: int
    saved_bytes: int
    compression_ratio: float
    files_processed: int
    errors: List[str]
    duration_seconds: float


class StorageOptimizer:
    """Optimizes storage through compression and deduplication."""
    
    COMPRESSION_ALGORITHMS = {
        'zlib': (zlib.compress, zlib.decompress),
        'lzma': (lzma.compress, lzma.decompress),
        'bz2': (bz2.compress, bz2.decompress)
    }
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        self.objects_dir = self.chronolog_dir / "objects"
        self.optimized_dir = self.chronolog_dir / "optimized"
        self.optimized_dir.mkdir(exist_ok=True)
    
    def optimize_storage(self, algorithm: str = 'zlib', 
                        min_size_bytes: int = 1024) -> OptimizationResult:
        """Optimize storage using compression."""
        start_time = datetime.now()
        
        if algorithm not in self.COMPRESSION_ALGORITHMS:
            raise ValueError(f"Unknown compression algorithm: {algorithm}")
        
        compress_func, _ = self.COMPRESSION_ALGORITHMS[algorithm]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        original_size = 0
        optimized_size = 0
        files_processed = 0
        errors = []
        
        try:
            # Get all unique content hashes
            cursor.execute("""
                SELECT DISTINCT version_hash, file_size 
                FROM versions
                WHERE file_size >= ?
                ORDER BY file_size DESC
            """, (min_size_bytes,))
            
            hashes = cursor.fetchall()
            
            for content_hash, file_size in hashes:
                try:
                    # Get original content
                    object_path = self.objects_dir / content_hash[:2] / content_hash[2:]
                    
                    if not object_path.exists():
                        continue
                    
                    original_content = object_path.read_bytes()
                    original_size += len(original_content)
                    
                    # Check if already optimized
                    optimized_path = self.optimized_dir / content_hash[:2] / content_hash[2:]
                    if optimized_path.exists():
                        optimized_size += optimized_path.stat().st_size
                        files_processed += 1
                        continue
                    
                    # Compress content
                    compressed = compress_func(original_content)
                    
                    # Only store if compression is beneficial
                    if len(compressed) < len(original_content) * 0.9:
                        optimized_path.parent.mkdir(parents=True, exist_ok=True)
                        optimized_path.write_bytes(compressed)
                        
                        # Update metadata
                        cursor.execute("""
                            INSERT OR REPLACE INTO storage_metadata
                            (hash, size, compression_ratio, access_count, last_accessed)
                            VALUES (?, ?, ?, 0, ?)
                        """, (
                            content_hash,
                            len(compressed),
                            len(compressed) / len(original_content),
                            datetime.now()
                        ))
                        
                        optimized_size += len(compressed)
                    else:
                        optimized_size += len(original_content)
                    
                    files_processed += 1
                    
                except Exception as e:
                    errors.append(f"Failed to optimize {content_hash}: {e}")
            
            conn.commit()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return OptimizationResult(
                original_size=original_size,
                optimized_size=optimized_size,
                saved_bytes=original_size - optimized_size,
                compression_ratio=optimized_size / original_size if original_size > 0 else 1.0,
                files_processed=files_processed,
                errors=errors,
                duration_seconds=duration
            )
            
        finally:
            conn.close()
    
    def deduplicate_content(self) -> Dict[str, Any]:
        """Find and handle duplicate content across files."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Find duplicate content
            cursor.execute("""
                SELECT 
                    version_hash,
                    COUNT(DISTINCT file_path) as file_count,
                    GROUP_CONCAT(DISTINCT file_path) as files,
                    file_size
                FROM versions
                GROUP BY version_hash
                HAVING file_count > 1
                ORDER BY file_count DESC, file_size DESC
            """)
            
            duplicates = []
            total_waste = 0
            
            for row in cursor.fetchall():
                hash, count, files_str, size = row
                files = files_str.split(',')
                waste = size * (count - 1)
                total_waste += waste
                
                duplicates.append({
                    'hash': hash,
                    'size': size,
                    'file_count': count,
                    'files': files[:10],  # Limit to first 10
                    'wasted_bytes': waste
                })
            
            # Create deduplication map
            dedup_map = {}
            for dup in duplicates:
                for file in dup['files'][1:]:  # Keep first file as primary
                    dedup_map[file] = dup['files'][0]
            
            return {
                'duplicates': duplicates[:50],  # Top 50
                'total_duplicates': len(duplicates),
                'total_wasted_bytes': total_waste,
                'deduplication_map': dedup_map
            }
            
        finally:
            conn.close()
    
    def optimize_database(self) -> Dict[str, Any]:
        """Optimize database performance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            before_size = Path(self.db_path).stat().st_size
            
            # Analyze tables
            cursor.execute("ANALYZE")
            
            # Rebuild indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            for index in indexes:
                cursor.execute(f"REINDEX {index}")
            
            # Vacuum database
            conn.commit()
            conn.execute("VACUUM")
            
            after_size = Path(self.db_path).stat().st_size
            
            return {
                'before_size': before_size,
                'after_size': after_size,
                'saved_bytes': before_size - after_size,
                'indexes_rebuilt': len(indexes)
            }
            
        finally:
            conn.close()
    
    def archive_old_versions(self, days_old: int = 90) -> Dict[str, Any]:
        """Archive old versions to separate storage."""
        archive_dir = self.chronolog_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Find old versions
            cursor.execute("""
                SELECT 
                    version_hash,
                    file_path,
                    timestamp,
                    file_size
                FROM versions
                WHERE timestamp < ?
                ORDER BY timestamp
            """, (cutoff_date,))
            
            archived_count = 0
            archived_size = 0
            
            for row in cursor.fetchall():
                hash, file_path, timestamp, size = row
                
                # Move object to archive
                src_path = self.objects_dir / hash[:2] / hash[2:]
                if src_path.exists():
                    dst_path = archive_dir / hash[:2] / hash[2:]
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    src_path.rename(dst_path)
                    archived_count += 1
                    archived_size += size
            
            return {
                'archived_versions': archived_count,
                'archived_size_bytes': archived_size,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        finally:
            conn.close()
    
    def get_storage_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for storage optimization."""
        recommendations = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check for large uncompressed files
            cursor.execute("""
                SELECT COUNT(*), SUM(file_size)
                FROM versions
                WHERE file_size > 1048576  -- Files > 1MB
                AND version_hash NOT IN (
                    SELECT hash FROM storage_metadata
                )
            """)
            count, size = cursor.fetchone()
            
            if count and count > 0:
                recommendations.append({
                    'type': 'compression',
                    'priority': 'high',
                    'description': f"Compress {count} large files to save ~{size * 0.6 / 1048576:.1f} MB",
                    'action': 'optimize_storage'
                })
            
            # Check for duplicates
            dedup_info = self.deduplicate_content()
            if dedup_info['total_wasted_bytes'] > 1048576:  # > 1MB waste
                recommendations.append({
                    'type': 'deduplication',
                    'priority': 'medium',
                    'description': f"Remove {dedup_info['total_duplicates']} duplicates to save {dedup_info['total_wasted_bytes'] / 1048576:.1f} MB",
                    'action': 'deduplicate_content'
                })
            
            # Check database size
            db_size = Path(self.db_path).stat().st_size
            if db_size > 50 * 1048576:  # > 50MB
                recommendations.append({
                    'type': 'database',
                    'priority': 'low',
                    'description': "Optimize database to improve query performance",
                    'action': 'optimize_database'
                })
            
            # Check for old versions
            cursor.execute("""
                SELECT COUNT(*), SUM(file_size)
                FROM versions
                WHERE timestamp < datetime('now', '-90 days')
            """)
            old_count, old_size = cursor.fetchone()
            
            if old_count and old_count > 100:
                recommendations.append({
                    'type': 'archival',
                    'priority': 'low',
                    'description': f"Archive {old_count} old versions ({old_size / 1048576:.1f} MB) older than 90 days",
                    'action': 'archive_old_versions'
                })
            
            return recommendations
            
        finally:
            conn.close()