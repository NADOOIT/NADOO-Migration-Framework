import os
import pytest
import tempfile
import shutil
from src.functions.extract_function_from_file_to_new_file import (
    extract_function_from_file_to_new_file,
)


@pytest.fixture
def test_files():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # Create source file with function and imports
    source_content = '''
import os
from typing import List

def test_function(param: str) -> List[str]:
    """Test function docstring."""
    return [param]

def another_function():
    pass
'''

    source_file = os.path.join(temp_dir, 'source.py')
    with open(source_file, 'w') as f:
        f.write(source_content)

    yield temp_dir, source_file

    # Cleanup
    shutil.rmtree(temp_dir)


def test_extract_function(test_files):
    """Test that function extraction works correctly."""
    temp_dir, source_file = test_files
    target_dir = os.path.join(temp_dir, 'functions')
    os.makedirs(target_dir)

    # Extract the function
    new_file = extract_function_from_file_to_new_file(source_file, 'test_function', target_dir)

    # Check that new file was created
    assert new_file is not None
    assert os.path.exists(new_file)

    # Check content of new file
    with open(new_file, 'r') as f:
        content = f.read()

        # Check that imports were included
        assert 'import os' in content
        assert 'from typing import List' in content

        # Check that function was included
        assert 'def test_function(param: str) -> List[str]:' in content
        assert '"""Test function docstring."""' in content

        # Check that only the target function was included
        assert 'another_function' not in content


def test_extract_nonexistent_function(test_files):
    """Test that extracting a nonexistent function returns None."""
    temp_dir, source_file = test_files
    target_dir = os.path.join(temp_dir, 'functions')
    os.makedirs(target_dir)

    result = extract_function_from_file_to_new_file(source_file, 'nonexistent_function', target_dir)
    assert result is None
