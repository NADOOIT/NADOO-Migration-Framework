"""Test suite for project structure cleanup migration."""

import os
import shutil
import pytest
from pathlib import Path
from nadoo_migration_framework.migrations.cleanup_project_structure import (
    CleanupProjectStructureMigration,
)


def create_test_structure(base_path: Path):
    """Create a test project structure with actual functionality."""
    print(f"\nCreating test structure in {base_path}")

    # Create both old and new structure with real functions
    paths = [
        # Old structure
        base_path / 'src' / 'functions',
        base_path / 'src' / 'classes',
        base_path / 'src' / 'gui',
        base_path / 'src' / 'migrations',
        base_path / 'src' / 'utils',
        base_path / 'src' / 'resources',
        base_path / 'src' / 'types',
        # New structure
        base_path / 'src' / 'nadoo_migration_framework' / 'functions',
        base_path / 'src' / 'nadoo_migration_framework' / 'classes',
        base_path / 'src' / 'nadoo_migration_framework' / 'gui',
        base_path / 'src' / 'nadoo_migration_framework' / 'migrations',
        base_path / 'src' / 'nadoo_migration_framework' / 'utils',
        base_path / 'src' / 'nadoo_migration_framework' / 'resources',
        base_path / 'src' / 'nadoo_migration_framework' / 'types',
        # Other directories
        base_path / 'tests',
        base_path / 'build',
        base_path / 'dist',
        base_path / '.pytest_cache'
    ]

    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {path}")

    # Create test function files with actual content
    function_content = '''from pathlib import Path

def test_function():
    """Test function that returns test."""
    return "test"
'''

    get_function_discovery_content = '''from pathlib import Path

def find_function_in_discovery_paths():
    """Find function in discovery paths."""
    return "test"
'''

    # Create function files in both old and new structure
    # Old structure
    (base_path / 'src' / 'functions' / 'test_function.py').write_text(function_content)
    print(f"Created test function file (old): {base_path / 'src' / 'functions' / 'test_function.py'}")

    (base_path / 'src' / 'functions' / 'get_function_discovery_paths.py').write_text(get_function_discovery_content)
    print(f"Created discovery paths file (old): {base_path / 'src' / 'functions' / 'get_function_discovery_paths.py'}")

    # New structure
    (base_path / 'src' / 'nadoo_migration_framework' / 'functions' / 'test_function.py').write_text(function_content)
    print(f"Created test function file (new): {base_path / 'src' / 'nadoo_migration_framework' / 'functions' / 'test_function.py'}")

    (base_path / 'src' / 'nadoo_migration_framework' / 'functions' / 'get_function_discovery_paths.py').write_text(get_function_discovery_content)
    print(f"Created discovery paths file (new): {base_path / 'src' / 'nadoo_migration_framework' / 'functions' / 'get_function_discovery_paths.py'}")

    # Create __init__.py files in both structures
    for path in paths:
        if 'src' in str(path):
            init_file = path / '__init__.py'
            init_file.touch()
            print(f"Created __init__.py: {init_file}")

    # Create root __init__.py files
    root_init = base_path / 'src' / '__init__.py'
    root_init.touch()
    print(f"Created root __init__.py: {root_init}")

    pkg_init = base_path / 'src' / 'nadoo_migration_framework' / '__init__.py'
    pkg_init.touch()
    print(f"Created package __init__.py: {pkg_init}")

    # Create some test files
    (base_path / '.coverage').touch()
    print(f"Created .coverage file: {base_path / '.coverage'}")

    (base_path / '.DS_Store').touch()
    print(f"Created .DS_Store file: {base_path / '.DS_Store'}")

    (base_path / 'LICENSE').write_text('MIT License')
    print(f"Created LICENSE file: {base_path / 'LICENSE'}")

    (base_path / 'README.md').write_text('# Test Project')
    print(f"Created README.md file: {base_path / 'README.md'}")

    (base_path / 'pyproject.toml').write_text(
        '''[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "Test project for NADOO-Framework migration"

[tool.poetry.dependencies]
python = "^3.8"
'''
    )
    print(f"Created pyproject.toml file: {base_path / 'pyproject.toml'}")


def verify_nadoo_structure(project_path: Path):
    """Verify that the project follows NADOO-Framework structure."""
    # Core NADOO-Framework directories
    assert (project_path / 'src').exists(), "src directory missing"
    project_name = project_path.name.replace('-', '_')
    project_src = project_path / 'src' / project_name

    required_dirs = [
        'classes',
        'migrations',
        'resources',
        'functions',
        'types',
    ]

    for dir_name in required_dirs:
        assert (project_src / dir_name).exists(), f"{dir_name} directory missing"
        assert (project_src / dir_name / '__init__.py').exists(), f"{dir_name}/__init__.py missing"

    # Required project files
    required_files = [
        'pyproject.toml',
        'README.md',
        'LICENSE',
    ]

    for file_name in required_files:
        assert (project_path / file_name).exists(), f"{file_name} missing"
        assert (project_path / file_name).stat().st_size > 0, f"{file_name} is empty"


