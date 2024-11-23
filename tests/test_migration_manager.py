"""Tests for migration manager system."""

import pytest
from pathlib import Path
import tempfile
import shutil

from nadoo_migration_framework.migration_manager import (
    MigrationManager, MigrationFile, MigrationType
)

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create migrations directory
        migrations_dir = project_dir / "migrations"
        migrations_dir.mkdir()
        
        # Create sample migration files
        migration_files = [
            "001_initial_migration.py",
            "002_add_feature.py",
            "003_update_imports.py"
        ]
        
        for file in migration_files:
            with open(migrations_dir / file, "w") as f:
                f.write(f"""
from nadoo_migration_framework.base import BaseMigration

class Migration(BaseMigration):
    version = "0.1.{file[0:3]}"
    description = "Test migration {file}"
    
    def _up(self):
        pass
    
    def _down(self):
        pass
""")
        
        yield project_dir

class TestMigrationFile:
    """Test MigrationFile class."""
    
    def test_load_migration(self, temp_project_dir):
        """Test loading a migration file."""
        file_path = temp_project_dir / "migrations" / "001_initial_migration.py"
        migration = MigrationFile(file_path)
        
        assert migration.version == "0.1.001"
        assert "Test migration" in migration.description
        assert hasattr(migration.migration_class, "_up")
        assert hasattr(migration.migration_class, "_down")
    
    def test_invalid_migration_file(self, temp_project_dir):
        """Test loading an invalid migration file."""
        file_path = temp_project_dir / "migrations" / "invalid.py"
        with open(file_path, "w") as f:
            f.write("invalid python code")
        
        with pytest.raises(Exception):
            MigrationFile(file_path)

class TestMigrationManager:
    """Test MigrationManager class."""
    
    def test_discover_migrations(self, temp_project_dir):
        """Test discovering migration files."""
        manager = MigrationManager(temp_project_dir)
        migrations = manager.discover_migrations()
        
        assert len(migrations) == 3
        assert all(m.version.startswith("0.1.") for m in migrations)
    
    def test_get_migration_path(self, temp_project_dir):
        """Test getting migration path."""
        manager = MigrationManager(temp_project_dir)
        
        # Test forward path
        path = manager.get_migration_path("0.1.001", "0.1.003")
        assert len(path) == 2
        assert path[0].version == "0.1.002"
        assert path[1].version == "0.1.003"
        
        # Test backward path
        path = manager.get_migration_path("0.1.003", "0.1.001")
        assert len(path) == 2
        assert path[0].version == "0.1.002"
        assert path[1].version == "0.1.001"
    
    def test_create_migration(self, temp_project_dir):
        """Test creating a new migration."""
        manager = MigrationManager(temp_project_dir)
        migration = manager.create_migration(
            name="test_migration",
            description="Test migration",
            migration_type=MigrationType.FUNCTIONAL
        )
        
        assert migration.exists()
        assert "test_migration" in migration.name
        
        # Load and verify migration content
        content = migration.read_text()
        assert "Migration" in content
        assert "Test migration" in content
        assert "_up" in content
        assert "_down" in content
    
    def test_run_migration(self, temp_project_dir):
        """Test running a migration."""
        manager = MigrationManager(temp_project_dir)
        
        # Create a test migration that modifies a file
        test_file = temp_project_dir / "test.txt"
        with open(test_file, "w") as f:
            f.write("original content")
        
        migration_file = temp_project_dir / "migrations" / "004_test_migration.py"
        with open(migration_file, "w") as f:
            f.write("""
from nadoo_migration_framework.base import Migration
from pathlib import Path

class Migration(Migration):
    version = "0.1.004"
    description = "Test migration"
    
    def _up(self):
        test_file = Path(self.project_dir) / "test.txt"
        with open(test_file, "w") as f:
            f.write("migrated content")
    
    def _down(self):
        test_file = Path(self.project_dir) / "test.txt"
        with open(test_file, "w") as f:
            f.write("original content")
""")
        
        # Run forward migration
        migration = MigrationFile(migration_file)
        manager.run_migration(migration, forward=True)
        
        with open(test_file) as f:
            assert f.read() == "migrated content"
        
        # Run backward migration
        manager.run_migration(migration, forward=False)
        
        with open(test_file) as f:
            assert f.read() == "original content"
    
    def test_dry_run(self, temp_project_dir):
        """Test dry run migration."""
        manager = MigrationManager(temp_project_dir)
        
        # Create a test file
        test_file = temp_project_dir / "test.txt"
        original_content = "original content"
        with open(test_file, "w") as f:
            f.write(original_content)
        
        # Create a test migration
        migration_file = temp_project_dir / "migrations" / "005_test_migration.py"
        with open(migration_file, "w") as f:
            f.write("""
from nadoo_migration_framework.base import Migration
from pathlib import Path

class Migration(Migration):
    version = "0.1.005"
    description = "Test migration"
    
    def _up(self):
        test_file = Path(self.project_dir) / "test.txt"
        with open(test_file, "w") as f:
            f.write("migrated content")
""")
        
        # Run dry run
        migration = MigrationFile(migration_file)
        changes = manager.dry_run(migration, forward=True)
        
        # Verify that file wasn't actually changed
        with open(test_file) as f:
            assert f.read() == original_content
        
        # Verify that changes were detected
        assert changes
        assert "test.txt" in str(changes)
