import os
import pytest
import tempfile
import shutil
from src.functions.convert_to_briefcase_toga import convert_to_briefcase_toga
from src.functions.update_feed_manager import update_feed_manager

@pytest.fixture
def test_project():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create test project structure
    files = {
        'src/main_window.py': '''
def create_main_window(data):
    window = MainWindow('Test')
    return window
''',
        'src/feed_manager.py': '''
from .FeedManager import FeedManager

def process_data():
    manager = FeedManager.get_instance()
    manager.create_element('test_function', 'arg1', 'arg2')
'''
    }
    
    # Write test files
    for file_path, content in files.items():
        full_path = os.path.join(temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
            
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

def test_briefcase_toga_conversion(test_project):
    """Test that project is correctly converted to a briefcase toga app."""
    success = convert_to_briefcase_toga(test_project, 'testapp', 'Test App')
    assert success, "Conversion to briefcase toga app should succeed"
    
    # Check that pyproject.toml was created
    assert os.path.exists(os.path.join(test_project, 'pyproject.toml'))
    
    # Check that app directory was created
    assert os.path.exists(os.path.join(test_project, 'src', 'testapp'))
    assert os.path.exists(os.path.join(test_project, 'src', 'testapp', 'resources'))
    
    # Check that __main__.py was created
    assert os.path.exists(os.path.join(test_project, 'src', 'testapp', '__main__.py'))

def test_feed_manager_update(test_project):
    """Test that FeedManager code is correctly updated."""
    success = update_feed_manager(test_project)
    assert success, "FeedManager update should succeed"
    
    # Check that main window was updated
    with open(os.path.join(test_project, 'src', 'main_window.py'), 'r') as f:
        content = f.read()
        assert 'def get_main_window_element_for_data:' in content
        
    # Check that FeedManager usage was updated
    with open(os.path.join(test_project, 'src', 'feed_manager.py'), 'r') as f:
        content = f.read()
        assert 'from nadoo_framework.feed_manager import FeedManager' in content
        assert 'add_element_to_feed(' in content
