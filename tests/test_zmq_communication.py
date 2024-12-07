import pytest
import zmq
import threading
import time
import json
from src.classes.FeedManager import FeedManager

class MockApp:
    def __init__(self, app_id):
        self.app_id = app_id
        self.context = zmq.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect("tcp://localhost:5556")
        # Subscribe to all messages
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.received_messages = []
        self.running = False
        
    def start_listening(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen)
            self.thread.daemon = True  # Make thread daemon so it doesn't block test exit
            self.thread.start()
            # Give time for connection to establish
            time.sleep(0.1)
        
    def _listen(self):
        while self.running:
            try:
                if self.sub_socket.poll(100) != 0:  # Wait up to 100ms for message
                    message = self.sub_socket.recv_string()
                    self.received_messages.append(json.loads(message))
            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    break  # Context terminated
                print(f"ZMQ Error in {self.app_id}: {e}")
            except Exception as e:
                print(f"Error in {self.app_id}: {e}")
                
    def stop_listening(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        self.sub_socket.close()
        self.context.term()

@pytest.fixture(scope="function")
def feed_manager():
    # Ensure no previous instance exists
    FeedManager._instance = None
    manager = FeedManager.get_instance()
    # Give time for ZMQ socket to bind
    time.sleep(0.1)
    yield manager
    manager.cleanup()
    FeedManager._instance = None

@pytest.fixture(scope="function")
def mock_apps():
    apps = [MockApp(f"app_{i}") for i in range(3)]
    # Start listening before yielding
    for app in apps:
        app.start_listening()
    # Give time for connections to establish
    time.sleep(0.1)
    yield apps
    # Clean up after test
    for app in apps:
        app.stop_listening()

def test_zmq_basic_communication(feed_manager, mock_apps):
    """Test basic ZMQ pub/sub communication between apps."""
    test_message = {
        "action": "create_element",
        "element_id": "test_element",
        "data": {"value": 42}
    }
    
    # Send message through feed manager
    feed_manager.broadcast_message(test_message)
    
    # Give time for message propagation
    time.sleep(0.5)
    
    # Verify all apps received the message
    for app in mock_apps:
        assert len(app.received_messages) > 0, f"App {app.app_id} received no messages"
        assert app.received_messages[0]["element_id"] == "test_element"

def test_zmq_high_frequency_messages(feed_manager, mock_apps):
    """Test handling of high-frequency messages."""
    num_messages = 100
    
    for i in range(num_messages):
        message = {
            "action": "update",
            "element_id": f"element_{i}",
            "data": {"value": i}
        }
        feed_manager.broadcast_message(message)
    
    # Give time for message processing
    time.sleep(2)
    
    # Verify message reception
    for app in mock_apps:
        assert len(app.received_messages) == num_messages

def test_zmq_large_payload(feed_manager, mock_apps):
    """Test handling of large message payloads."""
    large_data = {"key_" + str(i): "x" * 1000 for i in range(100)}
    message = {
        "action": "create_element",
        "element_id": "large_element",
        "data": large_data
    }
    
    feed_manager.broadcast_message(message)
    
    time.sleep(0.5)
    
    for app in mock_apps:
        assert len(app.received_messages) > 0
        received = app.received_messages[0]
        assert received["element_id"] == "large_element"
        assert len(received["data"]) == len(large_data)

def test_zmq_connection_handling(feed_manager):
    """Test connection handling with dynamically joining/leaving apps."""
    # Create app after feed manager is running
    late_app = MockApp("late_app")
    late_app.start_listening()
    
    time.sleep(0.5)
    
    test_message = {
        "action": "create_element",
        "element_id": "late_test",
        "data": {"value": "late"}
    }
    
    feed_manager.broadcast_message(test_message)
    
    time.sleep(0.5)
    
    assert len(late_app.received_messages) > 0
    assert late_app.received_messages[0]["element_id"] == "late_test"
    
    late_app.stop_listening()
