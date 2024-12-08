import os
import pytest
import tempfile
import shutil
from nadoo_migration_framework.src.nadoo_migration_framework.functions.get_function_discovery_paths import (
    get_function_discovery_paths,
    find_function_in_discovery_paths,
)
from nadoo_migration_framework.src.nadoo_migration_framework.classes.FeedManager import FeedManager
from tests.test_utils import TestElement


@pytest.fixture
def test_apps():
    # Create a temporary directory structure with multiple apps
    temp_dir = tempfile.mkdtemp()

    # Create app1
    app1_dir = os.path.join(temp_dir, 'app1')
    os.makedirs(os.path.join(app1_dir, 'src', 'app1', 'functions'))

    # Create app2
    app2_dir = os.path.join(temp_dir, 'app2')
    os.makedirs(os.path.join(app2_dir, 'src', 'app2', 'functions'))

    # Create test functions
    test_func1 = '''
from tests.test_utils import TestElement

def test_function1(arg1, arg2):
    return TestElement("test1", f"{arg1}, {arg2}")
'''

    test_func2 = '''
from tests.test_utils import TestElement

def test_function2(arg1):
    return TestElement("test2", f"{arg1}")
'''

    # Write functions to different apps
    with open(os.path.join(app1_dir, 'src', 'app1', 'functions', 'test_function1.py'), 'w') as f:
        f.write(test_func1)

    with open(os.path.join(app2_dir, 'src', 'app2', 'functions', 'test_function2.py'), 'w') as f:
        f.write(test_func2)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_function_discovery(test_apps):
    """Test that functions can be discovered across different apps."""
    # Get discovery paths
    paths = get_function_discovery_paths(test_apps)
    assert len(paths) == 2, "Should find functions directories from both apps"

    # Find specific functions
    func1_path = find_function_in_discovery_paths('test_function1', paths)
    func2_path = find_function_in_discovery_paths('test_function2', paths)

    assert func1_path is not None, "Should find test_function1"
    assert func2_path is not None, "Should find test_function2"
    assert 'app1' in func1_path, "test_function1 should be in app1"
    assert 'app2' in func2_path, "test_function2 should be in app2"


def test_feed_manager_function_discovery(test_apps):
    """Test that FeedManager can find and execute functions from different apps."""
    manager = FeedManager.get_instance()
    manager.set_base_path(test_apps)

    # Try to create elements using functions from different apps
    try:
        element1 = manager.create_element('test_function1', 'hello', 'world')
        assert element1 is not None, "Should create element using test_function1"
        assert isinstance(element1, TestElement), "Should return TestElement instance"

        element2 = manager.create_element('test_function2', 'test')
        assert element2 is not None, "Should create element using test_function2"
        assert isinstance(element2, TestElement), "Should return TestElement instance"

    finally:
        manager.cleanup()
        FeedManager._instance = None  # Reset singleton for other tests


def test_nested_app_structure(test_apps):
    """Test function discovery in deeply nested app structures."""
    # Create a nested app structure
    nested_app_dir = os.path.join(test_apps, 'nested', 'deep', 'app3')
    os.makedirs(os.path.join(nested_app_dir, 'src', 'app3', 'functions'))

    test_func3 = '''
from tests.test_utils import TestElement

def test_function3(arg1):
    return TestElement("test3", f"{arg1}")
'''

    with open(
        os.path.join(nested_app_dir, 'src', 'app3', 'functions', 'test_function3.py'), 'w'
    ) as f:
        f.write(test_func3)

    paths = get_function_discovery_paths(test_apps)
    assert len(paths) == 3, "Should find functions directories from all apps including nested ones"

    func3_path = find_function_in_discovery_paths('test_function3', paths)
    assert func3_path is not None, "Should find function in nested app structure"


def test_malformed_app_structure(test_apps):
    """Test handling of malformed app directory structures."""
    # Create malformed app directories
    malformed1 = os.path.join(test_apps, 'malformed1', 'src')  # Missing functions dir
    malformed2 = os.path.join(test_apps, 'malformed2', 'functions')  # Missing src dir
    os.makedirs(malformed1)
    os.makedirs(malformed2)

    paths = get_function_discovery_paths(test_apps)
    original_path_count = len(paths)

    # Verify malformed directories are not included
    assert len([p for p in paths if 'malformed1' in p]) == 0
    assert len([p for p in paths if 'malformed2' in p]) == 0


def test_concurrent_function_discovery():
    """Test concurrent function discovery from multiple threads."""
    import threading
    import queue

    results_queue = queue.Queue()

    def discover_functions(test_apps, thread_id):
        paths = get_function_discovery_paths(test_apps)
        results_queue.put((thread_id, paths))

    # Create temporary test directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Create test app structure
        app_dir = os.path.join(temp_dir, 'app')
        os.makedirs(os.path.join(app_dir, 'src', 'app', 'functions'))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=discover_functions, args=(temp_dir, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        assert len(results) == 5, "All threads should complete"

        # All threads should find the same paths
        first_paths = results[0][1]
        for _, paths in results[1:]:
            assert paths == first_paths, "All threads should discover the same paths"

    finally:
        shutil.rmtree(temp_dir)


def test_function_versioning(test_apps):
    """Test handling of multiple function versions."""
    # Create two versions of the same function in different apps
    app3_dir = os.path.join(test_apps, 'app3')
    os.makedirs(os.path.join(app3_dir, 'src', 'app3', 'functions'))

    test_func_v1 = '''
from tests.test_utils import TestElement

def shared_function(arg1):
    return TestElement("shared1", f"{arg1}")
'''

    test_func_v2 = '''
from tests.test_utils import TestElement

def shared_function(arg1):
    return TestElement("shared2", f"{arg1}")
'''

    # Write different versions to different apps
    with open(os.path.join(app3_dir, 'src', 'app3', 'functions', 'shared_function.py'), 'w') as f:
        f.write(test_func_v1)

    with open(
        os.path.join(
            os.path.join(test_apps, 'app1'), 'src', 'app1', 'functions', 'shared_function.py'
        ),
        'w',
    ) as f:
        f.write(test_func_v2)

    paths = get_function_discovery_paths(test_apps)

    # Find all instances of the shared function
    shared_func_paths = [p for p in paths if os.path.exists(os.path.join(p, 'shared_function.py'))]
    assert len(shared_func_paths) == 2, "Should find both versions of the shared function"


def test_error_handling():
    """Test error handling in function discovery."""
    # Test with non-existent directory
    paths = get_function_discovery_paths("/nonexistent/path")
    assert len(paths) == 0, "Should handle non-existent directory gracefully"

    # Test with invalid path type
    with pytest.raises(TypeError):
        get_function_discovery_paths(None)

    # Test finding non-existent function
    paths = get_function_discovery_paths(os.getcwd())
    result = find_function_in_discovery_paths("nonexistent_function", paths)
    assert result is None, "Should return None for non-existent function"
