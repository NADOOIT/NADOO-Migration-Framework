import os
import pytest
import tempfile
import shutil
from src.functions.create_standard_directory_structure_for_path import (
    create_standard_directory_structure_for_path,
)


@pytest.fixture
def test_dir():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir)


def test_create_directory_structure(test_dir):
    """Test that directory structure is created correctly."""
    created_dirs = create_standard_directory_structure_for_path(test_dir)

    # Expected directories
    expected_dirs = [
        os.path.join(test_dir, 'src/functions'),
        os.path.join(test_dir, 'src/classes'),
        os.path.join(test_dir, 'src/processes'),
        os.path.join(test_dir, 'src/types'),
        os.path.join(test_dir, 'tests'),
        os.path.join(test_dir, 'logs'),
    ]

    # Check all expected directories exist
    for dir_path in expected_dirs:
        assert os.path.exists(dir_path), f"Directory {dir_path} was not created"
        assert os.path.isdir(dir_path), f"{dir_path} is not a directory"

    # Check __init__.py files exist in Python packages
    for dir_path in expected_dirs:
        if dir_path.startswith(os.path.join(test_dir, 'src/')):
            init_file = os.path.join(dir_path, '__init__.py')
            assert os.path.exists(init_file), f"__init__.py not created in {dir_path}"

            # Check content of __init__.py
            with open(init_file, 'r') as f:
                content = f.read()
                dir_type = os.path.basename(dir_path)
                assert f'contains {dir_type}' in content, f"Incorrect content in {init_file}"
