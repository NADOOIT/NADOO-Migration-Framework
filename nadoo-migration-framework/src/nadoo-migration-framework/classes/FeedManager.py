import os
import sys
import json
import importlib.util
import traceback
import zmq
from typing import Any, Dict, Set, Optional
from nadoo-migration-framework.functions.get_function_discovery_paths import get_function_discovery_paths, find_function_in_discovery_paths

class FeedManager:
    _instance = None
    
    def __init__(self):
        """Initialize the FeedManager."""
        if FeedManager._instance is not None:
            raise Exception("FeedManager is a singleton!")
            
        self.elements = {}
        self.element_history = set()
        self.feed = None  # Will be set by the app
        self.discovery_paths = []
        self.context = zmq.Context()
        self.sync_pub_socket = self.context.socket(zmq.PUB)
        self.sync_pub_socket.bind("tcp://*:5556")
        self.failed_functions = set()  # Track functions that failed to load
        
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of FeedManager."""
        if cls._instance is None:
            cls._instance = FeedManager()
        return cls._instance
        
    def set_feed(self, feed):
        """Set the feed instance."""
        self.feed = feed
        
    def set_base_path(self, base_path: str):
        """Set the base path for function discovery."""
        self.discovery_paths = get_function_discovery_paths(base_path)
        
    def log_and_flush(self, level: str, message: str):
        """Log a message and flush stdout."""
        print(f"{level}: {message}", flush=True)
        
    def process_message(self, message):
        """Process a received message."""
        action = message.get('action')
        element_id = message.get('element_id')
        
        if action == 'create_element':
            try:
                self.create_element(message.get('function_name'), *message.get('args', []))
            except ImportError:
                # Silently ignore missing functions in production
                pass
            except Exception as e:
                self.log_and_flush('ERROR', f"Error creating element: {str(e)}")
        elif action == 'completed':
            self.complete_element(element_id)
        elif action == 'hide':
            self.hide_element(element_id)
        else:
            self.log_and_flush('WARNING', f"Unknown action in message: {action}")
            
    def create_element(self, function_name: str, *args) -> Optional[Any]:
        """
        Create a new element using the specified function.
        
        Args:
            function_name: Name of the function to call
            *args: Arguments to pass to the function
            
        Returns:
            Created element or None if function is not available
        """
        # Skip if function previously failed
        if function_name in self.failed_functions:
            return None
            
        try:
            # Find the function module
            function_file = find_function_in_discovery_paths(function_name, self.discovery_paths)
            if not function_file:
                self.failed_functions.add(function_name)
                raise ImportError(f"Could not find function {function_name} in discovery paths")
                
            # Import the function
            spec = importlib.util.spec_from_file_location(function_name, function_file)
            if not spec or not spec.loader:
                self.failed_functions.add(function_name)
                raise ImportError(f"Could not load spec for {function_name}")
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[function_name] = module
            spec.loader.exec_module(module)
            
            # Get and call the function
            function = getattr(module, function_name)
            element = function(*args)
            
            # Add to feed if not already present
            element_id = element.get_id()
            if element_id not in self.element_history:
                self.elements[element_id] = element
                self.element_history.add(element_id)
                if self.feed:
                    self.feed.add(element.get_card())
                    
            return element
            
        except ImportError as e:
            self.log_and_flush('WARNING', f"Function not available: {str(e)}")
            return None
        except Exception as e:
            self.log_and_flush('ERROR', f"Error creating element: {str(e)}")
            self.log_and_flush('ERROR', traceback.format_exc())
            return None
            
    def complete_element(self, element_id: str):
        """Mark an element as completed."""
        if element_id in self.elements:
            element = self.elements[element_id]
            element.complete()
            if self.feed:
                self.feed.update(element.get_card())
                
    def hide_element(self, element_id: str):
        """Hide an element from the feed."""
        if element_id in self.elements:
            element = self.elements[element_id]
            element.hide()
            if self.feed:
                self.feed.remove(element.get_card())
                
    def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all listeners."""
        try:
            self.sync_pub_socket.send_json(message)
        except Exception as e:
            self.log_and_flush('ERROR', f"Error broadcasting message: {str(e)}")
            
    def cleanup(self):
        """Clean up resources."""
        self.failed_functions.clear()
        if hasattr(self, 'sync_pub_socket'):
            self.sync_pub_socket.close()
            del self.sync_pub_socket
        if hasattr(self, 'context'):
            self.context.term()
            del self.context
        FeedManager._instance = None
        
    def __del__(self):
        """Ensure cleanup on deletion."""
        self.cleanup()

    def reset_failed_functions(self):
        """Reset the list of failed functions, allowing retry."""
        self.failed_functions.clear()
