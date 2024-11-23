"""Tests for Briefcase migrations."""

import pytest
from pathlib import Path
import toml

from nadoo_migration_framework.migrations.briefcase_migrations import UpdateBriefcaseLicenseMigration


def test_update_briefcase_license(tmp_path):
    """Test updating Briefcase license configuration."""
    # Create test project directory
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml with old license format
    pyproject_file = project_dir / "pyproject.toml"
    config = {
        "project": {
            "name": "test-project",
            "version": "0.1.0",
            "license": "Proprietary"
        }
    }
    with open(pyproject_file, "w") as f:
        toml.dump(config, f)

    # Create and run migration
    migration = UpdateBriefcaseLicenseMigration()
    migration.project_dir = project_dir

    # Check if migration is needed
    assert migration.check_if_needed()

    # Apply migration
    migration.up()

    # Verify changes
    with open(pyproject_file) as f:
        updated_config = toml.load(f)

    assert "license" in updated_config["project"]
    assert isinstance(updated_config["project"]["license"], dict)
    assert updated_config["project"]["license"]["file"] == "LICENSE"

    # Verify LICENSE file was created
    license_file = project_dir / "LICENSE"
    assert license_file.exists()
    assert license_file.read_text().strip() == "Proprietary"

    # Test rollback
    migration.down()

    # Verify rollback
    with open(pyproject_file) as f:
        rollback_config = toml.load(f)

    assert rollback_config == config


def test_update_briefcase_license_no_project(tmp_path):
    """Test migration with no project table."""
    # Create test project directory
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml without project table
    pyproject_file = project_dir / "pyproject.toml"
    config = {
        "tool": {
            "briefcase": {
                "version": "0.3.20"
            }
        }
    }
    with open(pyproject_file, "w") as f:
        toml.dump(config, f)

    # Create and run migration
    migration = UpdateBriefcaseLicenseMigration()
    migration.project_dir = project_dir

    # Check if migration is needed
    assert not migration.check_if_needed()


def test_update_briefcase_license_no_pyproject(tmp_path):
    """Test migration with no pyproject.toml."""
    # Create test project directory
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create and run migration
    migration = UpdateBriefcaseLicenseMigration()
    migration.project_dir = project_dir

    # Check if migration is needed
    assert not migration.check_if_needed()


def test_update_briefcase_license_already_pep621(tmp_path):
    """Test migration with already PEP 621 compliant license."""
    # Create test project directory
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml with PEP 621 license format
    pyproject_file = project_dir / "pyproject.toml"
    config = {
        "project": {
            "name": "test-project",
            "version": "0.1.0",
            "license": {
                "file": "LICENSE"
            }
        }
    }
    with open(pyproject_file, "w") as f:
        toml.dump(config, f)

    # Create and run migration
    migration = UpdateBriefcaseLicenseMigration()
    migration.project_dir = project_dir

    # Check if migration is needed
    assert not migration.check_if_needed()
