#!/usr/bin/env python3
"""
Master test runner for all ChronoLog tests
This script runs all Phase 1, 2, 3, 4, and 5 tests
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_test_file(test_file):
    """Run a single test file"""
    print(f"\n{'='*60}")
    print(f"Running {test_file.name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, str(test_file)
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Exit code: {result.returncode}")
        print(f"Duration: {duration:.2f} seconds")
        
        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")
        
        return result.returncode == 0, duration
        
    except subprocess.TimeoutExpired:
        print(f"Test {test_file.name} timed out after 5 minutes")
        return False, 300
    except Exception as e:
        print(f"Error running {test_file.name}: {e}")
        return False, 0

def main():
    """Main test runner"""
    print("ChronoLog Comprehensive Test Suite")
    print("="*60)
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # List all test files
    test_files = [
        project_root / "test_phase1_features.py",
        project_root / "test_phase2_phase3_features.py", 
        project_root / "test_phase4_phase5_features.py",
        project_root / "tests" / "test_analytics.py",
        project_root / "tests" / "test_optimization.py",
        project_root / "tests" / "test_users.py",
        project_root / "tests" / "test_merge.py",
        project_root / "tests" / "test_web_api.py"
    ]
    
    # Filter existing test files
    existing_test_files = [f for f in test_files if f.exists()]
    missing_test_files = [f for f in test_files if not f.exists()]
    
    if missing_test_files:
        print("Missing test files:")
        for f in missing_test_files:
            print(f"  - {f}")
        print()
    
    print(f"Found {len(existing_test_files)} test files to run")
    print()
    
    # Track results
    results = []
    total_duration = 0
    
    # Run each test file
    for test_file in existing_test_files:
        success, duration = run_test_file(test_file)
        results.append((test_file.name, success, duration))
        total_duration += duration
        
        # Small delay between tests
        time.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print(f"Total test files: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total duration: {total_duration:.2f} seconds")
    print()
    
    # Detailed results
    print("Detailed Results:")
    print("-" * 60)
    for test_name, success, duration in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:<35} {status:<8} {duration:>6.2f}s")
    
    if failed == 0:
        print(f"\n🎉 ALL {passed} TEST FILES PASSED!")
        print("ChronoLog is working correctly across all phases.")
    else:
        print(f"\n⚠️  {failed} test file(s) failed.")
        print("Please review the output above for details.")
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()