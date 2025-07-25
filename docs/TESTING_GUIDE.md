# ChronoLog Testing Guide

Comprehensive guide for testing ChronoLog functionality across all phases and components.

## Table of Contents

1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Running Tests](#running-tests)
4. [Test Suites](#test-suites)
5. [Writing Tests](#writing-tests)
6. [Continuous Integration](#continuous-integration)
7. [Performance Testing](#performance-testing)
8. [Troubleshooting](#troubleshooting)

## Overview

ChronoLog includes comprehensive test coverage across all phases:

- **Phase 1-3**: Core version control functionality
- **Phase 4**: Analytics, optimization, metrics, hooks
- **Phase 5**: User management, merge engine, web API
- **Integration**: End-to-end workflow testing
- **Performance**: Load and stress testing

### Test Statistics

- **Total Test Files**: 9
- **Total Test Cases**: 200+
- **Coverage Areas**: All major components
- **Test Types**: Unit, Integration, End-to-End, API

## Test Architecture

### Test Structure

```
tests/
├── test_analytics.py          # Analytics component tests
├── test_optimization.py       # Storage optimization tests
├── test_users.py              # User management tests
├── test_merge.py              # Merge engine tests
├── test_web_api.py            # Web API integration tests
├── fixtures/                  # Test data and fixtures
├── helpers/                   # Test utility functions
└── conftest.py                # Test configuration
```

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Component interaction testing
3. **End-to-End Tests**: Complete workflow testing
4. **API Tests**: REST and GraphQL endpoint testing
5. **Performance Tests**: Load and stress testing

## Running Tests

### Master Test Runner

Run all tests with the comprehensive test runner:

```bash
# Run all test suites
python run_all_tests.py

# Run with verbose output
python run_all_tests.py --verbose

# Run specific test categories
python run_all_tests.py --category unit
python run_all_tests.py --category integration
```

### Individual Test Suites

#### Core Feature Tests

```bash
# Phase 1 features (basic version control)
python test_phase1_features.py

# Phase 2-3 features (advanced version control)
python test_phase2_phase3_features.py

# Phase 4-5 features (analytics, users, merge)
python test_phase4_phase5_features.py
```

#### Component-Specific Tests

```bash
# Analytics and metrics
python tests/test_analytics.py

# Storage optimization
python tests/test_optimization.py

# User management and authentication
python tests/test_users.py

# Merge engine and conflict resolution
python tests/test_merge.py

# Web API endpoints
python tests/test_web_api.py
```

#### Using unittest directly

```bash
# Run specific test class
python -m unittest tests.test_analytics.TestPerformanceAnalytics

# Run specific test method
python -m unittest tests.test_users.TestUserManager.test_user_creation

# Run with verbose output
python -m unittest tests.test_web_api -v

# Discover and run all tests
python -m unittest discover tests/
```

### Test Configuration

#### Environment Variables

```bash
# Test environment
export CHRONOLOG_TEST_ENV=true
export CHRONOLOG_TEST_DB_PATH=/tmp/chronolog_test.db
export CHRONOLOG_LOG_LEVEL=DEBUG

# Web API testing
export CHRONOLOG_TEST_PORT=5001
export CHRONOLOG_TEST_HOST=127.0.0.1

# Performance testing
export CHRONOLOG_PERF_TEST_SIZE=1000
export CHRONOLOG_PERF_TEST_TIMEOUT=300
```

#### Test Configuration File

Create `test_config.json`:

```json
{
  "test_settings": {
    "temp_dir": "/tmp/chronolog_tests",
    "cleanup_after_test": true,
    "verbose_output": false,
    "parallel_execution": false
  },
  "database_settings": {
    "use_memory_db": true,
    "connection_timeout": 30,
    "max_connections": 10
  },
  "web_api_settings": {
    "test_port": 5001,
    "test_host": "127.0.0.1",
    "request_timeout": 30
  }
}
```

## Test Suites

### Core Version Control Tests (test_phase1_features.py)

Tests basic ChronoLog functionality:

```python
class TestPhase1Features(unittest.TestCase):
    def test_repository_initialization(self):
        """Test repository creation and setup"""
        
    def test_file_versioning(self):
        """Test automatic file versioning"""
        
    def test_version_retrieval(self):
        """Test version content retrieval"""
        
    def test_diff_generation(self):
        """Test diff between versions"""
        
    def test_file_checkout(self):
        """Test reverting to previous versions"""
```

Key test areas:
- Repository initialization and configuration
- Automatic file versioning via daemon
- Version storage and retrieval
- Diff generation and formatting
- File checkout and restoration
- Hash generation and validation

### Advanced Features Tests (test_phase2_phase3_features.py)

Tests advanced version control features:

```python
class TestPhase2Phase3Features(unittest.TestCase):
    def test_daemon_management(self):
        """Test background daemon operations"""
        
    def test_version_annotations(self):
        """Test version annotation system"""
        
    def test_bulk_operations(self):
        """Test batch version operations"""
        
    def test_search_functionality(self):
        """Test content and metadata search"""
```

Key test areas:
- Daemon lifecycle management
- File watching and monitoring
- Version annotations and metadata
- Bulk version operations
- Search and query functionality
- Performance optimizations

### Analytics Tests (tests/test_analytics.py)

Tests performance analytics and metrics:

```python
class TestPerformanceAnalytics(unittest.TestCase):
    def test_repository_statistics(self):
        """Test repository stats collection"""
        
    def test_performance_metrics(self):
        """Test performance metric calculation"""
        
    def test_visualization_generation(self):
        """Test chart and graph generation"""

class TestMetricsCollector(unittest.TestCase):
    def test_code_metrics(self):
        """Test code complexity analysis"""
        
    def test_developer_metrics(self):
        """Test developer productivity metrics"""
```

Key test areas:
- Repository statistics calculation
- Performance metrics collection
- Visualization generation (charts, graphs)
- Code complexity analysis
- Developer productivity metrics
- Historical trend analysis

### Storage Optimization Tests (tests/test_optimization.py)

Tests storage optimization and garbage collection:

```python
class TestStorageOptimizer(unittest.TestCase):
    def test_compression_analysis(self):
        """Test compression opportunity analysis"""
        
    def test_deduplication(self):
        """Test content deduplication"""
        
    def test_storage_optimization(self):
        """Test full storage optimization"""

class TestGarbageCollector(unittest.TestCase):
    def test_orphan_detection(self):
        """Test orphaned object detection"""
        
    def test_database_integrity(self):
        """Test database integrity verification"""
        
    def test_cleanup_execution(self):
        """Test garbage collection execution"""
```

Key test areas:
- Compression algorithm testing
- Content deduplication analysis
- Storage optimization execution
- Orphaned object detection
- Database integrity verification
- Cleanup and garbage collection

### User Management Tests (tests/test_users.py)

Tests user management and authentication:

```python
class TestUserManager(unittest.TestCase):
    def test_user_creation(self):
        """Test user account creation"""
        
    def test_authentication(self):
        """Test user authentication"""
        
    def test_permission_management(self):
        """Test permission granting and revocation"""

class TestAuthenticationManager(unittest.TestCase):
    def test_token_management(self):
        """Test JWT token creation and validation"""
        
    def test_api_key_management(self):
        """Test API key generation and verification"""
        
    def test_session_management(self):
        """Test user session handling"""
```

Key test areas:
- User account creation and management
- Password hashing and verification
- JWT token generation and validation
- API key management
- Permission system testing
- Session management
- Role-based access control

### Merge Engine Tests (tests/test_merge.py)

Tests merge operations and conflict resolution:

```python
class TestMergeEngine(unittest.TestCase):
    def test_three_way_merge(self):
        """Test three-way merge algorithm"""
        
    def test_conflict_detection(self):
        """Test merge conflict detection"""
        
    def test_merge_strategies(self):
        """Test different merge strategies"""

class TestConflictResolver(unittest.TestCase):
    def test_conflict_parsing(self):
        """Test conflict marker parsing"""
        
    def test_auto_resolution(self):
        """Test automatic conflict resolution"""
        
    def test_interactive_resolution(self):
        """Test interactive conflict resolution"""
```

Key test areas:
- Three-way merge algorithm
- Conflict detection and classification
- Merge strategy implementation
- Conflict marker parsing
- Automatic resolution strategies
- Interactive resolution interface
- Merge result validation

### Web API Tests (tests/test_web_api.py)

Tests REST and GraphQL API endpoints:

```python
class TestWebAPI(unittest.TestCase):
    def test_authentication_endpoints(self):
        """Test login/logout API endpoints"""
        
    def test_version_endpoints(self):
        """Test version management endpoints"""
        
    def test_user_endpoints(self):
        """Test user management endpoints"""
        
    def test_analytics_endpoints(self):
        """Test analytics API endpoints"""

class TestGraphQLAPI(unittest.TestCase):
    def test_schema_validation(self):
        """Test GraphQL schema structure"""
        
    def test_query_execution(self):
        """Test GraphQL query execution"""
        
    def test_mutation_execution(self):
        """Test GraphQL mutation execution"""
```

Key test areas:
- REST API endpoint testing
- Authentication flow testing
- Request/response validation
- Error handling verification
- GraphQL schema validation
- Query and mutation testing
- Subscription functionality
- API rate limiting

## Writing Tests

### Test Structure Template

```python
import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronolog.component import ComponentClass

class TestComponentClass(unittest.TestCase):
    """Test cases for ComponentClass"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.component = ComponentClass(self.test_dir)
        # Add any additional setup
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_basic_functionality(self):
        """Test basic component functionality"""
        # Arrange
        input_data = "test data"
        expected_result = "expected output"
        
        # Act
        result = self.component.process(input_data)
        
        # Assert
        self.assertEqual(result, expected_result)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

if __name__ == '__main__':
    unittest.main()
```

### Test Best Practices

#### 1. Isolation and Independence

```python
def setUp(self):
    """Each test gets a fresh environment"""
    self.test_dir = Path(tempfile.mkdtemp())
    self.storage = ChronoLogStorage(self.test_dir)
    
def tearDown(self):
    """Clean up after each test"""
    shutil.rmtree(self.test_dir, ignore_errors=True)
```

#### 2. Descriptive Test Names

```python
def test_user_creation_with_valid_data_succeeds(self):
    """Test that user creation succeeds with valid input data"""
    
def test_authentication_fails_with_invalid_password(self):
    """Test that authentication fails when wrong password provided"""
```

#### 3. Arrange-Act-Assert Pattern

```python
def test_version_comparison(self):
    """Test version diff generation"""
    # Arrange
    content_a = "original content"
    content_b = "modified content"
    
    # Act
    diff = self.storage.generate_diff(content_a, content_b)
    
    # Assert
    self.assertIn("original content", diff)
    self.assertIn("modified content", diff)
    self.assertIn("-", diff)  # Deletion marker
    self.assertIn("+", diff)  # Addition marker
```

#### 4. Edge Case Testing

```python
def test_empty_file_handling(self):
    """Test handling of empty files"""
    empty_content = ""
    result = self.component.process(empty_content)
    self.assertIsNotNone(result)
    
def test_large_file_handling(self):
    """Test handling of large files"""
    large_content = "x" * 1024 * 1024  # 1MB
    result = self.component.process(large_content)
    self.assertTrue(result.success)
    
def test_unicode_content_handling(self):
    """Test handling of Unicode content"""
    unicode_content = "Hello 世界 🌍"
    result = self.component.process(unicode_content)
    self.assertIn("世界", result.content)
```

#### 5. Error Condition Testing

```python
def test_invalid_input_raises_exception(self):
    """Test that invalid input raises appropriate exception"""
    with self.assertRaises(ValueError):
        self.component.process(None)
        
def test_permission_denied_handling(self):
    """Test handling of permission denied errors"""
    # Create read-only file
    readonly_file = self.test_dir / "readonly.txt"
    readonly_file.touch()
    readonly_file.chmod(0o444)
    
    with self.assertRaises(PermissionError):
        self.component.modify_file(readonly_file)
```

### Mock and Patch Usage

```python
from unittest.mock import Mock, patch, MagicMock

class TestWithMocks(unittest.TestCase):
    
    @patch('chronolog.daemon.watchdog.Observer')
    def test_daemon_with_mock_observer(self, mock_observer):
        """Test daemon functionality with mocked file observer"""
        mock_observer_instance = Mock()
        mock_observer.return_value = mock_observer_instance
        
        daemon = FileDaemon(self.test_dir)
        daemon.start()
        
        mock_observer.assert_called_once()
        mock_observer_instance.start.assert_called_once()
    
    def test_with_mock_database(self):
        """Test with mocked database connection"""
        with patch('chronolog.storage.sqlite3.connect') as mock_connect:
            mock_connection = MagicMock()
            mock_connect.return_value = mock_connection
            
            storage = ChronoLogStorage(self.test_dir)
            storage.store_version("test content")
            
            mock_connection.execute.assert_called()
```

## Continuous Integration

### GitHub Actions Configuration

Create `.github/workflows/test.yml`:

```yaml
name: ChronoLog Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .
        pip install -r requirements-dev.txt
    
    - name: Run core tests
      run: |
        python test_phase1_features.py
        python test_phase2_phase3_features.py
        python test_phase4_phase5_features.py
    
    - name: Run component tests
      run: |
        python -m unittest discover tests/
    
    - name: Run master test suite
      run: |
        python run_all_tests.py
    
    - name: Generate coverage report
      run: |
        pip install coverage
        coverage run run_all_tests.py
        coverage report
        coverage xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
-   repo: local
    hooks:
    -   id: chronolog-tests
        name: ChronoLog Tests
        entry: python run_all_tests.py
        language: system
        always_run: true
        pass_filenames: false
```

## Performance Testing

### Load Testing

```python
import time
import concurrent.futures
from pathlib import Path

class TestPerformance(unittest.TestCase):
    
    def test_concurrent_version_creation(self):
        """Test performance under concurrent load"""
        def create_versions(file_index):
            test_file = self.test_dir / f"test_{file_index}.txt"
            results = []
            
            for i in range(100):
                content = f"Content {i} for file {file_index}"
                test_file.write_text(content)
                
                start_time = time.time()
                # Wait for version creation
                time.sleep(0.1)
                end_time = time.time()
                
                results.append(end_time - start_time)
            
            return results
        
        # Test with multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_versions, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # Verify performance
        all_times = [time for result in results for time in result]
        avg_time = sum(all_times) / len(all_times)
        max_time = max(all_times)
        
        self.assertLess(avg_time, 0.5, "Average version creation too slow")
        self.assertLess(max_time, 2.0, "Maximum version creation too slow")
    
    def test_large_repository_performance(self):
        """Test performance with large repository"""
        # Create large repository
        for i in range(1000):
            test_file = self.test_dir / f"file_{i}.txt"
            test_file.write_text(f"Content for file {i}" * 100)
        
        # Test operations
        start_time = time.time()
        stats = self.storage.get_repository_stats()
        stats_time = time.time() - start_time
        
        start_time = time.time()
        versions = self.storage.list_versions(limit=100)
        list_time = time.time() - start_time
        
        # Assertions
        self.assertLess(stats_time, 1.0, "Stats collection too slow")
        self.assertLess(list_time, 0.5, "Version listing too slow")
        self.assertGreaterEqual(len(versions), 100)
```

### Memory Usage Testing

```python
import psutil
import os

class TestMemoryUsage(unittest.TestCase):
    
    def test_memory_usage_during_operations(self):
        """Test memory usage doesn't grow excessively"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        for i in range(100):
            large_content = "x" * (1024 * 1024)  # 1MB
            test_file = self.test_dir / f"large_{i}.txt"
            test_file.write_text(large_content)
            
            # Check memory periodically
            if i % 10 == 0:
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be reasonable
                self.assertLess(memory_growth, 100 * 1024 * 1024,  # 100MB
                              f"Memory growth too large: {memory_growth / 1024 / 1024:.1f}MB")
```

## Troubleshooting

### Common Test Issues

#### 1. Temporary Directory Cleanup

```bash
# Issue: Tests fail due to leftover files
# Solution: Ensure proper cleanup in tearDown

def tearDown(self):
    """Clean up test environment"""
    try:
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
    except Exception as e:
        print(f"Cleanup warning: {e}")
```

#### 2. Database Lock Issues

```bash
# Issue: Database locked errors in tests
# Solution: Use separate test databases

def setUp(self):
    """Use unique database for each test"""
    self.test_dir = Path(tempfile.mkdtemp(prefix="chronolog_test_"))
    self.storage = ChronoLogStorage(self.test_dir)
```

#### 3. Port Conflicts in Web Tests

```bash
# Issue: Web server port already in use
# Solution: Use dynamic port allocation

def setUp(self):
    """Find available port for web server"""
    import socket
    
    sock = socket.socket()
    sock.bind(('', 0))
    self.test_port = sock.getsockname()[1]
    sock.close()
    
    self.app = create_app(self.test_dir, port=self.test_port)
```

#### 4. Timing Issues in Async Tests

```bash
# Issue: Race conditions in daemon tests
# Solution: Add proper synchronization

def test_daemon_file_watching(self):
    """Test file watching with proper synchronization"""
    self.daemon.start()
    
    # Wait for daemon to be ready
    timeout = 5
    while not self.daemon.is_running and timeout > 0:
        time.sleep(0.1)
        timeout -= 0.1
    
    self.assertTrue(self.daemon.is_running, "Daemon failed to start")
```

### Test Debugging

#### Enable Debug Logging

```python
import logging

def setUp(self):
    """Enable debug logging for tests"""
    logging.basicConfig(level=logging.DEBUG)
    self.logger = logging.getLogger(__name__)
```

#### Use Test Fixtures

```python
def create_test_repository(self, file_count=10):
    """Create repository with test data"""
    for i in range(file_count):
        test_file = self.test_dir / f"test_{i}.txt"
        test_file.write_text(f"Initial content {i}")
        
        # Create some versions
        for j in range(3):
            test_file.write_text(f"Modified content {i}.{j}")
            time.sleep(0.1)  # Ensure different timestamps
    
    return self.test_dir
```

#### Profile Test Performance

```python
import cProfile
import pstats

def test_with_profiling(self):
    """Test with performance profiling"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run test code
    self.component.expensive_operation()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

### Test Data Management

#### Create Realistic Test Data

```python
def create_realistic_test_data(self):
    """Create realistic test repository data"""
    # Simulate real development workflow
    files = [
        ("src/main.py", "python"),
        ("src/utils.py", "python"),
        ("README.md", "markdown"),
        ("package.json", "json"),
        ("style.css", "css")
    ]
    
    for file_path, file_type in files:
        full_path = self.test_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create initial version
        content = self.generate_content(file_type)
        full_path.write_text(content)
        
        # Create evolution over time
        for version in range(5):
            modified_content = self.modify_content(content, version)
            full_path.write_text(modified_content)
            time.sleep(0.1)
```

For additional testing resources and examples, see the individual test files and the master test runner documentation.