def verify_function_preservation(project_path: Path):
    """Verify that all functions are preserved and working."""
    project_name = project_path.name.replace('-', '_')

    # Check if functions were moved to functions directory
    functions_path = project_path / 'src' / project_name / 'functions'
    assert (functions_path / 'get_function_discovery_paths.py').exists(), "Function file not migrated"

    # Import and test the function
    import sys

    sys.path.insert(0, str(project_path / 'src'))

    # Test the discovery paths function
    module = __import__(
        f"{project_name}.functions.get_function_discovery_paths",
        fromlist=['find_function_in_discovery_paths'],
    )
    find_function = getattr(module, 'find_function_in_discovery_paths')

    test_paths = [str(functions_path)]
    result = find_function()
    assert result is not None, "Function not working after migration"


def test_cleanup_migration_nadoo_structure(tmp_path):
    """Test that cleanup migration creates proper NADOO-Framework structure."""
    # Create test project
    create_test_structure(tmp_path)

    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success

    # Verify NADOO-Framework structure
    verify_nadoo_structure(tmp_path)

    # Verify functions were preserved
    verify_function_preservation(tmp_path)


def test_cleanup_migration_no_data_loss(tmp_path):
    """Test that cleanup migration preserves all important data."""
    create_test_structure(tmp_path)

    # Get initial function content
    orig_function_path = tmp_path / 'src' / 'nadoo_migration_framework' / 'functions' / 'get_function_discovery_paths.py'
    original_content = orig_function_path.read_text()

    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success

    # Get migrated function content
    project_name = tmp_path.name.replace('-', '_')
    new_function_path = (
        tmp_path
        / 'src'
        / project_name
        / 'functions'
        / 'get_function_discovery_paths.py'
    )
    migrated_content = new_function_path.read_text()

    # Check content preservation
    assert migrated_content == original_content, "Function content changed during migration"


def test_cleanup_migration_removes_clutter(tmp_path):
    """Test that cleanup migration removes unnecessary files and directories."""
    create_test_structure(tmp_path)

    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success

    # Check that clutter is removed
    clutter_files = ['.DS_Store', '.coverage']
    clutter_dirs = ['build', 'dist', '.pytest_cache']

    for file in clutter_files:
        assert not (tmp_path / file).exists(), f"Clutter file {file} not removed"

    for dir_name in clutter_dirs:
        assert not (tmp_path / dir_name).exists(), f"Clutter directory {dir_name} not removed"


def test_cleanup_migration_imports_update(tmp_path):
    """Test that imports are properly updated after migration."""
    create_test_structure(tmp_path)

    # Create a file with imports
    test_file_content = '''
from nadoo_migration_framework.functions.get_function_discovery_paths import find_function_in_discovery_paths
from nadoo_migration_framework.utils.some_util import util_function
'''
    (tmp_path / 'src' / 'test_imports.py').write_text(
        test_file_content
    )

    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success

    # Verify imports are updated
    project_name = tmp_path.name.replace('-', '_')
    migrated_file = tmp_path / 'src' / project_name / 'test_imports.py'
    assert migrated_file.exists()

    new_content = migrated_file.read_text()
    assert f"from {project_name}.functions.get_function_discovery_paths" in new_content
    assert f"from {project_name}.utils.some_util" in new_content


def test_cleanup_migration_rollback(tmp_path):
    """Test that cleanup migration can be rolled back completely."""
    create_test_structure(tmp_path)

    # Save initial state
    initial_files = set()
    initial_contents = {}
    for path in tmp_path.rglob('*'):
        if path.is_file() and path.name not in ['.gitignore']:  # Ignore generated files
            relative_path = path.relative_to(tmp_path)
            initial_files.add(str(relative_path))
            initial_contents[str(relative_path)] = path.read_text()

    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success

    # Run rollback
    success = migration.rollback(str(tmp_path))
    assert success

    # Verify all files are restored
    current_files = set()
    for path in tmp_path.rglob('*'):
        if path.is_file() and path.name not in ['.gitignore']:  # Ignore generated files
            relative_path = path.relative_to(tmp_path)
            current_files.add(str(relative_path))
            assert (
                path.read_text() == initial_contents[str(relative_path)]
            ), f"Content mismatch in {relative_path}"

    # Verify all original files are present
    assert current_files == initial_files
