import os
import pytest
import tempfile
import shutil
from src.functions.get_project_structure_for_path import get_project_structure_for_path

@pytest.fixture
def test_project():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create test files
    files = {
        'function.py': '''
def test_function():
    return "test"
''',
        'class_file.py': '''
class TestClass:
    def __init__(self):
        pass
''',
        'process.py': '''
import zmq
class ProcessManager:
    pass
''',
        'types.py': '''
from typing import TypeAlias
MyType = TypeAlias = str
'''
    }
    
    # Write test files
    for filename, content in files.items():
        with open(os.path.join(temp_dir, filename), 'w') as f:
            f.write(content)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

def test_get_project_structure(test_project):
    """Test that project structure is correctly analyzed."""
    structure = get_project_structure_for_path(test_project)
    
    # Check that each file is categorized correctly
    assert any('function.py' in f for f in structure['functions'])
    assert any('class_file.py' in f for f in structure['classes'])
    assert any('process.py' in f for f in structure['processes'])
    assert any('types.py' in f for f in structure['types'])
    
    # Check that files are categorized uniquely
    all_files = []
    for category in structure.values():
        all_files.extend(category)
    assert len(all_files) == len(set(all_files)), "Files should not be in multiple categories"
