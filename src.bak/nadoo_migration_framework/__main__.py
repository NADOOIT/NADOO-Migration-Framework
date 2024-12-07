"""NADOO Migration Framework main entry point."""

import sys
from pathlib import Path
from .cli import migrate
from .gui.app import NADOOMigrationApp

def main():
    """
    Main entry point for the application.
    This is used by briefcase when running the app.
    """
    return NADOOMigrationApp().main_loop()

if __name__ == "__main__":
    # Get project path from command line args
    project_path = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    
    # Check if GUI mode is requested
    if "--gui" in sys.argv:
        # Run the GUI application with the project path
        app = NADOOMigrationApp(project_path)
        app.main_loop()
    else:
        # Run the CLI application
        migrate([str(project_path)])
