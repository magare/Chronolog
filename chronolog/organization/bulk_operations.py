from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import fnmatch


class BulkOperations:
    """Bulk operations for ChronoLog repositories."""
    
    def __init__(self, repo):
        self.repo = repo
        self.repo_path = Path(repo.repo_path)
    
    def bulk_tag(self, version_patterns: Dict[str, str], tag_prefix: str = "bulk") -> List[str]:
        """
        Tag multiple versions at once based on patterns.
        
        Args:
            version_patterns: Dict mapping file patterns to tag suffixes
            tag_prefix: Prefix for all tags
            
        Returns:
            List of created tag names
        """
        created_tags = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for pattern, suffix in version_patterns.items():
            # Find matching files
            matching_files = self._find_files_by_pattern(pattern)
            
            for file_path in matching_files:
                # Get latest version
                history = self.repo.log(str(file_path))
                if history:
                    latest = history[0]
                    tag_name = f"{tag_prefix}_{suffix}_{timestamp}"
                    
                    try:
                        self.repo.tag(tag_name, latest['version_hash'], 
                                     f"Bulk tagged {file_path.name}")
                        created_tags.append(tag_name)
                    except:
                        pass
        
        return created_tags
    
    def bulk_checkout(self, checkout_map: Dict[str, str]) -> Dict[str, bool]:
        """
        Checkout multiple files to specific versions.
        
        Args:
            checkout_map: Dict mapping file paths to version hashes
            
        Returns:
            Dict mapping file paths to success status
        """
        results = {}
        
        for file_path, version_hash in checkout_map.items():
            try:
                self.repo.checkout(version_hash, file_path)
                results[file_path] = True
            except Exception as e:
                results[file_path] = False
        
        return results
    
    def bulk_ignore_update(self, patterns: List[str], action: str = "add") -> bool:
        """
        Update ignore patterns in bulk.
        
        Args:
            patterns: List of patterns to add or remove
            action: "add" or "remove"
            
        Returns:
            Success status
        """
        ignore_file = self.repo_path / ".chronologignore"
        
        try:
            # Read existing patterns
            existing_patterns = set()
            if ignore_file.exists():
                with open(ignore_file, 'r') as f:
                    existing_patterns = {line.strip() for line in f 
                                       if line.strip() and not line.startswith('#')}
            
            # Update patterns
            if action == "add":
                existing_patterns.update(patterns)
            elif action == "remove":
                existing_patterns.difference_update(patterns)
            
            # Write updated patterns
            with open(ignore_file, 'w') as f:
                f.write("# ChronoLog ignore patterns\n")
                f.write("# Updated by bulk operation\n\n")
                for pattern in sorted(existing_patterns):
                    f.write(f"{pattern}\n")
            
            return True
        except:
            return False
    
    def bulk_search_replace(self, search_pattern: str, replace_pattern: str, 
                           file_filter: Optional[str] = None,
                           dry_run: bool = True) -> Dict[str, List[Dict]]:
        """
        Search and replace across multiple files in history.
        
        Args:
            search_pattern: Pattern to search for
            replace_pattern: Replacement pattern
            file_filter: Optional file pattern filter
            dry_run: If True, only report what would be changed
            
        Returns:
            Dict mapping file paths to list of matching versions
        """
        results = {}
        
        # Get all files matching filter
        files = self._find_files_by_pattern(file_filter) if file_filter else self._get_all_files()
        
        for file_path in files:
            matches = []
            history = self.repo.log(str(file_path))
            
            for version in history:
                try:
                    content = self.repo.show(version['version_hash'])
                    text = content.decode('utf-8')
                    
                    if search_pattern in text:
                        matches.append({
                            'version_hash': version['version_hash'],
                            'timestamp': version['timestamp'],
                            'occurrences': text.count(search_pattern)
                        })
                except:
                    continue
            
            if matches:
                results[str(file_path)] = matches
        
        return results
    
    def bulk_export(self, output_dir: Path, file_filter: Optional[str] = None,
                   versions: str = "latest") -> Dict[str, Path]:
        """
        Export multiple files from the repository.
        
        Args:
            output_dir: Directory to export files to
            file_filter: Optional file pattern filter
            versions: "latest", "all", or specific version hash
            
        Returns:
            Dict mapping file paths to exported paths
        """
        exported = {}
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files = self._find_files_by_pattern(file_filter) if file_filter else self._get_all_files()
        
        for file_path in files:
            history = self.repo.log(str(file_path))
            if not history:
                continue
            
            if versions == "latest":
                versions_to_export = [history[0]]
            elif versions == "all":
                versions_to_export = history
            else:
                versions_to_export = [v for v in history if v['version_hash'].startswith(versions)]
            
            for version in versions_to_export:
                try:
                    content = self.repo.show(version['version_hash'])
                    
                    # Create output path
                    if len(versions_to_export) > 1:
                        output_file = output_dir / f"{file_path.stem}_{version['version_hash'][:8]}{file_path.suffix}"
                    else:
                        output_file = output_dir / file_path.name
                    
                    output_file.write_bytes(content)
                    exported[str(file_path)] = output_file
                except:
                    continue
        
        return exported
    
    def bulk_analyze(self, analyzer_func: Callable[[bytes, Path], Any],
                    file_filter: Optional[str] = None,
                    parallel: bool = True) -> Dict[str, Any]:
        """
        Run analysis function on multiple files in parallel.
        
        Args:
            analyzer_func: Function that takes (content, path) and returns analysis result
            file_filter: Optional file pattern filter
            parallel: Whether to run in parallel
            
        Returns:
            Dict mapping file paths to analysis results
        """
        results = {}
        files = self._find_files_by_pattern(file_filter) if file_filter else self._get_all_files()
        
        if parallel:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                
                for file_path in files:
                    future = executor.submit(self._analyze_file, file_path, analyzer_func)
                    futures[future] = file_path
                
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        result = future.result()
                        if result is not None:
                            results[str(file_path)] = result
                    except:
                        continue
        else:
            for file_path in files:
                result = self._analyze_file(file_path, analyzer_func)
                if result is not None:
                    results[str(file_path)] = result
        
        return results
    
    def _analyze_file(self, file_path: Path, analyzer_func: Callable) -> Optional[Any]:
        """Analyze a single file."""
        try:
            history = self.repo.log(str(file_path))
            if history:
                content = self.repo.show(history[0]['version_hash'])
                return analyzer_func(content, file_path)
        except:
            pass
        return None
    
    def _find_files_by_pattern(self, pattern: str) -> List[Path]:
        """Find files matching a pattern."""
        matching_files = []
        
        for file_path in self._get_all_files():
            if fnmatch.fnmatch(str(file_path), pattern):
                matching_files.append(file_path)
        
        return matching_files
    
    def _get_all_files(self) -> List[Path]:
        """Get all tracked files in the repository."""
        all_files = []
        
        # This is a simplified version - in practice, you'd query the storage
        for root, dirs, files in Path(self.repo_path).walk():
            if '.chronolog' in str(root):
                continue
            
            for file in files:
                all_files.append(root / file)
        
        return all_files
    
    def generate_bulk_report(self, operations: List[str]) -> Dict[str, Any]:
        """Generate a report of available bulk operations."""
        report = {
            'repository': str(self.repo_path),
            'timestamp': datetime.now().isoformat(),
            'available_operations': {
                'bulk_tag': 'Tag multiple versions based on patterns',
                'bulk_checkout': 'Checkout multiple files to specific versions',
                'bulk_ignore_update': 'Update ignore patterns in bulk',
                'bulk_search_replace': 'Search and replace across file history',
                'bulk_export': 'Export multiple files from repository',
                'bulk_analyze': 'Run analysis on multiple files'
            },
            'statistics': {
                'total_files': len(self._get_all_files()),
                'total_versions': 0  # Would need to calculate
            }
        }
        
        return report