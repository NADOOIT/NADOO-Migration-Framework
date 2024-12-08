"""NADOO Migration Framework GUI application."""

import toga
import logging
import sys
from pathlib import Path
from .classes.MigrationEngine import MigrationEngine
from .utils.github_projects import get_list_of_github_projects

from toga.style import Pack
from toga.style.pack import COLUMN

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


    def startup(self):
        """Initialize the application."""
        logger.info("Starting up NADOO Migration Framework")
        try:
            # Create main window
            self.main_window = toga.MainWindow(title="NADOO Migration Framework")

            # Set up layout
            box = toga.Box(style=Pack(direction=COLUMN, padding=10))

            # Get list of GitHub projects
            projects = get_list_of_github_projects()

            # Project selection
            project_label = toga.Label("Select your Project:", style=Pack(padding=(0, 0, 5, 0)))
            box.add(project_label)

            project_selection = toga.Selection(
                items=projects,
                style=Pack(flex=1, padding=(0, 0, 5, 0), width=200, height=30)
            )
            box.add(project_selection)

            # Add buttons
            dry_run_button = toga.Button(
                'Dry Run',
                on_press=lambda widget: self.dry_run(project_selection.value),
                style=Pack(padding=(5, 0, 0, 0))
            )
            box.add(dry_run_button)

            migrate_button = toga.Button(
                'Migrate',
                on_press=lambda widget: self.migrate(project_selection.value),
                style=Pack(padding=(5, 0, 0, 0))
            )
            box.add(migrate_button)

            self.main_window.content = box

            # Show the main window
            self.main_window.show()
            logger.info("Main window setup completed")

        except Exception as e:
            logger.error(f"Error during application startup: {str(e)}")
            raise

    def dry_run(self, project_name):
        logger.info(f"Performing dry run for project: {project_name}")
        # TODO: Implement dry run logic

    def migrate(self, project_name):
        logger.info(f"Migrating project: {project_name}")
        # TODO: Implement migration logic


def main():
    return NADOOMigrationApp()

if __name__ == '__main__':
    main().main_loop()
