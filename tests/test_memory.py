"""Memory management tests for the migration framework."""

import os
import gc
import sys
import pytest
import psutil
import tempfile
import resource
from pathlib import Path
from memory_profiler import profile
from nadoo_migration_framework.src.nadoo_migration_framework.migrations.cleanup_project_structure import (
    CleanupProjectStructureMigration,
)


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def create_large_project(base_path: Path, num_files: int = 1000) -> None:
    """Create a large project structure for memory testing."""
    (base_path / "src" / "functions").mkdir(parents=True)
    (base_path / "src" / "classes").mkdir(parents=True)

    # Create many files with content
    for i in range(num_files):
        file_content = f"""
def function_{i}():
    \"\"\"Test function {i}.\"\"\"
    return {i}

class TestClass_{i}:
    \"\"\"Test class {i}.\"\"\"
    def method_{i}(self):
        return {i}
"""
        if i % 2 == 0:
            (base_path / "src" / "functions" / f"test_file_{i}.py").write_text(file_content)
        else:
            (base_path / "src" / "classes" / f"test_file_{i}.py").write_text(file_content)


@profile
def test_memory_usage_large_project():
    """Test memory usage with a large project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        create_large_project(base_path)

        initial_memory = get_memory_usage()

        migration = CleanupProjectStructureMigration()
        migration.migrate(str(base_path))

        # Force garbage collection
        gc.collect()

        final_memory = get_memory_usage()
        memory_increase = final_memory - initial_memory

        # Memory increase should be minimal (less than 50MB for 1000 files)
        assert memory_increase < 50, f"Memory increase too high: {memory_increase}MB"


def test_file_handle_cleanup():
    """Test that all file handles are properly closed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        create_large_project(base_path, num_files=100)

        initial_fds = psutil.Process().num_fds()

        migration = CleanupProjectStructureMigration()
        migration.migrate(str(base_path))

        # Force cleanup
        gc.collect()

        final_fds = psutil.Process().num_fds()

        # Number of open file descriptors should be the same or less
        assert final_fds <= initial_fds, "File descriptors were not properly closed"


def test_memory_limit_handling():
    """Test handling of memory limits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        create_large_project(base_path)

        # Set memory limit to 100MB
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, hard))

        migration = CleanupProjectStructureMigration()

        try:
            # Should handle memory limit gracefully
            migration.migrate(str(base_path))
        except MemoryError:
            pytest.fail("Migration should handle memory limits gracefully")
        finally:
            # Reset memory limit
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


@pytest.mark.parametrize("num_files", [10, 100, 1000])
def test_memory_scaling(num_files):
    """Test memory usage scales linearly with project size."""
    memory_usage = []

    for _ in range(3):  # Run multiple times to get average
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            create_large_project(base_path, num_files)

            initial_memory = get_memory_usage()

            migration = CleanupProjectStructureMigration()
            migration.migrate(str(base_path))

            gc.collect()

            final_memory = get_memory_usage()
            memory_usage.append(final_memory - initial_memory)

    avg_memory = sum(memory_usage) / len(memory_usage)

    # Memory usage should scale roughly linearly (less than quadratic)
    # For 10x more files, memory should increase less than 10x
    assert avg_memory < (50 * (num_files / 1000) * 1.5), "Memory usage scaling is not linear"
