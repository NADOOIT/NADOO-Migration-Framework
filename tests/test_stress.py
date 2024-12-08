"""Stress tests for the migration framework."""

import os
import time
import pytest
import tempfile
import threading
import multiprocessing
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from nadoo_migration_framework.src.nadoo_migration_framework.migrations.cleanup_project_structure import (
    CleanupProjectStructureMigration,
)


def create_test_project(base_path: Path, size_mb: int = 1) -> None:
    """Create a test project with specified size in MB."""
    (base_path / "src" / "functions").mkdir(parents=True)
    (base_path / "src" / "classes").mkdir(parents=True)

    # Create a file with specified size
    content = "x" * (size_mb * 1024 * 1024)  # 1MB of content
    (base_path / "src" / "functions" / "large_file.py").write_text(content)


def test_concurrent_migrations():
    """Test multiple migrations running concurrently."""
    num_projects = 5
    temp_dirs = []

    try:
        # Create multiple test projects
        for _ in range(num_projects):
            temp_dir = tempfile.mkdtemp()
            create_test_project(Path(temp_dir))
            temp_dirs.append(temp_dir)

        # Run migrations concurrently
        with ThreadPoolExecutor(max_workers=num_projects) as executor:
            futures = []
            for temp_dir in temp_dirs:
                migration = CleanupProjectStructureMigration()
                futures.append(executor.submit(migration.migrate, temp_dir))

            # Check results
            for future in futures:
                assert future.result(), "Concurrent migration failed"

    finally:
        # Cleanup
        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


def test_large_file_handling():
    """Test migration of large files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        create_test_project(base_path, size_mb=100)  # 100MB file

        migration = CleanupProjectStructureMigration()
        start_time = time.time()
        success = migration.migrate(str(base_path))
        end_time = time.time()

        assert success, "Large file migration failed"
        assert end_time - start_time < 30, "Large file migration took too long"


@pytest.mark.parametrize("depth", [5, 10, 20])
def test_deep_directory_structure(depth):
    """Test migration of deeply nested directory structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create deep directory structure
        current_path = base_path / "src" / "functions"
        current_path.mkdir(parents=True)

        for i in range(depth):
            current_path = current_path / f"level_{i}"
            current_path.mkdir()
            (current_path / "test.py").write_text(f"def test_{i}(): pass")

        migration = CleanupProjectStructureMigration()
        success = migration.migrate(str(base_path))

        assert success, "Deep directory migration failed"

        # Verify all files were migrated
        migrated_files = list(Path(base_path).rglob("test.py"))
        assert len(migrated_files) == depth, "Not all files were migrated"


def test_interrupted_migration():
    """Test migration behavior when interrupted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        create_test_project(base_path)

        def interrupt_migration():
            time.sleep(0.1)  # Wait a bit before interrupting
            raise KeyboardInterrupt()

        # Start migration in a separate thread
        migration = CleanupProjectStructureMigration()
        migration_thread = threading.Thread(target=migration.migrate, args=(str(base_path),))

        interrupt_thread = threading.Thread(target=interrupt_migration)

        migration_thread.start()
        interrupt_thread.start()

        migration_thread.join()
        interrupt_thread.join()

        # Verify project is in a consistent state
        assert (base_path / ".backup").exists(), "Backup not created"
        assert migration.rollback(str(base_path)), "Rollback failed"


def test_repeated_migrations():
    """Test multiple migrations on the same project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        create_test_project(base_path)

        migration = CleanupProjectStructureMigration()

        # Run migration multiple times
        for _ in range(5):
            success = migration.migrate(str(base_path))
            assert success, "Repeated migration failed"

            # Verify project structure is correct
            assert (base_path / "src").exists()
            assert (base_path / "src" / base_path.name.replace("-", "_")).exists()

            # Small delay between migrations
            time.sleep(0.1)
