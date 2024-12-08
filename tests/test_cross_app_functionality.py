import os
import pytest
import tempfile
import shutil
import json
from nadoo_migration_framework.src.nadoo_migration_framework.functions.get_function_discovery_paths import (
    get_function_discovery_paths,
)
from nadoo_migration_framework.src.nadoo_migration_framework.classes.FeedManager import FeedManager


class MockFeed:
    def __init__(self):
        self.elements = []

    def add(self, element):
        self.elements.append(element)

    def update(self, element):
        for i, e in enumerate(self.elements):
            if e.get('id') == element.get('id'):
                self.elements[i] = element

    def remove(self, element):
        self.elements = [e for e in self.elements if e.get('id') != element.get('id')]


class TestElement:
    def __init__(self, element_id, data):
        self.id = element_id
        self.data = data
        self.is_complete = False
        self.is_hidden = False

    def get_id(self):
        return self.id

    def get_card(self):
        return {
            'id': self.id,
            'data': self.data,
            'complete': self.is_complete,
            'hidden': self.is_hidden,
        }

    def complete(self):
        self.is_complete = True

    def hide(self):
        self.is_hidden = True


@pytest.fixture
def test_apps():
    # Create a temporary directory structure with multiple apps
    temp_dir = tempfile.mkdtemp()

    # Create app1 (main app)
    app1_dir = os.path.join(temp_dir, 'app1')
    os.makedirs(os.path.join(app1_dir, 'src', 'app1', 'functions'))

    # Create app2 (secondary app)
    app2_dir = os.path.join(temp_dir, 'app2')
    os.makedirs(os.path.join(app2_dir, 'src', 'app2', 'functions'))

    # Create test functions for app1
    test_element_func = '''
from typing import Dict, Any

class TestElement:
    def __init__(self, element_id: str, data: Any):
        self.id = element_id
        self.data = data
        self.is_complete = False
        self.is_hidden = False
        
    def get_id(self):
        return self.id
        
    def get_card(self):
        return {
            'id': self.id,
            'data': self.data,
            'complete': self.is_complete,
            'hidden': self.is_hidden
        }
        
    def complete(self):
        self.is_complete = True
        
    def hide(self):
        self.is_hidden = True

def create_test_element(data: Dict[str, Any]) -> TestElement:
    """Creates a test element with the given data."""
    return TestElement(f"test-{data.get('id', 'default')}", data)
'''

    # Create test functions for app2
    secondary_func = '''
from typing import Dict, Any
import json

class TestElement:
    def __init__(self, element_id: str, data: Any):
        self.id = element_id
        self.data = data
        self.is_complete = False
        self.is_hidden = False
        
    def get_id(self):
        return self.id
        
    def get_card(self):
        return {
            'id': self.id,
            'data': self.data,
            'complete': self.is_complete,
            'hidden': self.is_hidden
        }
        
    def complete(self):
        self.is_complete = True
        
    def hide(self):
        self.is_hidden = True

def process_secondary_data(data: Dict[str, Any]) -> TestElement:
    """Processes data in the secondary app."""
    processed = {
        'id': data.get('id', 'unknown'),
        'source': 'app2',
        'processed': True,
        'original': json.dumps(data)
    }
    return TestElement(f"secondary-{data.get('id', 'default')}", processed)
'''

    # Write functions to their respective apps
    with open(
        os.path.join(app1_dir, 'src', 'app1', 'functions', 'create_test_element.py'), 'w'
    ) as f:
        f.write(test_element_func)

    with open(
        os.path.join(app2_dir, 'src', 'app2', 'functions', 'process_secondary_data.py'), 'w'
    ) as f:
        f.write(secondary_func)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_cross_app_function_discovery(test_apps):
    """Test that functions can be discovered across different apps."""
    paths = get_function_discovery_paths(test_apps)
    assert len(paths) == 2, "Should find functions directories from both apps"

    # Find functions in different apps
    func1 = find_function_in_discovery_paths('create_test_element', paths)
    func2 = find_function_in_discovery_paths('process_secondary_data', paths)

    assert func1 is not None, "Should find create_test_element"
    assert func2 is not None, "Should find process_secondary_data"
    assert 'app1' in func1, "create_test_element should be in app1"
    assert 'app2' in func2, "process_secondary_data should be in app2"


def test_feed_manager_cross_app_execution(test_apps):
    """Test that FeedManager can execute functions from different apps in sequence."""
    manager = FeedManager.get_instance()
    try:
        manager.set_base_path(test_apps)
        mock_feed = MockFeed()
        manager.set_feed(mock_feed)

        # Test data
        test_data = {'id': '123', 'value': 'test'}

        # Process data in app2
        processed_data = manager.create_element('process_secondary_data', test_data)
        assert processed_data is not None
        assert processed_data.get_id().startswith('secondary-')

        # Create element in app1 using processed data
        element = manager.create_element('create_test_element', processed_data.get_card()['data'])
        assert element is not None
        assert element.get_id().startswith('test-')

        # Verify element was added to feed
        assert len(mock_feed.elements) == 2  # Both elements should be in feed
        assert any(e['id'].startswith('secondary-') for e in mock_feed.elements)
        assert any(e['id'].startswith('test-') for e in mock_feed.elements)

    finally:
        manager.cleanup()
        FeedManager._instance = None


def test_missing_app_handling(test_apps):
    """Test that FeedManager handles missing apps gracefully."""
    manager = FeedManager.get_instance()
    try:
        manager.set_base_path(test_apps)
        mock_feed = MockFeed()
        manager.set_feed(mock_feed)

        # Remove app2 to simulate it being uninstalled
        shutil.rmtree(os.path.join(test_apps, 'app2'))

        # Attempt to call function from removed app
        result = manager.create_element('process_secondary_data', {'id': '123'})
        assert result is None, "Should return None for missing function"

        # Verify feed is still empty
        assert len(mock_feed.elements) == 0

        # Verify function is marked as failed
        assert 'process_secondary_data' in manager.failed_functions

    finally:
        manager.cleanup()
        FeedManager._instance = None


def test_concurrent_app_usage(test_apps):
    """Test that multiple apps can use FeedManager concurrently."""
    manager = FeedManager.get_instance()
    try:
        manager.set_base_path(test_apps)
        mock_feed = MockFeed()
        manager.set_feed(mock_feed)

        # Simulate concurrent usage
        test_data = [{'id': str(i), 'value': f'test{i}'} for i in range(5)]

        elements = []
        for data in test_data:
            # Process in app2
            processed = manager.create_element('process_secondary_data', data)
            if processed:
                # Create element in app1
                element = manager.create_element(
                    'create_test_element', processed.get_card()['data']
                )
                if element:
                    elements.append(element)

        # Verify all elements were created
        assert len(elements) == len(test_data), "All elements should be created"
        assert (
            len(mock_feed.elements) == len(test_data) * 2
        ), "Both processed and final elements should be in feed"

        # Verify element IDs
        for i, element in enumerate(elements):
            assert element.get_id() == f"test-{i}", f"Element {i} should have correct ID"

    finally:
        manager.cleanup()
        FeedManager._instance = None
