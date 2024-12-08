"""Tests for version management system."""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import toml

from nadoo_migration_framework.version_management import (
    Version,
    VersionType,
    Release,
    VersionManager,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create pyproject.toml
        pyproject_data = {"tool": {"poetry": {"version": "0.1.0"}}}
        with open(project_dir / "pyproject.toml", "w") as f:
            toml.dump(pyproject_data, f)

        yield project_dir


class TestVersion:
    """Test Version class."""

    def test_from_string(self):
        """Test creating Version from string."""
        version = Version.from_string("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_invalid_version_string(self):
        """Test creating Version from invalid string."""
        with pytest.raises(ValueError):
            Version.from_string("invalid")

    def test_bump_major(self):
        """Test bumping major version."""
        version = Version(1, 2, 3)
        new_version = version.bump(VersionType.MAJOR)
        assert str(new_version) == "2.0.0"

    def test_bump_minor(self):
        """Test bumping minor version."""
        version = Version(1, 2, 3)
        new_version = version.bump(VersionType.MINOR)
        assert str(new_version) == "1.3.0"

    def test_bump_patch(self):
        """Test bumping patch version."""
        version = Version(1, 2, 3)
        new_version = version.bump(VersionType.PATCH)
        assert str(new_version) == "1.2.4"

    def test_version_comparison(self):
        """Test version comparison."""
        v1 = Version(1, 2, 3)
        v2 = Version(1, 2, 4)
        v3 = Version(1, 2, 3)

        assert v1 < v2
        assert not v1 > v2
        assert v1 == v3
        assert v1 <= v2
        assert v1 <= v3
        assert v2 >= v1


class TestRelease:
    """Test Release class."""

    @pytest.fixture
    def sample_release(self):
        """Create a sample release."""
        return Release(
            version=Version(1, 2, 3),
            timestamp=datetime(2023, 1, 1),
            changes=["Change 1", "Change 2"],
            description="Test release",
            dependencies={"dep1": "1.0.0"},
            breaking_changes=["Breaking change 1"],
            migration_required=True,
        )

    def test_to_dict(self, sample_release):
        """Test converting Release to dictionary."""
        data = sample_release.to_dict()
        assert data["version"] == "1.2.3"
        assert data["changes"] == ["Change 1", "Change 2"]
        assert data["description"] == "Test release"
        assert data["dependencies"] == {"dep1": "1.0.0"}
        assert data["breaking_changes"] == ["Breaking change 1"]
        assert data["migration_required"] is True

    def test_from_dict(self, sample_release):
        """Test creating Release from dictionary."""
        data = sample_release.to_dict()
        release = Release.from_dict(data)
        assert str(release.version) == "1.2.3"
        assert release.changes == ["Change 1", "Change 2"]
        assert release.description == "Test release"
        assert release.dependencies == {"dep1": "1.0.0"}
        assert release.breaking_changes == ["Breaking change 1"]
        assert release.migration_required is True


class TestVersionManager:
    """Test VersionManager class."""

    def test_get_current_version(self, temp_project_dir):
        """Test getting current version."""
        manager = VersionManager(temp_project_dir)
        version = manager.get_current_version()
        assert str(version) == "0.1.0"

    def test_set_version(self, temp_project_dir):
        """Test setting version."""
        manager = VersionManager(temp_project_dir)
        new_version = Version(0, 2, 0)
        manager.set_version(new_version)

        # Read version directly from file
        with open(temp_project_dir / "pyproject.toml") as f:
            data = toml.load(f)
            assert data["tool"]["poetry"]["version"] == "0.2.0"

    def test_add_release(self, temp_project_dir):
        """Test adding a release."""
        manager = VersionManager(temp_project_dir)
        release = manager.add_release(
            version_type=VersionType.MINOR,
            changes=["Test change"],
            description="Test release",
            breaking_changes=["Test breaking change"],
            dependencies={"test-dep": "1.0.0"},
            migration_required=True,
        )

        assert str(release.version) == "0.2.0"
        assert release.changes == ["Test change"]
        assert release.breaking_changes == ["Test breaking change"]
        assert release.dependencies == {"test-dep": "1.0.0"}
        assert release.migration_required is True

    def test_get_migration_path(self, temp_project_dir):
        """Test getting migration path."""
        manager = VersionManager(temp_project_dir)

        # Add some releases
        manager.add_release(VersionType.MINOR, ["Change 1"], "Release 1")
        manager.add_release(VersionType.MINOR, ["Change 2"], "Release 2")
        manager.add_release(VersionType.MINOR, ["Change 3"], "Release 3")

        # Test forward path
        path = manager.get_migration_path("0.1.0", "0.4.0")
        assert len(path) == 3
        assert str(path[0].version) == "0.2.0"
        assert str(path[1].version) == "0.3.0"
        assert str(path[2].version) == "0.4.0"

        # Test backward path
        path = manager.get_migration_path("0.4.0", "0.2.0")
        assert len(path) == 2
        assert str(path[0].version) == "0.3.0"
        assert str(path[1].version) == "0.2.0"

    def test_check_compatibility(self, temp_project_dir):
        """Test checking version compatibility."""
        manager = VersionManager(temp_project_dir)

        # Add a release with incompatible dependency
        manager.add_release(
            version_type=VersionType.MINOR,
            changes=["Test change"],
            description="Test release",
            dependencies={"test-dep": "999.0.0"},  # Incompatible version
            migration_required=True,
        )

        is_compatible, reasons = manager.check_compatibility("0.2.0")
        assert not is_compatible
        assert len(reasons) > 0

    def test_get_changelog(self, temp_project_dir):
        """Test generating changelog."""
        manager = VersionManager(temp_project_dir)

        # Add some releases
        manager.add_release(
            version_type=VersionType.MINOR,
            changes=["Change 1"],
            description="Release 1",
            breaking_changes=["Breaking 1"],
        )
        manager.add_release(
            version_type=VersionType.MINOR,
            changes=["Change 2"],
            description="Release 2",
            dependencies={"test-dep": "1.0.0"},
        )

        changelog = manager.get_changelog()
        assert "Release 1" in changelog
        assert "Release 2" in changelog
        assert "Change 1" in changelog
        assert "Change 2" in changelog
        assert "Breaking 1" in changelog
        assert "test-dep: 1.0.0" in changelog
