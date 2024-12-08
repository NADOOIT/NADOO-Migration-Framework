import os
import pytest
import tempfile
import shutil
from src.classes.ProjectMigrator import ProjectMigrator


@pytest.fixture
def test_project():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # Create test project structure
    files = {
        'function_file.py': '''
def test_function():
    return "test"
''',
        'class_file.py': '''
class TestClass:
    def __init__(self):
        pass
''',
        'process_file.py': '''
import zmq
class ProcessManager:
    pass
''',
        'type_file.py': '''
from typing import TypeAlias
MyType = TypeAlias = str
''',
    }

    # Write test files
    for filename, content in files.items():
        with open(os.path.join(temp_dir, filename), 'w') as f:
            f.write(content)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_project_migration(test_project):
    """Test that project migration works correctly."""
    # Create and run migrator
    migrator = ProjectMigrator(test_project)
    success = migrator.migrate()

    assert success, "Migration should succeed"

    # Check that new structure was created
    assert os.path.exists(os.path.join(test_project, 'src/functions'))
    assert os.path.exists(os.path.join(test_project, 'src/classes'))
    assert os.path.exists(os.path.join(test_project, 'src/processes'))
    assert os.path.exists(os.path.join(test_project, 'src/types'))

    # Check that files were moved correctly
    assert os.path.exists(os.path.join(test_project, 'src/functions/test_function.py'))
    assert os.path.exists(os.path.join(test_project, 'src/classes/class_file.py'))
    assert os.path.exists(os.path.join(test_project, 'src/processes/process_file.py'))
    assert os.path.exists(os.path.join(test_project, 'src/types/type_file.py'))

    # Check that log file was created
    assert os.path.exists(os.path.join(test_project, 'logs/migration.log'))


def test_project_migration_empty_project(tmpdir):
    """Test that migrating an empty project works."""
    migrator = ProjectMigrator(str(tmpdir))
    success = migrator.migrate()

    assert success, "Migration of empty project should succeed"
    assert os.path.exists(os.path.join(str(tmpdir), 'src/functions'))
    assert os.path.exists(os.path.join(str(tmpdir), 'logs/migration.log'))
