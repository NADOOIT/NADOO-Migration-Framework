"""Tests for Django migrator functionality."""

import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from nadoo_migration_framework.src.nadoo_migration_framework.frameworks.django import DjangoMigrator
from nadoo_migration_framework.src.nadoo_migration_framework.frameworks.django_analyzer import CompatibilityIssue


@pytest.fixture
def temp_django_project():
    """Create a temporary Django project structure."""
    with TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)

        # Create basic Django project structure
        (project_dir / "manage.py").write_text(
            """
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myapp.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        raise ImportError("Couldn't import Django")
    execute_from_command_line(sys.argv)
"""
        )
        (project_dir / "myapp").mkdir()
        (project_dir / "myapp" / "__init__.py").touch()
        (project_dir / "myapp" / "settings.py").touch()
        (project_dir / "myapp" / "urls.py").touch()

        yield project_dir


def test_migrator_initialization(temp_django_project):
    """Test Django migrator initialization."""
    migrator = DjangoMigrator(temp_django_project)

    assert migrator.project_dir == temp_django_project
    assert migrator.settings_module == "myapp.settings"
    assert migrator.settings_file == temp_django_project / "myapp" / "settings.py"
    assert migrator.urls_file == temp_django_project / "myapp" / "urls.py"
    assert migrator.analyzer is not None


def test_get_migration_steps_with_analyzer(temp_django_project, mocker):
    """Test migration step generation based on analyzer results."""
    # Create settings file with deprecated settings
    settings_file = temp_django_project / "myapp" / "settings.py"
    with open(settings_file, "w") as f:
        f.write("MIDDLEWARE_CLASSES = []")

    # Mock analyzer to return some issues
    mock_issues = [
        CompatibilityIssue(
            issue_type="deprecated_setting",
            message="MIDDLEWARE_CLASSES is deprecated",
            file=str(settings_file),
            line_number=1,
            severity="error",
            suggested_fix="Use MIDDLEWARE instead",
        ),
        CompatibilityIssue(
            issue_type="security_setting",
            message="Missing security settings",
            file=str(settings_file),
            line_number=1,
            severity="warning",
            suggested_fix="Add recommended security settings",
        ),
    ]

    migrator = DjangoMigrator(temp_django_project)
    mocker.patch.object(migrator.analyzer, 'analyze_project', return_value=mock_issues)

    steps = migrator.get_migration_steps()

    # Verify steps are generated based on issues
    step_names = [step["name"] for step in steps]
    assert "Update dependencies" in step_names
    assert "Update deprecated settings" in step_names
    assert "Update security settings" in step_names
    assert "Database migrations" in step_names  # Should always be included


def test_get_migration_steps_with_version_upgrade(temp_django_project, mocker):
    """Test migration steps for version upgrade."""
    migrator = DjangoMigrator(temp_django_project)
    migrator.current_django_version = "2.2.0"
    migrator.target_django_version = "5.0.0"

    # Mock analyzer to return no issues
    mocker.patch.object(migrator.analyzer, 'analyze_project', return_value=[])

    steps = migrator.get_migration_steps()

    # Verify version upgrade steps are included
    step_names = [step["name"] for step in steps]
    assert "Backup database" in step_names
    assert "Update Django version" in step_names
    assert "Database migrations" in step_names


def test_get_migration_steps_with_multiple_issues(temp_django_project, mocker):
    """Test migration steps with multiple types of issues."""
    urls_file = temp_django_project / "myapp" / "urls.py"
    settings_file = temp_django_project / "myapp" / "settings.py"

    # Create files with issues
    with open(urls_file, "w") as f:
        f.write("from django.conf.urls import url")

    with open(settings_file, "w") as f:
        f.write("MIDDLEWARE_CLASSES = []")

    # Mock analyzer to return multiple issues
    mock_issues = [
        CompatibilityIssue(
            issue_type="deprecated_urls",
            message="url() is deprecated",
            file=str(urls_file),
            line_number=1,
            severity="warning",
            suggested_fix="Use path() instead",
        ),
        CompatibilityIssue(
            issue_type="deprecated_setting",
            message="MIDDLEWARE_CLASSES is deprecated",
            file=str(settings_file),
            line_number=1,
            severity="error",
            suggested_fix="Use MIDDLEWARE instead",
        ),
        CompatibilityIssue(
            issue_type="security_setting",
            message="Missing security settings",
            file=str(settings_file),
            line_number=1,
            severity="warning",
            suggested_fix="Add recommended security settings",
        ),
    ]

    migrator = DjangoMigrator(temp_django_project)
    mocker.patch.object(migrator.analyzer, 'analyze_project', return_value=mock_issues)

    steps = migrator.get_migration_steps()

    # Verify all necessary steps are included
    step_names = [step["name"] for step in steps]
    assert "Update URL patterns" in step_names
    assert "Update deprecated settings" in step_names
    assert "Update security settings" in step_names
    assert "Database migrations" in step_names


def test_get_requirements(temp_django_project):
    """Test getting Django requirements."""
    migrator = DjangoMigrator(temp_django_project)
    requirements = migrator.get_requirements()

    assert any(req.startswith("django>=") for req in requirements)
    assert any(req.startswith("django-allauth>=") for req in requirements)


def test_find_settings_module(temp_django_project):
    """Test finding Django settings module."""
    migrator = DjangoMigrator(temp_django_project)
    settings_module = migrator._find_settings_module()

    assert settings_module == "myapp.settings"


def test_find_settings_file(temp_django_project):
    """Test finding Django settings file."""
    migrator = DjangoMigrator(temp_django_project)
    settings_file = migrator._find_settings_file()

    assert settings_file == temp_django_project / "myapp" / "settings.py"
    assert settings_file.exists()


def test_find_urls_file(temp_django_project):
    """Test finding Django URLs file."""
    migrator = DjangoMigrator(temp_django_project)
    urls_file = migrator._find_urls_file()

    assert urls_file == temp_django_project / "myapp" / "urls.py"
    assert urls_file.exists()
