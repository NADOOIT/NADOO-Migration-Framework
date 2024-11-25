"""Tests for the Performance Optimization migration."""

import pytest
from pathlib import Path
import tempfile
import ast
import time

from nadoo_migration_framework.migrations.performance_optimization_migration import PerformanceOptimizationMigration

@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "sample_project"
        project_dir.mkdir()
        
        # Create a sample Python file with performance bottlenecks
        main_py = project_dir / "main.py"
        main_py.write_text("""
def slow_function():
    result = 0
    for i in range(1000):
        for j in range(1000):
            result += i * j
    return result

def process_list(data):
    results = []
    for item in data:
        results.append(item * 2)
    return results

def matrix_multiply(a, b):
    n = len(a)
    result = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                result[i][j] += a[i][k] * b[k][j]
    return result
""")
        
        yield project_dir

def test_performance_optimization_basic(temp_project):
    """Test basic performance optimization functionality."""
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Run migration
    migration._up()
    
    # Check if main.py was transformed
    main_py = temp_project / "main.py"
    content = main_py.read_text()
    
    # Verify optimizations
    assert "import numpy as np" in content
    assert "from concurrent.futures import ThreadPoolExecutor" in content
    assert "parallel" in content.lower() or "vectorize" in content.lower()

def test_performance_optimization_benchmarking(temp_project):
    """Test performance benchmarking functionality."""
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Get original execution time
    main_py = temp_project / "main.py"
    original_code = main_py.read_text()
    
    # Create a test module
    test_module = ast.parse(original_code)
    exec(compile(test_module, filename="<ast>", mode="exec"), globals())
    
    start_time = time.time()
    slow_function()  # type: ignore
    original_time = time.time() - start_time
    
    # Run migration
    migration._up()
    
    # Load optimized code
    optimized_code = main_py.read_text()
    test_module = ast.parse(optimized_code)
    exec(compile(test_module, filename="<ast>", mode="exec"), globals())
    
    # Test optimized performance
    start_time = time.time()
    slow_function()  # type: ignore
    optimized_time = time.time() - start_time
    
    # Verify performance improvement
    assert optimized_time < original_time

def test_performance_optimization_rollback(temp_project):
    """Test performance optimization rollback functionality."""
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Store original content
    main_py = temp_project / "main.py"
    original_content = main_py.read_text()
    
    # Run migration
    migration._up()
    
    # Verify changes were made
    assert main_py.read_text() != original_content
    
    # Rollback migration
    migration._down()
    
    # Verify content was restored
    assert main_py.read_text() == original_content

def test_performance_optimization_multiple_files(temp_project):
    """Test performance optimization with multiple Python files."""
    # Create additional files
    utils_py = temp_project / "utils.py"
    utils_py.write_text("""
def helper_function(data):
    result = []
    for x in data:
        result.append(x ** 2)
    return result
""")
    
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Run migration
    migration._up()
    
    # Verify optimization of utils.py
    utils_content = utils_py.read_text()
    assert "import numpy as np" in utils_content
    assert "vectorize" in utils_content.lower() or "parallel" in utils_content.lower()

def test_performance_optimization_error_handling(temp_project):
    """Test performance optimization error handling."""
    # Create invalid Python file
    main_py = temp_project / "main.py"
    main_py.write_text("invalid python code {")
    
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Verify migration raises error
    with pytest.raises(Exception):
        migration._up()

def test_performance_optimization_complex_functions(temp_project):
    """Test performance optimization of complex functions."""
    # Create file with complex functions
    main_py = temp_project / "main.py"
    main_py.write_text("""
def recursive_function(n):
    if n <= 1:
        return n
    return recursive_function(n-1) + recursive_function(n-2)

def nested_loops():
    result = 0
    for i in range(100):
        for j in range(100):
            for k in range(100):
                result += i * j * k
    return result

def mixed_operations(data):
    result = []
    for i, value in enumerate(data):
        if isinstance(value, (int, float)):
            result.append(value ** 2)
        else:
            result.append(str(value))
    return result
""")
    
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Run migration
    migration._up()
    
    # Check optimized content
    content = main_py.read_text()
    
    # Verify optimizations for different function types
    assert "cache" in content.lower() or "lru_cache" in content.lower()  # For recursive function
    assert "parallel" in content.lower() or "vectorize" in content.lower()  # For nested loops
    assert "numpy" in content.lower() or "numba" in content.lower()  # For numerical operations

def test_performance_optimization_memory_usage(temp_project):
    """Test memory usage optimization."""
    # Create memory-intensive code
    main_py = temp_project / "main.py"
    main_py.write_text("""
def memory_intensive():
    data = []
    for i in range(1000000):
        data.append(i ** 2)
    return data

def large_list_processing(size):
    data = list(range(size))
    result = []
    for item in data:
        result.append(item * 2)
    return result
""")
    
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Run migration
    migration._up()
    
    # Check optimized content
    content = main_py.read_text()
    
    # Verify memory optimizations
    assert "generator" in content.lower() or "yield" in content.lower()
    assert "numpy" in content.lower()  # For efficient array operations

def test_performance_optimization_platform_specific(temp_project):
    """Test platform-specific optimizations."""
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Run migration
    migration._up()
    
    # Check platform-specific optimizations
    main_py = temp_project / "main.py"
    content = main_py.read_text()
    
    # Verify platform detection and optimization
    assert "platform" in content.lower() or "sys" in content.lower()
    assert "multiprocessing" in content.lower() or "threading" in content.lower()

def test_performance_optimization_logging(temp_project):
    """Test performance optimization logging."""
    migration = PerformanceOptimizationMigration()
    migration.set_project_dir(temp_project)
    
    # Run migration
    migration._up()
    
    # Check for logging configuration
    main_py = temp_project / "main.py"
    content = main_py.read_text()
    
    # Verify logging setup
    assert "import logging" in content
    assert "logger" in content.lower()
    assert "performance" in content.lower() and "metrics" in content.lower()
