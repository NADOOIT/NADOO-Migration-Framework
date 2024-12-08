"""Tests for the project structure fix migration."""

import os
import shutil
from pathlib import Path
import pytest
import toml
from typing import Generator

from nadoo_migration_framework.migrations.fix_project_structure import FixProjectStructureMigration


@pytest.fixture
def migration() -> FixProjectStructureMigration:
    """Fixture for the migration class.

    Returns:
        FixProjectStructureMigration: The migration class instance.
    """
    return FixProjectStructureMigration()


@pytest.fixture
def test_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a test project structure.

    Args:
        tmp_path: Temporary directory path.

    Yields:
        Path to the test project.
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create old project structure
    nested_dir = project_dir / "nadoo_law"
    nested_dir.mkdir()

    src_dir = nested_dir / "src" / "nadoo_law"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").touch()

    tests_dir = nested_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").touch()
    (tests_dir / "test_app.py").write_text("def test_example(): assert True")

    # Create multiple pyproject.toml files
    root_toml = {"project": {"name": "old-name", "version": "0.0.1"}}
    nested_toml = {
        "project": {"description": "Test description"},
        "tool": {"poetry": {"dependencies": {"requests": "^2.0.0"}}},
    }

    with open(project_dir / "pyproject.toml", "w") as f:
        toml.dump(root_toml, f)
    with open(nested_dir / "pyproject.toml", "w") as f:
        toml.dump(nested_toml, f)

    # Create multiple README files
    (project_dir / "README.md").write_text("# Old README")
    (nested_dir / "README.rst").write_text("Old RST README")

    old_cwd = os.getcwd()
    os.chdir(project_dir)
    yield project_dir
    os.chdir(old_cwd)
    shutil.rmtree(project_dir)


def test_migration_initialization(migration: FixProjectStructureMigration) -> None:
    """Test migration initialization.

    Args:
        migration: The migration instance.
    """
    assert migration.migration_id == "fix_project_structure"
    assert migration.description == "Fixes project structure to follow standards"
    assert migration.backup_dir is None


def test_backup_files(migration: FixProjectStructureMigration, test_project: Path) -> None:
    """Test file backup functionality.

    Args:
        migration: The migration instance.
        test_project: Test project directory.
    """
    files_to_backup = [Path("nadoo_law"), Path("README.md"), Path("pyproject.toml")]

    migration.backup_files(files_to_backup)

    backup_dir = Path(".migration_backup")
    assert backup_dir.exists()
    assert (backup_dir / "nadoo_law").exists()
    assert (backup_dir / "README.md").exists()
    assert (backup_dir / "pyproject.toml").exists()


def test_merge_toml_files(migration: FixProjectStructureMigration, test_project: Path) -> None:
    """Test TOML file merging.

    Args:
        migration: The migration instance.
        test_project: Test project directory.
    """
    toml_files = [Path("pyproject.toml"), Path("nadoo_law/pyproject.toml")]

    merged = migration.merge_toml_files(toml_files)

    assert merged["project"]["name"] == "old-name"
    assert merged["project"]["version"] == "0.0.1"
    assert merged["project"]["description"] == "Test description"
    assert merged["tool"]["poetry"]["dependencies"]["requests"] == "^2.0.0"


def test_migrate(migration: FixProjectStructureMigration, test_project: Path) -> None:
    """Test full migration process.

    Args:
        migration: The migration instance.
        test_project: Test project directory.
    """
    migration.migrate()

    # Check new directory structure
    assert Path("src/nadoo_law").exists()
    assert Path("src/nadoo_law/__init__.py").exists()
    assert Path("tests").exists()
    assert Path("tests/__init__.py").exists()
    assert Path("tests/test_app.py").exists()

    # Check pyproject.toml
    with open("pyproject.toml") as f:
        content = toml.load(f)

    assert content["project"]["name"] == "nadoo_law"
    assert content["project"]["version"] == "0.1.0"
    assert "pytest" in content["tool"]["poetry"]["group"]["test"]["dependencies"]

    # Check README.md
    assert Path("README.md").exists()
    readme_content = Path("README.md").read_text()
    assert "NADOO Law" in readme_content
    assert "Legal Document Processing Framework" in readme_content

    # Check old files are removed
    assert not Path("nadoo_law").exists()


def test_rollback(migration: FixProjectStructureMigration, test_project: Path) -> None:
    """Test migration rollback.

    Args:
        migration: The migration instance.
        test_project: Test project directory.
    """
    # First migrate
    migration.migrate()

    # Then rollback
    migration.rollback()

    # Check old structure is restored
    assert Path("nadoo_law").exists()
    assert Path("nadoo_law/src/nadoo_law/__init__.py").exists()
    assert Path("nadoo_law/tests/test_app.py").exists()
    assert Path("README.md").exists()
    assert Path("pyproject.toml").exists()

    # Check backup is cleaned up
    assert not Path(".migration_backup").exists()
