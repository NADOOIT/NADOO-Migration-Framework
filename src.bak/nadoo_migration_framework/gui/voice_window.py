"""NADOO Migration Framework Voice Command Window."""

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import asyncio
import logging
from pathlib import Path
from ..voice_commands import VoiceCommandManager

logger = logging.getLogger(__name__)

class VoiceCommandWindow(toga.Window):
    def __init__(self, title: str, project_path: Path, migration_window):
        """Initialize voice command window.
        
        Args:
            title (str): Window title
            project_path (Path): Path to project
            migration_window (MigrationWindow): Reference to main migration window
        """
        logger.info("Initializing Voice Command Window")
        super().__init__(title=title)
        self.project_path = project_path
        self.migration_window = migration_window
        
        try:
            logger.info("Initializing Voice Command Manager")
            self.voice_manager = VoiceCommandManager()
        except Exception as e:
            logger.error(f"Failed to initialize Voice Command Manager: {str(e)}")
            raise
        
        # Create main box
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        
        # Add header
        header = toga.Box(style=Pack(direction=COLUMN, padding=(0, 0, 10, 0)))
        title_label = toga.Label(
            'Voice Command Interface',
            style=Pack(font_size=20, padding=(0, 0, 5, 0))
        )
        subtitle = toga.Label(
            'Say commands to control the migration process',
            style=Pack(font_size=14, padding=(0, 0, 10, 0))
        )
        header.add(title_label)
        header.add(subtitle)
        
        # Add status indicator
        self.status_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))
        self.status_label = toga.Label(
            'Status: Not Listening',
            style=Pack(padding=(0, 5, 0, 0))
        )
        self.status_box.add(self.status_label)
        
        # Add command list
        commands_box = toga.Box(style=Pack(direction=COLUMN, padding=5))
        commands_label = toga.Label(
            'Available Commands:',
            style=Pack(font_size=16, padding=(0, 0, 5, 0))
        )
        commands = [
            "Start migration",
            "Cancel migration",
            "Show status",
            "Create backup",
            "Stop listening"
        ]
        for cmd in commands:
            cmd_label = toga.Label(
                f"• {cmd}",
                style=Pack(padding=(0, 0, 5, 20))
            )
            commands_box.add(cmd_label)
            
        # Add Ollama status
        self.ollama_status = toga.Label(
            'Ollama Status: Checking...',
            style=Pack(padding=(10, 0))
        )
        main_box.add(self.ollama_status)
        
        # Add start/stop button
        self.toggle_button = toga.Button(
            'Start Listening',
            on_press=self.toggle_listening,
            style=Pack(padding=5)
        )
        main_box.add(self.toggle_button)
        
        # Add feedback label
        self.feedback_label = toga.Label(
            'Ready to start voice control. Just speak naturally!',
            style=Pack(font_size=14, padding=(10, 0))
        )
        main_box.add(self.feedback_label)
        
        # Add help text
        help_text = toga.MultilineTextInput(
            readonly=True,
            value=(
                "Voice Control Instructions:\n\n"
                "1. Click 'Enable Voice Control' to start\n"
                "2. Speak naturally about what you want to do\n"
                "3. I'll interpret your request and ask if I understood correctly\n"
                "4. Respond naturally to confirm or correct my understanding\n\n"
                "Example conversations:\n"
                "You: 'I need to move some files from my downloads to my documents folder'\n"
                "AI: 'I think you want to migrate files. Would you like me to help you set that up?'\n"
                "You: 'That would be great, thanks'\n\n"
                "You: 'Could you help me pick where I want to move files from?'\n"
                "AI: 'I think you want to select a source directory. Should I open the directory selector?'\n"
                "You: 'Actually, I want to configure the settings first'\n"
                "AI: 'Okay, I'll open the settings instead'\n"
            ),
            style=Pack(flex=1, padding=(10, 0))
        )
        main_box.add(help_text)
        
        # Add buttons
        button_box = toga.Box(style=Pack(direction=ROW, padding=(10, 0)))
        self.close_button = toga.Button(
            'Close Window',
            on_press=self.close_window,
            style=Pack(padding=(0, 5), width=120)
        )
        button_box.add(self.close_button)
        main_box.add(button_box)
        
        self.content = main_box
        logger.info("Voice Command Window initialized successfully")
        
        # Set up voice commands
        self._setup_voice_commands()
        
    def _setup_voice_commands(self):
        """Set up voice command handlers."""
        self.voice_manager.add_command(
            "start migration",
            lambda: asyncio.create_task(self.migration_window.start_migration(None))
        )
        self.voice_manager.add_command(
            "cancel migration",
            lambda: self.migration_window.cancel_migration(None)
        )
        self.voice_manager.add_command(
            "show status",
            self._show_status
        )
        self.voice_manager.add_command(
            "create backup",
            lambda: asyncio.create_task(self.migration_window._create_backup())
        )
        self.voice_manager.add_command(
            "stop listening",
            self.stop_listening
        )
        
    def _show_status(self):
        """Show current migration status."""
        completed = sum(1 for step in self.migration_window.steps if step.status == "completed")
        total = len(self.migration_window.steps)
        self.voice_manager.speak(f"Migration progress: {completed} of {total} steps completed")
        
    async def check_ollama_status(self):
        """Check if Ollama is running and update status."""
        try:
            status = await self.voice_manager.check_ollama_connection()
            if status:
                self.ollama_status.text = 'Ollama Status: Connected'
                logger.info("Successfully connected to Ollama")
            else:
                self.ollama_status.text = 'Ollama Status: Not Connected'
                logger.warning("Could not connect to Ollama")
        except Exception as e:
            self.ollama_status.text = f'Ollama Status: Error - {str(e)}'
            logger.error(f"Error checking Ollama status: {str(e)}")

    async def toggle_listening(self, widget):
        """Toggle voice command listening."""
        try:
            if self.voice_manager.is_listening:
                logger.info("Stopping voice command listening")
                await self.voice_manager.stop_listening()
                self.toggle_button.text = 'Start Listening'
                self.status_label.text = 'Status: Not Listening'
            else:
                logger.info("Starting voice command listening")
                await self.voice_manager.start_listening()
                self.toggle_button.text = 'Stop Listening'
                self.status_label.text = 'Status: Listening'
        except Exception as e:
            logger.error(f"Error toggling voice listening: {str(e)}")
            self.status_label.text = f'Status: Error - {str(e)}'
            
    def stop_listening(self):
        """Stop voice command listening."""
        self.voice_manager.stop_listening()
        self.status_label.text = "Status: Not Listening"
        self.toggle_button.text = 'Start Listening'
        
    def close_window(self, widget):
        """Close the voice command window."""
        self.stop_listening()
        self.close()
        self._impl = None  # Reset implementation to allow reopening
