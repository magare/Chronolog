#!/usr/bin/env python3
"""
Unit tests for analytics components
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronolog.analytics.performance_analytics import PerformanceAnalytics, RepositoryStats
from chronolog.analytics.visualization import Visualization
from chronolog.analytics.metrics_collector import MetricsCollector, FileMetrics
from chronolog.storage.storage import ChronoLogStorage


class TestPerformanceAnalytics(unittest.TestCase):
    """Test cases for PerformanceAnalytics"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = ChronoLogStorage(self.test_dir)
        self.analytics = PerformanceAnalytics(self.test_dir)
        
        # Create some test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_data(self):
        """Create test data for analytics"""
        # Create some test files and versions
        test_file = self.test_dir / "test.py"
        test_file.write_text("print('hello world')")
        
        # Simulate some versions
        for i in range(5):
            test_file.write_text(f"print('hello world {i}')")
            # In a real scenario, this would be handled by the watcher
    
    def test_repository_stats_collection(self):
        """Test repository statistics collection"""
        stats = self.analytics.collect_repository_stats()
        
        self.assertIsInstance(stats, RepositoryStats)
        self.assertIsInstance(stats.total_versions, int)
        self.assertIsInstance(stats.total_files, int)
        self.assertIsInstance(stats.total_size_mb, float)
        self.assertIsInstance(stats.unique_authors, list)
        self.assertIsInstance(stats.language_stats, dict)
        self.assertGreaterEqual(stats.compression_ratio, 0)
        self.assertGreaterEqual(stats.growth_rate_mb_per_day, 0)
    
    def test_operation_metrics(self):
        """Test operation metrics collection"""
        # Record some test metrics
        self.analytics.record_operation_metric("test_operation", 1.5, 10, True)
        self.analytics.record_operation_metric("another_operation", 0.8, 5, False)
        
        metrics = self.analytics.get_operation_metrics(days=1)
        self.assertIsInstance(metrics, list)
        
        if metrics:  # May be empty in test environment
            metric = metrics[0]
            self.assertIn('operation_type', metric)
            self.assertIn('duration', metric)
            self.assertIn('files_processed', metric)
            self.assertIn('success', metric)
    
    def test_storage_efficiency_analysis(self):
        """Test storage efficiency analysis"""
        efficiency = self.analytics.analyze_storage_efficiency()
        
        self.assertIsInstance(efficiency, dict)
        self.assertIn('compression_ratio', efficiency)
        self.assertIn('storage_efficiency', efficiency)
        self.assertIn('recommendations', efficiency)
        
        # Validate compression ratio is reasonable
        compression_ratio = efficiency['compression_ratio']
        self.assertGreaterEqual(compression_ratio, 0)
        self.assertLessEqual(compression_ratio, 10)  # Should be reasonable


class TestVisualization(unittest.TestCase):
    """Test cases for Visualization"""
    
    def setUp(self):
        """Set up test environment"""
        self.viz = Visualization()
    
    def test_bar_chart_creation(self):
        """Test bar chart creation"""
        labels = ['A', 'B', 'C']
        values = [10, 20, 15]
        
        chart = self.viz.create_bar_chart(labels, values, title="Test Chart")
        
        self.assertIsInstance(chart, str)
        self.assertIn("Test Chart", chart)
        self.assertTrue(len(chart) > 0)
        
        # Test with empty data
        empty_chart = self.viz.create_bar_chart([], [])
        self.assertIsInstance(empty_chart, str)
    
    def test_line_chart_creation(self):
        """Test line chart creation"""
        x_values = [1, 2, 3, 4, 5]
        y_values = [10, 12, 11, 15, 14]
        
        chart = self.viz.create_line_chart(x_values, y_values, title="Line Chart")
        
        self.assertIsInstance(chart, str)
        self.assertIn("Line Chart", chart)
        self.assertTrue(len(chart) > 0)
    
    def test_sparkline_creation(self):
        """Test sparkline creation"""
        data = [1, 3, 2, 5, 4, 6, 7]
        
        sparkline = self.viz.create_sparkline(data)
        
        self.assertIsInstance(sparkline, str)
        self.assertTrue(len(sparkline) > 0)
        
        # Test with single value
        single_sparkline = self.viz.create_sparkline([5])
        self.assertIsInstance(single_sparkline, str)
    
    def test_activity_calendar_creation(self):
        """Test activity calendar creation"""
        dates = [
            '2024-01-01', '2024-01-02', '2024-01-03',
            '2024-01-05', '2024-01-08'
        ]
        
        calendar = self.viz.create_activity_calendar(dates)
        
        self.assertIsInstance(calendar, str)
        self.assertTrue(len(calendar) > 0)
    
    def test_heatmap_creation(self):
        """Test heatmap creation"""
        data = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ]
        
        heatmap = self.viz.create_heatmap(data, title="Test Heatmap")
        
        self.assertIsInstance(heatmap, str)
        self.assertIn("Test Heatmap", heatmap)
    
    def test_progress_bar_creation(self):
        """Test progress bar creation"""
        progress_bar = self.viz.create_progress_bar(75, 100, "Processing")
        
        self.assertIsInstance(progress_bar, str)
        self.assertIn("Processing", progress_bar)
        self.assertIn("75", progress_bar)
    
    def test_tree_map_creation(self):
        """Test tree map creation"""
        data = {
            'A': 30,
            'B': 20,
            'C': 15,
            'D': 10
        }
        
        tree_map = self.viz.create_tree_map(data, title="Tree Map")
        
        self.assertIsInstance(tree_map, str)
        self.assertIn("Tree Map", tree_map)


