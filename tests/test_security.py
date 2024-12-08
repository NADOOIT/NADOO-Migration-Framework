"""Security tests for the migration framework."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from nadoo_migration_framework.migrations.cleanup_project_structure import (
    CleanupProjectStructureMigration,
    SecurityError,
)


def create_malicious_symlink(base_path: Path) -> None:
    """Create a malicious symlink for testing."""
    (base_path / "src" / "functions").mkdir(parents=True, exist_ok=True)
    malicious_link = base_path / "src" / "functions" / "malicious.py"
    malicious_link.symlink_to("/etc/passwd")


def test_symlink_attack():
    """Test that the migration safely handles malicious symlinks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        create_malicious_symlink(base_path)

        migration = CleanupProjectStructureMigration()
        result = migration.migrate(str(base_path))
        assert not result, "Migration should fail when malicious symlink is detected"

        # Verify no sensitive files were accessed
        assert not (base_path / "etc" / "passwd").exists()


def test_path_traversal():
    """Test protection against path traversal attacks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        malicious_path = base_path / "src" / "functions" / ".." / ".." / ".." / "etc" / "passwd"
        malicious_path.parent.mkdir(parents=True, exist_ok=True)
        malicious_path.touch()

        migration = CleanupProjectStructureMigration()
        result = migration.migrate(str(base_path))

        # Verify migration stayed within project directory
        assert not any("etc" in str(p) for p in Path(base_path).rglob("*"))


def test_file_permission_security():
    """Test that migrated files maintain secure permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        test_file = base_path / "src" / "functions" / "test.py"
        test_file.parent.mkdir(parents=True)
        test_file.touch()
        test_file.chmod(0o777)  # Insecure permissions

        migration = CleanupProjectStructureMigration()
        migration.migrate(str(base_path))

        # Check migrated file has secure permissions (0o644 or similar)
        migrated_file = list(Path(base_path).rglob("test.py"))[0]
        assert oct(migrated_file.stat().st_mode)[-3:] in ('644', '640')


def test_resource_cleanup():
    """Test that all resources are properly cleaned up after migration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        test_file = base_path / "src" / "functions" / "test.py"
        test_file.parent.mkdir(parents=True)
        test_file.touch()

        migration = CleanupProjectStructureMigration()
        with patch('builtins.open') as mock_open:
            migration.migrate(str(base_path))
            # Verify all file handles were closed
            for call in mock_open.mock_calls:
                if 'enter' in str(call):
                    assert any(
                        'exit' in str(c)
                        for c in mock_open.mock_calls[mock_open.mock_calls.index(call) :]
                    )


def test_memory_limit_enforcement():
    """Test that memory usage stays within acceptable limits."""
    import psutil
    import gc

    process = psutil.Process()
    initial_memory = process.memory_info().rss

    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        # Create a large project structure
        for i in range(100):
            file_path = base_path / "src" / "functions" / f"test_{i}.py"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("# Test file" * 1000)  # Create some content

        migration = CleanupProjectStructureMigration()
        migration.migrate(str(base_path))

        # Force garbage collection
        gc.collect()

        # Check memory usage after migration
        final_memory = process.memory_info().rss
        # Allow for some memory overhead but ensure it's reasonable
        assert (final_memory - initial_memory) < 100 * 1024 * 1024  # 100MB limit


def test_concurrent_access_security():
    """Test handling of concurrent access attempts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        test_file = base_path / "src" / "functions" / "test.py"
        test_file.parent.mkdir(parents=True)
        test_file.touch()

        # Simulate concurrent access
        with open(test_file, 'w') as f:
            migration = CleanupProjectStructureMigration()
            # Should handle file being locked by another process
            migration.migrate(str(base_path))

        # Verify migration completed successfully
        assert any(Path(base_path).rglob("test.py"))
