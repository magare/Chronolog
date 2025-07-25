import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import sqlite3
import json


class CodeComplexityAnalyzer:
    """Analyzes code complexity for various programming languages."""
    
    @staticmethod
    def analyze_python(content: str) -> Dict[str, Any]:
        """Analyze Python code complexity."""
        try:
            tree = ast.parse(content)
            
            # Count various elements
            functions = []
            classes = []
            imports = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports += 1
            
            # Calculate cyclomatic complexity (simplified)
            complexity = 1  # Base complexity
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            
            # Count lines
            lines = content.split('\n')
            loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            
            return {
                'language': 'python',
                'lines_of_code': loc,
                'total_lines': len(lines),
                'functions': len(functions),
                'classes': len(classes),
                'imports': imports,
                'cyclomatic_complexity': complexity,
                'maintainability_index': max(0, 171 - 5.2 * complexity - 0.23 * loc)
            }
        except:
            return None
    
    @staticmethod
    def analyze_javascript(content: str) -> Dict[str, Any]:
        """Analyze JavaScript code complexity (basic)."""
        lines = content.split('\n')
        
        # Basic pattern matching
        function_pattern = r'function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)'
        class_pattern = r'class\s+\w+'
        import_pattern = r'import\s+.*from|require\s*\('
        
        functions = len(re.findall(function_pattern, content))
        classes = len(re.findall(class_pattern, content))
        imports = len(re.findall(import_pattern, content))
        
        # Count control structures for complexity
        complexity = 1
        control_patterns = [
            r'\bif\s*\(',
            r'\bwhile\s*\(',
            r'\bfor\s*\(',
            r'\bcatch\s*\(',
            r'\bcase\s+',
            r'\?\s*[^:]+\s*:'  # Ternary operators
        ]
        
        for pattern in control_patterns:
            complexity += len(re.findall(pattern, content))
        
        # Count lines
        loc = len([l for l in lines if l.strip() and not l.strip().startswith('//')])
        
        return {
            'language': 'javascript',
            'lines_of_code': loc,
            'total_lines': len(lines),
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'cyclomatic_complexity': complexity,
            'maintainability_index': max(0, 171 - 5.2 * complexity - 0.23 * loc)
        }
    
    @staticmethod
    def analyze_generic(content: str, language: str) -> Dict[str, Any]:
        """Generic code analysis for unsupported languages."""
        lines = content.split('\n')
        
        # Count non-empty, non-comment lines (simplified)
        loc = 0
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(('#', '//', '/*', '*')):
                loc += 1
        
        return {
            'language': language,
            'lines_of_code': loc,
            'total_lines': len(lines),
            'cyclomatic_complexity': 0,  # Cannot calculate for generic
            'maintainability_index': 0
        }


