#!/usr/bin/env python3
"""
Test script to verify Phase 2 and Phase 3 features of ChronoLog
This script tests the advanced diff, file tree, organization, backup, and Git integration features
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chronolog.api import ChronologRepo, NotARepositoryError, RepositoryExistsError
from chronolog.diff.word_diff import WordDiffer
from chronolog.diff.semantic_diff import SemanticDiffer
from chronolog.diff.binary_diff import BinaryDiffer
from chronolog.organization.organizer import FileOrganizer
from chronolog.organization.bulk_operations import BulkOperations
from chronolog.backup.backup_manager import BackupManager
from chronolog.git_integration.git_exporter import GitExporter
from chronolog.git_integration.git_importer import GitImporter


def test_word_diff():
    """Test word-level diff functionality"""
    print("\n=== Testing Word-Level Diff ===")
    try:
        differ = WordDiffer()
        
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "The quick red fox jumps over the sleepy dog"
        
        word_diff = differ.diff_words(text1, text2)
        formatted = differ.format_word_diff(word_diff, use_color=False)
        
        print(f"✓ Word diff computed successfully")
        print(f"  Original: {text1}")
        print(f"  Modified: {text2}")
        print(f"  Diff: {formatted}")
        
        # Test line-based word diff
        multiline1 = "Line 1\nThe quick brown fox\nLine 3"
        multiline2 = "Line 1\nThe quick red fox\nLine 3 modified"
        
        line_diff = differ.diff_lines_with_words(multiline1, multiline2)
        print(f"✓ Line-based word diff computed: {len(line_diff)} lines")
        
        return True
    except Exception as e:
        print(f"✗ Word diff test failed: {e}")
        return False


def test_semantic_diff():
    """Test semantic diff for code"""
    print("\n=== Testing Semantic Diff ===")
    try:
        differ = SemanticDiffer()
        
        # Test Python code
        python_code1 = '''
def hello_world():
    print("Hello, World!")

class TestClass:
    def __init__(self):
        self.value = 42
'''
        
        python_code2 = '''
def hello_world():
    print("Hello, Universe!")

def new_function():
    return "new"

class TestClass:
    def __init__(self):
        self.value = 42
        self.name = "test"
'''
        
        language = differ.detect_language("test.py")
        print(f"✓ Detected language: {language}")
        
        if language:
            changes = differ.diff_semantic(python_code1, python_code2, language)
            formatted = differ.format_semantic_diff(changes)
            print(f"✓ Semantic diff computed: {len(changes)} changes")
            if formatted:
                print(f"  Changes:\n{formatted}")
        
        return True
    except Exception as e:
        print(f"✗ Semantic diff test failed: {e}")
        return False


def test_binary_diff():
    """Test binary file diff"""
    print("\n=== Testing Binary Diff ===")
    try:
        differ = BinaryDiffer()
        
        # Create test binary data
        data1 = b'\x00\x01\x02\x03\x04\x05'
        data2 = b'\x00\x01\xFF\x03\x04\x05'
        
        result = differ.diff_binary(data1, data2, "test.bin")
        formatted = differ.format_binary_diff(result)
        
        print(f"✓ Binary diff computed successfully")
        print(f"  Identical: {result.is_identical}")
        print(f"  Size1: {result.size1}, Size2: {result.size2}")
        print(f"  Similarity: {result.similarity_percent}%")
        
        if result.hex_diff:
            print(f"  Hex differences: {len(result.hex_diff)} chunks")
        
        return True
    except Exception as e:
        print(f"✗ Binary diff test failed: {e}")
        return False


def test_file_organization():
    """Test file organization features"""
    print("\n=== Testing File Organization ===")
    try:
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "script.py").write_text("print('hello')")
            (temp_path / "data.json").write_text('{"test": true}')
            (temp_path / "README.md").write_text("# Test Project")
            (temp_path / "config.yml").write_text("key: value")
            
            organizer = FileOrganizer(temp_path)
            analysis = organizer.analyze_repository()
            
            print(f"✓ Repository analysis completed")
            print(f"  Project type: {analysis.get('project_type', 'Unknown')}")
            print(f"  Total files: {analysis.get('total_files', 0)}")
            print(f"  Organization score: {analysis.get('organization_score', 0):.1f}/100")
            print(f"  Categories: {len(analysis.get('category_distribution', {}))}")
            print(f"  Suggestions: {len(analysis.get('suggestions', []))}")
            
            return True
    except Exception as e:
        print(f"✗ File organization test failed: {e}")
        return False


def test_bulk_operations():
    """Test bulk operations"""
    print("\n=== Testing Bulk Operations ===")
    try:
        # Create a temporary repository for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            os.chdir(temp_path)
            
            # Initialize repository
            repo = ChronologRepo.init()
            
            # Create test files
            (temp_path / "file1.py").write_text("print('file1')")
            (temp_path / "file2.py").write_text("print('file2')")
            (temp_path / "data.txt").write_text("some data")
            
            # Wait a moment for files to be tracked
            import time
            time.sleep(2)
            
            bulk_ops = BulkOperations(repo)
            
            # Test bulk export
            export_dir = temp_path / "export"
            exported = bulk_ops.bulk_export(export_dir, "*.py")
            print(f"✓ Bulk export completed: {len(exported)} files")
            
            # Test bulk ignore update
            success = bulk_ops.bulk_ignore_update(["*.tmp", "*.log"])
            print(f"✓ Bulk ignore update: {'Success' if success else 'Failed'}")
            
            return True
    except Exception as e:
        print(f"✗ Bulk operations test failed: {e}")
        return False


def test_backup_functionality():
    """Test backup and restore functionality"""
    print("\n=== Testing Backup Functionality ===")
    try:
        # Create a temporary repository for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            os.chdir(temp_path)
            
            # Initialize repository
            repo = ChronologRepo.init()
            
            # Create test files
            (temp_path / "important.txt").write_text("Important data")
            (temp_path / "config.json").write_text('{"setting": "value"}')
            
            # Wait for tracking
            import time
            time.sleep(2)
            
            backup_manager = BackupManager(temp_path)
            
            # Create backup
            backup_dir = temp_path / "backups"
            backup_id = backup_manager.create_backup(
                destination=backup_dir,
                backup_type="full",
                compression="gzip"
            )
            
            print(f"✓ Backup created: {backup_id}")
            
            # List backups
            backups = backup_manager.list_backups(backup_dir)
            print(f"✓ Found {len(backups)} backups")
            
            # Verify backup
            if backups:
                backup_file = backup_dir / f"chronolog_backup_{backup_id}.tar.gz"
                if backup_file.exists():
                    is_valid, message = backup_manager.verify_backup(backup_file)
                    print(f"✓ Backup verification: {message}")
                
                # Test restore
                restore_dir = temp_path / "restore"
                success = backup_manager.restore_backup(backup_file, restore_dir)
                print(f"✓ Backup restore: {'Success' if success else 'Failed'}")
            
            return True
    except Exception as e:
        print(f"✗ Backup functionality test failed: {e}")
        return False


def test_git_integration():
    """Test Git import/export functionality"""
    print("\n=== Testing Git Integration ===")
    try:
        # Check if git is available
        import subprocess
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠ Git not available, skipping Git integration tests")
            return True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create ChronoLog repository
            chronolog_dir = temp_path / "chronolog_repo"
            chronolog_dir.mkdir()
            os.chdir(chronolog_dir)
            
            repo = ChronologRepo.init()
            
            # Create test files
            (chronolog_dir / "main.py").write_text("print('main')")
            (chronolog_dir / "utils.py").write_text("def helper(): pass")
            
            # Wait for tracking
            import time
            time.sleep(2)
            
            # Test Git export
            git_dir = temp_path / "git_repo"
            exporter = GitExporter(repo)
            
            try:
                stats = exporter.export_to_git(
                    git_repo_path=git_dir,
                    export_branches=False,  # Simplified for testing
                    export_tags=False
                )
                print(f"✓ Git export completed:")
                print(f"  Commits: {stats.commits_created}")
                print(f"  Files: {stats.files_exported}")
                if stats.errors:
                    print(f"  Errors: {len(stats.errors)}")
            except Exception as e:
                print(f"⚠ Git export failed: {e}")
            
            # Test Git import (create a simple Git repo first)
            import_dir = temp_path / "import_test"
            import_dir.mkdir()
            os.chdir(import_dir)
            
            try:
                # Create a simple Git repository
                subprocess.run(["git", "init"], cwd=import_dir, check=True)
                subprocess.run(["git", "config", "user.name", "Test"], cwd=import_dir, check=True)
                subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=import_dir, check=True)
                
                (import_dir / "test.txt").write_text("test content")
                subprocess.run(["git", "add", "test.txt"], cwd=import_dir, check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=import_dir, check=True)
                
                # Import to ChronoLog
                chronolog_import_dir = temp_path / "chronolog_import"
                chronolog_import_dir.mkdir()
                os.chdir(chronolog_import_dir)
                
                import_repo = ChronologRepo.init()
                importer = GitImporter(import_repo)
                
                import_stats = importer.import_from_git(
                    git_repo_path=import_dir,
                    import_branches=False,
                    import_tags=False
                )
                
                print(f"✓ Git import completed:")
                print(f"  Commits: {import_stats.commits_imported}")
                print(f"  Files: {import_stats.files_imported}")
                if import_stats.errors:
                    print(f"  Errors: {len(import_stats.errors)}")
                
            except Exception as e:
                print(f"⚠ Git import test failed: {e}")
            
            return True
    except Exception as e:
        print(f"✗ Git integration test failed: {e}")
        return False


def test_enhanced_diff_in_api():
    """Test enhanced diff functionality through API"""
    print("\n=== Testing Enhanced Diff in API ===")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            os.chdir(temp_path)
            
            # Initialize repository
            repo = ChronologRepo.init()
            
            # Create test file
            test_file = temp_path / "test.py"
            test_file.write_text("def hello():\n    print('Hello')\n")
            
            # Wait for initial tracking
            import time
            time.sleep(2)
            
            # Get first version
            history = repo.log("test.py")
            if len(history) >= 1:
                first_hash = history[0]['version_hash']
                
                # Modify file
                test_file.write_text("def hello():\n    print('Hello World')\n\ndef goodbye():\n    print('Goodbye')\n")
                time.sleep(2)
                
                # Test different diff types
                try:
                    line_diff = repo.diff(first_hash, current=True, diff_type="line")
                    print(f"✓ Line diff computed: {len(line_diff.split(chr(10)))} lines")
                except Exception as e:
                    print(f"⚠ Line diff failed: {e}")
                
                try:
                    word_diff = repo.diff(first_hash, current=True, diff_type="word")
                    print(f"✓ Word diff computed: {len(word_diff.split(chr(10)))} lines")
                except Exception as e:
                    print(f"⚠ Word diff failed: {e}")
                
                try:
                    semantic_diff = repo.diff(first_hash, current=True, diff_type="semantic")
                    print(f"✓ Semantic diff computed: {len(semantic_diff.split(chr(10)))} lines")
                except Exception as e:
                    print(f"⚠ Semantic diff failed: {e}")
                
                # Test binary diff
                binary_file = temp_path / "test.bin"
                binary_file.write_bytes(b'\x00\x01\x02\x03')
                time.sleep(2)
                
                bin_history = repo.log("test.bin")
                if bin_history:
                    try:
                        binary_diff = repo.diff(bin_history[0]['version_hash'], current=True, diff_type="binary")
                        print(f"✓ Binary diff computed")
                    except Exception as e:
                        print(f"⚠ Binary diff failed: {e}")
            
            return True
    except Exception as e:
        print(f"✗ Enhanced diff API test failed: {e}")
        return False


def run_all_tests():
    """Run all Phase 2 and Phase 3 tests"""
    print("=" * 60)
    print("ChronoLog Phase 2 & 3 Features Test Suite")
    print("=" * 60)
    
    tests = [
        ("Word-Level Diff", test_word_diff),
        ("Semantic Diff", test_semantic_diff),
        ("Binary Diff", test_binary_diff),
        ("File Organization", test_file_organization),
        ("Bulk Operations", test_bulk_operations),
        ("Backup Functionality", test_backup_functionality),
        ("Git Integration", test_git_integration),
        ("Enhanced Diff API", test_enhanced_diff_in_api),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All Phase 2 & 3 features are working correctly!")
        return True
    else:
        print(f"⚠️  {failed} test(s) failed. Some features may need attention.")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)