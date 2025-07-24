"""Advanced search functionality for ChronoLog repositories."""

import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from ..storage import Storage


class SearchFilter:
    """Represents search filters and criteria."""
    
    def __init__(self):
        self.query: Optional[str] = None
        self.file_paths: List[str] = []
        self.file_types: List[str] = []
        self.date_from: Optional[datetime] = None
        self.date_to: Optional[datetime] = None
        self.regex: bool = False
        self.case_sensitive: bool = False
        self.whole_words: bool = False
        self.limit: Optional[int] = None
    
    def add_file_type(self, extension: str):
        """Add a file type filter (e.g., '.py', '.txt')."""
        if not extension.startswith('.'):
            extension = '.' + extension
        self.file_types.append(extension)
    
    def set_date_range(self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None):
        """Set date range filter."""
        self.date_from = from_date
        self.date_to = to_date
    
    def set_recent(self, days: int):
        """Set filter to search only recent versions."""
        self.date_from = datetime.now() - timedelta(days=days)
        self.date_to = datetime.now()


class Searcher:
    """Advanced search engine for ChronoLog repositories."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
        self.db_path = storage.db_path
    
    def search(self, filter: SearchFilter) -> List[Dict]:
        """Search for content based on filters."""
        if not filter.query:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build the SQL query dynamically based on filters
        base_query = """
            SELECT DISTINCT si.version_hash, si.file_path, v.timestamp, v.annotation,
                   snippet(search_index, 2, '<mark>', '</mark>', '...', 50) as snippet
            FROM search_index si
            JOIN versions v ON si.version_hash = v.version_hash AND si.file_path = v.file_path
            WHERE 1=1
        """
        
        params = []
        conditions = []
        
        # Add content search condition
        if filter.regex:
            # For regex search, we'll need to use a custom function
            conditions.append("si.content_text REGEXP ?")
            params.append(filter.query)
        elif filter.whole_words:
            # Whole word search
            word_pattern = r'\b' + re.escape(filter.query) + r'\b'
            conditions.append("si.content_text REGEXP ?")
            params.append(word_pattern)
        else:
            # Standard LIKE search
            if filter.case_sensitive:
                conditions.append("si.content_text LIKE ?")
            else:
                conditions.append("LOWER(si.content_text) LIKE LOWER(?)")
            params.append(f'%{filter.query}%')
        
        # Add file path filters
        if filter.file_paths:
            path_conditions = []
            for path in filter.file_paths:
                path_conditions.append("si.file_path LIKE ?")
                params.append(f'%{path}%')
            conditions.append(f"({' OR '.join(path_conditions)})")
        
        # Add file type filters
        if filter.file_types:
            type_conditions = []
            for ext in filter.file_types:
                type_conditions.append("si.file_path LIKE ?")
                params.append(f'%{ext}')
            conditions.append(f"({' OR '.join(type_conditions)})")
        
        # Add date range filters
        if filter.date_from:
            conditions.append("v.timestamp >= ?")
            params.append(filter.date_from.isoformat())
        
        if filter.date_to:
            conditions.append("v.timestamp <= ?")
            params.append(filter.date_to.isoformat())
        
        # Combine all conditions
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Add ordering and limit
        base_query += " ORDER BY v.timestamp DESC"
        if filter.limit:
            base_query += f" LIMIT {filter.limit}"
        
        # Enable regex support
        conn.create_function("REGEXP", 2, self._regexp)
        
        try:
            cursor.execute(base_query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "hash": row[0],
                    "file_path": row[1],
                    "timestamp": row[2],
                    "annotation": row[3],
                    "snippet": row[4] if row[4] else ""
                })
            
            return results
        
        finally:
            conn.close()
    
    def _regexp(self, pattern: str, text: str) -> bool:
        """SQLite REGEXP implementation."""
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return False
    
    def search_by_content_change(self, added_text: Optional[str] = None, 
                                removed_text: Optional[str] = None) -> List[Dict]:
        """Search for versions where specific text was added or removed."""
        results = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all file paths with versions
        cursor.execute("""
            SELECT DISTINCT file_path FROM versions ORDER BY file_path
        """)
        file_paths = [row[0] for row in cursor.fetchall()]
        
        for file_path in file_paths:
            # Get version history for this file
            cursor.execute("""
                SELECT version_hash, timestamp, annotation
                FROM versions
                WHERE file_path = ?
                ORDER BY timestamp ASC
            """, (file_path,))
            
            versions = list(cursor.fetchall())
            
            for i in range(1, len(versions)):
                prev_hash = versions[i-1][0]
                curr_hash = versions[i][0]
                
                # Get content for both versions
                prev_content = self.storage.get_version_content(prev_hash)
                curr_content = self.storage.get_version_content(curr_hash)
                
                if not prev_content or not curr_content:
                    continue
                
                try:
                    prev_text = prev_content.decode('utf-8')
                    curr_text = curr_content.decode('utf-8')
                except UnicodeDecodeError:
                    continue
                
                # Check for added/removed text
                if added_text and added_text in curr_text and added_text not in prev_text:
                    results.append({
                        "hash": curr_hash,
                        "file_path": file_path,
                        "timestamp": versions[i][1],
                        "annotation": versions[i][2],
                        "change_type": "added",
                        "change_text": added_text
                    })
                
                if removed_text and removed_text in prev_text and removed_text not in curr_text:
                    results.append({
                        "hash": curr_hash,
                        "file_path": file_path,
                        "timestamp": versions[i][1],
                        "annotation": versions[i][2],
                        "change_type": "removed",
                        "change_text": removed_text
                    })
        
        conn.close()
        return results
    
    def reindex_all(self, progress_callback=None) -> Tuple[int, int]:
        """Reindex all versions in the repository.
        
        Returns:
            Tuple of (indexed_count, total_count)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing index
        cursor.execute("DELETE FROM search_index")
        conn.commit()
        
        # Get all versions
        cursor.execute("""
            SELECT version_hash, file_path FROM versions
            ORDER BY timestamp DESC
        """)
        
        versions = list(cursor.fetchall())
        total = len(versions)
        indexed = 0
        
        for i, (version_hash, file_path) in enumerate(versions):
            content = self.storage.get_version_content(version_hash)
            if content:
                # Try to index the content
                self.storage.index_content(version_hash, file_path, content)
                indexed += 1
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        conn.close()
        return indexed, total
    
    def get_search_stats(self) -> Dict:
        """Get statistics about the search index."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total indexed versions
        cursor.execute("SELECT COUNT(*) FROM search_index")
        indexed_count = cursor.fetchone()[0]
        
        # Total versions
        cursor.execute("SELECT COUNT(*) FROM versions")
        total_count = cursor.fetchone()[0]
        
        # Index size estimate
        cursor.execute("SELECT SUM(LENGTH(content_text)) FROM search_index")
        index_size = cursor.fetchone()[0] or 0
        
        # Most indexed file types
        cursor.execute("""
            SELECT 
                SUBSTR(file_path, -4) as ext,
                COUNT(*) as count
            FROM search_index
            WHERE file_path LIKE '%.%'
            GROUP BY ext
            ORDER BY count DESC
            LIMIT 10
        """)
        
        file_types = []
        for row in cursor.fetchall():
            file_types.append({"extension": row[0], "count": row[1]})
        
        conn.close()
        
        return {
            "indexed_versions": indexed_count,
            "total_versions": total_count,
            "index_size_bytes": index_size,
            "coverage_percent": (indexed_count / total_count * 100) if total_count > 0 else 0,
            "top_file_types": file_types
        }