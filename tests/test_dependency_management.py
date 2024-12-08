"""Tests for dependency management system."""

import pytest
from pathlib import Path
import tempfile
import toml

from nadoo_migration_framework.src.nadoo_migration_framework.classes.DependencyManagement import DependencyRequirement, DependencyManager


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create pyproject.toml
        pyproject_data = {"project": {"dependencies": ["toga>=0.3.0", "briefcase>=0.3.14"]}}
        with open(project_dir / "pyproject.toml", "w") as f:
            toml.dump(pyproject_data, f)

        # Create requirements.txt
        with open(project_dir / "requirements.txt", "w") as f:
            f.write("libcst>=1.0.0\n")

        yield project_dir


class TestDependencyRequirement:
    """Test DependencyRequirement class."""

    def test_is_compatible_basic(self):
        """Test basic version compatibility."""
        req = DependencyRequirement(name="test", min_version="1.0.0", max_version="2.0.0")

        assert req.is_compatible("1.5.0")
        assert not req.is_compatible("0.9.0")
        assert not req.is_compatible("2.1.0")

    def test_is_compatible_excluded_versions(self):
        """Test compatibility with excluded versions."""
        req = DependencyRequirement(
            name="test", min_version="1.0.0", max_version="2.0.0", excluded_versions={"1.5.0"}
        )

        assert req.is_compatible("1.4.0")
        assert not req.is_compatible("1.5.0")
        assert req.is_compatible("1.6.0")

    def test_is_compatible_invalid_version(self):
        """Test compatibility with invalid version string."""
        req = DependencyRequirement(name="test", min_version="1.0.0", max_version="2.0.0")

        assert not req.is_compatible("invalid")


class TestDependencyManager:
    """Test DependencyManager class."""

    def test_load_dependencies(self, temp_project_dir):
        """Test loading dependencies from files."""
        manager = DependencyManager(temp_project_dir)

        assert "toga" in manager.dependencies
        assert "briefcase" in manager.dependencies
        assert "libcst" in manager.dependencies

    def test_add_dependency(self, temp_project_dir):
        """Test adding a new dependency."""
        manager = DependencyManager(temp_project_dir)
        manager.add_dependency("test-dep", "1.0.0", "2.0.0")

        assert "test-dep" in manager.dependencies
        dep = manager.dependencies["test-dep"]
        assert dep.min_version == "1.0.0"
        assert dep.max_version == "2.0.0"

        # Check if dependency was written to files
        with open(temp_project_dir / "pyproject.toml") as f:
            data = toml.load(f)
            deps = data["project"]["dependencies"]
            assert any("test-dep>=1.0.0" in d for d in deps)

    def test_remove_dependency(self, temp_project_dir):
        """Test removing a dependency."""
        manager = DependencyManager(temp_project_dir)
        manager.remove_dependency("toga")

        assert "toga" not in manager.dependencies

        # Check if dependency was removed from files
        with open(temp_project_dir / "pyproject.toml") as f:
            data = toml.load(f)
            deps = data["project"]["dependencies"]
            assert not any("toga" in d for d in deps)

    def test_update_dependency(self, temp_project_dir):
        """Test updating a dependency."""
        manager = DependencyManager(temp_project_dir)
        manager.update_dependency("toga", min_version="0.4.0")

        dep = manager.dependencies["toga"]
        assert dep.min_version == "0.4.0"

        # Check if dependency was updated in files
        with open(temp_project_dir / "pyproject.toml") as f:
            data = toml.load(f)
            deps = data["project"]["dependencies"]
            assert any("toga>=0.4.0" in d for d in deps)

    def test_check_compatibility(self, temp_project_dir):
        """Test checking dependency compatibility."""
        manager = DependencyManager(temp_project_dir)

        # Test compatible version
        is_compatible, reasons = manager.check_compatibility("toga", "0.3.5")
        assert is_compatible
        assert not reasons

        # Test incompatible version
        is_compatible, reasons = manager.check_compatibility("toga", "0.2.0")
        assert not is_compatible
        assert len(reasons) > 0

    def test_get_compatible_versions(self, temp_project_dir):
        """Test getting compatible versions."""
        manager = DependencyManager(temp_project_dir)
        versions = manager.get_compatible_versions("toga")

        assert len(versions) > 0
        assert all(manager.check_compatibility("toga", v)[0] for v in versions)
