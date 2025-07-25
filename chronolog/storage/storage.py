import os
import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple


class Storage:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.objects_dir = base_path / "objects"
        self.db_path = base_path / "history.db"
        self.current_branch = "main"  # Default branch
        
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_current_branch()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                version_hash TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                parent_hash TEXT,
                annotation TEXT,
                file_size INTEGER,
                UNIQUE(file_path, version_hash)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path 
            ON versions(file_path)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON versions(timestamp)
        """)
        
        # New tables for enhanced features
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                tag_name TEXT PRIMARY KEY,
                version_hash TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                description TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS branches (
                branch_name TEXT PRIMARY KEY,
                head_hash TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                parent_branch TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_index (
                version_hash TEXT,
                file_path TEXT,
                content_text TEXT,
                PRIMARY KEY (version_hash, file_path)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                value REAL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_hash TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                author TEXT,
                comment TEXT NOT NULL
            )
        """)
        
        # Add indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_content 
            ON search_index(content_text)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_hash 
            ON tags(version_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_branches_head 
            ON branches(head_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_comments_hash 
            ON comments(version_hash)
        """)
        
        # Phase 4 & 5 Tables
        
        # Performance analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                context TEXT,
                file_path TEXT,
                user_id TEXT
            )
        """)
        
        # Storage optimization metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storage_metadata (
                hash TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                compression_ratio REAL,
                access_count INTEGER DEFAULT 0,
                last_accessed DATETIME,
                is_orphaned BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Hooks configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                hook_name TEXT NOT NULL,
                script_path TEXT,
                script_content TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                created_at DATETIME NOT NULL,
                UNIQUE(event_type, hook_name)
            )
        """)
        
        # Developer activity tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                resource_path TEXT,
                timestamp DATETIME NOT NULL,
                details TEXT
            )
        """)
        
        # User management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                full_name TEXT,
                password_hash TEXT,
                created_at DATETIME NOT NULL,
                last_active DATETIME,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Permissions system
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                permission_level TEXT NOT NULL,
                granted_at DATETIME NOT NULL,
                granted_by TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, resource_type, resource_id)
            )
        """)
        
        # File locks for collaboration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                user_id TEXT NOT NULL,
                lock_type TEXT NOT NULL,
                acquired_at DATETIME NOT NULL,
                expires_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Merge conflicts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merge_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                base_hash TEXT NOT NULL,
                our_hash TEXT NOT NULL,
                their_hash TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                resolved_at DATETIME,
                resolved_by TEXT,
                resolution_strategy TEXT
            )
        """)
        
        # API sessions and tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                last_used DATETIME,
                client_info TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Code quality metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                version_hash TEXT NOT NULL,
                language TEXT,
                lines_of_code INTEGER,
                complexity_score REAL,
                maintainability_index REAL,
                cyclomatic_complexity INTEGER,
                analyzed_at DATETIME NOT NULL
            )
        """)
        
        # Add indexes for new tables
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_timestamp 
            ON analytics(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_metric 
            ON analytics(metric_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_storage_metadata_access 
            ON storage_metadata(last_accessed)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_user 
            ON activity_log(user_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_permissions_user 
            ON permissions(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_locks_path 
            ON file_locks(file_path)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_sessions_token 
            ON api_sessions(token_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_metrics_file 
            ON code_metrics(file_path, version_hash)
        """)
        
        # Initialize default branch if this is a new repository
        cursor.execute("SELECT COUNT(*) FROM branches")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO branches (branch_name, head_hash, created_at, parent_branch)
                VALUES ('main', '', ?, NULL)
            """, (datetime.now(),))
        
        conn.commit()
        conn.close()
    
    def _calculate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
    
    def store_content(self, content: bytes) -> str:
        """Store content and return its hash"""
        content_hash = self._calculate_hash(content)
        
        # Store the content in objects directory
        hash_dir = self.objects_dir / content_hash[:2]
        hash_dir.mkdir(exist_ok=True)
        
        hash_file = hash_dir / content_hash[2:]
        if not hash_file.exists():
            hash_file.write_bytes(content)
        
        return content_hash
    
    def get_content(self, content_hash: str) -> Optional[bytes]:
        """Get content by hash"""
        hash_dir = self.objects_dir / content_hash[:2]
        hash_file = hash_dir / content_hash[2:]
        
        if hash_file.exists():
            return hash_file.read_bytes()
        return None
    
    def store_version(self, file_path: str, content: bytes, 
                     parent_hash: Optional[str] = None, 
                     annotation: Optional[str] = None) -> str:
        content_hash = self._calculate_hash(content)
        
        # Check if this exact content already exists for this file
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT version_hash FROM versions 
            WHERE file_path = ? AND version_hash = ?
        """, (file_path, content_hash))
        
        if cursor.fetchone():
            conn.close()
            return content_hash
        
        # Store content in content-addressable storage
        object_path = self.objects_dir / content_hash[:2] / content_hash[2:]
        object_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not object_path.exists():
            object_path.write_bytes(content)
        
        # Store metadata in database
        cursor.execute("""
            INSERT INTO versions 
            (file_path, version_hash, timestamp, parent_hash, annotation, file_size)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (file_path, content_hash, datetime.now(), parent_hash, 
              annotation, len(content)))
        
        conn.commit()
        conn.close()
        
        # Index content for search
        self.index_content(content_hash, file_path, content)
        
        # Update current branch head if we have branches
        self._update_current_branch_head(content_hash)
        
        # Record storage metric
        self.record_metric("storage_bytes", len(content), {"file_path": file_path})
        
        return content_hash
    
    def get_version_content(self, version_hash: str) -> Optional[bytes]:
        object_path = self.objects_dir / version_hash[:2] / version_hash[2:]
        
        if object_path.exists():
            return object_path.read_bytes()
        return None
    
    def get_file_history(self, file_path: str) -> List[dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT version_hash, timestamp, annotation, file_size
            FROM versions
            WHERE file_path = ?
            ORDER BY timestamp DESC
        """, (file_path,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "hash": row[0],
                "timestamp": row[1],
                "annotation": row[2],
                "size": row[3]
            })
        
        conn.close()
        return history
    
    def get_latest_version_hash(self, file_path: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT version_hash
            FROM versions
            WHERE file_path = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (file_path,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_version_info(self, version_hash: str) -> Optional[dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, timestamp, parent_hash, annotation, file_size
            FROM versions
            WHERE version_hash = ?
        """, (version_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "file_path": result[0],
                "timestamp": result[1],
                "parent_hash": result[2],
                "annotation": result[3],
                "size": result[4]
            }
        return None
    
    # Tag system methods
    def create_tag(self, tag_name: str, version_hash: str, description: Optional[str] = None) -> bool:
        """Create a new tag pointing to a specific version."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO tags (tag_name, version_hash, timestamp, description)
                VALUES (?, ?, ?, ?)
            """, (tag_name, version_hash, datetime.now(), description))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_tags(self) -> List[dict]:
        """Get all tags in the repository."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tag_name, version_hash, timestamp, description
            FROM tags
            ORDER BY timestamp DESC
        """)
        
        tags = []
        for row in cursor.fetchall():
            tags.append({
                "name": row[0],
                "hash": row[1],
                "timestamp": row[2],
                "description": row[3]
            })
        
        conn.close()
        return tags
    
    def get_tag(self, tag_name: str) -> Optional[dict]:
        """Get a specific tag by name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT version_hash, timestamp, description
            FROM tags
            WHERE tag_name = ?
        """, (tag_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "name": tag_name,
                "hash": result[0],
                "timestamp": result[1],
                "description": result[2]
            }
        return None
    
    def delete_tag(self, tag_name: str) -> bool:
        """Delete a tag."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM tags WHERE tag_name = ?", (tag_name,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    # Branch system methods
    def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> bool:
        """Create a new branch."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get the head of the parent branch
            if from_branch:
                cursor.execute("SELECT head_hash FROM branches WHERE branch_name = ?", (from_branch,))
                result = cursor.fetchone()
                if not result:
                    conn.close()
                    return False
                head_hash = result[0]
            else:
                # Branch from current main
                cursor.execute("SELECT head_hash FROM branches WHERE branch_name = 'main'")
                result = cursor.fetchone()
                head_hash = result[0] if result else ''
                from_branch = 'main'
            
            cursor.execute("""
                INSERT INTO branches (branch_name, head_hash, created_at, parent_branch)
                VALUES (?, ?, ?, ?)
            """, (branch_name, head_hash, datetime.now(), from_branch))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_branches(self) -> List[dict]:
        """Get all branches in the repository."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT branch_name, head_hash, created_at, parent_branch
            FROM branches
            ORDER BY created_at DESC
        """)
        
        branches = []
        for row in cursor.fetchall():
            branches.append({
                "name": row[0],
                "head": row[1],
                "created_at": row[2],
                "parent": row[3]
            })
        
        conn.close()
        return branches
    
    def get_branch(self, branch_name: str) -> Optional[dict]:
        """Get a specific branch by name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT head_hash, created_at, parent_branch
            FROM branches
            WHERE branch_name = ?
        """, (branch_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "name": branch_name,
                "head": result[0],
                "created_at": result[1],
                "parent": result[2]
            }
        return None
    
    def update_branch_head(self, branch_name: str, new_head: str) -> bool:
        """Update the head of a branch."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE branches
            SET head_hash = ?
            WHERE branch_name = ?
        """, (new_head, branch_name))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    def delete_branch(self, branch_name: str) -> bool:
        """Delete a branch (cannot delete 'main')."""
        if branch_name == 'main':
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM branches WHERE branch_name = ?", (branch_name,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    # Search index methods
    def index_content(self, version_hash: str, file_path: str, content: bytes):
        """Index content for search (only for text files)."""
        try:
            # Try to decode as text
            text_content = content.decode('utf-8')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO search_index (version_hash, file_path, content_text)
                VALUES (?, ?, ?)
            """, (version_hash, file_path, text_content))
            
            conn.commit()
            conn.close()
        except UnicodeDecodeError:
            # Skip binary files
            pass
    
    def search_content(self, query: str, file_path: Optional[str] = None) -> List[dict]:
        """Search for content in the repository."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if file_path:
            cursor.execute("""
                SELECT DISTINCT si.version_hash, si.file_path, v.timestamp
                FROM search_index si
                JOIN versions v ON si.version_hash = v.version_hash AND si.file_path = v.file_path
                WHERE si.content_text LIKE ? AND si.file_path = ?
                ORDER BY v.timestamp DESC
            """, (f'%{query}%', file_path))
        else:
            cursor.execute("""
                SELECT DISTINCT si.version_hash, si.file_path, v.timestamp
                FROM search_index si
                JOIN versions v ON si.version_hash = v.version_hash AND si.file_path = v.file_path
                WHERE si.content_text LIKE ?
                ORDER BY v.timestamp DESC
            """, (f'%{query}%',))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "hash": row[0],
                "file_path": row[1],
                "timestamp": row[2]
            })
        
        conn.close()
        return results
    
    # Metrics methods
    def record_metric(self, metric_type: str, value: float, metadata: Optional[dict] = None):
        """Record a metric for analytics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO metrics (metric_type, timestamp, value, metadata)
            VALUES (?, ?, ?, ?)
        """, (metric_type, datetime.now(), value, metadata_json))
        
        conn.commit()
        conn.close()
    
    def get_metrics(self, metric_type: str, since: Optional[datetime] = None) -> List[dict]:
        """Get metrics of a specific type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if since:
            cursor.execute("""
                SELECT timestamp, value, metadata
                FROM metrics
                WHERE metric_type = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (metric_type, since))
        else:
            cursor.execute("""
                SELECT timestamp, value, metadata
                FROM metrics
                WHERE metric_type = ?
                ORDER BY timestamp DESC
            """, (metric_type,))
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                "timestamp": row[0],
                "value": row[1],
                "metadata": json.loads(row[2]) if row[2] else None
            })
        
        conn.close()
        return metrics
    
    # Helper methods for branch management
    def _load_current_branch(self):
        """Load the current branch from a file or default to main."""
        branch_file = self.base_path / "current_branch"
        if branch_file.exists():
            self.current_branch = branch_file.read_text().strip()
        else:
            self.current_branch = "main"
    
    def _save_current_branch(self):
        """Save the current branch to a file."""
        branch_file = self.base_path / "current_branch"
        branch_file.write_text(self.current_branch)
    
    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch."""
        # Check if branch exists
        if self.get_branch(branch_name):
            self.current_branch = branch_name
            self._save_current_branch()
            return True
        return False
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        return self.current_branch
    
    def _update_current_branch_head(self, version_hash: str):
        """Update the head of the current branch."""
        self.update_branch_head(self.current_branch, version_hash)

# Alias for backward compatibility
ChronoLogStorage = Storage
