import sqlite3
import shutil
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class GarbageCollectionResult:
    orphaned_objects_removed: int
    orphaned_bytes_freed: int
    empty_directories_removed: int
    invalid_entries_cleaned: int
    temporary_files_removed: int
    total_bytes_freed: int
    duration_seconds: float
    errors: List[str]


class GarbageCollector:
    """Cleans up orphaned objects and optimizes storage."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        self.objects_dir = self.chronolog_dir / "objects"
        self.temp_patterns = ['*.tmp', '*.swp', '*.lock', '~*']
    
    def collect_garbage(self, dry_run: bool = False) -> GarbageCollectionResult:
        """Perform garbage collection on the repository."""
        start_time = datetime.now()
        errors = []
        
        # Collect all phases
        orphaned_result = self._remove_orphaned_objects(dry_run, errors)
        empty_dirs_result = self._remove_empty_directories(dry_run, errors)
        invalid_result = self._clean_invalid_entries(dry_run, errors)
        temp_result = self._remove_temporary_files(dry_run, errors)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return GarbageCollectionResult(
            orphaned_objects_removed=orphaned_result[0],
            orphaned_bytes_freed=orphaned_result[1],
            empty_directories_removed=empty_dirs_result,
            invalid_entries_cleaned=invalid_result,
            temporary_files_removed=temp_result[0],
            total_bytes_freed=orphaned_result[1] + temp_result[1],
            duration_seconds=duration,
            errors=errors
        )
    
    def _remove_orphaned_objects(self, dry_run: bool, 
                                errors: List[str]) -> Tuple[int, int]:
        """Remove objects not referenced in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all valid hashes from database
            cursor.execute("SELECT DISTINCT version_hash FROM versions")
            valid_hashes = {row[0] for row in cursor.fetchall()}
            
            # Also include hashes from other tables
            cursor.execute("SELECT DISTINCT version_hash FROM tags")
            valid_hashes.update(row[0] for row in cursor.fetchall())
            
            cursor.execute("SELECT DISTINCT head_hash FROM branches WHERE head_hash != ''")
            valid_hashes.update(row[0] for row in cursor.fetchall())
            
            orphaned_count = 0
            orphaned_bytes = 0
            
            # Check all objects in storage
            for obj_dir in self.objects_dir.iterdir():
                if not obj_dir.is_dir():
                    continue
                
                for obj_file in obj_dir.iterdir():
                    if not obj_file.is_file():
                        continue
                    
                    hash = obj_dir.name + obj_file.name
                    
                    if hash not in valid_hashes:
                        try:
                            size = obj_file.stat().st_size
                            
                            if not dry_run:
                                obj_file.unlink()
                                
                                # Mark as orphaned in metadata
                                cursor.execute("""
                                    UPDATE storage_metadata 
                                    SET is_orphaned = TRUE 
                                    WHERE hash = ?
                                """, (hash,))
                            
                            orphaned_count += 1
                            orphaned_bytes += size
                            
                        except Exception as e:
                            errors.append(f"Failed to remove orphaned object {hash}: {e}")
            
            if not dry_run:
                conn.commit()
            
            return orphaned_count, orphaned_bytes
            
        finally:
            conn.close()
    
    def _remove_empty_directories(self, dry_run: bool, 
                                 errors: List[str]) -> int:
        """Remove empty directories in objects storage."""
        removed_count = 0
        
        # Walk bottom-up to remove empty dirs
        for root, dirs, files in self.objects_dir.walk(top_down=False):
            if not files and not dirs:
                try:
                    if not dry_run:
                        root.rmdir()
                    removed_count += 1
                except Exception as e:
                    errors.append(f"Failed to remove empty directory {root}: {e}")
        
        return removed_count
    
    def _clean_invalid_entries(self, dry_run: bool, 
                              errors: List[str]) -> int:
        """Clean invalid database entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cleaned_count = 0
        
        try:
            # Find versions without corresponding objects
            cursor.execute("SELECT version_hash, file_path FROM versions")
            
            invalid_hashes = []
            for hash, file_path in cursor.fetchall():
                obj_path = self.objects_dir / hash[:2] / hash[2:]
                if not obj_path.exists():
                    invalid_hashes.append((hash, file_path))
            
            if not dry_run and invalid_hashes:
                # Remove invalid entries
                for hash, file_path in invalid_hashes:
                    cursor.execute("""
                        DELETE FROM versions 
                        WHERE version_hash = ? AND file_path = ?
                    """, (hash, file_path))
                    
                    # Also clean related tables
                    cursor.execute("DELETE FROM tags WHERE version_hash = ?", (hash,))
                    cursor.execute("DELETE FROM search_index WHERE version_hash = ?", (hash,))
                    cursor.execute("DELETE FROM comments WHERE version_hash = ?", (hash,))
                    cursor.execute("DELETE FROM code_metrics WHERE version_hash = ?", (hash,))
                    
                    cleaned_count += 1
                
                conn.commit()
            else:
                cleaned_count = len(invalid_hashes)
            
            return cleaned_count
            
        except Exception as e:
            errors.append(f"Failed to clean invalid entries: {e}")
            return 0
            
        finally:
            conn.close()
    
    def _remove_temporary_files(self, dry_run: bool, 
                               errors: List[str]) -> Tuple[int, int]:
        """Remove temporary files."""
        removed_count = 0
        removed_bytes = 0
        
        # Check repository root
        for pattern in self.temp_patterns:
            for temp_file in self.repo_path.glob(f"**/{pattern}"):
                try:
                    if temp_file.is_file():
                        size = temp_file.stat().st_size
                        
                        if not dry_run:
                            temp_file.unlink()
                        
                        removed_count += 1
                        removed_bytes += size
                        
                except Exception as e:
                    errors.append(f"Failed to remove temporary file {temp_file}: {e}")
        
        # Check .chronolog directory
        temp_dir = self.chronolog_dir / "tmp"
        if temp_dir.exists():
            try:
                if not dry_run:
                    shutil.rmtree(temp_dir)
                removed_count += 1
            except Exception as e:
                errors.append(f"Failed to remove temp directory: {e}")
        
        return removed_count, removed_bytes
    
    def find_large_objects(self, min_size_mb: float = 10) -> List[Dict[str, any]]:
        """Find large objects that might benefit from optimization."""
        min_size_bytes = int(min_size_mb * 1024 * 1024)
        large_objects = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    v.version_hash,
                    v.file_path,
                    v.file_size,
                    v.timestamp,
                    COUNT(*) OVER (PARTITION BY v.version_hash) as ref_count
                FROM versions v
                WHERE v.file_size >= ?
                ORDER BY v.file_size DESC
                LIMIT 50
            """, (min_size_bytes,))
            
            for row in cursor.fetchall():
                hash, file_path, size, timestamp, ref_count = row
                
                # Check if object exists
                obj_path = self.objects_dir / hash[:2] / hash[2:]
                if obj_path.exists():
                    actual_size = obj_path.stat().st_size
                    
                    large_objects.append({
                        'hash': hash,
                        'file_path': file_path,
                        'size_mb': size / (1024 * 1024),
                        'actual_size_mb': actual_size / (1024 * 1024),
                        'timestamp': timestamp,
                        'reference_count': ref_count
                    })
            
            return large_objects
            
        finally:
            conn.close()
    
    def verify_integrity(self) -> Dict[str, any]:
        """Verify repository integrity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        issues = {
            'missing_objects': [],
            'corrupted_objects': [],
            'orphaned_objects': [],
            'database_inconsistencies': []
        }
        
        try:
            # Check all version objects exist
            cursor.execute("SELECT DISTINCT version_hash, file_path FROM versions")
            
            for hash, file_path in cursor.fetchall():
                obj_path = self.objects_dir / hash[:2] / hash[2:]
                
                if not obj_path.exists():
                    issues['missing_objects'].append({
                        'hash': hash,
                        'file_path': file_path
                    })
                else:
                    # Verify hash matches content
                    try:
                        content = obj_path.read_bytes()
                        import hashlib
                        actual_hash = hashlib.sha256(content).hexdigest()
                        
                        if actual_hash != hash:
                            issues['corrupted_objects'].append({
                                'hash': hash,
                                'actual_hash': actual_hash,
                                'file_path': file_path
                            })
                    except:
                        issues['corrupted_objects'].append({
                            'hash': hash,
                            'file_path': file_path,
                            'error': 'Could not read object'
                        })
            
            # Check for orphaned objects
            all_db_hashes = set()
            cursor.execute("SELECT DISTINCT version_hash FROM versions")
            all_db_hashes.update(row[0] for row in cursor.fetchall())
            
            for obj_dir in self.objects_dir.iterdir():
                if obj_dir.is_dir():
                    for obj_file in obj_dir.iterdir():
                        hash = obj_dir.name + obj_file.name
                        if hash not in all_db_hashes:
                            issues['orphaned_objects'].append(hash)
            
            # Check referential integrity
            cursor.execute("""
                SELECT COUNT(*) FROM tags 
                WHERE version_hash NOT IN (SELECT version_hash FROM versions)
            """)
            invalid_tags = cursor.fetchone()[0]
            
            if invalid_tags > 0:
                issues['database_inconsistencies'].append(
                    f"{invalid_tags} tags reference non-existent versions"
                )
            
            return {
                'is_healthy': all(len(v) == 0 for v in issues.values()),
                'issues': issues,
                'summary': {
                    'missing_objects': len(issues['missing_objects']),
                    'corrupted_objects': len(issues['corrupted_objects']),
                    'orphaned_objects': len(issues['orphaned_objects']),
                    'database_issues': len(issues['database_inconsistencies'])
                }
            }
            
        finally:
            conn.close()