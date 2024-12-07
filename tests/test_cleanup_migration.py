"""Test suite for project structure cleanup migration."""

import os
import shutil
import pytest
from pathlib import Path
from nadoo_migration_framework.migrations.cleanup_project_structure import CleanupProjectStructureMigration

def create_test_structure(base_path: Path):
    """Create a test project structure with actual functionality."""
    # Create old structure with real functions
    paths = [
        base_path / 'src' / 'functions',
        base_path / 'src' / 'nadoo_migration_framework' / 'functions',
        base_path / 'src' / 'nadoo_migration_framework' / 'gui',
        base_path / 'src' / 'nadoo_migration_framework' / 'migrations',
        base_path / 'src' / 'nadoo_migration_framework' / 'utils',
        base_path / 'src' / 'nadoo_migration_framework' / 'resources',
        base_path / 'tests',
        base_path / 'build',
        base_path / 'dist',
        base_path / '.pytest_cache',
    ]
    
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

    # Create test function files with actual content
    function_content = '''
def test_function():
    """Test function that returns a value."""
    return "test successful"
'''
    
    (base_path / 'src' / 'functions' / 'test_function.py').write_text(function_content)
    (base_path / 'src' / 'nadoo_migration_framework' / 'functions' / 'get_function_discovery_paths.py').write_text('''
def find_function_in_discovery_paths(function_name: str, paths: list) -> str:
    """Find a function in the discovery paths."""
    for path in paths:
        if (Path(path) / f"{function_name}.py").exists():
            return str(Path(path) / f"{function_name}.py")
    return None
''')
    
    # Create some test files
    (base_path / '.coverage').touch()
    (base_path / '.DS_Store').touch()
    (base_path / 'LICENSE').write_text('MIT License')
    (base_path / 'README.md').write_text('# Test Project')
    (base_path / 'pyproject.toml').write_text('''[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "Test project for NADOO Framework"

[tool.poetry.dependencies]
python = "^3.8"
''')

def verify_nadoo_structure(project_path: Path):
    """Verify that the project follows NADOO-Framework structure."""
    # Core NADOO-Framework directories
    assert (project_path / 'src').exists(), "src directory missing"
    project_name = project_path.name.replace('-', '_')
    project_src = project_path / 'src' / project_name
    
    required_dirs = [
        'core',
        'gui',
        'migrations',
        'resources',
        'utils',
    ]
    
    for dir_name in required_dirs:
        assert (project_src / dir_name).exists(), f"{dir_name} directory missing"
    
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
    
    # Check if functions were moved to core
    core_path = project_path / 'src' / project_name / 'core'
    assert (core_path / 'get_function_discovery_paths.py').exists(), "Function file not migrated"
    
    # Import and test the function
    import sys
    sys.path.insert(0, str(project_path / 'src'))
    
    # Test the discovery paths function
    module = __import__(f"{project_name}.core.get_function_discovery_paths", fromlist=['find_function_in_discovery_paths'])
    find_function = getattr(module, 'find_function_in_discovery_paths')
    
    test_paths = [str(core_path)]
    result = find_function('get_function_discovery_paths', test_paths)
    assert result is not None, "Function not working after migration"
    
    sys.path.pop(0)

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
    
    # Check function content after migration
    project_name = tmp_path.name.replace('-', '_')
    new_function_path = tmp_path / 'src' / project_name / 'core' / 'get_function_discovery_paths.py'
    migrated_content = new_function_path.read_text()
    
    # Verify content is preserved (ignoring whitespace)
    assert original_content.strip() == migrated_content.strip()

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
    (tmp_path / 'src' / 'nadoo_migration_framework' / 'test_imports.py').write_text(test_file_content)
    
    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success
    
    # Verify imports are updated
    project_name = tmp_path.name.replace('-', '_')
    migrated_file = tmp_path / 'src' / project_name / 'test_imports.py'
    assert migrated_file.exists()
    
    new_content = migrated_file.read_text()
    assert f"from {project_name}.core.get_function_discovery_paths" in new_content
    assert f"from {project_name}.utils.some_util" in new_content

def test_cleanup_migration_rollback(tmp_path):
    """Test that cleanup migration can be rolled back completely."""
    create_test_structure(tmp_path)
    
    # Save initial state
    initial_files = set()
    initial_contents = {}
    for path in tmp_path.rglob('*'):
        if path.is_file():
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
        if path.is_file():
            relative_path = path.relative_to(tmp_path)
            current_files.add(str(relative_path))
            assert path.read_text() == initial_contents[str(relative_path)], f"Content mismatch in {relative_path}"
    
    assert initial_files == current_files, "Not all files were restored"
