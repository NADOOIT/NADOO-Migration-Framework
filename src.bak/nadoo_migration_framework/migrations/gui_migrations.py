"""GUI-related migrations for NADOO Framework."""

from pathlib import Path
import os
import shutil
from typing import List, Dict, Any

class GUIMigration:
    """Migration handler for GUI-related changes."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.gui_dir = project_path / "gui"
        self.templates_dir = self.gui_dir / "templates"
        self.static_dir = self.gui_dir / "static"
        
    def check_needed(self) -> bool:
        """Check if GUI migrations are needed."""
        # Check if GUI directory exists with proper structure
        if not self.gui_dir.exists():
            return True
            
        # Check for required subdirectories
        if not self.templates_dir.exists() or not self.static_dir.exists():
            return True
            
        # Check for essential files
        window_file = self.gui_dir / "window.py"
        app_file = self.gui_dir / "app.py"
        if not window_file.exists() or not app_file.exists():
            return True
            
        return False
        
    def get_changes(self) -> List[str]:
        """Get list of GUI-related changes needed."""
        changes = []
        
        if not self.gui_dir.exists():
            changes.append("Create GUI directory structure")
            
        if not self.templates_dir.exists():
            changes.append("Create GUI templates directory")
            
        if not self.static_dir.exists():
            changes.append("Create GUI static assets directory")
            
        window_file = self.gui_dir / "window.py"
        if not window_file.exists():
            changes.append("Create window management module")
            
        app_file = self.gui_dir / "app.py"
        if not app_file.exists():
            changes.append("Create GUI application module")
            
        return changes
        
    def apply_migrations(self) -> None:
        """Apply GUI-related migrations."""
        # Create directory structure
        self.gui_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.static_dir.mkdir(exist_ok=True)
        
        # Create __init__.py
        init_file = self.gui_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            
        # Create window.py template
        window_file = self.gui_dir / "window.py"
        if not window_file.exists():
            window_content = '''"""Window management for GUI applications."""

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class MainWindow(toga.MainWindow):
    def __init__(self, title, app):
        """Initialize main window.
        
        Args:
            title (str): Window title
            app (toga.App): Parent application
        """
        super().__init__(title=title)
        self.app = app
        
        # Create main box with padding
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        
        # Add header
        header = toga.Box(style=Pack(direction=COLUMN, padding=(0, 0, 10, 0)))
        title_label = toga.Label(
            title,
            style=Pack(font_size=20, padding=(0, 0, 5, 0))
        )
        header.add(title_label)
        
        # Add content area
        content = toga.Box(style=Pack(direction=COLUMN, padding=5))
        
        # Add buttons
        button_box = toga.Box(style=Pack(direction=ROW, padding=(10, 0)))
        
        # Add components to main box
        main_box.add(header)
        main_box.add(content)
        main_box.add(button_box)
        
        self.content = main_box
'''
            window_file.write_text(window_content)
            
        # Create app.py template
        app_file = self.gui_dir / "app.py"
        if not app_file.exists():
            app_content = '''"""GUI application management."""

import toga

class Application(toga.App):
    def __init__(self, formal_name, app_id, app_name, author, description, version):
        """Initialize application.
        
        Args:
            formal_name (str): Formal application name
            app_id (str): Application identifier
            app_name (str): Application name
            author (str): Application author
            description (str): Application description
            version (str): Application version
        """
        super().__init__(
            formal_name=formal_name,
            app_id=app_id,
            app_name=app_name,
            author=author,
            description=description,
            version=version,
        )
        
    def startup(self):
        """Initialize application on startup."""
        from .window import MainWindow
        self.main_window = MainWindow(self.formal_name, self)
        self.main_window.show()

def run_app(**kwargs):
    """Run the GUI application.
    
    Args:
        **kwargs: Application configuration parameters
    
    Returns:
        int: Application exit code
    """
    return Application(**kwargs).main_loop()
'''
            app_file.write_text(app_content)
            
        # Create requirements.txt or update existing one
        requirements_file = self.project_path / "requirements.txt"
        gui_requirements = [
            "toga>=0.4.0",
            "toga-cocoa>=0.4.0; sys_platform == 'darwin'",
            "toga-gtk>=0.4.0; sys_platform == 'linux'",
            "toga-winforms>=0.4.0; sys_platform == 'win32'"
        ]
        
        if requirements_file.exists():
            current_reqs = requirements_file.read_text().splitlines()
            # Add only missing requirements
            new_reqs = [req for req in gui_requirements if req not in current_reqs]
            if new_reqs:
                with requirements_file.open('a') as f:
                    f.write('\n' + '\n'.join(new_reqs))
        else:
            requirements_file.write_text('\n'.join(gui_requirements))
