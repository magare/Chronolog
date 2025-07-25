#!/usr/bin/env python3
"""
Unit tests for merge engine components
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronolog.merge.merge_engine import MergeEngine, MergeResult, ConflictRegion, ConflictType
from chronolog.merge.conflict_resolver import ConflictResolver, ConflictInfo


class TestMergeEngine(unittest.TestCase):
    """Test cases for MergeEngine"""
    
    def setUp(self):
        """Set up test environment"""
        self.merge_engine = MergeEngine()
    
    def test_successful_merge_no_conflicts(self):
        """Test successful merge with no conflicts"""
        base = b"line 1\\nline 2\\nline 3\\n"
        ours = b"line 1\\nmodified line 2\\nline 3\\n"
        theirs = b"line 1\\nline 2\\nline 3\\nadded line 4\\n"
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.content)
        self.assertEqual(len(result.conflicts), 0)
        
        # The merged content should contain both changes
        merged_text = result.content.decode('utf-8')
        self.assertIn("modified line 2", merged_text)
        self.assertIn("added line 4", merged_text)
    
    def test_merge_with_conflicts(self):
        """Test merge that results in conflicts"""
        base = b"line 1\\nline 2\\nline 3\\n"
        ours = b"line 1\\nour modification\\nline 3\\n"
        theirs = b"line 1\\ntheir modification\\nline 3\\n"
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        self.assertFalse(result.success)
        self.assertGreater(len(result.conflicts), 0)
        
        # Check conflict details
        conflict = result.conflicts[0]
        self.assertIsInstance(conflict, ConflictRegion)
        self.assertEqual(conflict.conflict_type, ConflictType.CONTENT)
        self.assertGreater(conflict.start_line, 0)
        self.assertGreaterEqual(conflict.end_line, conflict.start_line)
    
    def test_binary_merge(self):
        """Test merge of binary content"""
        base = b"\\x00\\x01\\x02\\x03"
        ours = b"\\x00\\x01\\x02\\x04"  # Different last byte
        theirs = b"\\x00\\x01\\x02\\x03\\x05"  # Additional byte
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        # Binary merges typically result in conflicts
        self.assertFalse(result.success)
        self.assertGreater(len(result.conflicts), 0)
    
    def test_identical_changes(self):
        """Test merge where both sides make identical changes"""
        base = b"line 1\\nline 2\\nline 3\\n"
        ours = b"line 1\\nsame modification\\nline 3\\n"
        theirs = b"line 1\\nsame modification\\nline 3\\n"
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.conflicts), 0)
        
        merged_text = result.content.decode('utf-8')
        self.assertIn("same modification", merged_text)
    
    def test_empty_base(self):
        """Test merge with empty base (new file)"""
        base = b""
        ours = b"our content\\n"
        theirs = b"their content\\n"
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        # New file with different content should conflict
        self.assertFalse(result.success)
        self.assertGreater(len(result.conflicts), 0)
    
    def test_one_side_unchanged(self):
        """Test merge where one side is unchanged"""
        base = b"line 1\\nline 2\\nline 3\\n"
        ours = base  # No changes
        theirs = b"line 1\\nmodified line 2\\nline 3\\n"
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.conflicts), 0)
        
        # Should take the changes from 'theirs'
        merged_text = result.content.decode('utf-8')
        self.assertIn("modified line 2", merged_text)
    
    def test_deletion_vs_modification(self):
        """Test conflict between deletion and modification"""
        base = b"line 1\\nline 2\\nline 3\\n"
        ours = b"line 1\\nline 3\\n"  # Deleted line 2
        theirs = b"line 1\\nmodified line 2\\nline 3\\n"  # Modified line 2
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        self.assertFalse(result.success)
        self.assertGreater(len(result.conflicts), 0)
        
        # Should be a deletion vs modification conflict
        conflict = result.conflicts[0]
        self.assertEqual(conflict.conflict_type, ConflictType.CONTENT)
    
    def test_large_file_merge(self):
        """Test merge with larger content"""
        # Create larger test content
        base_lines = [f"line {i}\\n" for i in range(100)]
        base = "".join(base_lines).encode('utf-8')
        
        # Modify different sections
        ours_lines = base_lines.copy()
        ours_lines[10] = "modified line 10 by ours\\n"
        ours = "".join(ours_lines).encode('utf-8')
        
        theirs_lines = base_lines.copy()
        theirs_lines[50] = "modified line 50 by theirs\\n"
        theirs = "".join(theirs_lines).encode('utf-8')
        
        result = self.merge_engine.three_way_merge(base, ours, theirs)
        
        self.assertIsInstance(result, MergeResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.conflicts), 0)
        
        # Both modifications should be present
        merged_text = result.content.decode('utf-8')
        self.assertIn("modified line 10 by ours", merged_text)
        self.assertIn("modified line 50 by theirs", merged_text)
    
    def test_text_merge_methods(self):
        """Test internal text merge methods"""
        base_text = "line 1\\nline 2\\nline 3\\n"
        ours_text = "line 1\\nour line 2\\nline 3\\n"
        theirs_text = "line 1\\ntheir line 2\\nline 3\\n"
        
        result = self.merge_engine._merge_text(base_text, ours_text, theirs_text)
        
        self.assertIsInstance(result, MergeResult)
        # This should result in a conflict
        self.assertFalse(result.success)
        self.assertGreater(len(result.conflicts), 0)
    
    def test_conflict_detection(self):
        """Test conflict detection methods"""
        base_lines = ["line 1", "line 2", "line 3"]
        ours_lines = ["line 1", "our modification", "line 3"]
        theirs_lines = ["line 1", "their modification", "line 3"]
        
        conflicts = self.merge_engine._find_conflicts(base_lines, ours_lines, theirs_lines)
        
        self.assertIsInstance(conflicts, list)
        self.assertGreater(len(conflicts), 0)
        
        conflict = conflicts[0]
        self.assertIsInstance(conflict, ConflictRegion)
        self.assertEqual(conflict.start_line, 2)  # Line 2 (1-indexed)
        self.assertEqual(conflict.end_line, 2)


class TestConflictResolver(unittest.TestCase):
    """Test cases for ConflictResolver"""
    
    def setUp(self):
        """Set up test environment"""
        self.resolver = ConflictResolver()
    
    def test_conflict_parsing(self):
        """Test parsing conflicts from merge markers"""
        content_with_conflicts = '''line 1
line 2
<<<<<<< ours
our modification
=======
their modification
>>>>>>> theirs
line 4
line 5'''
        
        conflicts = self.resolver.parse_conflicts(content_with_conflicts)
        
        self.assertIsInstance(conflicts, list)
        self.assertEqual(len(conflicts), 1)
        
        conflict = conflicts[0]
        self.assertIsInstance(conflict, ConflictInfo)
        self.assertEqual(conflict.start_line, 3)
        self.assertEqual(conflict.end_line, 7)
        self.assertIn("our modification", conflict.ours_content)
        self.assertIn("their modification", conflict.theirs_content)
    
    def test_multiple_conflicts_parsing(self):
        """Test parsing multiple conflicts"""
        content_with_conflicts = '''line 1
<<<<<<< ours
first our change
=======
first their change
>>>>>>> theirs
line 3
line 4
<<<<<<< ours
second our change
=======
second their change
>>>>>>> theirs
line 6'''
        
        conflicts = self.resolver.parse_conflicts(content_with_conflicts)
        
        self.assertEqual(len(conflicts), 2)
        
        # Check first conflict
        self.assertIn("first our change", conflicts[0].ours_content)
        self.assertIn("first their change", conflicts[0].theirs_content)
        
        # Check second conflict
        self.assertIn("second our change", conflicts[1].ours_content)
        self.assertIn("second their change", conflicts[1].theirs_content)
    
    def test_auto_resolve_ours_strategy(self):
        """Test automatic resolution using 'ours' strategy"""
        content_with_conflicts = '''line 1
<<<<<<< ours
our modification
=======
their modification
>>>>>>> theirs
line 3'''
        
        resolved = self.resolver.auto_resolve_conflicts(content_with_conflicts, "ours")
        
        self.assertIsNotNone(resolved)
        self.assertIn("our modification", resolved)
        self.assertNotIn("their modification", resolved)
        self.assertNotIn("<<<<<<<", resolved)
        self.assertNotIn("=======", resolved)
        self.assertNotIn(">>>>>>>", resolved)
    
    def test_auto_resolve_theirs_strategy(self):
        """Test automatic resolution using 'theirs' strategy"""
        content_with_conflicts = '''line 1
<<<<<<< ours
our modification
=======
their modification
>>>>>>> theirs
line 3'''
        
        resolved = self.resolver.auto_resolve_conflicts(content_with_conflicts, "theirs")
        
        self.assertIsNotNone(resolved)
        self.assertNotIn("our modification", resolved)
        self.assertIn("their modification", resolved)
        self.assertNotIn("<<<<<<<", resolved)
        self.assertNotIn("=======", resolved)
        self.assertNotIn(">>>>>>>", resolved)
    
    def test_conflict_statistics(self):
        """Test conflict statistics generation"""
        merge_result = MergeResult(
            success=False,
            content=b"",
            conflicts=[
                ConflictRegion(1, 3, ConflictType.CONTENT, ["our1"], ["their1"]),
                ConflictRegion(5, 7, ConflictType.CONTENT, ["our2"], ["their2"]),
            ]
        )
        
        stats = self.resolver.get_conflict_statistics(merge_result)
        
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['total_conflicts'], 2)
        self.assertEqual(stats['content_conflicts'], 2)
        self.assertEqual(stats['deletion_conflicts'], 0)
        self.assertIn('conflict_density', stats)
        self.assertIn('largest_conflict_size', stats)
    
    def test_conflict_resolution_suggestions(self):
        """Test conflict resolution suggestions"""
        conflict = ConflictInfo(
            start_line=1,
            end_line=3,
            ours_content="our simple change",
            theirs_content="their simple change",
            base_content="original content"
        )
        
        suggestions = self.resolver.get_resolution_suggestions(conflict)
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        for suggestion in suggestions:
            self.assertIn('strategy', suggestion)
            self.assertIn('description', suggestion)
            self.assertIn('confidence', suggestion)
            self.assertGreaterEqual(suggestion['confidence'], 0)
            self.assertLessEqual(suggestion['confidence'], 1)
    
    def test_interactive_conflict_data(self):
        """Test data preparation for interactive conflict resolution"""
        content_with_conflicts = '''line 1
<<<<<<< ours
our modification line 1
our modification line 2
=======
their modification line 1
their modification line 2
their modification line 3
>>>>>>> theirs
line 3'''
        
        conflicts = self.resolver.parse_conflicts(content_with_conflicts)
        conflict_data = self.resolver.prepare_interactive_data(conflicts[0])
        
        self.assertIsInstance(conflict_data, dict)
        self.assertIn('ours_lines', conflict_data)
        self.assertIn('theirs_lines', conflict_data)
        self.assertIn('base_lines', conflict_data)
        self.assertIn('line_mapping', conflict_data)
        
        # Check line data
        self.assertEqual(len(conflict_data['ours_lines']), 2)
        self.assertEqual(len(conflict_data['theirs_lines']), 3)
    
    def test_similarity_analysis(self):
        """Test similarity analysis between conflicting sections"""
        ours_content = "function calculate(x) { return x * 2; }"
        theirs_content = "function calculate(x) { return x * 3; }"
        
        similarity = self.resolver.calculate_similarity(ours_content, theirs_content)
        
        self.assertIsInstance(similarity, float)
        self.assertGreaterEqual(similarity, 0)
        self.assertLessEqual(similarity, 1)
        self.assertGreater(similarity, 0.8)  # Should be quite similar
    
    def test_merge_markers_validation(self):
        """Test validation of merge markers"""
        valid_content = '''line 1
<<<<<<< ours
our change
=======
their change
>>>>>>> theirs
line 3'''
        
        invalid_content = '''line 1
<<<<<<< ours
our change
=======
their change
line 3'''  # Missing closing marker
        
        self.assertTrue(self.resolver.validate_merge_markers(valid_content))
        self.assertFalse(self.resolver.validate_merge_markers(invalid_content))
    
    def test_conflict_context_extraction(self):
        """Test extraction of context around conflicts"""
        full_content = '''line 1
line 2
line 3
<<<<<<< ours
our change
=======
their change
>>>>>>> theirs
line 8
line 9
line 10'''
        
        conflicts = self.resolver.parse_conflicts(full_content)
        context = self.resolver.extract_conflict_context(full_content, conflicts[0], context_lines=2)
        
        self.assertIsInstance(context, dict)
        self.assertIn('before', context)
        self.assertIn('after', context)
        
        # Should have 2 lines before and after
        self.assertEqual(len(context['before']), 2)
        self.assertEqual(len(context['after']), 2)
        self.assertIn("line 2", context['before'])
        self.assertIn("line 3", context['before'])
        self.assertIn("line 8", context['after'])
        self.assertIn("line 9", context['after'])
    
    def test_complex_conflict_resolution(self):
        """Test resolution of complex conflicts with multiple strategies"""
        complex_conflict = '''line 1
<<<<<<< ours
// Our implementation
function processData(data) {
    return data.map(x => x * 2);
}
=======
// Their implementation  
function processData(data) {
    return data.map(x => x * 3);
}
>>>>>>> theirs
line 10'''
        
        # Test different resolution strategies
        resolved_ours = self.resolver.auto_resolve_conflicts(complex_conflict, "ours")
        resolved_theirs = self.resolver.auto_resolve_conflicts(complex_conflict, "theirs")
        
        self.assertIn("x * 2", resolved_ours)
        self.assertNotIn("x * 3", resolved_ours)
        
        self.assertIn("x * 3", resolved_theirs)
        self.assertNotIn("x * 2", resolved_theirs)
        
        # Both should have clean content without markers
        for resolved in [resolved_ours, resolved_theirs]:
            self.assertNotIn("<<<<<<<", resolved)
            self.assertNotIn("=======", resolved)
            self.assertNotIn(">>>>>>>", resolved)


if __name__ == '__main__':
    unittest.main()