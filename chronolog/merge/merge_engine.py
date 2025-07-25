import difflib
from pathlib import Path
from typing import List, Optional, Union, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class ConflictType(Enum):
    CONTENT = "content"
    BINARY = "binary"
    DELETE_MODIFY = "delete_modify"
    RENAME = "rename"


@dataclass
class ConflictRegion:
    start_line: int
    end_line: int
    base_content: List[str]
    our_content: List[str]
    their_content: List[str]


@dataclass
class MergeResult:
    success: bool
    content: Optional[bytes]
    conflicts: List[ConflictRegion]
    conflict_type: Optional[ConflictType]
    metadata: Dict[str, any]


class MergeEngine:
    """Three-way merge engine for ChronoLog."""
    
    def __init__(self):
        self.conflict_markers = {
            'start': '<<<<<<< OURS',
            'separator': '=======',
            'end': '>>>>>>> THEIRS'
        }
    
    def three_way_merge(self, base: bytes, ours: bytes, theirs: bytes,
                       file_path: Optional[str] = None) -> MergeResult:
        """Perform three-way merge on content."""
        # Handle binary files
        if self._is_binary(base) or self._is_binary(ours) or self._is_binary(theirs):
            return self._merge_binary(base, ours, theirs)
        
        # Convert to text
        try:
            base_text = base.decode('utf-8')
            ours_text = ours.decode('utf-8')
            theirs_text = theirs.decode('utf-8')
        except UnicodeDecodeError:
            return MergeResult(
                success=False,
                content=None,
                conflicts=[],
                conflict_type=ConflictType.BINARY,
                metadata={'error': 'Failed to decode as text'}
            )
        
        # Perform text merge
        return self._merge_text(base_text, ours_text, theirs_text, file_path)
    
    def _is_binary(self, content: bytes) -> bool:
        """Check if content is binary."""
        if not content:
            return False
        
        # Simple heuristic: check for null bytes in first 8KB
        sample = content[:8192]
        return b'\x00' in sample
    
    def _merge_binary(self, base: bytes, ours: bytes, theirs: bytes) -> MergeResult:
        """Handle binary file merge."""
        # For binary files, we can't do automatic merging
        # User must choose one version
        
        if ours == theirs:
            # Both sides made the same change
            return MergeResult(
                success=True,
                content=ours,
                conflicts=[],
                conflict_type=None,
                metadata={'resolution': 'identical_changes'}
            )
        elif ours == base:
            # Only theirs changed
            return MergeResult(
                success=True,
                content=theirs,
                conflicts=[],
                conflict_type=None,
                metadata={'resolution': 'theirs_only_changed'}
            )
        elif theirs == base:
            # Only ours changed
            return MergeResult(
                success=True,
                content=ours,
                conflicts=[],
                conflict_type=None,
                metadata={'resolution': 'ours_only_changed'}
            )
        else:
            # Both sides changed - conflict
            return MergeResult(
                success=False,
                content=None,
                conflicts=[],
                conflict_type=ConflictType.BINARY,
                metadata={
                    'base_size': len(base),
                    'ours_size': len(ours),
                    'theirs_size': len(theirs)
                }
            )
    
    def _merge_text(self, base: str, ours: str, theirs: str,
                   file_path: Optional[str] = None) -> MergeResult:
        """Perform text-based three-way merge."""
        base_lines = base.splitlines()
        ours_lines = ours.splitlines()
        theirs_lines = theirs.splitlines()
        
        # Use difflib to find differences
        base_to_ours = list(difflib.unified_diff(base_lines, ours_lines, n=0))
        base_to_theirs = list(difflib.unified_diff(base_lines, theirs_lines, n=0))
        
        # Parse the diffs to find changed regions
        ours_changes = self._parse_diff(base_to_ours)
        theirs_changes = self._parse_diff(base_to_theirs)
        
        # Find conflicts
        conflicts = self._find_conflicts(base_lines, ours_changes, theirs_changes)
        
        if not conflicts:
            # No conflicts, we can merge automatically
            merged_lines = self._apply_non_conflicting_changes(
                base_lines, ours_changes, theirs_changes
            )
            
            return MergeResult(
                success=True,
                content='\n'.join(merged_lines).encode('utf-8'),
                conflicts=[],
                conflict_type=None,
                metadata={'auto_merged': True}
            )
        else:
            # Generate conflict markers
            merged_lines = self._generate_conflict_markers(
                base_lines, ours_lines, theirs_lines, conflicts
            )
            
            return MergeResult(
                success=False,
                content='\n'.join(merged_lines).encode('utf-8'),
                conflicts=conflicts,
                conflict_type=ConflictType.CONTENT,
                metadata={'conflicts_count': len(conflicts)}
            )
    
    def _parse_diff(self, diff_lines: List[str]) -> List[Tuple[int, int, List[str]]]:
        """Parse unified diff to extract changes."""
        changes = []
        current_change = None
        
        for line in diff_lines:
            if line.startswith('@@'):
                # Parse hunk header
                # Format: @@ -start,count +start,count @@
                parts = line.split()
                if len(parts) >= 3:
                    old_info = parts[1][1:]  # Remove leading -
                    new_info = parts[2][1:]  # Remove leading +
                    
                    old_start = int(old_info.split(',')[0])
                    current_change = [old_start, 0, []]
            elif line.startswith('+') and current_change:
                current_change[2].append(line[1:])  # Remove + prefix
                current_change[1] += 1
            elif line.startswith('-') and current_change:
                current_change[1] += 1
            elif line.startswith(' '):
                # Context line, end current change
                if current_change and current_change[2]:
                    changes.append(tuple(current_change))
                    current_change = None
        
        # Add final change if exists
        if current_change and current_change[2]:
            changes.append(tuple(current_change))
        
        return changes
    
    def _find_conflicts(self, base_lines: List[str], 
                       ours_changes: List[Tuple[int, int, List[str]]],
                       theirs_changes: List[Tuple[int, int, List[str]]]) -> List[ConflictRegion]:
        """Find conflicting regions between our changes and their changes."""
        conflicts = []
        
        for ours_start, ours_count, ours_content in ours_changes:
            for theirs_start, theirs_count, theirs_content in theirs_changes:
                # Check for overlapping regions
                ours_end = ours_start + ours_count
                theirs_end = theirs_start + theirs_count
                
                # Ranges overlap if start1 <= end2 and start2 <= end1
                if ours_start <= theirs_end and theirs_start <= ours_end:
                    # We have a conflict
                    conflict_start = min(ours_start, theirs_start)
                    conflict_end = max(ours_end, theirs_end)
                    
                    # Get base content for conflict region
                    base_content = base_lines[conflict_start:conflict_end]
                    
                    conflicts.append(ConflictRegion(
                        start_line=conflict_start,
                        end_line=conflict_end,
                        base_content=base_content,
                        our_content=ours_content,
                        their_content=theirs_content
                    ))
        
        return conflicts
    
    def _apply_non_conflicting_changes(self, base_lines: List[str],
                                     ours_changes: List[Tuple[int, int, List[str]]],
                                     theirs_changes: List[Tuple[int, int, List[str]]]) -> List[str]:
        """Apply non-conflicting changes to create merged result."""
        result = base_lines.copy()
        
        # Sort changes by position (reverse order to maintain line numbers)
        all_changes = []
        for start, count, content in ours_changes:
            all_changes.append((start, count, content, 'ours'))
        for start, count, content in theirs_changes:
            all_changes.append((start, count, content, 'theirs'))
        
        # Sort by position (descending) to apply from bottom up
        all_changes.sort(key=lambda x: x[0], reverse=True)
        
        for start, count, content, source in all_changes:
            # Replace lines in the range
            result[start:start + count] = content
        
        return result
    
    def _generate_conflict_markers(self, base_lines: List[str], ours_lines: List[str],
                                 theirs_lines: List[str], 
                                 conflicts: List[ConflictRegion]) -> List[str]:
        """Generate merge result with conflict markers."""
        result = base_lines.copy()
        
        # Process conflicts from bottom to top to maintain line numbers
        for conflict in sorted(conflicts, key=lambda c: c.start_line, reverse=True):
            conflict_section = []
            
            # Add conflict markers
            conflict_section.append(self.conflict_markers['start'])
            conflict_section.extend(conflict.our_content)
            conflict_section.append(self.conflict_markers['separator'])
            conflict_section.extend(conflict.their_content)
            conflict_section.append(self.conflict_markers['end'])
            
            # Replace the conflicted region
            result[conflict.start_line:conflict.end_line] = conflict_section
        
        return result
    
    def resolve_conflict(self, conflicted_content: bytes, 
                        resolution: str) -> Optional[bytes]:
        """Resolve conflicts in merged content."""
        try:
            text = conflicted_content.decode('utf-8')
            lines = text.splitlines()
            
            resolved_lines = []
            in_conflict = False
            conflict_lines = {'ours': [], 'theirs': []}
            current_section = None
            
            for line in lines:
                if line == self.conflict_markers['start']:
                    in_conflict = True
                    current_section = 'ours'
                    continue
                elif line == self.conflict_markers['separator']:
                    current_section = 'theirs'
                    continue
                elif line == self.conflict_markers['end']:
                    # Resolve the conflict
                    if resolution == 'ours':
                        resolved_lines.extend(conflict_lines['ours'])
                    elif resolution == 'theirs':
                        resolved_lines.extend(conflict_lines['theirs'])
                    elif resolution == 'both':
                        resolved_lines.extend(conflict_lines['ours'])
                        resolved_lines.extend(conflict_lines['theirs'])
                    # If resolution == 'none', skip both sections
                    
                    # Reset conflict state
                    in_conflict = False
                    conflict_lines = {'ours': [], 'theirs': []}
                    current_section = None
                    continue
                
                if in_conflict:
                    conflict_lines[current_section].append(line)
                else:
                    resolved_lines.append(line)
            
            return '\n'.join(resolved_lines).encode('utf-8')
            
        except UnicodeDecodeError:
            return None
    
    def has_conflicts(self, content: bytes) -> bool:
        """Check if content has unresolved conflicts."""
        try:
            text = content.decode('utf-8')
            return (
                self.conflict_markers['start'] in text or
                self.conflict_markers['separator'] in text or
                self.conflict_markers['end'] in text
            )
        except UnicodeDecodeError:
            return False