class MetricsCollector:
    """Collects advanced metrics for code quality and developer productivity."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        self.analyzer = CodeComplexityAnalyzer()
    
    def analyze_file(self, file_path: Path, content: bytes, 
                    version_hash: str) -> Optional[Dict[str, Any]]:
        """Analyze a single file for code metrics."""
        try:
            # Detect language
            ext = file_path.suffix.lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.go': 'go',
                '.rs': 'rust',
                '.rb': 'ruby',
                '.php': 'php'
            }
            
            language = language_map.get(ext)
            if not language:
                return None
            
            # Try to decode as text
            try:
                text_content = content.decode('utf-8')
            except:
                return None
            
            # Analyze based on language
            if language == 'python':
                metrics = self.analyzer.analyze_python(text_content)
            elif language in ['javascript', 'typescript']:
                metrics = self.analyzer.analyze_javascript(text_content)
            else:
                metrics = self.analyzer.analyze_generic(text_content, language)
            
            if metrics:
                # Store in database
                self._store_code_metrics(str(file_path), version_hash, metrics)
                
            return metrics
            
        except Exception as e:
            return None
    
    def _store_code_metrics(self, file_path: str, version_hash: str, 
                           metrics: Dict[str, Any]):
        """Store code metrics in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO code_metrics
                (file_path, version_hash, language, lines_of_code, 
                 complexity_score, maintainability_index, cyclomatic_complexity, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_path,
                version_hash,
                metrics.get('language'),
                metrics.get('lines_of_code', 0),
                metrics.get('cyclomatic_complexity', 0),
                metrics.get('maintainability_index', 0),
                metrics.get('cyclomatic_complexity', 0),
                datetime.now()
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_code_quality_trends(self, file_path: Optional[str] = None,
                              days: int = 30) -> Dict[str, List[float]]:
        """Get code quality trends over time."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            since = datetime.now().timestamp() - (days * 86400)
            
            if file_path:
                cursor.execute("""
                    SELECT 
                        analyzed_at,
                        lines_of_code,
                        complexity_score,
                        maintainability_index
                    FROM code_metrics
                    WHERE file_path = ? AND analyzed_at >= datetime(?, 'unixepoch')
                    ORDER BY analyzed_at
                """, (file_path, since))
            else:
                cursor.execute("""
                    SELECT 
                        analyzed_at,
                        AVG(lines_of_code),
                        AVG(complexity_score),
                        AVG(maintainability_index)
                    FROM code_metrics
                    WHERE analyzed_at >= datetime(?, 'unixepoch')
                    GROUP BY DATE(analyzed_at)
                    ORDER BY analyzed_at
                """, (since,))
            
            results = cursor.fetchall()
            
            trends = {
                'timestamps': [],
                'lines_of_code': [],
                'complexity': [],
                'maintainability': []
            }
            
            for row in results:
                trends['timestamps'].append(row[0])
                trends['lines_of_code'].append(row[1] or 0)
                trends['complexity'].append(row[2] or 0)
                trends['maintainability'].append(row[3] or 0)
            
            return trends
            
        finally:
            conn.close()
    
    def calculate_developer_metrics(self, user_id: str = "default", 
                                  days: int = 30) -> Dict[str, Any]:
        """Calculate developer productivity metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            since = datetime.now().timestamp() - (days * 86400)
            
            # Total commits/versions
            cursor.execute("""
                SELECT COUNT(*) FROM versions
                WHERE timestamp >= datetime(?, 'unixepoch')
            """, (since,))
            total_commits = cursor.fetchone()[0]
            
            # Files touched
            cursor.execute("""
                SELECT COUNT(DISTINCT file_path) FROM versions
                WHERE timestamp >= datetime(?, 'unixepoch')
            """, (since,))
            files_touched = cursor.fetchone()[0]
            
            # Lines changed (approximation based on file sizes)
            cursor.execute("""
                SELECT SUM(ABS(v2.file_size - v1.file_size))
                FROM versions v1
                INNER JOIN versions v2 ON v1.file_path = v2.file_path
                WHERE v2.timestamp > v1.timestamp
                AND v2.timestamp >= datetime(?, 'unixepoch')
            """, (since,))
            lines_changed = cursor.fetchone()[0] or 0
            
            # Most productive hours
            cursor.execute("""
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as count
                FROM versions
                WHERE timestamp >= datetime(?, 'unixepoch')
                GROUP BY hour
                ORDER BY count DESC
                LIMIT 3
            """, (since,))
            productive_hours = [int(row[0]) for row in cursor.fetchall()]
            
            # Most active days
            cursor.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as count
                FROM versions
                WHERE timestamp >= datetime(?, 'unixepoch')
                GROUP BY date
                ORDER BY count DESC
                LIMIT 5
            """, (since,))
            active_days = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Calculate productivity score (custom metric)
            avg_commits_per_day = total_commits / days if days > 0 else 0
            productivity_score = min(100, (
                (avg_commits_per_day * 20) +  # Weight commits
                (files_touched * 2) +          # Weight file diversity
                (lines_changed / 1000)         # Weight volume
            ))
            
            return {
                'user_id': user_id,
                'period_days': days,
                'total_commits': total_commits,
                'files_touched': files_touched,
                'lines_changed_estimate': lines_changed,
                'avg_commits_per_day': avg_commits_per_day,
                'productive_hours': productive_hours,
                'most_active_days': active_days,
                'productivity_score': productivity_score
            }
            
        finally:
            conn.close()
    
    def get_language_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics grouped by programming language."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    language,
                    COUNT(DISTINCT file_path) as file_count,
                    SUM(lines_of_code) as total_loc,
                    AVG(complexity_score) as avg_complexity,
                    AVG(maintainability_index) as avg_maintainability
                FROM code_metrics
                GROUP BY language
                ORDER BY total_loc DESC
            """)
            
            stats = {}
            for row in cursor.fetchall():
                language = row[0]
                stats[language] = {
                    'file_count': row[1],
                    'total_lines': row[2] or 0,
                    'avg_complexity': row[3] or 0,
                    'avg_maintainability': row[4] or 0
                }
            
            return stats
            
        finally:
            conn.close()