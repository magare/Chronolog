from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
from .merge_engine import MergeEngine, MergeResult, ConflictRegion, ConflictType


class ResolutionStrategy(Enum):
    OURS = "ours"
    THEIRS = "theirs"
    BOTH = "both"
    NONE = "none"
    MANUAL = "manual"


@dataclass
class ConflictResolution:
    conflict_id: str
    strategy: ResolutionStrategy
    manual_content: Optional[List[str]] = None


class ConflictResolver:
    """Interactive conflict resolution for merges."""
    
    def __init__(self):
        self.merge_engine = MergeEngine()
    
    def get_conflicts(self, merge_result: MergeResult) -> List[Dict[str, any]]:
        """Extract detailed conflict information for UI display."""
        if not merge_result.conflicts:
            return []
        
        conflicts = []
        for i, conflict in enumerate(merge_result.conflicts):
            conflicts.append({
                'id': f"conflict_{i}",
                'start_line': conflict.start_line,
                'end_line': conflict.end_line,
                'base_content': conflict.base_content,
                'our_content': conflict.our_content,
                'their_content': conflict.their_content,
                'type': merge_result.conflict_type.value if merge_result.conflict_type else 'content'
            })
        
        return conflicts
    
    def resolve_conflicts(self, merge_result: MergeResult, 
                         resolutions: List[ConflictResolution]) -> Optional[bytes]:
        """Apply conflict resolutions to create final merged content."""
        if not merge_result.content or not merge_result.conflicts:
            return merge_result.content
        
        try:
            content = merge_result.content.decode('utf-8')
            lines = content.splitlines()
            
            # Create resolution mapping
            resolution_map = {res.conflict_id: res for res in resolutions}
            
            # Process conflicts from bottom to top to maintain line numbers
            conflicts_with_ids = []
            for i, conflict in enumerate(merge_result.conflicts):
                conflicts_with_ids.append((f"conflict_{i}", conflict))
            
            conflicts_with_ids.sort(key=lambda x: x[1].start_line, reverse=True)
            
            for conflict_id, conflict in conflicts_with_ids:
                if conflict_id not in resolution_map:
                    continue  # Skip unresolved conflicts
                
                resolution = resolution_map[conflict_id]
                resolved_lines = self._apply_resolution(conflict, resolution)
                
                # Find conflict markers in the content
                conflict_start = None
                conflict_end = None
                
                for line_idx, line in enumerate(lines):
                    if line == self.merge_engine.conflict_markers['start']:
                        conflict_start = line_idx
                    elif line == self.merge_engine.conflict_markers['end'] and conflict_start is not None:
                        conflict_end = line_idx + 1
                        break
                
                if conflict_start is not None and conflict_end is not None:
                    # Replace conflict section with resolved content
                    lines[conflict_start:conflict_end] = resolved_lines
            
            return '\n'.join(lines).encode('utf-8')
            
        except UnicodeDecodeError:
            return None
    
    def _apply_resolution(self, conflict: ConflictRegion, 
                         resolution: ConflictResolution) -> List[str]:
        """Apply a specific resolution strategy to a conflict."""
        if resolution.strategy == ResolutionStrategy.OURS:
            return conflict.our_content
        elif resolution.strategy == ResolutionStrategy.THEIRS:
            return conflict.their_content
        elif resolution.strategy == ResolutionStrategy.BOTH:
            result = []
            result.extend(conflict.our_content)
            result.extend(conflict.their_content)
            return result
        elif resolution.strategy == ResolutionStrategy.NONE:
            return []
        elif resolution.strategy == ResolutionStrategy.MANUAL:
            return resolution.manual_content or []
        else:
            # Default to base content if no strategy matches
            return conflict.base_content
    
    def auto_resolve_conflicts(self, merge_result: MergeResult) -> List[ConflictResolution]:
        """Attempt automatic resolution of simple conflicts."""
        if not merge_result.conflicts:
            return []
        
        auto_resolutions = []
        
        for i, conflict in enumerate(merge_result.conflicts):
            conflict_id = f"conflict_{i}"
            resolution = self._analyze_conflict_for_auto_resolution(conflict)
            
            if resolution:
                auto_resolutions.append(ConflictResolution(
                    conflict_id=conflict_id,
                    strategy=resolution
                ))
        
        return auto_resolutions
    
    def _analyze_conflict_for_auto_resolution(self, 
                                            conflict: ConflictRegion) -> Optional[ResolutionStrategy]:
        """Analyze a conflict to determine if it can be auto-resolved."""
        # If one side is empty, prefer the non-empty side
        if not conflict.our_content and conflict.their_content:
            return ResolutionStrategy.THEIRS
        elif conflict.our_content and not conflict.their_content:
            return ResolutionStrategy.OURS
        
        # If both sides are identical, use either
        if conflict.our_content == conflict.their_content:
            return ResolutionStrategy.OURS
        
        # If one side is just whitespace changes, could potentially auto-resolve
        our_stripped = [line.strip() for line in conflict.our_content]
        their_stripped = [line.strip() for line in conflict.their_content]
        
        if our_stripped == their_stripped:
            # Prefer the version with more consistent indentation
            our_indent = self._analyze_indentation(conflict.our_content)
            their_indent = self._analyze_indentation(conflict.their_content)
            
            if our_indent['consistent'] and not their_indent['consistent']:
                return ResolutionStrategy.OURS
            elif their_indent['consistent'] and not our_indent['consistent']:
                return ResolutionStrategy.THEIRS
        
        # Cannot auto-resolve
        return None
    
    def _analyze_indentation(self, lines: List[str]) -> Dict[str, any]:
        """Analyze indentation consistency in a set of lines."""
        if not lines:
            return {'consistent': True, 'type': 'spaces', 'size': 0}
        
        indent_types = set()
        indent_sizes = []
        
        for line in lines:
            if not line.strip():
                continue  # Skip empty lines
            
            leading_spaces = len(line) - len(line.lstrip(' '))
            leading_tabs = len(line) - len(line.lstrip('\t'))
            
            if leading_tabs > 0:
                indent_types.add('tabs')
                indent_sizes.append(leading_tabs)
            elif leading_spaces > 0:
                indent_types.add('spaces')
                indent_sizes.append(leading_spaces)
        
        consistent_type = len(indent_types) <= 1
        consistent_size = len(set(indent_sizes)) <= 1 if indent_sizes else True
        
        return {
            'consistent': consistent_type and consistent_size,
            'type': list(indent_types)[0] if len(indent_types) == 1 else 'mixed',
            'size': indent_sizes[0] if len(set(indent_sizes)) == 1 and indent_sizes else 0
        }
    
    def get_resolution_preview(self, conflict: ConflictRegion, 
                              resolution: ConflictResolution) -> List[str]:
        """Preview what the resolution would look like."""
        return self._apply_resolution(conflict, resolution)
    
    def validate_resolution(self, resolution: ConflictResolution) -> bool:
        """Validate that a resolution is complete and valid."""
        if resolution.strategy == ResolutionStrategy.MANUAL:
            return resolution.manual_content is not None
        
        return resolution.strategy in [
            ResolutionStrategy.OURS,
            ResolutionStrategy.THEIRS,
            ResolutionStrategy.BOTH,
            ResolutionStrategy.NONE
        ]
    
    def get_conflict_stats(self, merge_result: MergeResult) -> Dict[str, any]:
        """Get statistics about conflicts in a merge result."""
        if not merge_result.conflicts:
            return {
                'total_conflicts': 0,
                'conflict_types': {},
                'total_lines_affected': 0,
                'largest_conflict': 0
            }
        
        conflict_types = {}
        total_lines = 0
        conflict_sizes = []
        
        for conflict in merge_result.conflicts:
            # Determine conflict complexity
            our_lines = len(conflict.our_content)
            their_lines = len(conflict.their_content)
            conflict_size = max(our_lines, their_lines)
            
            conflict_sizes.append(conflict_size)
            total_lines += conflict_size
            
            # Categorize conflict type
            if our_lines == 0:
                conflict_type = 'addition'
            elif their_lines == 0:
                conflict_type = 'deletion'
            elif our_lines == their_lines:
                conflict_type = 'modification'
            else:
                conflict_type = 'complex'
            
            conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1
        
        return {
            'total_conflicts': len(merge_result.conflicts),
            'conflict_types': conflict_types,
            'total_lines_affected': total_lines,
            'largest_conflict': max(conflict_sizes) if conflict_sizes else 0,
            'average_conflict_size': sum(conflict_sizes) / len(conflict_sizes) if conflict_sizes else 0
        }