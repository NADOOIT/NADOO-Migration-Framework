"""Voice command manager for the NADOO Migration Framework."""

import pyttsx3
from threading import Thread, Event
import asyncio
import json
import httpx
import pyaudio
import wave
import tempfile
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class VoiceManager:
    def __init__(self, app=None):
        self.engine = pyttsx3.init()
        self.is_listening = False
        self.stop_event = Event()
        self.app = app
        self.listen_thread = None
        self.ollama_url = "http://localhost:11434/api/generate"
        self.whisper_url = "http://localhost:11434/api/audio"
        
        # Audio recording settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 16000
        self.audio = pyaudio.PyAudio()
        
    def speak(self, text):
        """Speak the given text."""
        logger.info(f"Speaking: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
        
    def start_listening(self):
        """Start listening for voice commands."""
        if not self.is_listening:
            logger.info("Starting voice recognition")
            self.is_listening = True
            self.stop_event.clear()
            self.listen_thread = Thread(target=self._listen_loop)
            self.listen_thread.start()
            
    def stop_listening(self):
        """Stop listening for voice commands."""
        if self.is_listening:
            logger.info("Stopping voice recognition")
            self.is_listening = False
            self.stop_event.set()
            if self.listen_thread:
                self.listen_thread.join()
                
    async def _transcribe_audio(self, audio_file: str) -> Optional[str]:
        """Transcribe audio using Ollama's WhisperX."""
        try:
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.whisper_url,
                    files={'file': audio_data},
                    timeout=30.0
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get('text', '')
                else:
                    logger.error(f"Transcription failed: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return None
                
    async def _query_ollama(self, prompt: str, system: str, model: str = "mistral") -> Optional[Dict[str, Any]]:
        """Query Ollama API with the given prompt."""
        try:
            logger.info(f"Querying Ollama with prompt: {prompt}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "system": system,
                        "stream": False
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ollama query failed: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error querying Ollama: {str(e)}")
            return None

    def _record_audio(self) -> Optional[str]:
        """Record audio and save to a temporary file."""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name

            # Open the stream for recording
            stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )

            logger.info("Recording started")
            frames = []
            
            # Record until stop event is set or silence is detected
            while not self.stop_event.is_set():
                data = stream.read(self.CHUNK)
                frames.append(data)
                
                # TODO: Add silence detection here
                
            logger.info("Recording finished")
            
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            
            # Save the recorded data as a WAV file
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b''.join(frames))
            
            return temp_filename
            
        except Exception as e:
            logger.error(f"Error recording audio: {str(e)}")
            return None

    def _listen_loop(self):
        """Main listening loop."""
        while not self.stop_event.is_set():
            try:
                # Record audio
                audio_file = self._record_audio()
                if not audio_file:
                    continue
                
                # Transcribe audio using WhisperX
                text = asyncio.run(self._transcribe_audio(audio_file))
                
                # Clean up temporary file
                try:
                    os.unlink(audio_file)
                except:
                    pass
                
                if text:
                    logger.info(f"Transcribed text: {text}")
                    # Process the command
                    response = asyncio.run(self._process_command(text))
                    if response:
                        self.speak(response)
                
            except Exception as e:
                logger.error(f"Error in listen loop: {str(e)}")
                continue

    async def _process_command(self, text: str) -> Optional[str]:
        """Process the transcribed command."""
        system_prompt = """You are a voice assistant for the NADOO Migration Framework.
        Your task is to help users with migration tasks and respond to their commands.
        Keep responses concise and clear."""
        
        try:
            response = await self._query_ollama(text, system_prompt)
            if response:
                return response.get('response', '')
            return None
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
            return None

    async def check_ollama_connection(self) -> bool:
        """Check if Ollama is running and responding."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:11434/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking Ollama connection: {str(e)}")
            return False
