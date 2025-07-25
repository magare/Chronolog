import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, asdict


@dataclass
class RepositoryStats:
    total_files: int
    total_versions: int
    total_size_bytes: int
    unique_content_size_bytes: int
    compression_ratio: float
    average_file_size: float
    average_versions_per_file: float
    most_active_files: List[Tuple[str, int]]
    file_type_distribution: Dict[str, int]
    storage_growth_rate: float  # bytes per day


@dataclass
class PerformanceMetrics:
    operation: str
    average_time_ms: float
    min_time_ms: float
    max_time_ms: float
    count: int
    percentile_95_ms: float


class PerformanceAnalytics:
    """Collects and analyzes repository performance metrics and statistics."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        self.objects_dir = self.chronolog_dir / "objects"
    
    def collect_repository_stats(self) -> RepositoryStats:
        """Collect comprehensive repository statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Total files and versions
            cursor.execute("SELECT COUNT(DISTINCT file_path) FROM versions")
            total_files = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM versions")
            total_versions = cursor.fetchone()[0]
            
            # Total size
            cursor.execute("SELECT SUM(file_size) FROM versions")
            total_size = cursor.fetchone()[0] or 0
            
            # Unique content size
            cursor.execute("""
                SELECT SUM(file_size) FROM (
                    SELECT DISTINCT version_hash, file_size FROM versions
                )
            """)
            unique_size = cursor.fetchone()[0] or 0
            
            # Most active files
            cursor.execute("""
                SELECT file_path, COUNT(*) as version_count
                FROM versions
                GROUP BY file_path
                ORDER BY version_count DESC
                LIMIT 10
            """)
            most_active = cursor.fetchall()
            
            # File type distribution
            file_types = defaultdict(int)
            cursor.execute("SELECT DISTINCT file_path FROM versions")
            for (file_path,) in cursor.fetchall():
                ext = Path(file_path).suffix.lower() or 'no_extension'
                file_types[ext] += 1
            
            # Storage growth rate (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            cursor.execute("""
                SELECT SUM(file_size) FROM versions 
                WHERE timestamp >= ?
            """, (thirty_days_ago,))
            recent_growth = cursor.fetchone()[0] or 0
            growth_rate = recent_growth / 30  # bytes per day
            
            # Calculate derived metrics
            compression_ratio = total_size / unique_size if unique_size > 0 else 1.0
            avg_file_size = total_size / total_versions if total_versions > 0 else 0
            avg_versions = total_versions / total_files if total_files > 0 else 0
            
            return RepositoryStats(
                total_files=total_files,
                total_versions=total_versions,
                total_size_bytes=total_size,
                unique_content_size_bytes=unique_size,
                compression_ratio=compression_ratio,
                average_file_size=avg_file_size,
                average_versions_per_file=avg_versions,
                most_active_files=most_active,
                file_type_distribution=dict(file_types),
                storage_growth_rate=growth_rate
            )
            
        finally:
            conn.close()
    
    def record_operation_metric(self, operation: str, duration_ms: float, 
                               context: Optional[Dict[str, Any]] = None):
        """Record a performance metric for an operation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO analytics (metric_name, value, timestamp, context)
                VALUES (?, ?, ?, ?)
            """, (
                f"operation_{operation}",
                duration_ms,
                datetime.now(),
                json.dumps(context) if context else None
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_operation_metrics(self, operation: Optional[str] = None,
                            time_window_hours: int = 24) -> List[PerformanceMetrics]:
        """Get performance metrics for operations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            since = datetime.now() - timedelta(hours=time_window_hours)
            
            if operation:
                metric_names = [f"operation_{operation}"]
            else:
                cursor.execute("""
                    SELECT DISTINCT metric_name FROM analytics
                    WHERE metric_name LIKE 'operation_%' AND timestamp >= ?
                """, (since,))
                metric_names = [row[0] for row in cursor.fetchall()]
            
            metrics = []
            for metric_name in metric_names:
                cursor.execute("""
                    SELECT value FROM analytics
                    WHERE metric_name = ? AND timestamp >= ?
                    ORDER BY value
                """, (metric_name, since))
                
                values = [row[0] for row in cursor.fetchall()]
                if values:
                    operation_name = metric_name.replace('operation_', '')
                    
                    # Calculate percentiles
                    p95_index = int(len(values) * 0.95)
                    
                    metrics.append(PerformanceMetrics(
                        operation=operation_name,
                        average_time_ms=sum(values) / len(values),
                        min_time_ms=values[0],
                        max_time_ms=values[-1],
                        count=len(values),
                        percentile_95_ms=values[p95_index] if p95_index < len(values) else values[-1]
                    ))
            
            return metrics
            
        finally:
            conn.close()
    
    def analyze_storage_efficiency(self) -> Dict[str, Any]:
        """Analyze storage efficiency and find optimization opportunities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Find duplicate content across files
            cursor.execute("""
                SELECT version_hash, COUNT(DISTINCT file_path) as file_count, file_size
                FROM versions
                GROUP BY version_hash
                HAVING file_count > 1
                ORDER BY file_count DESC, file_size DESC
                LIMIT 20
            """)
            duplicates = []
            for hash, count, size in cursor.fetchall():
                cursor.execute("""
                    SELECT file_path FROM versions 
                    WHERE version_hash = ?
                """, (hash,))
                files = [row[0] for row in cursor.fetchall()]
                duplicates.append({
                    'hash': hash,
                    'file_count': count,
                    'size': size,
                    'files': files[:5]  # Limit to first 5 files
                })
            
            # Find large files
            cursor.execute("""
                SELECT DISTINCT file_path, MAX(file_size) as max_size
                FROM versions
                GROUP BY file_path
                HAVING max_size > 1048576  -- Files larger than 1MB
                ORDER BY max_size DESC
                LIMIT 20
            """)
            large_files = [
                {'path': row[0], 'size': row[1]} 
                for row in cursor.fetchall()
            ]
            
            # Calculate potential savings
            cursor.execute("""
                SELECT SUM(total_size - unique_size) as waste FROM (
                    SELECT 
                        version_hash,
                        COUNT(*) * file_size as total_size,
                        file_size as unique_size
                    FROM versions
                    GROUP BY version_hash
                    HAVING COUNT(*) > 1
                )
            """)
            potential_savings = cursor.fetchone()[0] or 0
            
            # Find orphaned objects
            all_hashes = set()
            cursor.execute("SELECT DISTINCT version_hash FROM versions")
            for (hash,) in cursor.fetchall():
                all_hashes.add(hash)
            
            orphaned_count = 0
            orphaned_size = 0
            
            for obj_dir in self.objects_dir.iterdir():
                if obj_dir.is_dir():
                    for obj_file in obj_dir.iterdir():
                        hash = obj_dir.name + obj_file.name
                        if hash not in all_hashes:
                            orphaned_count += 1
                            orphaned_size += obj_file.stat().st_size
            
            return {
                'duplicate_content': duplicates,
                'large_files': large_files,
                'potential_savings_bytes': potential_savings,
                'orphaned_objects': {
                    'count': orphaned_count,
                    'size_bytes': orphaned_size
                }
            }
            
        finally:
            conn.close()
    
    def get_activity_heatmap(self, days: int = 30) -> Dict[str, List[int]]:
        """Get activity heatmap data for the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            since = datetime.now() - timedelta(days=days)
            
            # Get hourly activity
            hourly_activity = [0] * 24
            cursor.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM versions
                WHERE timestamp >= ?
                GROUP BY hour
            """, (since,))
            
            for hour, count in cursor.fetchall():
                hourly_activity[int(hour)] = count
            
            # Get daily activity
            daily_activity = []
            for i in range(days):
                date = since + timedelta(days=i)
                cursor.execute("""
                    SELECT COUNT(*) FROM versions
                    WHERE DATE(timestamp) = DATE(?)
                """, (date,))
                daily_activity.append(cursor.fetchone()[0])
            
            # Get day of week activity
            dow_activity = [0] * 7
            cursor.execute("""
                SELECT strftime('%w', timestamp) as dow, COUNT(*) as count
                FROM versions
                WHERE timestamp >= ?
                GROUP BY dow
            """, (since,))
            
            for dow, count in cursor.fetchall():
                dow_activity[int(dow)] = count
            
            return {
                'hourly': hourly_activity,
                'daily': daily_activity,
                'day_of_week': dow_activity
            }
            
        finally:
            conn.close()
    
    def get_file_change_frequency(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Get files sorted by change frequency."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Calculate change frequency
            cursor.execute("""
                SELECT 
                    file_path,
                    COUNT(*) as total_versions,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen,
                    julianday(MAX(timestamp)) - julianday(MIN(timestamp)) as days_active
                FROM versions
                GROUP BY file_path
                HAVING days_active > 0
                ORDER BY (CAST(total_versions AS REAL) / days_active) DESC
                LIMIT ?
            """, (top_n,))
            
            results = []
            for row in cursor.fetchall():
                file_path, versions, first, last, days = row
                results.append({
                    'file_path': file_path,
                    'total_versions': versions,
                    'first_seen': first,
                    'last_seen': last,
                    'changes_per_day': versions / days if days > 0 else 0
                })
            
            return results
            
        finally:
            conn.close()
    
    def export_analytics_report(self, output_path: Path):
        """Export comprehensive analytics report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'repository': str(self.repo_path),
            'stats': asdict(self.collect_repository_stats()),
            'performance_metrics': [
                asdict(m) for m in self.get_operation_metrics()
            ],
            'storage_analysis': self.analyze_storage_efficiency(),
            'activity_heatmap': self.get_activity_heatmap(),
            'hot_files': self.get_file_change_frequency()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)