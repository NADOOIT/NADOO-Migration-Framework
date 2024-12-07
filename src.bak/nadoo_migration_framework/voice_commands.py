"""Voice command functionality for NADOO Migration Framework."""

import speech_recognition as sr
import pyttsx3
import threading
import queue
import json
from pathlib import Path
from typing import Optional, Dict, Any, Callable

class VoiceCommandManager:
    """Manages voice commands and speech synthesis."""
    
    def __init__(self, command_map: Optional[Dict[str, Callable]] = None):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.command_queue = queue.Queue()
        self.is_listening = False
        self.command_map = command_map or {}
        
    def start_listening(self):
        """Start listening for voice commands in a separate thread."""
        self.is_listening = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        
    def stop_listening(self):
        """Stop listening for voice commands."""
        self.is_listening = False
        
    def _listen_loop(self):
        """Continuous loop for listening to voice commands."""
        while self.is_listening:
            try:
                with sr.Microphone() as source:
                    print("Listening for commands...")
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source)
                    
                try:
                    text = self.recognizer.recognize_google(audio)
                    print(f"Recognized: {text}")
                    self.command_queue.put(text)
                    self._process_command(text)
                except sr.UnknownValueError:
                    print("Could not understand audio")
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                    
            except Exception as e:
                print(f"Error in listen loop: {e}")
                
    def _process_command(self, text: str):
        """Process a recognized voice command."""
        # Convert to lowercase for better matching
        text = text.lower()
        
        # Check for exact matches in command map
        if text in self.command_map:
            try:
                self.command_map[text]()
                self.speak(f"Executing command: {text}")
                return
            except Exception as e:
                self.speak(f"Error executing command: {str(e)}")
                return
                
        # Check for partial matches
        for cmd, func in self.command_map.items():
            if cmd.lower() in text:
                try:
                    func()
                    self.speak(f"Executing command: {cmd}")
                    return
                except Exception as e:
                    self.speak(f"Error executing command: {str(e)}")
                    return
                    
        self.speak("Command not recognized")
        
    def speak(self, text: str):
        """Convert text to speech."""
        print(f"Speaking: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
        
    def add_command(self, command: str, callback: Callable):
        """Add a new voice command."""
        self.command_map[command.lower()] = callback
        
    def remove_command(self, command: str):
        """Remove a voice command."""
        self.command_map.pop(command.lower(), None)
        
    def get_next_command(self) -> Optional[str]:
        """Get the next command from the queue."""
        try:
            return self.command_queue.get_nowait()
        except queue.Empty:
            return None
            
    def save_commands(self, file_path: Path):
        """Save command map to a JSON file."""
        with open(file_path, 'w') as f:
            json.dump({k: v.__name__ for k, v in self.command_map.items()}, f, indent=2)
            
    def load_commands(self, file_path: Path):
        """Load command map from a JSON file."""
        with open(file_path, 'r') as f:
            self.command_map = json.load(f)
