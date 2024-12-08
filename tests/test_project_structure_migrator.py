"""Tests for the project structure migrator."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from nadoo_migration_framework.functions.project_structure_migrator import (
    ProjectStructure,
    detect_project_structure,
    get_app_name,
    normalize_app_name,
    create_briefcase_structure,
    update_imports,
    migrate_project,
)


def create_test_project(tmp_path: Path, structure: ProjectStructure, app_name: str = "test_app"):
    """Create a test project with the specified structure."""
    if structure == ProjectStructure.LEGACY:
        # Create legacy structure
        src_path = tmp_path / "src"
        for dir_name in ["functions", "classes", "processes"]:
            (src_path / dir_name).mkdir(parents=True)
            with open(src_path / dir_name / "__init__.py", "w") as f:
                f.write(f'"""Test {dir_name}."""\n')

        # Create a test file with imports
        with open(src_path / "functions" / "test.py", "w") as f:
            f.write('from src.classes import TestClass\n')
            f.write('import src.processes.test_process\n')

    else:
        # Create Briefcase structure
        normalized_name = normalize_app_name(app_name, structure)
        app_path = tmp_path / normalized_name / "src" / normalized_name
        for dir_name in ["functions", "classes", "processes"]:
            (app_path / dir_name).mkdir(parents=True)
            with open(app_path / dir_name / "__init__.py", "w") as f:
                f.write(f'"""Test {dir_name}."""\n')

        # Create a test file with imports
        with open(app_path / "functions" / "test.py", "w") as f:
            f.write(f'from {normalized_name}.classes import TestClass\n')
            f.write(f'import {normalized_name}.processes.test_process\n')

    # Create pyproject.toml
    with open(tmp_path / "pyproject.toml", "w") as f:
        f.write(f'[tool.poetry]\nname = "{app_name}"\nversion = "0.1.0"\n')

    return tmp_path


def test_detect_project_structure(tmp_path):
    """Test project structure detection."""
    # Test legacy structure
    legacy_path = create_test_project(tmp_path / "legacy", ProjectStructure.LEGACY)
    assert detect_project_structure(legacy_path) == ProjectStructure.LEGACY

    # Test dash-based Briefcase structure
    dash_path = create_test_project(tmp_path / "dash", ProjectStructure.BRIEFCASE_DASH, "test-app")
    assert detect_project_structure(dash_path) == ProjectStructure.BRIEFCASE_DASH

    # Test underscore-based Briefcase structure
    underscore_path = create_test_project(
        tmp_path / "underscore", ProjectStructure.BRIEFCASE_UNDERSCORE, "test_app"
    )
    assert detect_project_structure(underscore_path) == ProjectStructure.BRIEFCASE_UNDERSCORE


def test_get_app_name(tmp_path):
    """Test app name extraction."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # Test with pyproject.toml
    with open(project_path / "pyproject.toml", "w") as f:
        f.write('[tool.poetry]\nname = "test_app"\nversion = "0.1.0"\n')
    assert get_app_name(str(project_path)) == "test_app"

    # Test without pyproject.toml
    os.remove(project_path / "pyproject.toml")
    assert get_app_name(str(project_path)) == "test_project"


def test_normalize_app_name():
    """Test app name normalization."""
    # Test dash to underscore
    assert normalize_app_name("test-app", ProjectStructure.BRIEFCASE_UNDERSCORE) == "test_app"

    # Test underscore to dash
    assert normalize_app_name("test_app", ProjectStructure.BRIEFCASE_DASH) == "test-app"

    # Test no change needed
    assert normalize_app_name("test_app", ProjectStructure.BRIEFCASE_UNDERSCORE) == "test_app"
    assert normalize_app_name("test-app", ProjectStructure.BRIEFCASE_DASH) == "test-app"


def test_create_briefcase_structure(tmp_path):
    """Test Briefcase structure creation."""
    project_path = str(tmp_path)
    app_name = "test_app"

    path_mapping = create_briefcase_structure(project_path, app_name)

    # Check that directories were created
    assert os.path.exists(os.path.join(project_path, app_name, "src", app_name))
    for dir_name in ["functions", "classes", "processes"]:
        dir_path = os.path.join(project_path, app_name, "src", app_name, dir_name)
        assert os.path.exists(dir_path)
        assert os.path.exists(os.path.join(dir_path, "__init__.py"))


def test_update_imports(tmp_path):
    """Test import statement updates."""
    test_file = tmp_path / "test.py"

    # Test legacy to Briefcase
    with open(test_file, "w") as f:
        f.write('from src.classes import TestClass\n')
        f.write('import src.processes.test_process\n')

    update_imports(
        str(test_file), "test_app", ProjectStructure.LEGACY, ProjectStructure.BRIEFCASE_UNDERSCORE
    )

    with open(test_file) as f:
        content = f.read()
        assert 'from test_app.classes import TestClass' in content
        assert 'import test_app.processes.test_process' in content

    # Test dash to underscore
    with open(test_file, "w") as f:
        f.write('from test-app.classes import TestClass\n')
        f.write('import test-app.processes.test_process\n')

    update_imports(
        str(test_file),
        "test-app",
        ProjectStructure.BRIEFCASE_DASH,
        ProjectStructure.BRIEFCASE_UNDERSCORE,
    )

    with open(test_file) as f:
        content = f.read()
        assert 'from test_app.classes import TestClass' in content
        assert 'import test_app.processes.test_process' in content


def test_migrate_project(tmp_path):
    """Test complete project migration."""
    # Create a legacy project
    legacy_path = create_test_project(
        tmp_path / "test_project", ProjectStructure.LEGACY, "test_app"
    )

    # Migrate to underscore-based Briefcase
    migrate_project(str(legacy_path))

    # Check that the project was migrated correctly
    assert os.path.exists(legacy_path / "test_app" / "src" / "test_app")
    assert os.path.exists(legacy_path / "src.bak")

    # Check import updates in migrated files
    with open(legacy_path / "test_app" / "src" / "test_app" / "functions" / "test.py") as f:
        content = f.read()
        assert 'from test_app.classes import TestClass' in content
        assert 'import test_app.processes.test_process' in content

    # Check pyproject.toml updates
    with open(legacy_path / "pyproject.toml") as f:
        content = f.read()
        assert 'name = "test_app"' in content


def test_migrate_dash_to_underscore(tmp_path):
    """Test migration from dash-based to underscore-based Briefcase."""
    # Create a dash-based project
    dash_path = create_test_project(
        tmp_path / "test_project", ProjectStructure.BRIEFCASE_DASH, "test-app"
    )

    # Migrate to underscore-based Briefcase
    migrate_project(str(dash_path))

    # Check that the project was migrated correctly
    assert os.path.exists(dash_path / "test_app" / "src" / "test_app")

    # Check import updates in migrated files
    with open(dash_path / "test_app" / "src" / "test_app" / "functions" / "test.py") as f:
        content = f.read()
        assert 'from test_app.classes import TestClass' in content
        assert 'import test_app.processes.test_process' in content

    # Check pyproject.toml updates
    with open(dash_path / "pyproject.toml") as f:
        content = f.read()
        assert 'name = "test_app"' in content
