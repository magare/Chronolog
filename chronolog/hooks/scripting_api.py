import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime


class ChronologScriptingAPI:
    """Public API for ChronoLog automation and scripting."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        
        # Import core modules lazily to avoid circular imports
        self._repo = None
        self._analytics = None
        self._optimizer = None
    
    @property
    def repo(self):
        """Lazy load repository instance."""
        if self._repo is None:
            from ..api import ChronologRepo
            self._repo = ChronologRepo(str(self.repo_path))
        return self._repo
    
    @property
    def analytics(self):
        """Lazy load analytics instance."""
        if self._analytics is None:
            from ..analytics import PerformanceAnalytics
            self._analytics = PerformanceAnalytics(self.repo_path)
        return self._analytics
    
    @property
    def optimizer(self):
        """Lazy load optimizer instance."""
        if self._optimizer is None:
            from ..optimization import StorageOptimizer
            self._optimizer = StorageOptimizer(self.repo_path)
        return self._optimizer
    
    # Repository Operations
    
    def get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        """Get version history for a file."""
        return self.repo.log(file_path)
    
    def get_file_content(self, version_hash: str) -> bytes:
        """Get content of a specific version."""
        return self.repo.show(version_hash)
    
    def create_tag(self, tag_name: str, version_hash: Optional[str] = None, 
                  description: Optional[str] = None) -> bool:
        """Create a tag."""
        try:
            self.repo.tag(tag_name, version_hash, description)
            return True
        except:
            return False
    
    def list_branches(self) -> List[Dict[str, Any]]:
        """List all branches."""
        return self.repo.list_branches()
    
    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch."""
        try:
            self.repo.switch_branch(branch_name)
            return True
        except:
            return False
    
    # Search Operations
    
    def search_content(self, pattern: str, **kwargs) -> List[Dict[str, Any]]:
        """Search file content."""
        from ..search.searcher import Searcher, SearchFilter
        
        searcher = Searcher(self.repo_path)
        search_filter = SearchFilter(
            pattern=pattern,
            regex=kwargs.get('regex', False),
            case_sensitive=kwargs.get('case_sensitive', False),
            whole_word=kwargs.get('whole_word', False),
            file_pattern=kwargs.get('file_pattern'),
            include_history=kwargs.get('include_history', False)
        )
        
        return searcher.search(search_filter)
    
    # Analytics Operations
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        from ..analytics import PerformanceAnalytics
        analytics = PerformanceAnalytics(self.repo_path)
        stats = analytics.collect_repository_stats()
        
        return {
            'total_files': stats.total_files,
            'total_versions': stats.total_versions,
            'total_size_mb': stats.total_size_bytes / (1024 * 1024),
            'compression_ratio': stats.compression_ratio,
            'file_types': stats.file_type_distribution,
            'most_active_files': stats.most_active_files[:10]
        }
    
    def get_activity_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get activity summary for the last N days."""
        return self.analytics.get_activity_heatmap(days)
    
    def analyze_code_quality(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Analyze code quality metrics for a file."""
        from ..analytics import MetricsCollector
        
        collector = MetricsCollector(self.repo_path)
        
        # Get latest version
        history = self.get_file_history(file_path)
        if not history:
            return None
        
        latest = history[0]
        content = self.get_file_content(latest['version_hash'])
        
        return collector.analyze_file(Path(file_path), content, latest['version_hash'])
    
    # Storage Operations
    
    def optimize_storage(self, algorithm: str = 'zlib') -> Dict[str, Any]:
        """Run storage optimization."""
        result = self.optimizer.optimize_storage(algorithm)
        
        return {
            'original_size_mb': result.original_size / (1024 * 1024),
            'optimized_size_mb': result.optimized_size / (1024 * 1024),
            'saved_mb': result.saved_bytes / (1024 * 1024),
            'compression_ratio': result.compression_ratio,
            'files_processed': result.files_processed
        }
    
    def collect_garbage(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run garbage collection."""
        from ..optimization import GarbageCollector
        
        gc = GarbageCollector(self.repo_path)
        result = gc.collect_garbage(dry_run)
        
        return {
            'orphaned_objects': result.orphaned_objects_removed,
            'bytes_freed_mb': result.total_bytes_freed / (1024 * 1024),
            'temporary_files': result.temporary_files_removed,
            'dry_run': dry_run
        }
    
    # Bulk Operations
    
    def bulk_tag_versions(self, file_patterns: List[str], 
                         tag_prefix: str = "auto") -> List[str]:
        """Tag multiple versions matching patterns."""
        from ..organization import BulkOperations
        
        bulk_ops = BulkOperations(self.repo)
        pattern_dict = {p: p.replace('*', '') for p in file_patterns}
        
        return bulk_ops.bulk_tag(pattern_dict, tag_prefix)
    
    def export_files(self, output_dir: str, pattern: Optional[str] = None) -> Dict[str, Path]:
        """Export files from repository."""
        from ..organization import BulkOperations
        
        bulk_ops = BulkOperations(self.repo)
        return bulk_ops.bulk_export(Path(output_dir), pattern)
    
    # Automation Helpers
    
    def run_if_changed(self, file_path: str, since: datetime, 
                      callback: Callable[[str, str], None]):
        """Run callback if file has changed since given time."""
        history = self.get_file_history(file_path)
        
        for version in history:
            version_time = datetime.fromisoformat(version['timestamp'])
            if version_time > since:
                content = self.get_file_content(version['version_hash'])
                callback(file_path, content.decode('utf-8', errors='ignore'))
                break
    
    def monitor_changes(self, callback: Callable[[str, str], None], 
                       interval_seconds: int = 60):
        """Monitor repository for changes (simplified version)."""
        import time
        
        last_check = datetime.now()
        
        while True:
            # Get recent changes
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT file_path, version_hash
                FROM versions
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (last_check,))
            
            for file_path, version_hash in cursor.fetchall():
                content = self.get_file_content(version_hash)
                callback(file_path, content.decode('utf-8', errors='ignore'))
            
            conn.close()
            
            last_check = datetime.now()
            time.sleep(interval_seconds)
    
    # Workflow Templates
    
    def create_backup_workflow(self, destination: str, 
                             compression: str = 'gzip') -> Dict[str, Any]:
        """Create a backup of the repository."""
        from ..backup import BackupManager
        
        backup_manager = BackupManager(self.repo_path)
        backup_id = backup_manager.create_backup(
            destination=Path(destination),
            backup_type='full',
            compression=compression
        )
        
        return {
            'backup_id': backup_id,
            'destination': destination,
            'success': True
        }
    
    def sync_to_cloud(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync repository to cloud storage."""
        from ..cloud import CloudSyncManager
        
        sync_manager = CloudSyncManager(self.repo_path)
        sync_manager.configure(
            provider_type=provider,
            provider_config=config
        )
        
        sync_manager.connect()
        result = sync_manager.sync()
        
        return result
    
    def generate_report(self, output_path: str) -> bool:
        """Generate comprehensive repository report."""
        try:
            # Collect all data
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'repository': str(self.repo_path),
                'stats': self.get_repository_stats(),
                'activity': self.get_activity_summary(),
                'storage': {
                    'recommendations': self.optimizer.get_storage_recommendations()
                }
            }
            
            # Get language statistics
            from ..analytics import MetricsCollector
            collector = MetricsCollector(self.repo_path)
            report_data['languages'] = collector.get_language_statistics()
            
            # Write report
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            return False
    
    # Utility Methods
    
    def execute_sql(self, query: str, params: Optional[tuple] = None) -> List[Any]:
        """Execute custom SQL query (read-only)."""
        if not query.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            return cursor.fetchall()
            
        finally:
            conn.close()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        config_file = self.chronolog_dir / "config.json"
        
        if not config_file.exists():
            return default
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get(key, default)
        except:
            return default
    
    def set_config(self, key: str, value: Any) -> bool:
        """Set configuration value."""
        config_file = self.chronolog_dir / "config.json"
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            config[key] = value
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
            
        except:
            return False