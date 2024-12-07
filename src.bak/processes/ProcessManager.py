import os
import zmq
import json
import signal
import logging
from typing import Dict, Any
from logging.handlers import RotatingFileHandler

class ProcessManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProcessManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
        
    def __init__(self):
        if self.initialized:
            return
            
        self.logger = self._setup_logging()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.port = self._find_available_port(5555)
        self.socket.bind(f"tcp://*:{self.port}")
        
        self.services = {}
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.initialized = True
        self.logger.info(f"ProcessManager initialized on port {self.port}")
        
    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger('ProcessManager')
        logger.setLevel(logging.INFO)
        
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        handler = RotatingFileHandler(
            os.path.join(log_dir, 'process_manager.log'),
            maxBytes=1024*1024,
            backupCount=5
        )
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    def _find_available_port(self, start_port: int) -> int:
        """Finds an available port starting from start_port."""
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        
        port = start_port
        while port < start_port + 100:
            try:
                socket.bind(f"tcp://*:{port}")
                socket.unbind(f"tcp://*:{port}")
                return port
            except zmq.error.ZMQError:
                port += 1
        
        raise RuntimeError("No available ports found")
        
    def _signal_handler(self, signum, frame):
        """Handles shutdown signals."""
        self.logger.info("Shutdown signal received")
        self.running = False
        
    def start(self):
        """Starts the process manager."""
        self.logger.info("Starting ProcessManager")
        
        while self.running:
            try:
                message = self.socket.recv_json(flags=zmq.NOBLOCK)
                response = self._handle_message(message)
                self.socket.send_json(response)
            except zmq.Again:
                continue
            except Exception as e:
                self.logger.error(f"Error handling message: {str(e)}")
                
        self.logger.info("ProcessManager shutting down")
        self.socket.close()
        self.context.term()
        
    def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handles incoming messages."""
        action = message.get('action')
        
        if action == 'register_service':
            service_name = message.get('service_name')
            port = message.get('port')
            self.services[service_name] = port
            return {'status': 'success', 'message': f'Service {service_name} registered'}
            
        elif action == 'get_service':
            service_name = message.get('service_name')
            port = self.services.get(service_name)
            if port:
                return {'status': 'success', 'port': port}
            return {'status': 'error', 'message': f'Service {service_name} not found'}
            
        elif action == 'shutdown':
            self.running = False
            return {'status': 'success', 'message': 'Shutting down'}
            
        return {'status': 'error', 'message': 'Invalid action'}
