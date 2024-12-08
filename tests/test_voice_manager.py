"""Tests for the voice manager module."""

import pytest
import asyncio
import tempfile
import wave
import numpy as np
import os
from unittest.mock import Mock, patch, AsyncMock
from nadoo_migration_framework.voice.voice_manager import VoiceManager


@pytest.fixture
def voice_manager():
    """Create a VoiceManager instance for testing."""
    return VoiceManager()


@pytest.fixture
def mock_audio_file():
    """Create a temporary WAV file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        filename = temp_file.name

    # Create a simple sine wave
    duration = 1.0  # seconds
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration))
    samples = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 2 bytes for int16
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())

    yield filename

    # Cleanup
    try:
        os.unlink(filename)
    except:
        pass


@pytest.mark.asyncio
async def test_transcribe_audio_success(voice_manager, mock_audio_file):
    """Test successful audio transcription."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "test transcription"}

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await voice_manager._transcribe_audio(mock_audio_file)

    assert result == "test transcription"
    assert mock_post.called


@pytest.mark.asyncio
async def test_transcribe_audio_failure(voice_manager, mock_audio_file):
    """Test failed audio transcription."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await voice_manager._transcribe_audio(mock_audio_file)

    assert result is None


@pytest.mark.asyncio
async def test_query_ollama_success(voice_manager):
    """Test successful Ollama query."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "test response"}

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await voice_manager._query_ollama("test prompt", "test system")

    assert result == {"response": "test response"}
    assert mock_post.called


@pytest.mark.asyncio
async def test_query_ollama_failure(voice_manager):
    """Test failed Ollama query."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await voice_manager._query_ollama("test prompt", "test system")

    assert result is None


@pytest.mark.asyncio
async def test_process_command_success(voice_manager):
    """Test successful command processing."""
    mock_response = {"response": "processed command"}

    with patch.object(voice_manager, '_query_ollama', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_response
        result = await voice_manager._process_command("test command")

    assert result == "processed command"
    assert mock_query.called


@pytest.mark.asyncio
async def test_process_command_failure(voice_manager):
    """Test failed command processing."""
    with patch.object(voice_manager, '_query_ollama', new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = Exception("Test error")
        result = await voice_manager._process_command("test command")

    assert result is None


def test_start_stop_listening(voice_manager):
    """Test starting and stopping the voice recognition."""
    # Start listening
    voice_manager.start_listening()
    assert voice_manager.is_listening
    assert voice_manager.listen_thread is not None
    assert voice_manager.listen_thread.is_alive()

    # Stop listening
    voice_manager.stop_listening()
    assert not voice_manager.is_listening
    assert not voice_manager.stop_event.is_set()


@pytest.mark.asyncio
async def test_check_ollama_connection_success(voice_manager):
    """Test successful Ollama connection check."""
    mock_response = Mock()
    mock_response.status_code = 200

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await voice_manager.check_ollama_connection()

    assert result is True
    assert mock_get.called


@pytest.mark.asyncio
async def test_check_ollama_connection_failure(voice_manager):
    """Test failed Ollama connection check."""
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Connection failed")
        result = await voice_manager.check_ollama_connection()

    assert result is False


def test_speak(voice_manager):
    """Test text-to-speech functionality."""
    with patch.object(voice_manager.engine, 'say') as mock_say, patch.object(
        voice_manager.engine, 'runAndWait'
    ) as mock_run:
        voice_manager.speak("test message")

    mock_say.assert_called_once_with("test message")
    mock_run.assert_called_once()


def test_record_audio(voice_manager):
    """Test audio recording functionality."""
    mock_stream = Mock()
    mock_stream.read.return_value = b'test_audio_data'

    with patch.object(voice_manager.audio, 'open', return_value=mock_stream), patch(
        'wave.open'
    ) as mock_wave:
        # Set stop event after one iteration
        voice_manager.stop_event.set()
        result = voice_manager._record_audio()

    assert result is not None
    assert os.path.exists(result)

    # Cleanup
    try:
        os.unlink(result)
    except:
        pass
