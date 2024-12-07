"""NADOO Migration Framework GUI application."""

import toga
import logging
import sys
from pathlib import Path
from ..migrations import MigrationEngine
from .migration_window import MigrationWindow
from .voice_window import VoiceCommandWindow
from toga.style import Pack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('nadoo_migration.log')
    ]
)

logger = logging.getLogger(__name__)

class NADOOMigrationApp(toga.App):
    def __init__(self, project_path: Path = None):
        logger.info("Initializing NADOO Migration Framework")
        super().__init__(
            formal_name='NADOO Migration Framework',
            app_id='it.nadoo.migration-framework',
            app_name='NADOO Migration',
            author='NADOO IT',
            description='NADOO Migration Framework GUI',
            version='0.2.1',
        )
        self.project_path = project_path or Path(".")
        logger.info(f"Project path set to: {self.project_path}")
        
        try:
            logger.info("Initializing Migration Engine")
            self.engine = MigrationEngine(self.project_path)
            self.changes = self.engine.check_migrations()
            logger.info(f"Found {len(self.changes)} pending migrations")
        except Exception as e:
            logger.error(f"Failed to initialize Migration Engine: {str(e)}")
            raise

    def startup(self):
        """Initialize the application."""
        logger.info("Starting up NADOO Migration Framework")
        try:
            # Create main migration window
            logger.info("Creating main migration window")
            self.main_window = MigrationWindow(
                title="NADOO Migration Framework",
                project_path=self.project_path,
                changes=self.changes
            )
            
            # Create voice command window
            logger.info("Initializing voice command window")
            self.voice_window = VoiceCommandWindow(
                title="Voice Commands",
                project_path=self.project_path,
                migration_window=self.main_window
            )
            
            # Add voice command toggle to main window's commands
            voice_cmd = toga.Command(
                self.toggle_voice_window,
                'Voice Control',
                'Toggle voice command interface',
                group=toga.Group.WINDOW,
                section=1
            )
            self.main_window.commands.add(voice_cmd)
            
            # Create main toolbar with voice control
            self.main_window.toolbar.add(voice_cmd)
            
            # Show the main window
            self.main_window.show()
            logger.info("Application startup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during application startup: {str(e)}")
            raise

    def toggle_voice_window(self, widget):
        """Toggle the voice command window."""
        if self.voice_window._impl is None:
            self.voice_window.show()
        else:
            self.voice_window.close()

def main():
    """Main entry point for the application when run through briefcase."""
    return NADOOMigrationApp().main_loop()

def run_migration_gui(project_path: Path):
    """Run the migration GUI application.
    
    Args:
        project_path (Path): Path to the project to migrate
    """
    logger.info(f"Starting NADOO Migration Framework GUI with project path: {project_path}")
    try:
        app = NADOOMigrationApp(project_path=project_path)
        return app.main_loop()
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}")
        raise
