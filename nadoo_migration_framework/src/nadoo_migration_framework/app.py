"""NADOO Migration Framework GUI application."""

import toga
import logging
import sys
from pathlib import Path
from .classes.MigrationEngine import MigrationEngine

from toga.style import Pack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('nadoo_migration.log')],
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
            # Create main window
            self.main_window = toga.MainWindow(title="NADOO Migration Framework")

            # Set up layout
            box = toga.Box()
            self.main_window.content = box

            # Show the main window
            self.main_window.show()
            logger.info("Main window setup completed")

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
    return NADOOMigrationApp()

if __name__ == '__main__':
    main().main_loop()
