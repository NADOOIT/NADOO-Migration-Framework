"""NADOO Migration Framework Toga GUI Application."""

import os
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from ..migrations.repository_scanner import RepositoryScanner
from ..migrations.dry_run import DryRunManager
from ..version import ProjectVersion

class NADOOMigrationApp(toga.App):
    """Main Toga application for NADOO Migration Framework."""

    def startup(self):
        """Initialize the application."""
        # Main window
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Create main box with padding
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))
        
        # Header
        header_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))
        title = toga.Label(
            'NADOO Migration Framework',
            style=Pack(font_size=20, font_weight='bold', padding=(0, 0, 0, 10))
        )
        scan_button = toga.Button(
            'Scan Repositories',
            on_press=self.scan_repositories,
            style=Pack(padding=(0, 0, 0, 10))
        )
        header_box.add(title)
        header_box.add(scan_button)
        
        # Projects list
        self.projects_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        self.projects_scroll = toga.ScrollContainer(
            content=self.projects_box,
            style=Pack(flex=1)
        )
        
        # Column headers
        headers_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))
        headers_box.add(toga.Label('Project', style=Pack(flex=1, padding=(0, 10, 0, 0))))
        headers_box.add(toga.Label('Status', style=Pack(flex=1, padding=(0, 10, 0, 0))))
        headers_box.add(toga.Label('Actions', style=Pack(flex=1, padding=(0, 10, 0, 0))))
        
        # Add all elements to main box
        main_box.add(header_box)
        main_box.add(headers_box)
        main_box.add(self.projects_scroll)
        
        # Set up main window
        self.main_window.content = main_box
        self.main_window.show()
        
        # Initialize storage
        self.projects = {}

    def scan_repositories(self, widget):
        """Scan for repositories when button is pressed."""
        try:
            # Clear existing projects
            for child in self.projects_box.children:
                self.projects_box.remove(child)
            
            # Scan for repositories
            github_path = os.path.expanduser("~/Documents/GitHub")
            scanner = RepositoryScanner(github_path)
            repos = scanner.scan_repositories()
            
            if not repos:
                self.projects_box.add(
                    toga.Label(
                        'No eligible repositories found',
                        style=Pack(padding=20, font_style='italic')
                    )
                )
                return
            
            # Add each repository to the list
            for repo in repos:
                project = ProjectVersion(
                    project_name=repo['name'],
                    current_version=None  # Will be determined by scanning project
                )
                self.projects[repo['name']] = project
                
                # Create row for project
                row_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))
                
                # Project name
                name_label = toga.Label(
                    project.project_name,
                    style=Pack(flex=1, padding=(0, 10, 0, 0))
                )
                
                # Status
                status_label = toga.Label(
                    project.status,
                    style=Pack(flex=1, padding=(0, 10, 0, 0))
                )
                
                # Migration button (if needed)
                button_box = toga.Box(style=Pack(flex=1, padding=(0, 10, 0, 0)))
                if project.needs_migration:
                    migrate_button = toga.Button(
                        'Migrate',
                        on_press=lambda p=project: self.migrate_project(p)
                    )
                    button_box.add(migrate_button)
                
                row_box.add(name_label)
                row_box.add(status_label)
                row_box.add(button_box)
                
                self.projects_box.add(row_box)
        
        except Exception as e:
            self.main_window.error_dialog(
                'Scan Error',
                f'Failed to scan repositories: {str(e)}'
            )

    def migrate_project(self, project):
        """Handle migration of a project."""
        try:
            # Perform dry run
            dry_run = DryRunManager(project.project_name)
            results = dry_run.dry_run_all([])  # Add migrations here
            
            # Format changes for display
            changes = "\n".join(
                f"- {change.action}: {change.path}"
                for result in results
                for change in result.changes
            )
            
            # Show confirmation dialog
            if self.main_window.question_dialog(
                'Confirm Migration',
                f'The following changes will be made:\n\n{changes}\n\nProceed?'
            ):
                # TODO: Implement actual migration
                self.main_window.info_dialog(
                    'Migration Complete',
                    f'Successfully migrated {project.project_name}'
                )
                
                # Refresh the project list
                self.scan_repositories(None)
        
        except Exception as e:
            self.main_window.error_dialog(
                'Migration Error',
                f'Failed to migrate {project.project_name}: {str(e)}'
            )

def main():
    """Run the Toga application."""
    return NADOOMigrationApp('NADOO Migration Framework', 'it.nadoo.migration-framework')

if __name__ == '__main__':
    main().main_loop()
