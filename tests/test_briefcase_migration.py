"""Tests for the Briefcase migration functionality."""

import os
import shutil
import tempfile
import pytest
from nadoo_migration_framework.src.nadoo_migration_framework.functions.migrate_to_briefcase import (
    migrate_project,
    get_app_name,
    create_briefcase_structure,
    update_imports,
)
from nadoo_migration_framework.src.nadoo_migration_framework.functions.migrate_to_briefcase import (
    migrate_files,
    update_pyproject_toml,
)


@pytest.fixture
def test_project():
    """Create a test project with the old structure."""
    temp_dir = tempfile.mkdtemp()

    # Create old structure
    os.makedirs(os.path.join(temp_dir, 'src', 'functions'))
    os.makedirs(os.path.join(temp_dir, 'src', 'classes'))
    os.makedirs(os.path.join(temp_dir, 'src', 'processes'))

    # Create test files
    test_function = '''
from src.classes.test_class import TestClass
from ..processes.test_process import test_process

def test_function():
    return TestClass().process(test_process())
'''

    test_class = '''
from ..functions.test_function import test_function

class TestClass:
    def process(self, data):
        return test_function()
'''

    test_process = '''
from src.functions.test_function import test_function

def test_process():
    return test_function()
'''

    # Create pyproject.toml
    pyproject = '''
[tool.poetry]
name = "test-app"
version = "0.1.0"
packages = [{ include = "src" }]
'''

    # Write files
    with open(os.path.join(temp_dir, 'src', 'functions', 'test_function.py'), 'w') as f:
        f.write(test_function)
    with open(os.path.join(temp_dir, 'src', 'classes', 'test_class.py'), 'w') as f:
        f.write(test_class)
    with open(os.path.join(temp_dir, 'src', 'processes', 'test_process.py'), 'w') as f:
        f.write(test_process)
    with open(os.path.join(temp_dir, 'pyproject.toml'), 'w') as f:
        f.write(pyproject)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_get_app_name(test_project):
    """Test app name extraction."""
    app_name = get_app_name(test_project)
    assert app_name == "test-app"

    # Test fallback to directory name
    os.remove(os.path.join(test_project, 'pyproject.toml'))
    app_name = get_app_name(test_project)
    assert app_name == os.path.basename(test_project)


def test_create_briefcase_structure(test_project):
    """Test creation of Briefcase structure."""
    app_name = "test-app"
    path_mapping = create_briefcase_structure(test_project, app_name)

    # Check new structure exists
    new_src_path = os.path.join(test_project, app_name, 'src', app_name)
    assert os.path.exists(new_src_path)
    assert os.path.exists(os.path.join(new_src_path, '__init__.py'))

    for dir_name in ['functions', 'classes', 'processes']:
        dir_path = os.path.join(new_src_path, dir_name)
        assert os.path.exists(dir_path)
        assert os.path.exists(os.path.join(dir_path, '__init__.py'))


def test_update_imports(test_project):
    """Test import statement updates."""
    test_file = os.path.join(test_project, 'test.py')
    content = '''
from src.functions.test import func
from ..classes.test import TestClass
from .processes.test import process
'''

    with open(test_file, 'w') as f:
        f.write(content)

    update_imports(test_file, 'test-app')

    with open(test_file, 'r') as f:
        updated = f.read()

    assert 'from test-app.functions.test import func' in updated
    assert 'from test-app.classes.test import TestClass' in updated
    assert 'from test-app.processes.test import process' in updated


def test_migrate_files(test_project):
    """Test file migration."""
    app_name = "test-app"
    path_mapping = create_briefcase_structure(test_project, app_name)
    migrate_files(path_mapping, app_name)

    # Check files were migrated
    new_src_path = os.path.join(test_project, app_name, 'src', app_name)
    assert os.path.exists(os.path.join(new_src_path, 'functions', 'test_function.py'))
    assert os.path.exists(os.path.join(new_src_path, 'classes', 'test_class.py'))
    assert os.path.exists(os.path.join(new_src_path, 'processes', 'test_process.py'))


def test_update_pyproject_toml(test_project):
    """Test pyproject.toml updates."""
    app_name = "test-app"
    update_pyproject_toml(test_project, app_name)

    with open(os.path.join(test_project, 'pyproject.toml'), 'r') as f:
        content = f.read()

    assert f'packages = [{{ include = "{app_name}"' in content


def test_full_migration(test_project):
    """Test complete project migration."""
    migrate_project(test_project)

    app_name = "test-app"
    new_src_path = os.path.join(test_project, app_name, 'src', app_name)

    # Check structure
    assert os.path.exists(new_src_path)
    assert os.path.exists(os.path.join(new_src_path, '__init__.py'))

    # Check files
    assert os.path.exists(os.path.join(new_src_path, 'functions', 'test_function.py'))
    assert os.path.exists(os.path.join(new_src_path, 'classes', 'test_class.py'))
    assert os.path.exists(os.path.join(new_src_path, 'processes', 'test_process.py'))

    # Check imports in migrated files
    with open(os.path.join(new_src_path, 'functions', 'test_function.py'), 'r') as f:
        content = f.read()
        assert 'from test-app.classes.test_class import TestClass' in content
        assert 'from test-app.processes.test_process import test_process' in content

    # Check backup
    assert os.path.exists(os.path.join(test_project, 'src.bak'))
