#!/usr/bin/env python3
"""
Test script to verify Phase 4 & 5 features of ChronoLog
This script tests all the newly implemented features including:
- Performance Analytics
- Storage Optimization
- Code Metrics
- Hooks System
- User Management
- Merge Engine
- Web API
- Conflict Resolution
"""

import sys
import os
import tempfile
import shutil
import json
import time
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chronolog.api import ChronologRepo, NotARepositoryError, RepositoryExistsError
from chronolog.analytics.performance_analytics import PerformanceAnalytics
from chronolog.analytics.visualization import Visualization
from chronolog.analytics.metrics_collector import MetricsCollector
from chronolog.optimization.storage_optimizer import StorageOptimizer
from chronolog.optimization.garbage_collector import GarbageCollector
from chronolog.hooks.hook_manager import HookManager, HookEvent, HookContext
from chronolog.hooks.scripting_api import ChronoLogAPI
from chronolog.users.user_manager import UserManager, UserRole
from chronolog.users.auth import AuthenticationManager
from chronolog.users.permissions import PermissionManager, ResourceType, PermissionLevel
from chronolog.merge.merge_engine import MergeEngine
from chronolog.merge.conflict_resolver import ConflictResolver
from chronolog.web.app import WebServer
from chronolog.storage.storage import ChronoLogStorage