class TestMetricsCollector(unittest.TestCase):
    """Test cases for MetricsCollector"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.collector = MetricsCollector(self.test_dir)
        
        # Create test files
        self._create_test_files()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_files(self):
        """Create test files for analysis"""
        # Python file
        python_file = self.test_dir / "test.py"
        python_content = '''def calculate(n):
    """Calculate something"""
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

class TestClass:
    def __init__(self):
        self.value = 0
    
    def method(self, x):
        if x > 10:
            return x * 2
        return x
'''
        python_file.write_text(python_content)
        
        # JavaScript file
        js_file = self.test_dir / "test.js"
        js_content = '''function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

function processData(data) {
    if (!data || data.length === 0) {
        return [];
    }
    
    return data
        .filter(item => item.value > 0)
        .map(item => ({
            ...item,
            processed: true
        }))
        .sort((a, b) => a.value - b.value);
}
'''
        js_file.write_text(js_content)
        
        # Text file (should be ignored)
        text_file = self.test_dir / "readme.txt"
        text_file.write_text("This is a text file")
    
    def test_language_detection(self):
        """Test programming language detection"""
        python_file = self.test_dir / "test.py"
        js_file = self.test_dir / "test.js"
        text_file = self.test_dir / "readme.txt"
        
        self.assertEqual(self.collector.detect_language(python_file), "python")
        self.assertEqual(self.collector.detect_language(js_file), "javascript")
        self.assertEqual(self.collector.detect_language(text_file), "text")
    
    def test_python_analysis(self):
        """Test Python file analysis"""
        python_file = self.test_dir / "test.py"
        metrics = self.collector.analyze_file(python_file)
        
        self.assertIsInstance(metrics, FileMetrics)
        self.assertEqual(metrics.language, "python")
        self.assertGreater(metrics.lines_of_code, 0)
        self.assertGreater(metrics.cyclomatic_complexity, 1)
        self.assertGreaterEqual(metrics.maintainability_index, 0)
        self.assertLessEqual(metrics.maintainability_index, 100)
    
    def test_javascript_analysis(self):
        """Test JavaScript file analysis"""
        js_file = self.test_dir / "test.js"
        metrics = self.collector.analyze_file(js_file)
        
        self.assertIsInstance(metrics, FileMetrics)
        self.assertEqual(metrics.language, "javascript")
        self.assertGreater(metrics.lines_of_code, 0)
        self.assertGreater(metrics.cyclomatic_complexity, 1)
    
    def test_repository_analysis(self):
        """Test full repository analysis"""
        results = self.collector.analyze_repository()
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        
        # Should have analyzed Python and JavaScript files
        languages = [r.language for r in results]
        self.assertIn("python", languages)
        self.assertIn("javascript", languages)
        self.assertNotIn("text", languages)  # Text files should be ignored
    
    def test_lines_of_code_counting(self):
        """Test lines of code counting"""
        python_file = self.test_dir / "test.py"
        
        # Test Python LOC counting
        loc = self.collector._count_python_loc(python_file.read_text())
        self.assertGreater(loc, 10)  # Should have meaningful LOC count
        
        # Test generic LOC counting
        generic_loc = self.collector._count_generic_loc(python_file.read_text())
        self.assertGreater(generic_loc, 0)
    
    def test_complexity_calculation(self):
        """Test cyclomatic complexity calculation"""
        python_code = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            return x
    else:
        return 0
'''
        
        complexity = self.collector._calculate_python_complexity(python_code)
        self.assertGreater(complexity, 1)  # Should detect the nested conditions
    
    def test_maintainability_index(self):
        """Test maintainability index calculation"""
        # Simple code should have high maintainability
        simple_code = "def simple(): return 42"
        simple_metrics = FileMetrics(
            file_path=Path("simple.py"),
            language="python",
            lines_of_code=1,
            cyclomatic_complexity=1,
            maintainability_index=0  # Will be calculated
        )
        
        mi = self.collector._calculate_maintainability_index(
            simple_metrics.lines_of_code,
            simple_metrics.cyclomatic_complexity,
            len(simple_code)
        )
        
        self.assertGreaterEqual(mi, 0)
        self.assertLessEqual(mi, 100)


if __name__ == '__main__':
    unittest.main()