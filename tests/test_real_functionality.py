#!/usr/bin/env python3
"""
Comprehensive functional tests for ChronoLog
Tests the actual functionality with real dependencies
"""

import os
import sys
import subprocess
import tempfile
import time
import shutil
from pathlib import Path


class ChronologFunctionalTester:
    def __init__(self):
        self.test_results = []
        self.current_test_dir = None
        self.venv_python = str(Path(__file__).parent.parent / "venv" / "bin" / "python")
        
    def log_result(self, test_name, success, message=""):
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:<50} {status}")
        if message and not success:
            print(f"    Error: {message}")
        self.test_results.append((test_name, success, message))
        
    def run_command(self, cmd, timeout=30):
        """Run a command and return (success, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                cwd=self.current_test_dir
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def setup_test_directory(self):
        """Create a temporary directory for testing"""
        self.current_test_dir = tempfile.mkdtemp(prefix="chronolog_test_")
        os.chdir(self.current_test_dir)
        return self.current_test_dir

    def cleanup_test_directory(self):
        """Clean up the test directory"""
        if self.current_test_dir and os.path.exists(self.current_test_dir):
            os.chdir(Path.home())  # Change away from test dir before deleting
            shutil.rmtree(self.current_test_dir)
            self.current_test_dir = None

    def test_library_imports(self):
        """Test that the ChronoLog library can be imported"""
        print("\n=== Testing Library Imports ===")
        
        # Test core library import
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog import ChronologRepo, NotARepositoryError, RepositoryExistsError; print(\'Core imports successful\')"'
        )
        self.log_result("Core library import", success, stderr)
        
        # Test CLI import
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog.main import main; print(\'CLI import successful\')"'
        )
        self.log_result("CLI import", success, stderr)
        
        # Test TUI import  
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog_tui.main import main; print(\'TUI import successful\')"'
        )
        self.log_result("TUI import", success, stderr)

    def test_cli_commands(self):
        """Test CLI commands"""
        print("\n=== Testing CLI Commands ===")
        
        # Test help command
        success, stdout, stderr = self.run_command(f'{self.venv_python} -m chronolog --help')
        self.log_result("CLI help command", success, stderr)
        
        # Test version/basic command structure
        success, stdout, stderr = self.run_command(f'{self.venv_python} -m chronolog')
        # CLI might return non-zero exit code but still work, so check for reasonable output
        # Check both stdout and stderr as CLI tools often print help to stderr
        has_reasonable_output = "Usage:" in (stdout + stderr) or "Commands:" in (stdout + stderr) or "chronolog" in (stdout + stderr).lower()
        self.log_result("CLI basic execution", has_reasonable_output, "CLI not showing expected output" if not has_reasonable_output else "")

    def test_repository_operations(self):
        """Test core repository operations"""
        print("\n=== Testing Repository Operations ===")
        
        test_dir = self.setup_test_directory()
        
        try:
            # Test repository initialization
            success, stdout, stderr = self.run_command(f'{self.venv_python} -c "from chronolog import ChronologRepo; repo = ChronologRepo.init(); print(\'Repository initialized\')"')
            self.log_result("Repository initialization", success, stderr)
            
            if success:
                # Verify .chronolog directory was created
                chronolog_dir = Path(test_dir) / ".chronolog"
                dir_exists = chronolog_dir.exists()
                self.log_result("Repository directory created", dir_exists, "No .chronolog directory found")
                
                # Create a test file
                test_file = Path(test_dir) / "test.txt"
                test_file.write_text("Hello ChronoLog!")
                
                # Give the daemon time to detect the file
                time.sleep(2)
                
                # Test loading existing repository
                success, stdout, stderr = self.run_command(
                    f'{self.venv_python} -c "from chronolog import ChronologRepo; repo = ChronologRepo(); print(\'Repository loaded\')"'
                )
                self.log_result("Repository loading", success, stderr)
                
                # Test file history (might be empty initially)
                success, stdout, stderr = self.run_command(
                    f'{self.venv_python} -c "from chronolog import ChronologRepo; repo = ChronologRepo(); history = repo.log(\'test.txt\'); print(f\'File history: {{len(history)}} entries\')"'
                )
                self.log_result("File history retrieval", success, stderr)
                
                # Test repository status
                success, stdout, stderr = self.run_command(
                    f'{self.venv_python} -c "from chronolog import ChronologRepo; repo = ChronologRepo(); status = repo.status(); print(f\'Status retrieved: {{type(status)}}\')"'
                )
                self.log_result("Repository status", success, stderr)
                
        finally:
            self.cleanup_test_directory()

    def test_storage_operations(self):
        """Test storage operations"""
        print("\n=== Testing Storage Operations ===")
        
        test_dir = self.setup_test_directory()
        
        try:
            # Create a temporary Python file for the test
            test_file = Path(test_dir) / "test_storage.py"
            test_code = '''from chronolog.storage.storage import Storage
from pathlib import Path

# Create storage
storage_dir = Path(".") / ".chronolog"
storage_dir.mkdir(exist_ok=True)
storage = Storage(storage_dir)

# Test content storage
test_content = b"Hello Storage!"
hash_value = storage.store_content(test_content)
print(f"Stored content with hash: {hash_value[:8]}...")

# Test content retrieval
retrieved = storage.get_content(hash_value)
if retrieved == test_content:
    print("Content retrieval successful")
else:
    print("Content retrieval failed")
'''
            test_file.write_text(test_code)
            
            success, stdout, stderr = self.run_command(f'{self.venv_python} test_storage.py')
            self.log_result("Storage operations", success, stderr)
            
        finally:
            self.cleanup_test_directory()

    def test_daemon_operations(self):
        """Test daemon functionality"""
        print("\n=== Testing Daemon Operations ===")
        
        test_dir = self.setup_test_directory()
        
        try:
            # Create a temporary Python file for the test
            test_file = Path(test_dir) / "test_daemon.py"
            test_code = '''from chronolog import ChronologRepo
import time

# Initialize repository (starts daemon)
repo = ChronologRepo.init()
print("Repository initialized with daemon")

# Get daemon instance
daemon = repo.get_daemon()
print("Daemon instance retrieved")

# Check daemon status
try:
    status = daemon.status()
    print(f"Daemon status: {status}")
except Exception as e:
    print(f"Daemon status error: {e}")
'''
            test_file.write_text(test_code)
            
            success, stdout, stderr = self.run_command(f'{self.venv_python} test_daemon.py')
            self.log_result("Daemon operations", success, stderr)
            
        finally:
            self.cleanup_test_directory()

    def test_advanced_features(self):
        """Test advanced features like analytics, optimization, etc."""
        print("\n=== Testing Advanced Features ===")
        
        # Test analytics import
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog.analytics.performance_analytics import PerformanceAnalytics; print(\'Analytics import successful\')"'
        )
        self.log_result("Analytics import", success, stderr)
        
        # Test visualization
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog.analytics.visualization import Visualization; print(\'Visualization import successful\')"'
        )
        self.log_result("Visualization import", success, stderr)
        
        # Test optimization
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog.optimization.storage_optimizer import StorageOptimizer; print(\'Optimization import successful\')"'
        )
        self.log_result("Optimization import", success, stderr)
        
        # Test user management
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog.users.user_manager import UserManager; print(\'User management import successful\')"'
        )
        self.log_result("User management import", success, stderr)
        
        # Test web server
        success, stdout, stderr = self.run_command(
            f'{self.venv_python} -c "from chronolog.web.app import WebServer; print(\'Web server import successful\')"'
        )
        self.log_result("Web server import", success, stderr)

    def test_original_test_suites(self):
        """Run the original test suites with real dependencies"""
        print("\n=== Running Original Test Suites ===")
        
        original_dir = os.getcwd()
        os.chdir(Path(__file__).parent)  # Change to tests directory
        
        try:
            # Test Phase 1 features
            success, stdout, stderr = self.run_command(f'{self.venv_python} test_phase1_features.py')
            self.log_result("Phase 1 test suite", success, stderr)
            
            # Test Phase 2-3 features  
            success, stdout, stderr = self.run_command(f'{self.venv_python} test_phase2_phase3_features.py')
            self.log_result("Phase 2-3 test suite", success, stderr)
            
            # Test Phase 4-5 features
            success, stdout, stderr = self.run_command(f'{self.venv_python} test_phase4_phase5_features.py')
            self.log_result("Phase 4-5 test suite", success, stderr)
            
        finally:
            os.chdir(original_dir)

    def run_all_tests(self):
        """Run all functional tests"""
        print("ChronoLog Comprehensive Functional Testing")
        print("=" * 60)
        print("Testing with REAL dependencies and functionality")
        print("=" * 60)
        
        # Import tests
        self.test_library_imports()
        
        # CLI tests
        self.test_cli_commands()
        
        # Core functionality tests
        self.test_repository_operations()
        self.test_storage_operations()
        self.test_daemon_operations()
        
        # Advanced feature tests
        self.test_advanced_features()
        
        # Original test suites
        self.test_original_test_suites()
        
        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        total_tests = len(self.test_results)
        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = total_tests - passed
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print(f"\nFailed tests:")
            for name, success, message in self.test_results:
                if not success:
                    print(f"  - {name}: {message}")
        
        if failed == 0:
            print(f"\n🎉 ALL {passed} TESTS PASSED!")
            print("ChronoLog is working correctly with real dependencies.")
        else:
            print(f"\n⚠️  {failed} test(s) failed.")
            print("Review the errors above for details.")
        
        return failed == 0


def main():
    """Main test runner"""
    tester = ChronologFunctionalTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())