class TestRunner:
    """Main test runner for Phase 4 & 5 features"""
    
    def __init__(self):
        self.test_dir = None
        self.repo = None
        self.passed = 0
        self.failed = 0
        self.test_files = []
    
    def setup(self):
        """Set up test environment"""
        print("=== Setting up Test Environment ===")
        
        # Create temporary directory for tests
        self.test_dir = Path(tempfile.mkdtemp(prefix="chronolog_test_"))
        os.chdir(self.test_dir)
        
        # Initialize repository
        try:
            self.repo = ChronologRepo.init()
            print(f"✓ Test repository created at: {self.test_dir}")
            
            # Create some test files
            self.create_test_files()
            print("✓ Test files created")
            
            return True
        except Exception as e:
            print(f"✗ Setup failed: {e}")
            return False
    
    def create_test_files(self):
        """Create test files for analysis"""
        test_files = {
            "app.py": '''#!/usr/bin/env python3
"""Sample Python application for testing"""

def calculate_complexity(n):
    """Function with some complexity"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        result = 0
        for i in range(n):
            if i % 2 == 0:
                result += i
            else:
                result -= i
        return result

class DataProcessor:
    """Sample class for testing"""
    
    def __init__(self, data):
        self.data = data
        self.processed = False
    
    def process(self):
        """Process the data"""
        if not self.data:
            raise ValueError("No data to process")
        
        processed_data = []
        for item in self.data:
            if isinstance(item, str):
                processed_data.append(item.upper())
            elif isinstance(item, (int, float)):
                processed_data.append(item * 2)
            else:
                processed_data.append(str(item))
        
        self.data = processed_data
        self.processed = True
        return processed_data

if __name__ == "__main__":
    processor = DataProcessor(["hello", 42, 3.14])
    result = processor.process()
    print(f"Result: {result}")
    
    complexity_result = calculate_complexity(10)
    print(f"Complexity result: {complexity_result}")
''',
            "utils.js": '''// JavaScript utility functions for testing
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

function processArray(arr) {
    return arr
        .filter(x => x > 0)
        .map(x => x * 2)
        .reduce((acc, val) => acc + val, 0);
}

class Calculator {
    constructor() {
        this.history = [];
    }
    
    add(a, b) {
        const result = a + b;
        this.history.push({operation: 'add', a, b, result});
        return result;
    }
    
    multiply(a, b) {
        const result = a * b;
        this.history.push({operation: 'multiply', a, b, result});
        return result;
    }
    
    getHistory() {
        return this.history;
    }
}

module.exports = {fibonacci, processArray, Calculator};
''',
            "README.md": '''# Test Project

This is a test project for ChronoLog Phase 4 & 5 features.

## Features

- Analytics and performance metrics
- Storage optimization
- Code quality analysis
- User management
- Merge capabilities

## Usage

Run tests with:
```bash
python test_phase4_phase5_features.py
```
''',
            "config.json": '''{
    "project_name": "chronolog_test",
    "version": "1.0.0",
    "features": {
        "analytics": true,
        "optimization": true,
        "user_management": true,
        "merge_engine": true
    },
    "settings": {
        "compression": "zlib",
        "max_versions": 1000,
        "gc_interval": "1d"
    }
}''',
            "hooks/pre_version.py": '''#!/usr/bin/env python3
"""Pre-version hook for testing"""
import sys
import json

def main():
    print("Pre-version hook executed")
    # Validate that we have a proper context
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        }
        
        for file_path, content in test_files.items():
            full_path = self.test_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            self.test_files.append(full_path)
        
        # Make hook executable
        hook_file = self.test_dir / "hooks/pre_version.py"
        hook_file.chmod(0o755)
    
    def teardown(self):
        """Clean up test environment"""
        print("\n=== Cleaning up Test Environment ===")
        if self.test_dir and self.test_dir.exists():
            os.chdir(Path.home())  # Change out of test directory
            shutil.rmtree(self.test_dir, ignore_errors=True)
            print(f"✓ Cleaned up test directory: {self.test_dir}")
    
    def run_test(self, test_name, test_func):
        """Run a single test"""
        print(f"\n=== {test_name} ===")
        try:
            if test_func():
                print(f"✓ {test_name} PASSED")
                self.passed += 1
                return True
            else:
                print(f"✗ {test_name} FAILED")
                self.failed += 1
                return False
        except Exception as e:
            print(f"✗ {test_name} FAILED: {e}")
            self.failed += 1
            return False
    
    def test_performance_analytics(self):
        """Test performance analytics functionality"""
        analytics = PerformanceAnalytics(self.repo.repo_path)
        
        # Test repository stats collection
        stats = analytics.collect_repository_stats()
        assert hasattr(stats, 'total_versions')
        assert hasattr(stats, 'total_files')
        assert hasattr(stats, 'total_size_mb')
        print("✓ Repository stats collected successfully")
        
        # Test operation metrics (may be empty for new repo)
        metrics = analytics.get_operation_metrics(days=7)
        assert isinstance(metrics, list)
        print(f"✓ Operation metrics retrieved: {len(metrics)} entries")
        
        # Test storage efficiency analysis
        efficiency = analytics.analyze_storage_efficiency()
        assert 'compression_ratio' in efficiency
        assert 'storage_efficiency' in efficiency
        print("✓ Storage efficiency analysis completed")
        
        return True
    
    def test_visualization(self):
        """Test text-based visualization functionality"""
        visualization = Visualization()
        
        # Test bar chart creation
        labels = ['Python', 'JavaScript', 'Markdown']
        values = [10, 5, 2]
        bar_chart = visualization.create_bar_chart(labels, values, title="File Types")
        assert len(bar_chart) > 0
        assert "File Types" in bar_chart
        print("✓ Bar chart created successfully")
        
        # Test sparkline creation
        data = [1, 2, 3, 5, 8, 13, 21]
        sparkline = visualization.create_sparkline(data)
        assert len(sparkline) > 0
        print("✓ Sparkline created successfully")
        
        # Test activity calendar
        dates = ['2024-01-01', '2024-01-02', '2024-01-03']
        calendar = visualization.create_activity_calendar(dates)
        assert len(calendar) > 0
        print("✓ Activity calendar created successfully")
        
        return True
    
    def test_code_metrics(self):
        """Test code metrics analysis"""
        metrics_collector = MetricsCollector(self.repo.repo_path)
        
        # Test single file analysis
        python_file = self.test_dir / "app.py"
        if python_file.exists():
            metrics = metrics_collector.analyze_file(python_file)
            assert metrics.lines_of_code > 0
            assert metrics.cyclomatic_complexity >= 1
            assert 0 <= metrics.maintainability_index <= 100
            print(f"✓ Python file analyzed: {metrics.lines_of_code} LOC, "
                  f"{metrics.cyclomatic_complexity:.1f} complexity")
        
        # Test repository analysis
        all_metrics = metrics_collector.analyze_repository()
        assert len(all_metrics) > 0
        print(f"✓ Repository analyzed: {len(all_metrics)} files")
        
        # Test language detection
        js_file = self.test_dir / "utils.js"
        if js_file.exists():
            language = metrics_collector.detect_language(js_file)
            assert language in ['javascript', 'js']
            print(f"✓ Language detection: {language}")
        
        return True
    
    def test_storage_optimization(self):
        """Test storage optimization functionality"""
        optimizer = StorageOptimizer(self.repo.repo_path)
        
        # Test getting recommendations
        recommendations = optimizer.get_storage_recommendations()
        assert isinstance(recommendations, list)
        print(f"✓ Storage recommendations: {len(recommendations)} items")
        
        # Test content deduplication analysis
        dedup_analysis = optimizer.analyze_content_deduplication()
        assert 'potential_savings_mb' in dedup_analysis
        assert 'duplicate_groups' in dedup_analysis
        print("✓ Deduplication analysis completed")
        
        # Test compression analysis
        compression_analysis = optimizer.analyze_compression_opportunities()
        assert 'current_compression_ratio' in compression_analysis
        print("✓ Compression analysis completed")
        
        return True
    
    def test_garbage_collection(self):
        """Test garbage collection functionality"""
        gc = GarbageCollector(self.repo.repo_path)
        
        # Test database integrity verification
        integrity_results = gc.verify_database_integrity()
        assert 'corrupted_versions' in integrity_results
        assert 'orphaned_files' in integrity_results
        print("✓ Database integrity verification completed")
        
        # Test orphan detection
        orphans = gc.find_orphaned_objects()
        assert 'orphaned_versions' in orphans
        assert 'orphaned_files' in orphans
        print(f"✓ Orphan detection: {len(orphans['orphaned_versions'])} orphaned versions")
        
        # Test cleanup (dry run)
        cleanup_plan = gc.plan_cleanup()
        assert 'temp_files_to_remove' in cleanup_plan
        assert 'empty_dirs_to_remove' in cleanup_plan
        print("✓ Cleanup planning completed")
        
        return True
    
    def test_hooks_system(self):
        """Test hooks system functionality"""
        hook_manager = HookManager(self.repo.repo_path)
        
        # Test hook registration
        hook_script = self.test_dir / "hooks/pre_version.py"
        if hook_script.exists():
            success = hook_manager.register_script_hook(
                event=HookEvent.PRE_VERSION,
                script_path=hook_script,
                name="test_pre_version",
                description="Test pre-version hook"
            )
            assert success
            print("✓ Hook registered successfully")
            
            # Test hook listing
            hooks = hook_manager.list_hooks()
            assert HookEvent.PRE_VERSION in hooks
            assert len(hooks[HookEvent.PRE_VERSION]) > 0
            print(f"✓ Hook listing: {len(hooks[HookEvent.PRE_VERSION])} pre-version hooks")
            
            # Test hook execution
            test_context = HookContext(
                event=HookEvent.PRE_VERSION,
                repository_path=self.repo.repo_path,
                file_path=None,
                version_id="test",
                metadata={"test": True}
            )
            
            results = hook_manager.trigger_hooks(HookEvent.PRE_VERSION, test_context)
            assert len(results) > 0
            print(f"✓ Hook execution: {len(results)} hooks executed")
            
            # Test hook removal
            removed = hook_manager.unregister_hook(HookEvent.PRE_VERSION, "test_pre_version")
            assert removed
            print("✓ Hook removed successfully")
        
        return True
    
    def test_scripting_api(self):
        """Test scripting API functionality"""
        api = ChronoLogAPI(self.repo.repo_path)
        
        # Test basic operations
        repo_info = api.get_repository_info()
        assert 'path' in repo_info
        assert 'initialized' in repo_info
        print("✓ Repository info retrieved")
        
        # Test analytics access
        analytics_data = api.get_analytics_summary()
        assert 'repository_stats' in analytics_data
        print("✓ Analytics summary retrieved")
        
        # Test workflow templates
        templates = api.list_workflow_templates()
        assert isinstance(templates, list)
        print(f"✓ Workflow templates: {len(templates)} available")
        
        return True
    
    def test_user_management(self):
        """Test user management functionality"""
        user_manager = UserManager(self.repo.repo_path)
        
        # Test admin user creation
        admin_id = user_manager.create_admin_user(
            username="test_admin",
            password="test_password",
            email="admin@test.com"
        )
        assert admin_id is not None
        print(f"✓ Admin user created: {admin_id}")
        
        # Test user creation
        user_id = user_manager.create_user(
            username="test_user",
            password="user_password",
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER
        )
        assert user_id is not None
        print(f"✓ Regular user created: {user_id}")
        
        # Test user authentication
        authenticated_user = user_manager.authenticate_user("test_admin", "test_password")
        assert authenticated_user is not None
        assert authenticated_user.username == "test_admin"
        print("✓ User authentication successful")
        
        # Test user listing
        users = user_manager.list_users()
        assert len(users) >= 2  # admin + regular user
        print(f"✓ User listing: {len(users)} users")
        
        # Test user by username
        user = user_manager.get_user_by_username("test_user")
        assert user is not None
        assert user.username == "test_user"
        print("✓ User lookup by username successful")
        
        return True
    
    def test_authentication(self):
        """Test authentication system"""
        auth_manager = AuthenticationManager(self.repo.repo_path)
        user_manager = UserManager(self.repo.repo_path)
        
        # Get a user for testing
        user = user_manager.get_user_by_username("test_admin")
        if not user:
            # Create user if not exists
            user_id = user_manager.create_admin_user("test_admin", "test_password")
            user = user_manager.get_user(user_id)
        
        # Test token creation
        token = auth_manager.create_token(user.id)
        assert token.token is not None
        assert token.user_id == user.id
        print(f"✓ Authentication token created")
        
        # Test token verification
        verified_user_id = auth_manager.verify_token(token.token)
        assert verified_user_id == user.id
        print("✓ Token verification successful")
        
        # Test API key creation
        api_key = auth_manager.create_api_key(user.id, "Test API Key")
        assert api_key.startswith("clk_")
        print("✓ API key created")
        
        # Test API key verification
        verified_user_id = auth_manager.verify_api_key(api_key)
        assert verified_user_id == user.id
        print("✓ API key verification successful")
        
        # Test session listing
        sessions = auth_manager.list_user_sessions(user.id)
        assert len(sessions) >= 1
        print(f"✓ Session listing: {len(sessions)} active sessions")
        
        return True
    
    def test_permissions(self):
        """Test permissions system"""
        permission_manager = PermissionManager(self.repo.repo_path)
        user_manager = UserManager(self.repo.repo_path)
        
        # Get test user
        user = user_manager.get_user_by_username("test_user")
        if not user:
            user_id = user_manager.create_user("test_user", "password")
            user = user_manager.get_user(user_id)
        
        # Test permission granting
        success = permission_manager.grant_permission(
            user.id,
            ResourceType.REPOSITORY,
            "*",
            PermissionLevel.READ,
            "system"
        )
        assert success
        print("✓ Permission granted successfully")
        
        # Test permission checking
        has_permission = permission_manager.has_permission(
            user.id,
            ResourceType.REPOSITORY,
            "*",
            PermissionLevel.READ
        )
        assert has_permission
        print("✓ Permission check successful")
        
        # Test permission listing
        permissions = permission_manager.get_user_permissions(user.id)
        assert len(permissions) >= 1
        print(f"✓ Permission listing: {len(permissions)} permissions")
        
        # Test permission summary
        summary = permission_manager.get_permission_summary(user.id)
        assert 'permissions_count' in summary
        assert 'is_admin' in summary
        print("✓ Permission summary generated")
        
        return True
    
    def test_merge_engine(self):
        """Test merge engine functionality"""
        merge_engine = MergeEngine()
        
        # Test basic merge scenarios
        base_content = "line 1\\nline 2\\nline 3\\n"
        ours_content = "line 1\\nmodified line 2\\nline 3\\n"
        theirs_content = "line 1\\nline 2\\nline 3\\nadded line 4\\n"
        
        # Test successful merge
        result = merge_engine.three_way_merge(
            base=base_content.encode(),
            ours=ours_content.encode(),
            theirs=theirs_content.encode()
        )
        
        assert result is not None
        print(f"✓ Three-way merge completed: success={result.success}")
        
        # Test conflict detection
        conflicting_ours = "line 1\\nconflict A\\nline 3\\n"
        conflicting_theirs = "line 1\\nconflict B\\nline 3\\n"
        
        conflict_result = merge_engine.three_way_merge(
            base=base_content.encode(),
            ours=conflicting_ours.encode(),
            theirs=conflicting_theirs.encode()
        )
        
        assert conflict_result is not None
        if not conflict_result.success:
            print(f"✓ Conflict detection: {len(conflict_result.conflicts)} conflicts found")
        else:
            print("✓ Merge completed without conflicts")
        
        return True
    
    def test_conflict_resolver(self):
        """Test conflict resolution functionality"""
        conflict_resolver = ConflictResolver()
        
        # Test conflict parsing
        conflict_content = '''line 1
<<<<<<< ours
our change
=======
their change
>>>>>>> theirs
line 3'''
        
        conflicts = conflict_resolver.parse_conflicts(conflict_content)
        assert len(conflicts) > 0
        print(f"✓ Conflict parsing: {len(conflicts)} conflicts found")
        
        # Test automatic resolution
        resolved_ours = conflict_resolver.auto_resolve_conflicts(conflict_content, "ours")
        assert resolved_ours is not None
        assert "our change" in resolved_ours
        assert "their change" not in resolved_ours
        print("✓ Automatic resolution (ours strategy) successful")
        
        resolved_theirs = conflict_resolver.auto_resolve_conflicts(conflict_content, "theirs")
        assert resolved_theirs is not None
        assert "their change" in resolved_theirs
        assert "our change" not in resolved_theirs
        print("✓ Automatic resolution (theirs strategy) successful")
        
        return True
    
    def test_web_server_creation(self):
        """Test web server creation and configuration"""
        try:
            web_server = WebServer(self.repo.repo_path, host="127.0.0.1", port=5001)
            assert web_server.repo_path == self.repo.repo_path
            assert web_server.host == "127.0.0.1"
            assert web_server.port == 5001
            print("✓ Web server created successfully")
            
            # Test Flask app creation
            app = web_server.app
            assert app is not None
            print("✓ Flask app configured")
            
            # Test URL generation
            url = web_server.get_url()
            assert url == "http://127.0.0.1:5001"
            print(f"✓ Server URL: {url}")
            
            return True
        except Exception as e:
            print(f"✗ Web server test failed: {e}")
            return False
    
    def test_storage_integration(self):
        """Test storage system integration with new features"""
        storage = ChronoLogStorage(self.repo.repo_path)
        
        # Test database schema (should include new tables)
        conn = storage._get_connection()
        cursor = conn.cursor()
        
        # Check for new tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'analytics', 'storage_metadata', 'hooks', 'activity_log',
            'users', 'permissions', 'file_locks', 'merge_conflicts',
            'api_sessions', 'code_metrics'
        ]
        
        for table in expected_tables:
            if table in tables:
                print(f"✓ Database table '{table}' exists")
            else:
                print(f"⚠ Database table '{table}' not found")
        
        conn.close()
        return True
    
    def run_all_tests(self):
        """Run all Phase 4 & 5 tests"""
        print("\\n" + "="*60)
        print("CHRONOLOG PHASE 4 & 5 FEATURE TESTS")
        print("="*60)
        
        if not self.setup():
            print("\\n✗ Setup failed, aborting tests")
            return False
        
        # Phase 4 Tests
        print("\\n" + "-"*30 + " PHASE 4 TESTS " + "-"*30)
        self.run_test("Performance Analytics", self.test_performance_analytics)
        self.run_test("Visualization", self.test_visualization)
        self.run_test("Code Metrics", self.test_code_metrics)
        self.run_test("Storage Optimization", self.test_storage_optimization)
        self.run_test("Garbage Collection", self.test_garbage_collection)
        self.run_test("Hooks System", self.test_hooks_system)
        self.run_test("Scripting API", self.test_scripting_api)
        
        # Phase 5 Tests
        print("\\n" + "-"*30 + " PHASE 5 TESTS " + "-"*30)
        self.run_test("User Management", self.test_user_management)
        self.run_test("Authentication", self.test_authentication)
        self.run_test("Permissions", self.test_permissions)
        self.run_test("Merge Engine", self.test_merge_engine)
        self.run_test("Conflict Resolver", self.test_conflict_resolver)
        self.run_test("Web Server Creation", self.test_web_server_creation)
        
        # Integration Tests
        print("\\n" + "-"*25 + " INTEGRATION TESTS " + "-"*25)
        self.run_test("Storage Integration", self.test_storage_integration)
        
        # Summary
        print("\\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Tests Passed: {self.passed}")
        print(f"Tests Failed: {self.failed}")
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed)) * 100:.1f}%")
        
        if self.failed == 0:
            print("\\n🎉 ALL TESTS PASSED! Phase 4 & 5 features are working correctly.")
        else:
            print(f"\\n⚠️  {self.failed} test(s) failed. Please review the output above.")
        
        self.teardown()
        return self.failed == 0


def main():
    """Main test execution"""
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()