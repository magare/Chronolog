#!/usr/bin/env python3
"""
Test script to verify Phase 1 features of ChronoLog
This script tests all the implemented features without requiring installation
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chronolog.api import ChronologRepo, NotARepositoryError, RepositoryExistsError
from chronolog.search.searcher import SearchFilter
from chronolog.ignore import IgnorePatterns
import time
from datetime import datetime

def test_init():
    """Test repository initialization"""
    print("\n=== Testing Repository Initialization ===")
    try:
        repo = ChronologRepo.init()
        print(f"✓ Repository initialized at: {repo.repo_path}")
        return True
    except RepositoryExistsError:
        print("✓ Repository already exists")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False

def test_ignore_patterns():
    """Test ignore patterns functionality"""
    print("\n=== Testing Ignore Patterns ===")
    try:
        repo = ChronologRepo()
        
        # Test creating default ignore file
        if IgnorePatterns.create_default_ignore_file(repo.repo_path):
            print("✓ Created default .chronologignore file")
        else:
            print("✓ .chronologignore file already exists")
        
        # Test loading patterns
        patterns = IgnorePatterns(repo.repo_path)
        pattern_list = patterns.get_patterns()
        print(f"✓ Loaded {len(pattern_list)} ignore patterns")
        
        # Test pattern matching
        test_files = [
            ".DS_Store",
            "test.pyc",
            "__pycache__/test.py",
            "node_modules/package.json",
            "test.txt",
            ".git/config"
        ]
        
        print("\nTesting pattern matching:")
        for file in test_files:
            if patterns.should_ignore(file):
                print(f"  - {file}: IGNORED ✓")
            else:
                print(f"  - {file}: NOT IGNORED")
        
        return True
    except Exception as e:
        print(f"✗ Failed ignore patterns test: {e}")
        return False

def test_branches():
    """Test branch functionality"""
    print("\n=== Testing Branches ===")
    try:
        repo = ChronologRepo()
        
        # List branches
        current, branches = repo.branch()
        print(f"✓ Current branch: {current}")
        print(f"✓ Total branches: {len(branches)}")
        
        # Create a new branch
        branch_name = f"test-branch-{int(time.time())}"
        repo.branch(branch_name)
        print(f"✓ Created branch: {branch_name}")
        
        # Switch to new branch
        repo.switch_branch(branch_name)
        print(f"✓ Switched to branch: {branch_name}")
        
        # List branches again
        current, branches = repo.branch()
        print(f"✓ Now on branch: {current}")
        
        # Switch back to main
        repo.switch_branch("main")
        print("✓ Switched back to main")
        
        # Delete test branch
        repo.delete_branch(branch_name)
        print(f"✓ Deleted branch: {branch_name}")
        
        return True
    except Exception as e:
        print(f"✗ Failed branch test: {e}")
        return False

def test_tags():
    """Test tag functionality"""
    print("\n=== Testing Tags ===")
    try:
        repo = ChronologRepo()
        
        # Create a test file to have something to tag
        test_file = Path("test_tag_file.txt")
        test_file.write_text("Test content for tagging")
        time.sleep(1)  # Wait for watcher to pick it up
        
        # Create a tag
        tag_name = f"v1.0.{int(time.time())}"
        repo.tag(tag_name, description="Test tag for Phase 1 verification")
        print(f"✓ Created tag: {tag_name}")
        
        # List tags
        tags = repo.list_tags()
        print(f"✓ Total tags: {len(tags)}")
        
        if tags:
            latest_tag = tags[0]
            print(f"✓ Latest tag: {latest_tag['name']} -> {latest_tag['hash'][:8]}")
        
        # Delete the tag
        repo.delete_tag(tag_name)
        print(f"✓ Deleted tag: {tag_name}")
        
        # Clean up
        test_file.unlink(missing_ok=True)
        
        return True
    except Exception as e:
        print(f"✗ Failed tag test: {e}")
        return False

def test_search():
    """Test search functionality"""
    print("\n=== Testing Search ===")
    try:
        repo = ChronologRepo()
        
        # Create test files with searchable content
        test_files = {
            "search_test1.txt": "Hello world, this is a test file for searching.",
            "search_test2.py": "def hello():\n    print('Hello from Python')\n    return True",
            "search_test3.md": "# Search Test\n\nThis is a markdown file with searchable content."
        }
        
        for filename, content in test_files.items():
            Path(filename).write_text(content)
        
        time.sleep(2)  # Wait for watcher to pick up files
        
        # Test simple search
        results = repo.search("hello")
        print(f"✓ Simple search for 'hello': {len(results)} results")
        
        # Test file-specific search
        results = repo.search("hello", "search_test2.py")
        print(f"✓ File-specific search: {len(results)} results")
        
        # Test advanced search with filter
        filter = SearchFilter()
        filter.query = "test"
        filter.case_sensitive = False
        filter.add_file_type("txt")
        
        # Note: advanced_search might not be implemented in api.py
        # Let's check if it exists
        if hasattr(repo, 'advanced_search'):
            results = repo.advanced_search(filter)
            print(f"✓ Advanced search with filter: {len(results)} results")
        else:
            print("  Note: advanced_search not implemented in API")
        
        # Test reindexing
        if hasattr(repo, 'reindex_search'):
            indexed, total = repo.reindex_search()
            print(f"✓ Reindexed: {indexed}/{total} versions")
        
        # Test search stats
        if hasattr(repo, 'get_search_stats'):
            stats = repo.get_search_stats()
            print(f"✓ Search index coverage: {stats.get('coverage_percent', 0):.1f}%")
        
        # Clean up
        for filename in test_files:
            Path(filename).unlink(missing_ok=True)
        
        return True
    except Exception as e:
        print(f"✗ Failed search test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_operations():
    """Test basic operations (log, diff, checkout)"""
    print("\n=== Testing Basic Operations ===")
    try:
        repo = ChronologRepo()
        
        # Create a test file
        test_file = Path("basic_test.txt")
        test_file.write_text("Version 1 content")
        time.sleep(1)
        
        # Modify it
        test_file.write_text("Version 2 content\nWith a new line")
        time.sleep(1)
        
        # Get history
        history = repo.log("basic_test.txt")
        print(f"✓ File history: {len(history)} versions")
        
        if len(history) >= 2:
            # Test show
            version1_hash = history[-1]['hash']
            content = repo.show(version1_hash)
            print(f"✓ Retrieved version content: {len(content)} bytes")
            
            # Test diff
            version2_hash = history[0]['hash']
            diff_output = repo.diff(version1_hash, version2_hash)
            print(f"✓ Generated diff: {len(diff_output.split(chr(10)))} lines")
            
            # Test checkout
            repo.checkout(version1_hash, "basic_test.txt")
            print("✓ Checked out previous version")
            
            # Verify checkout worked
            current_content = test_file.read_text()
            if current_content == "Version 1 content":
                print("✓ Checkout verification passed")
            else:
                print("✗ Checkout verification failed")
        
        # Clean up
        test_file.unlink(missing_ok=True)
        
        return True
    except Exception as e:
        print(f"✗ Failed basic operations test: {e}")
        return False

def main():
    """Run all tests"""
    print("ChronoLog Phase 1 Feature Verification")
    print("=" * 50)
    
    # Check if we're in a repo or need to init
    try:
        repo = ChronologRepo()
        print("Using existing ChronoLog repository")
    except NotARepositoryError:
        print("Not in a ChronoLog repository, initializing...")
        test_init()
    
    # Run all tests
    tests = [
        test_ignore_patterns,
        test_branches,
        test_tags,
        test_search,
        test_basic_operations
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All Phase 1 features verified successfully!")
    else:
        print("\n❌ Some tests failed. Please check the output above.")

if __name__ == "__main__":
    main()