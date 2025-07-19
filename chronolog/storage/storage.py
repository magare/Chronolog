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
        
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
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
        
        conn.commit()
        conn.close()
    
    def _calculate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
    
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